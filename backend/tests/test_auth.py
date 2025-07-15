import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from app.models.user import User


class TestAuth:
    """Test authentication endpoints."""

    def test_auth_root_endpoint(self, client: TestClient):
        """Test authentication root endpoint without auth."""
        response = client.get("/api/v1/auth/")
        assert response.status_code == 404  # Should not exist

    def test_get_current_user_without_auth(self, client: TestClient):
        """Test getting current user without authentication."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
        assert "Authorization header is required" in response.json()["detail"]

    def test_get_current_user_with_invalid_auth_format(self, client: TestClient):
        """Test getting current user with invalid auth header format."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "InvalidFormat token"}
        )
        assert response.status_code == 401
        assert "Invalid authorization header format" in response.json()["detail"]

    @patch('app.api.deps.verify_clerk_token')
    @patch('app.api.deps.get_or_create_user')
    def test_get_current_user_with_valid_auth(
        self,
        mock_get_or_create_user,
        mock_verify_token,
        client: TestClient,
        test_user_data
    ):
        """Test getting current user with valid authentication."""
        from datetime import datetime
        
        # Mock the token verification
        mock_verify_token.return_value = test_user_data
        
        # Mock the user retrieval - create user with proper structure
        mock_user = User(
            id=test_user_data["id"],  # Changed from user_id to id
            email=test_user_data["email"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_get_or_create_user.return_value = mock_user
        
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer valid-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user_data["id"]  # Changed from user_id to id
        assert data["email"] == test_user_data["email"]

    @patch('app.api.deps.verify_clerk_token')
    def test_get_current_user_with_invalid_token(
        self,
        mock_verify_token,
        client: TestClient
    ):
        """Test getting current user with invalid token."""
        mock_verify_token.side_effect = Exception("Invalid token")
        
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401
        assert "Invalid or expired token" in response.json()["detail"]

    @patch('app.api.deps.verify_clerk_token')
    @patch('app.api.deps.get_or_create_user')
    def test_refresh_token_endpoint(
        self,
        mock_get_or_create_user,
        mock_verify_token,
        client: TestClient,
        test_user_data
    ):
        """Test token refresh endpoint."""
        # Mock the token verification
        mock_verify_token.return_value = test_user_data
        
        # Mock the user retrieval
        mock_user = User(
            id=test_user_data["id"],  # Changed from user_id to id  
            email=test_user_data["email"]
        )
        mock_get_or_create_user.return_value = mock_user
        
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": "Bearer valid-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Token refreshed successfully"
        assert data["user_id"] == test_user_data["id"]

    @pytest.mark.asyncio
    async def test_get_or_create_user_existing_user(
        self,
        db_session: AsyncSession,
        test_user_data
    ):
        """Test getting existing user from database."""
        from app.api.deps import get_or_create_user
        
        # Create user in database
        user = User(
            id=test_user_data["id"],  # Changed from user_id to id
            email=test_user_data["email"]
        )
        db_session.add(user)
        await db_session.commit()
        
        # Test getting the user
        retrieved_user = await get_or_create_user(db_session, test_user_data)
        
        assert retrieved_user.id == test_user_data["id"]
        assert retrieved_user.email == test_user_data["email"]

    @pytest.mark.asyncio
    async def test_get_or_create_user_new_user(
        self,
        db_session: AsyncSession,
        test_user_data
    ):
        """Test creating new user in database."""
        from app.api.deps import get_or_create_user
        
        # Test creating new user
        new_user = await get_or_create_user(db_session, test_user_data)
        
        assert new_user.id == test_user_data["id"]
        assert new_user.email == test_user_data["email"]

    @pytest.mark.asyncio
    async def test_get_or_create_user_invalid_data(
        self,
        db_session: AsyncSession
    ):
        """Test creating user with invalid data."""
        from app.api.deps import get_or_create_user
        from fastapi import HTTPException
        
        # Test with missing user_id/id
        with pytest.raises(HTTPException) as exc_info:
            await get_or_create_user(db_session, {"email": "test@example.com"})
        
        assert exc_info.value.status_code == 400
        assert "Invalid user data" in str(exc_info.value.detail)
        
        # Test with missing email
        with pytest.raises(HTTPException) as exc_info:
            await get_or_create_user(db_session, {"id": "test-id"})
        
        assert exc_info.value.status_code == 400
        assert "Invalid user data" in str(exc_info.value.detail)