from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import List, Optional


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    id: str  # Clerk user ID


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    created_at: datetime
    updated_at: datetime


class UserWithFiles(UserResponse):
    model_config = ConfigDict(from_attributes=True)
    
    files: List["FileResponse"] = []


# Forward reference for circular import
from .file import FileResponse
UserWithFiles.model_rebuild()