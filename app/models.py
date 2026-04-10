from pydantic import BaseModel


class PinRequest(BaseModel):
    pin: str
    name: str | None = None


class AuthStatus(BaseModel):
    authenticated: bool
    is_admin: bool = False


class UploadItem(BaseModel):
    id: str
    original_filename: str
    mime_type: str
    file_extension: str
    file_size: int
    created_at: str
    is_owner: bool
    uploader_name: str | None = None
    thumbnail_url: str
    preview_url: str
    file_url: str
    thumbnail_ready: bool


class GalleryResponse(BaseModel):
    items: list[UploadItem]
    total: int
    page: int
    per_page: int
