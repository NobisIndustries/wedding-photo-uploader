import subprocess
from pathlib import Path

from PIL import Image

from app import config

THUMB_SIZE = (400, 400)


def generate_thumbnail(file_path: str, file_id: str, ext: str):
    thumb_path = config.THUMBNAILS_DIR / f"{file_id}_thumb.jpg"

    try:
        if ext in config.IMAGE_EXTENSIONS:
            _generate_image_thumbnail(file_path, thumb_path)
        elif ext in config.VIDEO_EXTENSIONS:
            _generate_video_thumbnail(file_path, thumb_path)
    except Exception as e:
        print(f"Thumbnail generation failed for {file_id}: {e}")


def _generate_image_thumbnail(file_path: str, thumb_path: Path):
    if file_path.lower().endswith((".heic", ".heif")):
        import pillow_heif
        pillow_heif.register_heif_opener()

    img = Image.open(file_path)

    # Auto-rotate based on EXIF
    from PIL import ImageOps
    img = ImageOps.exif_transpose(img)

    img.thumbnail(THUMB_SIZE)
    img = img.convert("RGB")
    img.save(str(thumb_path), "JPEG", quality=80)


def _generate_video_thumbnail(file_path: str, thumb_path: Path):
    subprocess.run(
        [
            "ffmpeg", "-i", file_path,
            "-ss", "00:00:01",
            "-vframes", "1",
            "-vf", f"scale={THUMB_SIZE[0]}:-1",
            "-y",
            str(thumb_path),
        ],
        capture_output=True,
        timeout=30,
    )
