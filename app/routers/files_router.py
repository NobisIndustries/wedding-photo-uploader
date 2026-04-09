from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from app.auth import require_session
from app.database import get_db
from app import config

router = APIRouter()


async def _get_upload(file_id: str):
    db = await get_db()
    cursor = await db.execute("SELECT * FROM uploads WHERE id = ?", (file_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    return row


@router.get("/{file_id}/thumbnail")
async def get_thumbnail(file_id: str, session_id: str = Depends(require_session)):
    await _get_upload(file_id)
    thumb_path = config.THUMBNAILS_DIR / f"{file_id}_thumb.jpg"
    if not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not ready")
    return FileResponse(str(thumb_path), media_type="image/jpeg")


@router.get("/{file_id}/original")
async def get_original(file_id: str, session_id: str = Depends(require_session)):
    row = await _get_upload(file_id)
    ext = row["file_extension"]
    file_path = config.UPLOADS_DIR / f"{file_id}.{ext}" if ext else config.UPLOADS_DIR / file_id
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(
        str(file_path),
        media_type=row["mime_type"],
        filename=row["original_filename"],
    )


@router.delete("/{file_id}")
async def delete_file(file_id: str, session_id: str = Depends(require_session)):
    row = await _get_upload(file_id)
    if row["session_id"] != session_id:
        raise HTTPException(status_code=403, detail="You can only delete your own uploads")

    ext = row["file_extension"]
    file_path = config.UPLOADS_DIR / (f"{file_id}.{ext}" if ext else file_id)
    thumb_path = config.THUMBNAILS_DIR / f"{file_id}_thumb.jpg"

    if file_path.exists():
        file_path.unlink()
    if thumb_path.exists():
        thumb_path.unlink()

    db = await get_db()
    await db.execute("DELETE FROM uploads WHERE id = ?", (file_id,))
    await db.commit()

    return {"deleted": True}
