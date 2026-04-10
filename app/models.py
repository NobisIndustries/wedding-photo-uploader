from pydantic import BaseModel


class PinRequest(BaseModel):
    pin: str


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
    thumbnail_url: str
    preview_url: str
    file_url: str
    thumbnail_ready: bool


class GalleryResponse(BaseModel):
    items: list[UploadItem]
    total: int
    page: int
    per_page: int
