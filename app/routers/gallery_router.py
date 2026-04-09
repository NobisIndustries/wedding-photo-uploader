from fastapi import APIRouter, Depends, Query
from app.auth import require_session
from app.database import get_db
from app.models import UploadItem, GalleryResponse

router = APIRouter()


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
        "SELECT * FROM uploads ORDER BY created_at DESC LIMIT ? OFFSET ?",
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
            thumbnail_url=f"/api/files/{row['id']}/thumbnail",
            file_url=f"/api/files/{row['id']}/original",
        )
        for row in rows
    ]

    return GalleryResponse(items=items, total=total, page=page, per_page=per_page)
