from fastapi import APIRouter, Response, Request
from fastapi.responses import JSONResponse
from app.models import PinRequest, AuthStatus
from app.config import UPLOAD_PIN
from app.auth import get_session_id, create_session
from app.database import get_db

router = APIRouter()


@router.post("/verify-pin")
async def verify_pin(body: PinRequest, response: Response):
    if body.pin != UPLOAD_PIN:
        return JSONResponse(status_code=401, content={"detail": "Invalid PIN"})

    session_id = await create_session()
    response = JSONResponse(content={"authenticated": True})
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=7 * 24 * 3600,
        path="/",
    )
    return response


@router.get("/status", response_model=AuthStatus)
async def auth_status(request: Request):
    session_id = await get_session_id(request)
    if not session_id:
        return AuthStatus(authenticated=False)
    db = await get_db()
    cursor = await db.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
    row = await cursor.fetchone()
    return AuthStatus(authenticated=row is not None)
