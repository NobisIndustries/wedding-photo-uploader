import subprocess
from pathlib import Path

from PIL import Image, ImageOps

from app import config

THUMB_SIZE = (400, 400)
PREVIEW_MAX = 1600  # longest edge for image previews


def generate_assets(file_path: str, file_id: str, ext: str):
    """Generate the grid thumbnail and (for images) the display-sized preview."""
    try:
        if ext in config.IMAGE_EXTENSIONS:
            _generate_image_thumbnail(file_path, _thumb_path(file_id))
            _generate_image_preview(file_path, _preview_path(file_id, "jpg"))
        elif ext in config.VIDEO_EXTENSIONS:
            _generate_video_thumbnail(file_path, _thumb_path(file_id))
    except Exception as e:
        print(f"Asset generation failed for {file_id}: {e}")


def _thumb_path(file_id: str) -> Path:
    return config.THUMBNAILS_DIR / f"{file_id}_thumb.jpg"


def _preview_path(file_id: str, ext: str) -> Path:
    return config.PREVIEWS_DIR / f"{file_id}_preview.{ext}"


def _open_image(file_path: str) -> Image.Image:
    if file_path.lower().endswith((".heic", ".heif")):
        import pillow_heif
        pillow_heif.register_heif_opener()
    img = Image.open(file_path)
    return ImageOps.exif_transpose(img)


def _generate_image_thumbnail(file_path: str, thumb_path: Path):
    img = _open_image(file_path)
    img.thumbnail(THUMB_SIZE)
    img = img.convert("RGB")
    img.save(str(thumb_path), "JPEG", quality=80)


def _generate_image_preview(file_path: str, preview_path: Path):
    img = _open_image(file_path)
    # Only downscale — never upscale small images
    if max(img.size) > PREVIEW_MAX:
        img.thumbnail((PREVIEW_MAX, PREVIEW_MAX))
    img = img.convert("RGB")
    img.save(str(preview_path), "JPEG", quality=85, optimize=True, progressive=True)


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


