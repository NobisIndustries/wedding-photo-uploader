import uuid
import asyncio
from pathlib import Path
from typing import Callable

from fastapi import Depends, Request, HTTPException, APIRouter
from tuspyserver import create_tus_router

from app import config
from app.auth import require_session
from app.database import get_db
from app.services.thumbnail import generate_assets


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

        file_id = uuid.uuid4().hex
        new_filename = f"{file_id}.{ext}" if ext else file_id
        new_path = config.UPLOADS_DIR / new_filename

        src = Path(file_path)
        src.rename(new_path)

        file_size = new_path.stat().st_size

        db = await get_db()
        await db.execute(
            """INSERT INTO uploads (id, session_id, original_filename, mime_type, file_extension, file_size)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (file_id, session_id, original_filename, mime_type, ext, file_size),
        )
        await db.commit()

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
