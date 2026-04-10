from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from app.auth import require_session, require_admin, is_admin_session
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


def _upload_path(row) -> Path:
    ext = row["file_extension"]
    return config.UPLOADS_DIR / (f"{row['id']}.{ext}" if ext else row["id"])


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
    file_path = _upload_path(row)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(
        str(file_path),
        media_type=row["mime_type"],
        filename=row["original_filename"],
    )


@router.get("/{file_id}/download")
async def download_original(file_id: str, session_id: str = Depends(require_admin)):
    """Force-download variant of /original — admin-only lightbox download button."""
    row = await _get_upload(file_id)
    file_path = _upload_path(row)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(
        str(file_path),
        media_type="application/octet-stream",
        filename=row["original_filename"],
        headers={
            "Content-Disposition": f'attachment; filename="{row["original_filename"]}"'
        },
    )


@router.delete("/{file_id}")
async def delete_file(file_id: str, session_id: str = Depends(require_session)):
    row = await _get_upload(file_id)
    admin = await is_admin_session(session_id)
    if not admin and row["session_id"] != session_id:
        raise HTTPException(status_code=403, detail="You can only delete your own uploads")

    file_path = _upload_path(row)
    thumb_path = config.THUMBNAILS_DIR / f"{file_id}_thumb.jpg"

    if file_path.exists():
        file_path.unlink()
    if thumb_path.exists():
        thumb_path.unlink()

    db = await get_db()
    await db.execute("DELETE FROM uploads WHERE id = ?", (file_id,))
    await db.commit()

    return {"deleted": True}


@router.get("/download-all")
async def download_all(session_id: str = Depends(require_admin)):
    """Stream a ZIP of every uploaded file. Admin only.

    Uses zipstream-ng with STORED (no compression) so memory usage stays flat
    regardless of archive size — important on the N100 mini PC.
    """
    from zipfile import ZIP_STORED

    from zipstream import ZipStream

    db = await get_db()
    cursor = await db.execute(
        "SELECT id, original_filename, file_extension FROM uploads ORDER BY created_at"
    )
    rows = await cursor.fetchall()

    zs = ZipStream(compress_type=ZIP_STORED, sized=True)

    used: set[str] = set()
    for row in rows:
        ext = row["file_extension"]
        disk_path = config.UPLOADS_DIR / (f"{row['id']}.{ext}" if ext else row["id"])
        if not disk_path.exists():
            continue

        # Deduplicate collisions in original filenames within the archive
        base = row["original_filename"] or (f"{row['id']}.{ext}" if ext else row["id"])
        arcname = base
        counter = 1
        while arcname in used:
            counter += 1
            stem, dot, tail = base.rpartition(".")
            arcname = f"{stem} ({counter}).{tail}" if dot else f"{base} ({counter})"
        used.add(arcname)

        zs.add_path(str(disk_path), arcname=arcname)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"wedding-photos-{timestamp}.zip"

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Length": str(len(zs)),
    }
    return StreamingResponse(zs, media_type="application/zip", headers=headers)
