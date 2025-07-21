from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import httpx
import secrets
from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, "secret", algorithm="HS256")
    return encoded_jwt


async def get_clerk_jwks() -> Dict[str, Any]:
    """
    Fetch Clerk's JSON Web Key Set (JWKS) for JWT verification.
    """
    try:
        # Extract the publishable key to get the instance ID
        publishable_key = settings.CLERK_PUBLISHABLE_KEY
        if not publishable_key.startswith("pk_"):
            raise ValueError("Invalid Clerk publishable key format")
        
        # Extract instance identifier from publishable key
        # Format: pk_test_<base64_instance_info>
        instance_part = publishable_key.split('_', 2)[-1]
        
        # Clerk JWKS URL format
        jwks_url = f"https://api.clerk.com/v1/jwks"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to fetch Clerk JWKS",
                )
            
            return response.json()
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"JWKS fetch error: {str(e)}",
        )


async def verify_clerk_token(token: str) -> Dict[str, Any]:
    """
    Verify Clerk JWT token with proper signature verification and return user data.
    """
    try:
        # Get the token header to extract the key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing key ID (kid) in header",
            )
        
        # Fetch JWKS from Clerk
        jwks = await get_clerk_jwks()
        
        # Find the matching key
        rsa_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = {
                    "kty": key.get("kty"),
                    "kid": key.get("kid"),
                    "use": key.get("use"),
                    "n": key.get("n"),
                    "e": key.get("e"),
                }
                break
        
        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find matching key in JWKS",
            )
        
        # Verify and decode the token
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                audience=settings.CLERK_PUBLISHABLE_KEY,
                options={"verify_exp": True, "verify_aud": True}
            )
        except JWTError as jwt_error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"JWT signature verification failed: {str(jwt_error)}",
            )
        
        # Extract user information from verified payload
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject (user_id)",
            )
        
        # Extract email - try multiple field names that Clerk might use
        email = (
            payload.get("email") or 
            payload.get("email_address") or
            payload.get("primary_email_address_id")
        )
        
        # If no email found, try to get it from email_addresses array
        if not email:
            email_addresses = payload.get("email_addresses", [])
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
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
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