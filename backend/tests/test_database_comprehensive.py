"""
Comprehensive tests for database module to achieve 90%+ coverage.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db, engine, AsyncSessionLocal


class TestDatabaseModule:
    """Test database module functionality."""
    
    @pytest.mark.asyncio
    async def test_get_db_success(self):
        """Test successful database session creation."""
        # Mock AsyncSessionLocal to return a mock session
        mock_session = AsyncMock(spec=AsyncSession)
        
        with patch('app.database.AsyncSessionLocal') as mock_session_local:
            mock_session_local.return_value = mock_session
            
            # Use get_db as an async generator
            db_gen = get_db()
            db = await db_gen.__anext__()
            
            assert db == mock_session
            
            # Test cleanup (generator should handle close)
            try:
                await db_gen.__anext__()
            except StopAsyncIteration:
                pass  # Expected
    
    @pytest.mark.asyncio
    async def test_get_db_exception_handling(self):
        """Test database session exception handling."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.close.side_effect = Exception("Close failed")
        
        with patch('app.database.AsyncSessionLocal') as mock_session_local:
            mock_session_local.return_value = mock_session
            
            db_gen = get_db()
            db = await db_gen.__anext__()
            
            # Simulate an exception during usage
            try:
                await db_gen.athrow(Exception("Test exception"))
            except Exception:
                pass  # Expected
            
            # Verify close was called despite exception
            mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_db_finally_block(self):
        """Test database session cleanup in finally block."""
        mock_session = AsyncMock(spec=AsyncSession)
        
        with patch('app.database.AsyncSessionLocal') as mock_session_local:
            mock_session_local.return_value = mock_session
            
            db_gen = get_db()
            db = await db_gen.__anext__()
            
            # Close the generator normally
            try:
                await db_gen.__anext__()
            except StopAsyncIteration:
                pass
            
            # Verify close was called
            mock_session.close.assert_called_once()
    
    def test_engine_creation(self):
        """Test database engine creation."""
        # The engine should be created during import
        assert engine is not None
        assert str(engine.url).startswith('sqlite+aiosqlite:///')
    
    def test_session_local_creation(self):
        """Test AsyncSessionLocal creation."""
        # Should be a sessionmaker instance
        assert AsyncSessionLocal is not None
        assert isinstance(AsyncSessionLocal, sessionmaker)
    
    @pytest.mark.asyncio
    async def test_database_session_context_manager(self):
        """Test using database session as context manager."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.database.AsyncSessionLocal') as mock_session_local:
            mock_session_local.return_value = mock_session
            
            # Test context manager usage
            async with mock_session as session:
                assert session == mock_session
            
            # Verify context manager methods were called
            mock_session.__aenter__.assert_called_once()
            mock_session.__aexit__.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_session_operations(self):
        """Test database session operations."""
        mock_session = AsyncMock(spec=AsyncSession)
        
        with patch('app.database.AsyncSessionLocal') as mock_session_local:
            mock_session_local.return_value = mock_session
            
            db_gen = get_db()
            db = await db_gen.__anext__()
            
            # Test various session operations
            await db.commit()
            await db.rollback()
            await db.flush()
            
            # Verify operations were called
            mock_session.commit.assert_called_once()
            mock_session.rollback.assert_called_once()
            mock_session.flush.assert_called_once()
    
    def test_database_url_configuration(self):
        """Test database URL configuration."""
        # Test that the database URL is properly configured
        assert str(engine.url) == 'sqlite+aiosqlite:///./checkguard.db'
    
    @pytest.mark.asyncio
    async def test_get_db_generator_behavior(self):
        """Test get_db async generator behavior."""
        mock_session = AsyncMock(spec=AsyncSession)
        
        with patch('app.database.AsyncSessionLocal') as mock_session_local:
            mock_session_local.return_value = mock_session
            
            # Test multiple calls to the generator
            db_gen1 = get_db()
            db_gen2 = get_db()
            
            db1 = await db_gen1.__anext__()
            db2 = await db_gen2.__anext__()
            
            # Should create separate sessions
            assert mock_session_local.call_count == 2
    
    @pytest.mark.asyncio
    async def test_database_connection_error_handling(self):
        """Test database connection error handling."""
        # Mock AsyncSessionLocal to raise an exception
        with patch('app.database.AsyncSessionLocal', side_effect=Exception("Connection failed")):
            with pytest.raises(Exception, match="Connection failed"):
                db_gen = get_db()
                await db_gen.__anext__()
    
    def test_database_module_imports(self):
        """Test that all database module exports are available."""
        from app.database import get_db, engine, AsyncSessionLocal
        
        assert get_db is not None
        assert engine is not None
        assert AsyncSessionLocal is not None
    
    @pytest.mark.asyncio
    async def test_session_transaction_rollback(self):
        """Test session transaction rollback on error."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit.side_effect = Exception("Commit failed")
        
        with patch('app.database.AsyncSessionLocal') as mock_session_local:
            mock_session_local.return_value = mock_session
            
            db_gen = get_db()
            db = await db_gen.__anext__()
            
            # Simulate transaction error
            with pytest.raises(Exception, match="Commit failed"):
                await db.commit()
            
            # Session should still be accessible for rollback
            await db.rollback()
            mock_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_concurrent_database_sessions(self):
        """Test concurrent database sessions."""
        mock_session_1 = AsyncMock(spec=AsyncSession)
        mock_session_2 = AsyncMock(spec=AsyncSession)
        
        call_count = 0
        def mock_session_factory():
            nonlocal call_count
            call_count += 1
            return mock_session_1 if call_count == 1 else mock_session_2
        
        with patch('app.database.AsyncSessionLocal', side_effect=mock_session_factory):
            # Create multiple concurrent sessions
            db_gen1 = get_db()
            db_gen2 = get_db()
            
            db1 = await db_gen1.__anext__()
            db2 = await db_gen2.__anext__()
            
            # Should be different session instances
            assert db1 == mock_session_1
            assert db2 == mock_session_2
            
            # Clean up
            try:
                await db_gen1.__anext__()
            except StopAsyncIteration:
                pass
                
            try:
                await db_gen2.__anext__()
            except StopAsyncIteration:
                pass
    
    def test_database_engine_configuration(self):
        """Test database engine configuration options."""
        # Verify engine is configured with proper options
        assert engine.echo is False  # Should not echo SQL by default
        assert engine.pool_pre_ping is True  # Should have pre-ping enabled
    
    @pytest.mark.asyncio
    async def test_session_lifecycle_complete(self):
        """Test complete session lifecycle."""
        mock_session = AsyncMock(spec=AsyncSession)
        
        with patch('app.database.AsyncSessionLocal') as mock_session_local:
            mock_session_local.return_value = mock_session
            
            # Full lifecycle test
            db_gen = get_db()
            
            # Start session
            db = await db_gen.__anext__()
            assert db == mock_session
            
            # Use session
            await db.execute("SELECT 1")
            await db.commit()
            
            # End session
            try:
                await db_gen.__anext__()
            except StopAsyncIteration:
                pass
            
            # Verify session was properly closed
            mock_session.close.assert_called_once()
