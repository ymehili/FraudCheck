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

    def test_get_current_user_without_auth(self):
        """Test getting current user without authentication."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        # Create a fresh client without dependency overrides
        with TestClient(app) as test_client:
            response = test_client.get("/api/v1/auth/me")
            assert response.status_code == 401
            assert "Authorization header is required" in response.json()["detail"]

    def test_get_current_user_with_invalid_auth_format(self):
        """Test getting current user with invalid auth header format."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        # Create a fresh client without dependency overrides
        with TestClient(app) as test_client:
            response = test_client.get(
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
        test_user_data
    ):
        """Test getting current user with valid authentication."""
        from datetime import datetime
        from fastapi.testclient import TestClient
        from app.main import app
        from app.database import get_db
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.ext.asyncio import create_async_engine
        
        # Create test database session
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async def override_get_db():
            async with async_session() as session:
                yield session
        
        # Mock the token verification
        mock_verify_token.return_value = test_user_data
        
        # Mock the user retrieval - create user with proper structure
        mock_user = User(
            id=test_user_data["id"],
            email=test_user_data["email"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_get_or_create_user.return_value = mock_user
        
        # Override the database dependency
        app.dependency_overrides[get_db] = override_get_db
        
        try:
            with TestClient(app) as test_client:
                response = test_client.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": "Bearer valid-token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["id"] == test_user_data["id"]
                assert data["email"] == test_user_data["email"]
        finally:
            app.dependency_overrides.clear()

    @patch('app.api.deps.verify_clerk_token')
    def test_get_current_user_with_invalid_token(
        self,
        mock_verify_token
    ):
        """Test getting current user with invalid token."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        mock_verify_token.side_effect = Exception("Invalid token")
        
        # Create a fresh client without dependency overrides
        with TestClient(app) as test_client:
            response = test_client.get(
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
        test_user_data
    ):
        """Test token refresh endpoint."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.database import get_db
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.ext.asyncio import create_async_engine
        
        # Create test database session
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async def override_get_db():
            async with async_session() as session:
                yield session
        
        # Mock the token verification
        mock_verify_token.return_value = test_user_data
        
        # Mock the user retrieval
        mock_user = User(
            id=test_user_data["id"],
            email=test_user_data["email"]
        )
        mock_get_or_create_user.return_value = mock_user
        
        # Override the database dependency
        app.dependency_overrides[get_db] = override_get_db
        
        try:
            with TestClient(app) as test_client:
                response = test_client.post(
                    "/api/v1/auth/refresh",
                    headers={"Authorization": "Bearer valid-token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "Token refreshed successfully"
                assert data["user_id"] == test_user_data["id"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_or_create_user_existing_user(
        self,
        db_session: AsyncSession
    ):
        """Test getting existing user from database."""
        from app.api.deps import get_or_create_user
        import uuid
        
        # Create unique test data for this test
        unique_id = f"test-user-{uuid.uuid4().hex[:8]}"
        test_data = {
            "id": unique_id,
            "email": f"{unique_id}@example.com"
        }
        
        # Create user in database
        user = User(
            id=test_data["id"],
            email=test_data["email"]
        )
        db_session.add(user)
        await db_session.commit()
        
        # Test getting the user
        retrieved_user = await get_or_create_user(db_session, test_data)
        
        assert retrieved_user.id == test_data["id"]
        assert retrieved_user.email == test_data["email"]

    @pytest.mark.asyncio
    async def test_get_or_create_user_new_user(
        self,
        db_session: AsyncSession
    ):
        """Test creating new user in database."""
        from app.api.deps import get_or_create_user
        import uuid
        
        # Create unique test data for this test
        unique_id = f"new-user-{uuid.uuid4().hex[:8]}"
        test_data = {
            "id": unique_id,
            "email": f"{unique_id}@example.com"
        }
        
        # Test creating new user
        new_user = await get_or_create_user(db_session, test_data)
        
        assert new_user.id == test_data["id"]
        assert new_user.email == test_data["email"]

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