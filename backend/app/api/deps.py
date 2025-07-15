from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from ..database import get_db
from ..models.user import User
from ..core.security import verify_clerk_token


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency to get current authenticated user from Clerk JWT token.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.replace("Bearer ", "")
    
    try:
        user_data = await verify_clerk_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get or create user in our database
    user = await get_or_create_user(db, user_data)
    return user


async def get_or_create_user(db: AsyncSession, user_data: dict) -> User:
    """
    Get user from database or create if doesn't exist.
    """
    user_id = user_data.get("user_id")
    email = user_data.get("email")
    
    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user data from token",
        )
    
    # Check if user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        # Create new user
        user = User(id=user_id, email=email)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    return user


async def get_db_session() -> AsyncSession:
    """
    Dependency to get database session.
    """
    async with get_db() as session:
        yield session