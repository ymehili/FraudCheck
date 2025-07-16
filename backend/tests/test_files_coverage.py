import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.v1.files import upload_file_debug
from app.models.user import User
from app.models.file import FileRecord


class TestFilesCoverageBoost:
    """Test additional scenarios to boost code coverage."""

    @pytest.mark.asyncio
    async def test_upload_file_debug_validation_failure(self, db_session):
        """Test upload_file_debug with file validation failure."""
        # Create a mock file that will fail validation
        mock_file = MagicMock()
        mock_file.filename = "test.txt"
        mock_file.content_type = "text/plain"
        mock_file.size = 999999999  # Very large file
        mock_file.file = MagicMock()
        
        # Mock S3 service validation to raise exception
        with patch('app.api.v1.files.s3_service') as mock_s3_service:
            mock_s3_service.validate_file.side_effect = HTTPException(status_code=400, detail="File too large")
            
            with pytest.raises(HTTPException) as exc_info:
                await upload_file_debug(file=mock_file, db=db_session)
            
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio 
    async def test_upload_file_debug_s3_upload_failure(self, db_session):
        """Test upload_file_debug with S3 upload failure."""
        mock_file = MagicMock()
        mock_file.filename = "test.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.size = 1024
        mock_file.file = MagicMock()
        
        with patch('app.api.v1.files.s3_service') as mock_s3_service:
            mock_s3_service.validate_file.return_value = True
            mock_s3_service.upload_file.side_effect = Exception("S3 upload failed")
            
            with pytest.raises(HTTPException) as exc_info:
                await upload_file_debug(file=mock_file, db=db_session)
            
            assert exc_info.value.status_code == 500
            assert "Failed to upload file" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_file_debug_db_commit_failure(self, db_session):
        """Test upload_file_debug with database commit failure."""
        mock_file = MagicMock()
        mock_file.filename = "test.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.size = 1024
        mock_file.file = MagicMock()
        
        with patch('app.api.v1.files.s3_service') as mock_s3_service:
            mock_s3_service.validate_file.return_value = True
            mock_s3_service.upload_file.return_value = {
                's3_key': 'test/key.jpg',
                's3_url': 'https://test-bucket.s3.amazonaws.com/test/key.jpg',
                'file_size': 1024,
                'content_type': 'image/jpeg'
            }
            
            # Mock database commit failure
            with patch.object(db_session, 'commit', side_effect=Exception("Database commit failed")):
                with pytest.raises(HTTPException) as exc_info:
                    await upload_file_debug(file=mock_file, db=db_session)
                
                assert exc_info.value.status_code == 500
                assert "Failed to upload file" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_file_validation_failure(self, db_session):
        """Test regular upload_file with validation failure."""
        from app.api.v1.files import upload_file
        
        user = User(id="test_validation_user", email="test@example.com")
        
        mock_file = MagicMock()
        mock_file.filename = "test.txt"
        mock_file.content_type = "text/plain"
        mock_file.size = 999999999  # Very large file
        mock_file.file = MagicMock()
        
        with patch('app.api.v1.files.s3_service') as mock_s3_service:
            mock_s3_service.validate_file.side_effect = HTTPException(status_code=400, detail="File too large")
            
            with pytest.raises(HTTPException) as exc_info:
                await upload_file(file=mock_file, current_user=user, db=db_session)
            
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_file_s3_upload_failure(self, db_session):
        """Test regular upload_file with S3 upload failure."""
        from app.api.v1.files import upload_file
        
        user = User(id="test_s3_fail_user", email="test@example.com")
        
        mock_file = MagicMock()
        mock_file.filename = "test.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.size = 1024
        mock_file.file = MagicMock()
        
        with patch('app.api.v1.files.s3_service') as mock_s3_service:
            mock_s3_service.validate_file.return_value = True
            mock_s3_service.upload_file.side_effect = Exception("S3 upload failed")
            
            with pytest.raises(HTTPException) as exc_info:
                await upload_file(file=mock_file, current_user=user, db=db_session)
            
            assert exc_info.value.status_code == 500
            assert "Failed to upload file" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_file_db_failure(self, db_session):
        """Test regular upload_file with database failure."""
        from app.api.v1.files import upload_file
        
        user = User(id="test_db_fail_user", email="test@example.com")
        
        mock_file = MagicMock()
        mock_file.filename = "test.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.size = 1024
        mock_file.file = MagicMock()
        
        with patch('app.api.v1.files.s3_service') as mock_s3_service:
            mock_s3_service.validate_file.return_value = True
            mock_s3_service.upload_file.return_value = {
                's3_key': 'test/key.jpg',
                's3_url': 'https://test-bucket.s3.amazonaws.com/test/key.jpg',
                'file_size': 1024,
                'content_type': 'image/jpeg'
            }
            
            # Mock database add failure
            with patch.object(db_session, 'add', side_effect=Exception("Database add failed")):
                with pytest.raises(HTTPException) as exc_info:
                    await upload_file(file=mock_file, current_user=user, db=db_session)
                
                assert exc_info.value.status_code == 500
                assert "Failed to upload file" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_download_file_not_found(self, db_session):
        """Test download_file with non-existent file."""
        from app.api.v1.files import download_file
        
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        user = User(id="test_download_user", email=f"test-download-{unique_id}@example.com")
        db_session.add(user)
        await db_session.commit()
        
        with pytest.raises(HTTPException) as exc_info:
            await download_file(file_id="non_existent_file", current_user=user, db=db_session)
        
        assert exc_info.value.status_code == 404
        assert "File not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_delete_file_not_found(self, db_session):
        """Test delete_file with non-existent file."""
        from app.api.v1.files import delete_file
        
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        user = User(id="test_delete_user", email=f"test-delete-{unique_id}@example.com")
        db_session.add(user)
        await db_session.commit()
        
        with pytest.raises(HTTPException) as exc_info:
            await delete_file(file_id="non_existent_file", current_user=user, db=db_session)
        
        assert exc_info.value.status_code == 404
        assert "File not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_file_not_found(self, db_session):
        """Test get_file with non-existent file."""
        from app.api.v1.files import get_file
        
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        user = User(id="test_get_user", email=f"test-get-{unique_id}@example.com")
        db_session.add(user)
        await db_session.commit()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_file(file_id="non_existent_file", current_user=user, db=db_session)
        
        assert exc_info.value.status_code == 404
        assert "File not found" in str(exc_info.value.detail)
