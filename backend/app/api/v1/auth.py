from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...schemas.user import UserResponse
from ...models.user import User
from ..deps import get_current_user

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get current authenticated user information."""
    return UserResponse.from_orm(current_user)

@router.post("/refresh")
async def refresh_token(
    current_user: User = Depends(get_current_user),
):
    """Refresh user session (handled by Clerk)."""
    return {"message": "Token refreshed successfully", "user_id": current_user.id}