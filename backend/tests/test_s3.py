import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, UploadFile
from botocore.exceptions import ClientError, NoCredentialsError

from app.core.s3 import S3Service
from app.core.config import settings


class TestS3Service:
    """Test S3 service functionality."""

    def test_s3_service_init_success(self):
        """Test successful S3 service initialization."""
        with patch('boto3.client') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.return_value = mock_client
            
            service = S3Service()
            assert service.s3_client == mock_client

    def test_s3_service_init_no_credentials(self):
        """Test S3 service initialization with no credentials."""
        with patch('boto3.client', side_effect=NoCredentialsError()):
            with pytest.raises(HTTPException) as exc_info:
                S3Service()
            
            assert exc_info.value.status_code == 500
            assert "AWS credentials not configured" in str(exc_info.value.detail)

    def test_s3_service_init_general_exception(self):
        """Test S3 service initialization with general exception."""
        with patch('boto3.client', side_effect=Exception("Connection failed")):
            with pytest.raises(HTTPException) as exc_info:
                S3Service()
            
            assert exc_info.value.status_code == 500
            assert "Failed to initialize S3 service" in str(exc_info.value.detail)

    def test_s3_service_init_with_endpoint_url(self):
        """Test S3 service initialization with endpoint URL."""
        with patch('boto3.client') as mock_boto3:
            with patch.object(settings, 'AWS_ENDPOINT_URL', 'http://localhost:4566'):
                mock_client = MagicMock()
                mock_boto3.return_value = mock_client
                
                S3Service()
                
                # Verify endpoint_url was passed to boto3.client
                mock_boto3.assert_called_once()
                args, kwargs = mock_boto3.call_args
                assert 'endpoint_url' in kwargs
                assert kwargs['endpoint_url'] == 'http://localhost:4566'

    def test_generate_s3_key(self):
        """Test S3 key generation."""
        with patch('boto3.client'):
            service = S3Service()
            
            user_id = "user123"
            filename = "test-file.jpg"
            
            with patch('app.core.s3.uuid.uuid4') as mock_uuid:
                mock_uuid.return_value = MagicMock()
                mock_uuid.return_value.hex = "abcd1234"
                key = service.generate_s3_key(user_id, filename)
                
                expected = f"uploads/{user_id}/abcd1234_{filename}"
                assert key == expected

    def test_generate_s3_key_with_path_separators(self):
        """Test S3 key generation with path separators in filename."""
        with patch('boto3.client'):
            service = S3Service()
            
            user_id = "user123"
            filename = "path/to/file.jpg"
            
            key = service.generate_s3_key(user_id, filename)
            
            # Should replace path separators
            assert "/" not in key.split("/")[-1]  # filename part shouldn't have /
            assert "\\" not in key

    @pytest.mark.asyncio
    async def test_upload_file_success(self):
        """Test successful file upload."""
        with patch('boto3.client') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.return_value = mock_client
            
            service = S3Service()
            
            # Mock file
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = "test.jpg"
            mock_file.content_type = "image/jpeg"
            mock_file.size = 1024
            mock_file.file = MagicMock()
            
            # Mock S3 upload
            mock_client.upload_fileobj.return_value = None
            
            with patch.object(service, 'generate_s3_key', return_value="test/key.jpg"):
                result = await service.upload_file(mock_file, "user123")
                
                assert result['s3_key'] == "test/key.jpg"
                assert result['file_size'] == 1024
                assert result['content_type'] == "image/jpeg"
                assert "s3_url" in result

    @pytest.mark.asyncio
    async def test_upload_file_no_such_bucket(self):
        """Test file upload with no such bucket error."""
        with patch('boto3.client') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.return_value = mock_client
            
            service = S3Service()
            
            # Mock file
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = "test.jpg"
            mock_file.content_type = "image/jpeg"
            mock_file.size = 1024
            mock_file.file = MagicMock()
            
            # Mock S3 upload error
            error_response = {'Error': {'Code': 'NoSuchBucket'}}
            mock_client.upload_fileobj.side_effect = ClientError(error_response, 'upload_fileobj')
            
            with pytest.raises(HTTPException) as exc_info:
                await service.upload_file(mock_file, "user123")
            
            assert exc_info.value.status_code == 500
            assert "S3 bucket not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_file_access_denied(self):
        """Test file upload with access denied error."""
        with patch('boto3.client') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.return_value = mock_client
            
            service = S3Service()
            
            # Mock file
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = "test.jpg"
            mock_file.content_type = "image/jpeg"
            mock_file.size = 1024
            mock_file.file = MagicMock()
            
            # Mock S3 upload error
            error_response = {'Error': {'Code': 'AccessDenied'}}
            mock_client.upload_fileobj.side_effect = ClientError(error_response, 'upload_fileobj')
            
            with pytest.raises(HTTPException) as exc_info:
                await service.upload_file(mock_file, "user123")
            
            assert exc_info.value.status_code == 500
            assert "Access denied to S3 bucket" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_file_other_client_error(self):
        """Test file upload with other client error."""
        with patch('boto3.client') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.return_value = mock_client
            
            service = S3Service()
            
            # Mock file
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = "test.jpg"
            mock_file.content_type = "image/jpeg"
            mock_file.size = 1024
            mock_file.file = MagicMock()
            
            # Mock S3 upload error
            error_response = {'Error': {'Code': 'SomeOtherError'}}
            mock_client.upload_fileobj.side_effect = ClientError(error_response, 'upload_fileobj')
            
            with pytest.raises(HTTPException) as exc_info:
                await service.upload_file(mock_file, "user123")
            
            assert exc_info.value.status_code == 500
            assert "Failed to upload file to S3: SomeOtherError" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_file_general_exception(self):
        """Test file upload with general exception."""
        with patch('boto3.client') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.return_value = mock_client
            
            service = S3Service()
            
            # Mock file
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = "test.jpg"
            mock_file.content_type = "image/jpeg"
            mock_file.size = 1024
            mock_file.file = MagicMock()
            
            # Mock S3 upload error
            mock_client.upload_fileobj.side_effect = Exception("Unexpected error")
            
            with pytest.raises(HTTPException) as exc_info:
                await service.upload_file(mock_file, "user123")
            
            assert exc_info.value.status_code == 500
            assert "Unexpected error during file upload" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_delete_file_success(self):
        """Test successful file deletion."""
        with patch('boto3.client') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.return_value = mock_client
            
            service = S3Service()
            
            # Mock S3 delete
            mock_client.delete_object.return_value = None
            
            result = await service.delete_file("test/key.jpg")
            
            assert result is True
            mock_client.delete_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_file_client_error(self):
        """Test file deletion with client error."""
        with patch('boto3.client') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.return_value = mock_client
            
            service = S3Service()
            
            # Mock S3 delete error
            error_response = {'Error': {'Code': 'NoSuchKey'}}
            mock_client.delete_object.side_effect = ClientError(error_response, 'delete_object')
            
            result = await service.delete_file("test/key.jpg")
            
            assert result is False

    @pytest.mark.asyncio
    async def test_delete_file_general_exception(self):
        """Test file deletion with general exception."""
        with patch('boto3.client') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.return_value = mock_client
            
            service = S3Service()
            
            # Mock S3 delete error
            mock_client.delete_object.side_effect = Exception("Unexpected error")
            
            result = await service.delete_file("test/key.jpg")
            
            assert result is False

    @pytest.mark.asyncio
    async def test_generate_presigned_url_success(self):
        """Test successful presigned URL generation."""
        with patch('boto3.client') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.return_value = mock_client
            
            service = S3Service()
            
            # Mock presigned URL generation
            mock_client.generate_presigned_url.return_value = "https://presigned-url.com"
            
            result = await service.generate_presigned_url("test/key.jpg")
            
            assert result == "https://presigned-url.com"
            mock_client.generate_presigned_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_presigned_url_client_error(self):
        """Test presigned URL generation with client error."""
        with patch('boto3.client') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.return_value = mock_client
            
            service = S3Service()
            
            # Mock presigned URL generation error
            error_response = {'Error': {'Code': 'NoSuchKey'}}
            mock_client.generate_presigned_url.side_effect = ClientError(error_response, 'generate_presigned_url')
            
            result = await service.generate_presigned_url("test/key.jpg")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_generate_presigned_url_general_exception(self):
        """Test presigned URL generation with general exception."""
        with patch('boto3.client') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.return_value = mock_client
            
            service = S3Service()
            
            # Mock presigned URL generation error
            mock_client.generate_presigned_url.side_effect = Exception("Unexpected error")
            
            result = await service.generate_presigned_url("test/key.jpg")
            
            assert result is None

    def test_validate_file_success(self):
        """Test successful file validation."""
        with patch('boto3.client'):
            service = S3Service()
            
            # Mock file
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = "test.jpg"
            mock_file.content_type = "image/jpeg"
            mock_file.size = 1024  # Small file
            
            with patch.object(settings, 'MAX_FILE_SIZE', 10 * 1024 * 1024):  # 10MB
                with patch.object(settings, 'ALLOWED_FILE_TYPES', ["image/jpeg", "image/png"]):
                    result = service.validate_file(mock_file)
                    assert result is True

    def test_validate_file_too_large(self):
        """Test file validation with file too large."""
        with patch('boto3.client'):
            service = S3Service()
            
            # Mock file
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = "test.jpg"
            mock_file.content_type = "image/jpeg"
            mock_file.size = 20 * 1024 * 1024  # 20MB
            
            with patch.object(settings, 'MAX_FILE_SIZE', 10 * 1024 * 1024):  # 10MB
                with pytest.raises(HTTPException) as exc_info:
                    service.validate_file(mock_file)
                
                assert exc_info.value.status_code == 413
                assert "File too large" in str(exc_info.value.detail)

    def test_validate_file_invalid_type(self):
        """Test file validation with invalid file type."""
        with patch('boto3.client'):
            service = S3Service()
            
            # Mock file
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = "test.txt"
            mock_file.content_type = "text/plain"
            mock_file.size = 1024
            
            with patch.object(settings, 'ALLOWED_FILE_TYPES', ["image/jpeg", "image/png"]):
                with pytest.raises(HTTPException) as exc_info:
                    service.validate_file(mock_file)
                
                assert exc_info.value.status_code == 400
                assert "File type not allowed" in str(exc_info.value.detail)

    def test_validate_file_no_filename(self):
        """Test file validation with no filename."""
        with patch('boto3.client'):
            service = S3Service()
            
            # Mock file
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = None
            mock_file.content_type = "image/jpeg"
            mock_file.size = 1024
            
            with pytest.raises(HTTPException) as exc_info:
                service.validate_file(mock_file)
            
            assert exc_info.value.status_code == 400
            assert "Filename is required" in str(exc_info.value.detail)

    def test_validate_file_empty_filename(self):
        """Test file validation with empty filename."""
        with patch('boto3.client'):
            service = S3Service()
            
            # Mock file
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = ""
            mock_file.content_type = "image/jpeg"
            mock_file.size = 1024
            
            with pytest.raises(HTTPException) as exc_info:
                service.validate_file(mock_file)
            
            assert exc_info.value.status_code == 400
            assert "Filename is required" in str(exc_info.value.detail)
