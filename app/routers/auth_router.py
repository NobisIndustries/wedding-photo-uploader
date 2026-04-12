import time
from asyncio import Lock
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.models import PinRequest, AuthStatus
from app.config import UPLOAD_PIN, ADMIN_PIN
from app.auth import get_session_id, create_session, _fetch_session

router = APIRouter()

_PIN_RATE_LIMIT_SECONDS = 1.0
_PIN_CLEANUP_INTERVAL_SECONDS = 60.0
_last_pin_attempt: dict[str, float] = {}
_pin_attempt_lock = Lock()
_last_cleanup = 0.0


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/verify-pin")
async def verify_pin(body: PinRequest, request: Request):
    ip = _client_ip(request)
    now = time.monotonic()
    global _last_cleanup
    async with _pin_attempt_lock:
        if now - _last_cleanup > _PIN_CLEANUP_INTERVAL_SECONDS:
            cutoff = now - _PIN_RATE_LIMIT_SECONDS
            for stale_ip in [k for k, v in _last_pin_attempt.items() if v < cutoff]:
                del _last_pin_attempt[stale_ip]
            _last_cleanup = now

        last = _last_pin_attempt.get(ip, 0.0)
        if now - last < _PIN_RATE_LIMIT_SECONDS:
            retry_after = _PIN_RATE_LIMIT_SECONDS - (now - last)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many attempts, slow down."},
                headers={"Retry-After": f"{retry_after:.1f}"},
            )
        _last_pin_attempt[ip] = now

    if body.pin == ADMIN_PIN:
        is_admin = True
    elif body.pin == UPLOAD_PIN:
        is_admin = False
    else:
        return JSONResponse(status_code=401, content={"detail": "Invalid PIN"})

    guest_name = (body.name or "").strip()[:50] or None
    session_id = await create_session(is_admin=is_admin, guest_name=guest_name)
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


@router.post("/logout")
async def logout(request: Request):
    response = JSONResponse(content={"ok": True})
    response.delete_cookie(key="session_id", path="/")
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
