import asyncio
import hashlib
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app import config
from app.database import init_db
from app.routers.auth_router import router as auth_router
from app.routers.gallery_router import router as gallery_router
from app.routers.files_router import router as files_router
from app.services.upload_handler import create_upload_router

logger = logging.getLogger(__name__)

app = FastAPI(title="Wedding Photo Uploader")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "Location", "Upload-Offset", "Tus-Resumable",
        "Tus-Version", "Tus-Extension", "Tus-Max-Size",
        "Upload-Expires", "Upload-Length",
    ],
)

# Register routers
app.include_router(auth_router, prefix="/api/auth")
app.include_router(gallery_router, prefix="/api/gallery")
app.include_router(files_router, prefix="/api/files")
app.include_router(create_upload_router(), prefix="/api/uploads")

# Static files and index
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _compute_file_hash(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


async def _backfill_hashes():
    """Compute hashes for any existing uploads that don't have one yet."""
    from app.database import get_db

    db = await get_db()
    cursor = await db.execute(
        "SELECT id, file_extension FROM uploads WHERE file_hash IS NULL"
    )
    rows = await cursor.fetchall()
    if not rows:
        return

    logger.info("Backfilling file hashes for %d uploads…", len(rows))
    loop = asyncio.get_event_loop()
    for row in rows:
        ext = row["file_extension"]
        disk_path = config.UPLOADS_DIR / (f"{row['id']}.{ext}" if ext else row["id"])
        if not disk_path.exists():
            continue
        file_hash = await loop.run_in_executor(None, _compute_file_hash, str(disk_path))
        await db.execute(
            "UPDATE uploads SET file_hash = ? WHERE id = ?", (file_hash, row["id"])
        )
    await db.commit()
    logger.info("Hash backfill complete.")


@app.on_event("startup")
async def startup():
    config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    config.THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
    config.PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    await init_db()
    await _backfill_hashes()


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")
