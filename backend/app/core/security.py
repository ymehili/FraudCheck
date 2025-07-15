from fastapi import HTTPException, status
from jose import JWTError, jwt
from typing import Dict, Any
import httpx
from ..core.config import settings


async def verify_clerk_token(token: str) -> Dict[str, Any]:
    """
    Verify Clerk JWT token and return user data.
    """
    try:
        # Get Clerk's public key for JWT verification
        jwks_url = f"https://clerk.{settings.CLERK_PUBLISHABLE_KEY.split('_')[1]}.lcl.dev/.well-known/jwks.json"
        
        # For development, we'll use a simplified approach
        # In production, you should properly validate the JWT with JWKS
        
        # Decode without verification for development
        # NOTE: In production, you must properly verify the JWT
        unverified_payload = jwt.get_unverified_claims(token)
        
        # Basic validation
        if not unverified_payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
            )
        
        # Extract user information
        user_data = {
            "user_id": unverified_payload.get("sub"),
            "email": unverified_payload.get("email", ""),
        }
        
        return user_data
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification error: {str(e)}",
        )


async def get_clerk_user_info(user_id: str) -> Dict[str, Any]:
    """
    Get user information from Clerk API.
    """
    try:
        headers = {
            "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.clerk.com/v1/users/{user_id}",
                headers=headers,
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to get user info from Clerk",
                )
            
            return response.json()
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to Clerk API: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Clerk API error: {str(e)}",
        )