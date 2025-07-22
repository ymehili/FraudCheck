from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .file import FileResponse


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


# Forward reference for circular import - moved to end of file
from .file import FileResponse  # type: ignore
UserWithFiles.model_rebuild()