import os
import uuid
from pathlib import Path


UPLOAD_PIN: str = os.environ.get("UPLOAD_PIN", "1234")
ADMIN_PIN: str = os.environ.get("ADMIN_PIN", "admin")
MAX_UPLOAD_SIZE: int = int(os.environ.get("MAX_UPLOAD_SIZE", 2_147_483_648))
DATA_DIR: Path = Path(os.environ.get("DATA_DIR", "/data"))
SESSION_SECRET: str = os.environ.get("SESSION_SECRET", uuid.uuid4().hex)

UPLOADS_DIR: Path = DATA_DIR / "uploads"
THUMBNAILS_DIR: Path = DATA_DIR / "thumbnails"
PREVIEWS_DIR: Path = DATA_DIR / "previews"
DB_PATH: Path = DATA_DIR / "metadata.db"

ALLOWED_EXTENSIONS: set[str] = {
    "jpg", "jpeg", "png", "gif", "heic", "heif", "webp",
    "mp4", "mov", "avi", "mkv", "webm",
}

ALLOWED_MIME_PREFIXES: set[str] = {"image/", "video/"}

IMAGE_EXTENSIONS: set[str] = {"jpg", "jpeg", "png", "gif", "heic", "heif", "webp"}
VIDEO_EXTENSIONS: set[str] = {"mp4", "mov", "avi", "mkv", "webm"}
