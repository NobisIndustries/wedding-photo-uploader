import uuid
from fastapi import Request, HTTPException
from app.database import get_db


async def get_session_id(request: Request) -> str | None:
    return request.cookies.get("session_id")


async def require_session(request: Request) -> str:
    session_id = await get_session_id(request)
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    db = await get_db()
    cursor = await db.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid session")
    return session_id


async def create_session() -> str:
    session_id = uuid.uuid4().hex
    db = await get_db()
    await db.execute("INSERT INTO sessions (id) VALUES (?)", (session_id,))
    await db.commit()
    return session_id
