from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any


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


class FileInfoResponse(BaseModel):
    """Detailed file information including type-specific metadata"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    filename: str
    file_type: str  # 'image', 'pdf', 'unknown'
    mime_type: str
    file_size: int
    upload_timestamp: datetime
    analysis_ready: bool
    pages: int  # Number of pages (1 for images)
    metadata: Optional[Dict[str, Any]] = None
    supported_operations: list[str] = []