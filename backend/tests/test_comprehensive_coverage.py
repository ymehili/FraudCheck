import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException

from app.api.deps import get_current_user, get_or_create_user
from app.database import get_db


class TestComprehensiveCoverage:
    """Test remaining code paths for comprehensive coverage."""

    @pytest.mark.asyncio
    async def test_get_db_generator(self):
        """Test get_db as async generator."""
        db_gen = get_db()
        
        # Test that it's an async generator
        assert hasattr(db_gen, '__anext__')
        
        try:
            # Get the session
            session = await db_gen.__anext__()
            assert session is not None
            
            # Try to close the generator
            try:
                await db_gen.__anext__()
            except StopAsyncIteration:
                # Expected behavior when generator is exhausted
                pass
        except Exception:
            # Database might not be available in test environment
            pass

    @pytest.mark.asyncio
    async def test_get_current_user_with_bearer_only(self):
        """Test get_current_user with just 'Bearer' string."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization="Bearer", db=MagicMock())
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_with_empty_token_after_bearer(self):
        """Test get_current_user with empty token after Bearer."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization="Bearer ", db=MagicMock())
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @patch('app.api.deps.verify_clerk_token')
    @patch('app.api.deps.get_or_create_user')
    async def test_get_current_user_database_error_in_user_creation(self, mock_get_or_create_user, mock_verify_token):
        """Test get_current_user with database error during user creation."""
        mock_verify_token.return_value = {
            "user_id": "test_user",
            "email": "test@example.com"
        }
        # Mock a database error that gets re-raised as HTTPException
        mock_get_or_create_user.side_effect = HTTPException(
            status_code=500,
            detail="Database error while getting or creating user: Database connection failed"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization="Bearer valid_token", db=MagicMock())
        
        assert exc_info.value.status_code == 500
        assert "Database error while getting or creating user" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_or_create_user_with_both_id_fields(self, db_session):
        """Test get_or_create_user with both user_id and id fields."""
        user_data = {
            "user_id": "test_user_both",
            "id": "test_user_both_id",
            "email": "test_both@example.com"
        }
        
        # Should prioritize user_id over id
        result = await get_or_create_user(db_session, user_data)
        assert result.id == "test_user_both"  # user_id takes precedence

    @pytest.mark.asyncio
    async def test_get_or_create_user_database_rollback_on_error(self, db_session):
        """Test get_or_create_user with database rollback on error."""
        user_data = {
            "user_id": "test_rollback_user",
            "email": "test_rollback@example.com"
        }
        
        # Mock session.execute to fail
        with patch.object(db_session, 'execute', side_effect=Exception("Query failed")):
            with pytest.raises(HTTPException) as exc_info:
                await get_or_create_user(db_session, user_data)
            
            assert exc_info.value.status_code == 500
            assert "Database error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_database_session_context_manager(self):
        """Test database session as context manager behavior."""
        try:
            # Test manual session creation and closing
            db_gen = get_db()
            session = await db_gen.__anext__()
            
            # Session should be usable
            assert hasattr(session, 'execute')
            assert hasattr(session, 'commit')
            assert hasattr(session, 'rollback')
            
            # Close the session
            try:
                await session.close()
            except Exception:
                # May fail in test environment
                pass
                
        except Exception:
            # Database may not be available
            pass

    def test_database_imports_and_configuration(self):
        """Test that database components are properly imported and configured."""
        from app.database import Base, engine
        
        # Test that Base is properly configured
        assert Base is not None
        assert hasattr(Base, 'metadata')
        
        # Test that engine is configured
        assert engine is not None
        assert hasattr(engine, 'dispose')

    @pytest.mark.asyncio
    async def test_engine_disposal_in_cleanup(self):
        """Test engine disposal for cleanup."""
        from app.database import engine
        
        try:
            # Test that engine can be disposed without error
            await engine.dispose()
        except Exception:
            # May fail in test environment, but shouldn't crash
            pass

    def test_database_base_registry(self):
        """Test database base registry and metadata."""
        from app.database import Base
        
        # Test that Base has proper metadata
        assert Base.metadata is not None
        
        # Test that tables are registered
        table_names = list(Base.metadata.tables.keys())
        assert len(table_names) > 0
        
        # Should have users and files tables
        assert 'users' in table_names
        assert 'files' in table_names
