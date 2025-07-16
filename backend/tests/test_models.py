import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.file import FileRecord


class TestModels:
    """Test database models."""

    def test_user_model_creation(self):
        """Test User model creation."""
        user = User(
            id="user123",
            email="test@example.com"
        )
        
        assert user.id == "user123"
        assert user.email == "test@example.com"
        # Note: created_at and updated_at are set by database server_default
        # They will be None until the record is saved to database

    def test_user_model_string_representation(self):
        """Test User model string representation."""
        user = User(
            id="user123",
            email="test@example.com"
        )
        
        # Default Python object representation
        str_repr = str(user)
        assert "User object" in str_repr

    def test_user_model_defaults(self):
        """Test User model default values."""
        user = User(
            id="user123",
            email="test@example.com"
        )
        
        # created_at and updated_at use server_default, so they're None until saved
        assert user.created_at is None
        assert user.updated_at is None

    def test_file_record_model_creation(self):
        """Test FileRecord model creation."""
        file_record = FileRecord(
            id="file123",
            user_id="user123",
            filename="test.jpg",
            s3_key="uploads/user123/file123_test.jpg",
            s3_url="https://bucket.s3.amazonaws.com/key",
            file_size=1024,
            mime_type="image/jpeg"
        )
        
        assert file_record.id == "file123"
        assert file_record.user_id == "user123"
        assert file_record.filename == "test.jpg"
        assert file_record.file_size == 1024

    def test_file_record_model_defaults(self):
        """Test FileRecord model default values."""
        file_record = FileRecord(
            id="file123",
            user_id="user123",
            filename="test.jpg",
            s3_key="key",
            s3_url="url",
            file_size=1024,
            mime_type="image/jpeg"
        )
        
        # upload_timestamp uses server_default, so it's None until saved
        assert file_record.upload_timestamp is None

    def test_file_record_string_representation(self):
        """Test FileRecord model string representation."""
        file_record = FileRecord(
            id="file123",
            user_id="user123",
            filename="test.jpg",
            s3_key="key",
            s3_url="url",
            file_size=1024,
            mime_type="image/jpeg"
        )
        
        # Default Python object representation
        str_repr = str(file_record)
        assert "FileRecord object" in str_repr

    @pytest.mark.asyncio
    async def test_user_model_database_operations(self, db_session: AsyncSession):
        """Test User model database operations."""
        # Create user
        user = User(
            id="test_user_db",
            email="test_db@example.com"
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Verify user was created
        assert user.id == "test_user_db"
        assert user.email == "test_db@example.com"

    @pytest.mark.asyncio
    async def test_file_record_model_database_operations(self, db_session: AsyncSession):
        """Test FileRecord model database operations."""
        # First create a user
        user = User(
            id="test_user_file_db",
            email="test_file_db@example.com"
        )
        db_session.add(user)
        await db_session.commit()
        
        # Create file record
        file_record = FileRecord(
            id="test_file_db",
            user_id="test_user_file_db",
            filename="test_db.jpg",
            s3_key="test/key/db",
            s3_url="https://test.url/db",
            file_size=2048,
            mime_type="image/jpeg"
        )
        
        db_session.add(file_record)
        await db_session.commit()
        await db_session.refresh(file_record)
        
        # Verify file record was created
        assert file_record.id == "test_file_db"
        assert file_record.user_id == "test_user_file_db"

    def test_user_model_table_name(self):
        """Test User model table name."""
        assert User.__tablename__ == "users"

    def test_file_record_model_table_name(self):
        """Test FileRecord model table name."""
        assert FileRecord.__tablename__ == "files"

    def test_model_relationships(self):
        """Test model relationships if any."""
        # Test that models can be created independently
        user = User(id="user123", email="test@example.com")
        file_record = FileRecord(
            id="file123",
            user_id="user123",
            filename="test.jpg",
            s3_key="key",
            s3_url="url",
            file_size=1024,
            mime_type="image/jpeg"
        )
        
        # Models should have proper foreign key relationship
        assert file_record.user_id == user.id

    def test_model_column_types(self):
        """Test model column types."""
        user = User(id="user123", email="test@example.com")
        
        # Test that string fields are strings
        assert isinstance(user.id, str)
        assert isinstance(user.email, str)
        
        file_record = FileRecord(
            id="file123",
            user_id="user123",
            filename="test.jpg",
            s3_key="key",
            s3_url="url",
            file_size=1024,
            mime_type="image/jpeg"
        )
        
        # Test that integer fields are integers
        assert isinstance(file_record.file_size, int)
        
        # Test that datetime fields are None until saved (server_default)
        assert file_record.upload_timestamp is None
