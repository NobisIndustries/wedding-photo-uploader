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


@app.on_event("startup")
async def startup():
    config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    config.THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
    config.PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    await init_db()


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")
