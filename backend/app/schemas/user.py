from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    id: str  # Clerk user ID


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None


class UserResponse(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserWithFiles(UserResponse):
    files: List["FileResponse"] = []

    class Config:
        from_attributes = True


# Forward reference for circular import
from .file import FileResponse
UserWithFiles.model_rebuild()