import uuid
import shutil
import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Callable

from fastapi import Depends, Request, HTTPException, APIRouter
from tuspyserver import create_tus_router

from app import config
from app.auth import require_session, is_admin_session
from app.database import get_db
from app.services.thumbnail import generate_assets

logger = logging.getLogger(__name__)


def _compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _get_extension(filename: str) -> str:
    if "." in filename:
        return filename.rsplit(".", 1)[1].lower()
    return ""


def pre_create_hook(metadata: dict, upload_info: dict):
    filename = metadata.get("filename", "")
    filetype = metadata.get("filetype", "")

    ext = _get_extension(filename)
    if ext not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type .{ext} not allowed")

    if not any(filetype.startswith(prefix) for prefix in config.ALLOWED_MIME_PREFIXES):
        raise HTTPException(status_code=400, detail=f"MIME type {filetype} not allowed")

    size = upload_info.get("size")
    if size and size > config.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large")


def _make_upload_complete_dep(
    request: Request,
    session_id: str = Depends(require_session),
) -> Callable[[str, dict], None]:
    async def handler(file_path: str, metadata: dict):
        original_filename = metadata.get("filename", "unknown")
        mime_type = metadata.get("filetype", "application/octet-stream")
        ext = _get_extension(original_filename)

        # Admin uploads are official unless explicitly opted out via metadata
        is_official = 0
        admin = await is_admin_session(session_id)
        if admin:
            official_meta = metadata.get("official", "1")
            is_official = 0 if official_meta == "0" else 1

        # Compute hash before moving to detect duplicates
        src = Path(file_path)
        file_hash = await asyncio.get_event_loop().run_in_executor(
            None, _compute_file_hash, str(src)
        )

        # Check for duplicate
        db = await get_db()
        cursor = await db.execute(
            "SELECT id FROM uploads WHERE file_hash = ?", (file_hash,)
        )
        existing = await cursor.fetchone()
        if existing:
            # Duplicate — remove the uploaded temp file and skip
            try:
                src.unlink()
            except Exception:
                pass
            logger.info("Duplicate upload skipped (hash %s matches %s)", file_hash, existing["id"])
            return

        file_id = uuid.uuid4().hex
        new_filename = f"{file_id}.{ext}" if ext else file_id
        new_path = config.UPLOADS_DIR / new_filename

        try:
            # shutil.move works across filesystems unlike Path.rename
            shutil.move(str(src), str(new_path))
        except Exception:
            logger.exception("Failed to move uploaded file %s -> %s", src, new_path)
            raise

        file_size = new_path.stat().st_size

        try:
            await db.execute(
                """INSERT INTO uploads (id, session_id, original_filename, mime_type, file_extension, file_size, file_hash, is_official)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (file_id, session_id, original_filename, mime_type, ext, file_size, file_hash, is_official),
            )
            await db.commit()
        except Exception:
            logger.exception(
                "DB insert failed for %s — file preserved at %s for recovery",
                file_id, new_path,
            )
            raise

        asyncio.get_event_loop().run_in_executor(
            None, generate_assets, str(new_path), file_id, ext
        )

    return handler


def create_upload_router() -> APIRouter:
    return create_tus_router(
        prefix="files",
        files_dir=str(config.UPLOADS_DIR),
        max_size=config.MAX_UPLOAD_SIZE,
        pre_create_hook=pre_create_hook,
        upload_complete_dep=_make_upload_complete_dep,
    )
