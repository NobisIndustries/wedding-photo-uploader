import uuid
from fastapi import Request, HTTPException
from app.database import get_db


async def get_session_id(request: Request) -> str | None:
    return request.cookies.get("session_id")


async def _fetch_session(session_id: str):
    db = await get_db()
    cursor = await db.execute(
        "SELECT id, is_admin FROM sessions WHERE id = ?", (session_id,)
    )
    return await cursor.fetchone()


async def require_session(request: Request) -> str:
    session_id = await get_session_id(request)
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    row = await _fetch_session(session_id)
    if not row:
        raise HTTPException(status_code=401, detail="Invalid session")
    return session_id


async def require_admin(request: Request) -> str:
    session_id = await get_session_id(request)
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    row = await _fetch_session(session_id)
    if not row:
        raise HTTPException(status_code=401, detail="Invalid session")
    if not row["is_admin"]:
        raise HTTPException(status_code=403, detail="Admin only")
    return session_id


async def is_admin_session(session_id: str | None) -> bool:
    if not session_id:
        return False
    row = await _fetch_session(session_id)
    return bool(row and row["is_admin"])


async def create_session(is_admin: bool = False) -> str:
    session_id = uuid.uuid4().hex
    db = await get_db()
    await db.execute(
        "INSERT INTO sessions (id, is_admin) VALUES (?, ?)",
        (session_id, 1 if is_admin else 0),
    )
    await db.commit()
    return session_id
