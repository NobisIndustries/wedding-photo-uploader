from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.models import PinRequest, AuthStatus
from app.config import UPLOAD_PIN, ADMIN_PIN
from app.auth import get_session_id, create_session, _fetch_session

router = APIRouter()


@router.post("/verify-pin")
async def verify_pin(body: PinRequest):
    if body.pin == ADMIN_PIN:
        is_admin = True
    elif body.pin == UPLOAD_PIN:
        is_admin = False
    else:
        return JSONResponse(status_code=401, content={"detail": "Invalid PIN"})

    session_id = await create_session(is_admin=is_admin)
    response = JSONResponse(content={"authenticated": True, "is_admin": is_admin})
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
    row = await _fetch_session(session_id)
    if not row:
        return AuthStatus(authenticated=False)
    return AuthStatus(authenticated=True, is_admin=bool(row["is_admin"]))
