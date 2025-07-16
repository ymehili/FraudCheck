from fastapi import HTTPException, status
from jose import JWTError, jwt
from typing import Dict, Any
import httpx
from .config import settings


async def verify_clerk_token(token: str) -> Dict[str, Any]:
    """
    Verify Clerk JWT token and return user data.
    """
    try:
        # Decode without verification for development
        # NOTE: In production, you must properly verify the JWT
        unverified_payload = jwt.get_unverified_claims(token)
        
        # Basic validation
        user_id = unverified_payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject (user_id)",
            )
        
        # Extract email - try multiple field names that Clerk might use
        email = (
            unverified_payload.get("email") or 
            unverified_payload.get("email_address") or
            unverified_payload.get("primary_email_address_id")
        )
        
        # If no email found, try to get it from email_addresses array
        if not email:
            email_addresses = unverified_payload.get("email_addresses", [])
            if email_addresses and len(email_addresses) > 0:
                # Take the first email address
                if isinstance(email_addresses[0], dict):
                    email = email_addresses[0].get("email_address", "")
                else:
                    email = str(email_addresses[0])
        
        # If still no email, use a default or user_id
        if not email:
            email = f"{user_id}@clerk.user"  # Fallback email
        
        # Extract user information
        user_data = {
            "user_id": user_id,
            "id": user_id,  # Support both field names
            "email": email,
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