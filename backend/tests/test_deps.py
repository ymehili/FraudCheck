import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_or_create_user, verify_clerk_token
from app.models.user import User


class TestDeps:
    """Test dependency injection functions."""

    @pytest.mark.asyncio
    async def test_get_current_user_missing_header(self):
        """Test get_current_user with missing authorization header."""
        from fastapi import Request
        
        # Mock request without authorization header
        request = MagicMock(spec=Request)
        request.headers = {}
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization=None, db=MagicMock())
        
        assert exc_info.value.status_code == 401
        assert "Authorization header is required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_header_format(self):
        """Test get_current_user with invalid authorization header format."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization="InvalidFormat token", db=MagicMock())
        
        assert exc_info.value.status_code == 401
        assert "Invalid authorization header format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('app.api.deps.verify_clerk_token')
    @patch('app.api.deps.get_or_create_user')
    async def test_get_current_user_success(self, mock_get_or_create_user, mock_verify_token):
        """Test successful get_current_user."""
        # Mock token verification
        mock_verify_token.return_value = {
            "user_id": "user123",
            "email": "test@example.com"
        }
        
        # Mock user creation/retrieval
        mock_user = User(id="user123", email="test@example.com")
        mock_get_or_create_user.return_value = mock_user
        
        # Mock database session
        mock_db = MagicMock(spec=AsyncSession)
        
        result = await get_current_user(authorization="Bearer valid_token", db=mock_db)
        
        assert result == mock_user
        mock_verify_token.assert_called_once_with("valid_token")
        mock_get_or_create_user.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.api.deps.verify_clerk_token')
    async def test_get_current_user_token_verification_failure(self, mock_verify_token):
        """Test get_current_user with token verification failure."""
        # Mock token verification failure
        mock_verify_token.side_effect = Exception("Invalid token")
        
        mock_db = MagicMock(spec=AsyncSession)
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization="Bearer invalid_token", db=mock_db)
        
        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_or_create_user_existing_user(self, db_session: AsyncSession):
        """Test get_or_create_user with existing user."""
        # Create user in database
        user = User(id="existing_user", email="existing@example.com")
        db_session.add(user)
        await db_session.commit()
        
        user_data = {
            "user_id": "existing_user",
            "id": "existing_user",
            "email": "existing@example.com"
        }
        
        result = await get_or_create_user(db_session, user_data)
        
        assert result.id == "existing_user"
        assert result.email == "existing@example.com"

    @pytest.mark.asyncio
    async def test_get_or_create_user_new_user(self, db_session: AsyncSession):
        """Test get_or_create_user with new user."""
        user_data = {
            "user_id": "new_user",
            "id": "new_user",
            "email": "new@example.com"
        }
        
        result = await get_or_create_user(db_session, user_data)
        
        assert result.id == "new_user"
        assert result.email == "new@example.com"

    @pytest.mark.asyncio
    async def test_get_or_create_user_user_id_field(self, db_session: AsyncSession):
        """Test get_or_create_user with user_id field."""
        user_data = {
            "user_id": "test_user_id",
            "email": "test_user_id@example.com"
        }
        
        result = await get_or_create_user(db_session, user_data)
        
        assert result.id == "test_user_id"
        assert result.email == "test_user_id@example.com"

    @pytest.mark.asyncio
    async def test_get_or_create_user_id_field(self, db_session: AsyncSession):
        """Test get_or_create_user with id field."""
        user_data = {
            "id": "test_id",
            "email": "test_id@example.com"
        }
        
        result = await get_or_create_user(db_session, user_data)
        
        assert result.id == "test_id"
        assert result.email == "test_id@example.com"

    @pytest.mark.asyncio
    async def test_get_or_create_user_missing_user_id(self, db_session: AsyncSession):
        """Test get_or_create_user with missing user_id/id."""
        user_data = {
            "email": "test@example.com"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await get_or_create_user(db_session, user_data)
        
        assert exc_info.value.status_code == 400
        assert "Invalid user data" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_or_create_user_missing_email(self, db_session: AsyncSession):
        """Test get_or_create_user with missing email."""
        user_data = {
            "user_id": "test_user",
            "id": "test_user"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await get_or_create_user(db_session, user_data)
        
        assert exc_info.value.status_code == 400
        assert "Invalid user data" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_or_create_user_database_error(self, db_session: AsyncSession):
        """Test get_or_create_user with database error."""
        user_data = {
            "user_id": "test_user",
            "email": "test@example.com"
        }
        
        # Mock database session to raise an error
        with patch.object(db_session, 'execute', side_effect=Exception("Database error")):
            with pytest.raises(HTTPException) as exc_info:
                await get_or_create_user(db_session, user_data)
            
            assert exc_info.value.status_code == 500
            assert "Database error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_verify_clerk_token_direct_call(self):
        """Test verify_clerk_token function directly."""
        # This tests the import and availability of the function
        # The actual functionality is tested in test_security.py
        assert verify_clerk_token is not None
        assert callable(verify_clerk_token)

    @pytest.mark.asyncio 
    async def test_get_current_user_with_none_authorization(self):
        """Test get_current_user with None authorization."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization=None, db=MagicMock())
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_with_empty_token(self):
        """Test get_current_user with empty token."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization="Bearer ", db=MagicMock())
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_only_bearer(self):
        """Test get_current_user with only 'Bearer' string."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization="Bearer", db=MagicMock())
        
        assert exc_info.value.status_code == 401
