import pytest
from pydantic import ValidationError

from app.schemas.file import FileResponse, FileUploadResponse, FileListResponse
from app.schemas.user import UserResponse, UserBase


class TestSchemas:
    """Test schema validation and serialization."""

    def test_user_base_schema(self):
        """Test UserBase schema validation."""
        # Valid data
        user_data = {
            "email": "test@example.com"
        }
        user = UserBase(**user_data)
        assert user.email == "test@example.com"

    def test_user_base_schema_validation_error(self):
        """Test UserBase schema validation with invalid data."""
        # Missing required fields
        with pytest.raises(ValidationError):
            UserBase()
        
        # Invalid email format
        with pytest.raises(ValidationError):
            UserBase(email="invalid-email")

    def test_user_response_schema(self):
        """Test UserResponse schema."""
        from datetime import datetime
        
        user_data = {
            "id": "user123",
            "email": "test@example.com",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        user = UserResponse(**user_data)
        assert user.id == "user123"
        assert user.email == "test@example.com"
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_file_response_schema(self):
        """Test FileResponse schema validation."""
        from datetime import datetime
        
        file_data = {
            "id": "file123",
            "user_id": "user123",
            "filename": "test.jpg",
            "s3_key": "uploads/user123/file123_test.jpg",
            "s3_url": "https://bucket.s3.amazonaws.com/key",
            "file_size": 1024,
            "mime_type": "image/jpeg",
            "upload_timestamp": datetime.now()
        }
        file_response = FileResponse(**file_data)
        assert file_response.id == "file123"
        assert file_response.filename == "test.jpg"
        assert file_response.file_size == 1024

    def test_file_response_schema_validation_error(self):
        """Test FileResponse schema validation with invalid data."""
        # Missing required fields
        with pytest.raises(ValidationError):
            FileResponse()
        
        # Invalid file size (negative)
        with pytest.raises(ValidationError):
            FileResponse(
                id="file123",
                user_id="user123",
                filename="test.jpg",
                s3_key="key",
                s3_url="url",
                file_size=-1,
                mime_type="image/jpeg"
            )

    def test_file_upload_response_schema(self):
        """Test FileUploadResponse schema validation."""
        from datetime import datetime
        
        upload_data = {
            "file_id": "file123",
            "s3_url": "https://bucket.s3.amazonaws.com/key",
            "upload_timestamp": datetime.now(),
            "message": "File uploaded successfully"
        }
        upload_response = FileUploadResponse(**upload_data)
        assert upload_response.file_id == "file123"
        assert upload_response.message == "File uploaded successfully"

    def test_file_upload_response_validation_error(self):
        """Test FileUploadResponse validation with invalid data."""
        with pytest.raises(ValidationError):
            FileUploadResponse()

    def test_file_list_response_schema(self):
        """Test FileListResponse schema validation."""
        from datetime import datetime
        
        # Create file response objects
        file1 = FileResponse(
            id="file1",
            user_id="user123",
            filename="test1.jpg",
            s3_key="key1",
            s3_url="url1",
            file_size=1024,
            mime_type="image/jpeg",
            upload_timestamp=datetime.now()
        )
        
        file2 = FileResponse(
            id="file2",
            user_id="user123",
            filename="test2.jpg",
            s3_key="key2",
            s3_url="url2",
            file_size=2048,
            mime_type="image/jpeg",
            upload_timestamp=datetime.now()
        )
        
        list_data = {
            "files": [file1, file2],
            "total": 2,
            "page": 1,
            "per_page": 10
        }
        
        file_list = FileListResponse(**list_data)
        assert len(file_list.files) == 2
        assert file_list.total == 2
        assert file_list.page == 1

    def test_file_list_response_empty(self):
        """Test FileListResponse with empty file list."""
        list_data = {
            "files": [],
            "total": 0,
            "page": 1,
            "per_page": 10
        }
        
        file_list = FileListResponse(**list_data)
        assert len(file_list.files) == 0
        assert file_list.total == 0

    def test_file_list_response_validation_error(self):
        """Test FileListResponse validation with invalid data."""
        # Test with missing required fields
        with pytest.raises(ValidationError):
            FileListResponse()
        
        # Test that negative values are accepted (no validation constraints in schema)
        # This test ensures the schema allows various integer values
        response = FileListResponse(
            files=[],
            total=0,
            page=-1,  # Negative values are allowed by the schema
            per_page=-1
        )
        assert response.page == -1
        assert response.per_page == -1

    def test_schema_serialization(self):
        """Test schema serialization to dict."""
        from datetime import datetime
        
        user = UserResponse(
            id="user123",
            email="test@example.com",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        user_dict = user.model_dump()
        assert isinstance(user_dict, dict)
        assert user_dict["id"] == "user123"
        assert user_dict["email"] == "test@example.com"

    def test_schema_json_serialization(self):
        """Test schema JSON serialization."""
        from datetime import datetime
        
        user = UserResponse(
            id="user123",
            email="test@example.com",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        user_json = user.model_dump_json()
        assert isinstance(user_json, str)
        assert "user123" in user_json
        assert "test@example.com" in user_json
