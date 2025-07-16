from pydantic import BaseModel, ConfigDict
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
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    s3_key: str
    s3_url: str
    upload_timestamp: datetime


class FileUploadResponse(BaseModel):
    file_id: str
    filename: Optional[str] = None
    s3_url: Optional[str] = None
    upload_timestamp: Optional[datetime] = None
    message: str = "File uploaded successfully"


class FileListResponse(BaseModel):
    files: list[FileResponse]
    total: int
    page: int
    per_page: int