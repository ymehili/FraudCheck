import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.api.v1.files import upload_file, upload_file_debug, list_files, get_file, delete_file, download_file
from app.models.user import User
from app.models.file import FileRecord


class TestFilesAdditional:
    """Additional comprehensive tests for files endpoints."""

    @patch('app.api.v1.files.s3_service')
    @pytest.mark.asyncio
    async def test_upload_file_debug_endpoint_new_user(self, mock_s3_service, db_session):
        """Test upload_file_debug endpoint with new user creation."""
        from fastapi import UploadFile
        import io
        
        # Mock S3 service
        mock_s3_service.validate_file.return_value = True
        mock_s3_service.upload_file.return_value = {
            's3_key': 'test/key.jpg',
            's3_url': 'https://test-bucket.s3.amazonaws.com/test/key.jpg',
            'file_size': 1024,
            'content_type': 'image/jpeg'
        }
        
        # Create mock file
        file_content = b"fake image content"
        file_obj = io.BytesIO(file_content)
        mock_file = UploadFile(filename="test.jpg", file=file_obj, content_type="image/jpeg")
        mock_file.size = len(file_content)
        
        result = await upload_file_debug(file=mock_file, db=db_session)
        
        assert result.message == "File uploaded successfully (debug mode)"
        assert result.file_id is not None

    @patch('app.api.v1.files.s3_service')
    @pytest.mark.asyncio
    async def test_upload_file_debug_endpoint_existing_user(self, mock_s3_service, db_session):
        """Test upload_file_debug endpoint with existing user."""
        from fastapi import UploadFile
        import io
        
        # Create debug user first
        debug_user = User(id="debug_user_123", email="debug@test.com")
        db_session.add(debug_user)
        await db_session.commit()
        
        # Mock S3 service
        mock_s3_service.validate_file.return_value = True
        mock_s3_service.upload_file.return_value = {
            's3_key': 'test/key.jpg',
            's3_url': 'https://test-bucket.s3.amazonaws.com/test/key.jpg',
            'file_size': 1024,
            'content_type': 'image/jpeg'
        }
        
        # Create mock file
        file_content = b"fake image content"
        file_obj = io.BytesIO(file_content)
        mock_file = UploadFile(filename="test.jpg", file=file_obj, content_type="image/jpeg")
        mock_file.size = len(file_content)
        
        result = await upload_file_debug(file=mock_file, db=db_session)
        
        assert result.message == "File uploaded successfully (debug mode)"

    @patch('app.api.v1.files.s3_service')
    @pytest.mark.asyncio
    async def test_upload_file_debug_s3_failure(self, mock_s3_service, db_session):
        """Test upload_file_debug endpoint with S3 failure."""
        from fastapi import UploadFile
        import io
        
        # Mock S3 service failure
        mock_s3_service.validate_file.return_value = True
        mock_s3_service.upload_file.side_effect = Exception("S3 upload failed")
        
        # Create mock file
        file_content = b"fake image content"
        file_obj = io.BytesIO(file_content)
        mock_file = UploadFile(filename="test.jpg", file=file_obj, content_type="image/jpeg")
        mock_file.size = len(file_content)
        
        with pytest.raises(HTTPException) as exc_info:
            await upload_file_debug(file=mock_file, db=db_session)
        
        assert exc_info.value.status_code == 500
        assert "Failed to upload file" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_files_with_pagination(self, db_session, test_user_data):
        """Test list_files with different pagination parameters."""
        # Create user
        user = User(id=test_user_data["id"], email=test_user_data["email"])
        db_session.add(user)
        await db_session.commit()
        
        # Create multiple files
        for i in range(5):
            file_record = FileRecord(
                id=f"file_{i}",
                user_id=test_user_data["id"],
                filename=f"test_{i}.jpg",
                s3_key=f"key_{i}",
                s3_url=f"url_{i}",
                file_size=1024,
                mime_type="image/jpeg"
            )
            db_session.add(file_record)
        
        await db_session.commit()
        
        # Test pagination
        result = await list_files(page=1, per_page=3, current_user=user, db=db_session)
        
        assert len(result.files) == 3
        assert result.total == 5
        assert result.page == 1
        assert result.per_page == 3

    @pytest.mark.asyncio
    async def test_list_files_page_2(self, db_session, test_user_data):
        """Test list_files second page."""
        # Create user
        user = User(id=test_user_data["id"], email=test_user_data["email"])
        db_session.add(user)
        await db_session.commit()
        
        # Create multiple files
        for i in range(5):
            file_record = FileRecord(
                id=f"file_page2_{i}",
                user_id=test_user_data["id"],
                filename=f"test_{i}.jpg",
                s3_key=f"key_{i}",
                s3_url=f"url_{i}",
                file_size=1024,
                mime_type="image/jpeg"
            )
            db_session.add(file_record)
        
        await db_session.commit()
        
        # Test second page
        result = await list_files(page=2, per_page=3, current_user=user, db=db_session)
        
        assert len(result.files) == 2  # Remaining files
        assert result.total == 5
        assert result.page == 2

    @pytest.mark.asyncio
    async def test_get_file_not_owned_by_user(self, db_session, test_user_data):
        """Test get_file with file not owned by user."""
        # Create two users
        user1 = User(id=test_user_data["id"], email=test_user_data["email"])
        user2 = User(id="other_user", email="other@example.com")
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()
        
        # Create file owned by user2
        file_record = FileRecord(
            id="file_other_user",
            user_id="other_user",
            filename="test.jpg",
            s3_key="key",
            s3_url="url",
            file_size=1024,
            mime_type="image/jpeg"
        )
        db_session.add(file_record)
        await db_session.commit()
        
        # Try to access file as user1
        with pytest.raises(HTTPException) as exc_info:
            await get_file(file_id="file_other_user", current_user=user1, db=db_session)
        
        assert exc_info.value.status_code == 404
        assert "File not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_delete_file_not_owned_by_user(self, db_session, test_user_data):
        """Test delete_file with file not owned by user."""
        # Create two users
        user1 = User(id=test_user_data["id"], email=test_user_data["email"])
        user2 = User(id="other_user_delete", email="other@example.com")
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()
        
        # Create file owned by user2
        file_record = FileRecord(
            id="file_other_user_delete",
            user_id="other_user_delete",
            filename="test.jpg",
            s3_key="key",
            s3_url="url",
            file_size=1024,
            mime_type="image/jpeg"
        )
        db_session.add(file_record)
        await db_session.commit()
        
        # Try to delete file as user1
        with pytest.raises(HTTPException) as exc_info:
            await delete_file(file_id="file_other_user_delete", current_user=user1, db=db_session)
        
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_file_s3_failure(self, db_session, test_user_data):
        """Test delete_file with S3 deletion failure."""
        # Create user and file
        user = User(id=test_user_data["id"], email=test_user_data["email"])
        db_session.add(user)
        await db_session.commit()
        
        file_record = FileRecord(
            id="file_s3_delete_fail",
            user_id=test_user_data["id"],
            filename="test.jpg",
            s3_key="key",
            s3_url="url",
            file_size=1024,
            mime_type="image/jpeg"
        )
        db_session.add(file_record)
        await db_session.commit()
        
        # Mock S3 service failure
        with patch('app.api.v1.files.s3_service') as mock_s3:
            mock_s3.delete_file.side_effect = Exception("S3 deletion failed")
            
            with pytest.raises(HTTPException) as exc_info:
                await delete_file(file_id="file_s3_delete_fail", current_user=user, db=db_session)
            
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_download_file_not_owned_by_user(self, db_session, test_user_data):
        """Test download_file with file not owned by user."""
        # Create two users
        user1 = User(id=test_user_data["id"], email=test_user_data["email"])
        user2 = User(id="other_user_download", email="other@example.com")
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()
        
        # Create file owned by user2
        file_record = FileRecord(
            id="file_other_user_download",
            user_id="other_user_download",
            filename="test.jpg",
            s3_key="key",
            s3_url="url",
            file_size=1024,
            mime_type="image/jpeg"
        )
        db_session.add(file_record)
        await db_session.commit()
        
        # Try to download file as user1
        with pytest.raises(HTTPException) as exc_info:
            await download_file(file_id="file_other_user_download", current_user=user1, db=db_session)
        
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_file_database_rollback(self, db_session):
        """Test upload_file with database error and rollback."""
        from fastapi import UploadFile
        import io
        
        # Create user
        user = User(id="test_rollback_user", email="test@example.com")
        db_session.add(user)
        await db_session.commit()
        
        # Create mock file
        file_content = b"fake image content"
        file_obj = io.BytesIO(file_content)
        mock_file = UploadFile(filename="test.jpg", file=file_obj, content_type="image/jpeg")
        mock_file.size = len(file_content)
        
        # Mock S3 service success but database failure
        with patch('app.api.v1.files.s3_service') as mock_s3:
            mock_s3.validate_file.return_value = True
            mock_s3.upload_file.return_value = {
                's3_key': 'test/key.jpg',
                's3_url': 'https://test-bucket.s3.amazonaws.com/test/key.jpg',
                'file_size': 1024,
                'content_type': 'image/jpeg'
            }
            
            # Mock database add to fail
            with patch.object(db_session, 'add', side_effect=Exception("Database error")):
                with pytest.raises(HTTPException) as exc_info:
                    await upload_file(file=mock_file, current_user=user, db=db_session)
                
                assert exc_info.value.status_code == 500
