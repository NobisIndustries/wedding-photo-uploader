from fastapi import APIRouter, Depends, Query
from app.auth import require_session
from app.database import get_db
from app.models import UploadItem, GalleryResponse
from app import config

router = APIRouter()


def _thumb_ready(file_id: str) -> bool:
    return (config.THUMBNAILS_DIR / f"{file_id}_thumb.jpg").exists()


@router.get("", response_model=GalleryResponse)
async def get_gallery(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    session_id: str = Depends(require_session),
):
    db = await get_db()
    offset = (page - 1) * per_page

    cursor = await db.execute("SELECT COUNT(*) FROM uploads")
    row = await cursor.fetchone()
    total = row[0]

    cursor = await db.execute(
        """SELECT uploads.*, sessions.guest_name AS uploader_name
           FROM uploads LEFT JOIN sessions ON uploads.session_id = sessions.id
           ORDER BY uploads.created_at DESC LIMIT ? OFFSET ?""",
        (per_page, offset),
    )
    rows = await cursor.fetchall()

    items = [
        UploadItem(
            id=row["id"],
            original_filename=row["original_filename"],
            mime_type=row["mime_type"],
            file_extension=row["file_extension"],
            file_size=row["file_size"],
            created_at=row["created_at"],
            is_owner=row["session_id"] == session_id,
            uploader_name=row["uploader_name"],
            thumbnail_url=f"/api/files/{row['id']}/thumbnail",
            preview_url=f"/api/files/{row['id']}/preview",
            file_url=f"/api/files/{row['id']}/original",
            thumbnail_ready=_thumb_ready(row["id"]),
        )
        for row in rows
    ]

    return GalleryResponse(items=items, total=total, page=page, per_page=per_page)


@router.post("/thumbnail-status")
async def thumbnail_status(
    ids: list[str],
    session_id: str = Depends(require_session),
):
    """Batch check which of the given file IDs have thumbnails ready."""
    return {file_id: _thumb_ready(file_id) for file_id in ids}
