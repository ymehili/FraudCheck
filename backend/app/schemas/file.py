from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class FileBase(BaseModel):
    filename: str
    mime_type: str
    file_size: int


class FileCreate(FileBase):
    user_id: str
    s3_key: str
    s3_url: str


class FileUpdate(BaseModel):
    filename: Optional[str] = None


class FileResponse(FileBase):
    id: str
    user_id: str
    s3_key: str
    s3_url: str
    upload_timestamp: datetime

    class Config:
        from_attributes = True


class FileUploadResponse(BaseModel):
    file_id: str
    s3_url: str
    upload_timestamp: datetime
    message: str = "File uploaded successfully"


class FileListResponse(BaseModel):
    files: list[FileResponse]
    total: int
    page: int
    per_page: int