import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from app.models.user import User
from app.models.file import FileRecord


class TestFiles:
    """Test file upload and management endpoints."""

    def test_upload_file_without_auth(self, client: TestClient, sample_image_file):
        """Test file upload without authentication."""
        response = client.post(
            "/api/v1/files/upload",
            files={"file": sample_image_file}
        )
        assert response.status_code == 401

    @patch('app.api.deps.verify_clerk_token')
    @patch('app.api.deps.get_or_create_user')
    def test_upload_file_with_auth(
        self,
        mock_get_or_create_user,
        mock_verify_token,
        client: TestClient,
        mock_s3_service,
        sample_image_file,
        test_user_data
    ):
        """Test successful file upload with authentication."""
        # Mock authentication
        mock_verify_token.return_value = test_user_data
        mock_user = User(
            id=test_user_data["id"],
            email=test_user_data["email"]
        )
        mock_get_or_create_user.return_value = mock_user
        
        response = client.post(
            "/api/v1/files/upload",
            files={"file": sample_image_file},
            headers={"Authorization": "Bearer valid-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "file_id" in data
        assert "s3_url" in data
        assert "upload_timestamp" in data
        assert data["message"] == "File uploaded successfully"

    @patch('app.api.deps.verify_clerk_token')
    @patch('app.api.deps.get_or_create_user')
    def test_upload_file_s3_failure(
        self,
        mock_get_or_create_user,
        mock_verify_token,
        client: TestClient,
        sample_image_file,
        test_user_data
    ):
        """Test file upload with S3 failure."""
        # Mock authentication
        mock_verify_token.return_value = test_user_data
        mock_user = User(
            id=test_user_data["id"],
            email=test_user_data["email"]
        )
        mock_get_or_create_user.return_value = mock_user
        
        # Mock S3 service failure
        with patch('app.core.s3.s3_service') as mock_s3:
            mock_s3.validate_file.return_value = True
            mock_s3.upload_file.side_effect = Exception("S3 upload failed")
            
            response = client.post(
                "/api/v1/files/upload",
                files={"file": sample_image_file},
                headers={"Authorization": "Bearer valid-token"}
            )
            
            assert response.status_code == 500
            assert "Failed to upload file" in response.json()["detail"]

    @patch('app.api.deps.verify_clerk_token')
    @patch('app.api.deps.get_or_create_user')
    def test_upload_invalid_file_type(
        self,
        mock_get_or_create_user,
        mock_verify_token,
        client: TestClient,
        test_user_data
    ):
        """Test uploading invalid file type."""
        # Mock authentication
        mock_verify_token.return_value = test_user_data
        mock_user = User(
            id=test_user_data["id"],
            email=test_user_data["email"]
        )
        mock_get_or_create_user.return_value = mock_user
        
        # Mock S3 service validation failure
        with patch('app.core.s3.s3_service') as mock_s3:
            mock_s3.validate_file.side_effect = Exception("Invalid file type")
            
            response = client.post(
                "/api/v1/files/upload",
                files={"file": ("test.txt", b"text content", "text/plain")},
                headers={"Authorization": "Bearer valid-token"}
            )
            
            assert response.status_code == 400  # Changed from 500 to 400

    @patch('app.api.deps.verify_clerk_token')
    @patch('app.api.deps.get_or_create_user')
    def test_list_files_without_files(
        self,
        mock_get_or_create_user,
        mock_verify_token,
        client: TestClient,
        test_user_data
    ):
        """Test listing files when user has no files."""
        # Mock authentication
        mock_verify_token.return_value = test_user_data
        mock_user = User(id=test_user_data["id"], email=test_user_data["email"])
        mock_get_or_create_user.return_value = mock_user
        
        response = client.get(
            "/api/v1/files/",
            headers={"Authorization": "Bearer valid-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["files"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["per_page"] == 10

    @pytest.mark.asyncio
    async def test_list_files_with_files(
        self,
        db_session: AsyncSession,
        test_user_data,
        test_file_data
    ):
        """Test listing files when user has files."""
        from app.api.v1.files import list_files
        from app.models.user import User
        
        # Create user and file in database
        user = User(id=test_user_data["id"], email=test_user_data["email"])
        db_session.add(user)
        await db_session.commit()
        
        # Create file record with the same user_id as the test user
        file_data = test_file_data.copy()
        file_data["user_id"] = test_user_data["id"]
        file_record = FileRecord(**file_data)
        db_session.add(file_record)
        await db_session.commit()
        
        # Mock current user
        with patch('app.api.deps.get_current_user', return_value=user):
            response = await list_files(
                page=1,
                per_page=10,
                current_user=user,
                db=db_session
            )
        
        assert response.total == 1
        assert len(response.files) == 1
        assert response.files[0].id == test_file_data["id"]

    @patch('app.api.deps.verify_clerk_token')
    @patch('app.api.deps.get_or_create_user')
    def test_get_file_not_found(
        self,
        mock_get_or_create_user,
        mock_verify_token,
        client: TestClient,
        test_user_data
    ):
        """Test getting non-existent file."""
        # Mock authentication
        mock_verify_token.return_value = test_user_data
        mock_user = User(id=test_user_data["id"], email=test_user_data["email"])
        mock_get_or_create_user.return_value = mock_user
        
        response = client.get(
            "/api/v1/files/non-existent-id",
            headers={"Authorization": "Bearer valid-token"}
        )
        
        assert response.status_code == 404
        assert "File not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_file_success(
        self,
        db_session: AsyncSession,
        test_user_data,
        test_file_data
    ):
        """Test successfully getting file."""
        from app.api.v1.files import get_file
        from app.models.user import User
        
        # Create user and file in database
        user = User(id=test_user_data["id"], email=test_user_data["email"])
        db_session.add(user)
        await db_session.commit()
        
        # Create file record with the same user_id as the test user
        file_data = test_file_data.copy()
        file_data["user_id"] = test_user_data["id"]
        file_record = FileRecord(**file_data)
        db_session.add(file_record)
        await db_session.commit()
        
        # Get file
        response = await get_file(
            file_id=test_file_data["id"],
            current_user=user,
            db=db_session
        )
        
        assert response.id == test_file_data["id"]
        assert response.filename == test_file_data["filename"]

    @pytest.mark.asyncio
    async def test_delete_file_success(
        self,
        db_session: AsyncSession,
        test_user_data,
        test_file_data
    ):
        """Test successfully deleting file."""
        from app.api.v1.files import delete_file
        from app.models.user import User
        
        # Create user and file in database
        user = User(id=test_user_data["id"], email=test_user_data["email"])
        db_session.add(user)
        await db_session.commit()
        
        # Create file record with the same user_id as the test user
        file_data = test_file_data.copy()
        file_data["user_id"] = test_user_data["id"]
        file_record = FileRecord(**file_data)
        db_session.add(file_record)
        await db_session.commit()
        
        # Mock S3 service
        with patch('app.core.s3.s3_service') as mock_s3:
            mock_s3.delete_file.return_value = True
            
            response = await delete_file(
                file_id=test_file_data["id"],
                current_user=user,
                db=db_session
            )
        
        assert response["message"] == "File deleted successfully"

    @pytest.mark.asyncio
    async def test_delete_file_not_found(
        self,
        db_session: AsyncSession,
        test_user_data
    ):
        """Test deleting non-existent file."""
        from app.api.v1.files import delete_file
        from app.models.user import User
        from fastapi import HTTPException
        
        # Create user in database
        user = User(id=test_user_data["id"], email=test_user_data["email"])
        db_session.add(user)
        await db_session.commit()
        
        # Try to delete non-existent file
        with pytest.raises(HTTPException) as exc_info:
            await delete_file(
                file_id="non-existent-id",
                current_user=user,
                db=db_session
            )
        
        assert exc_info.value.status_code == 404
        assert "File not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_download_file_success(
        self,
        db_session: AsyncSession,
        test_user_data,
        test_file_data
    ):
        """Test successfully generating download URL."""
        from app.api.v1.files import download_file
        from app.models.user import User
        
        # Create user and file in database
        user = User(id=test_user_data["id"], email=test_user_data["email"])
        db_session.add(user)
        await db_session.commit()
        
        # Create file record with the same user_id as the test user
        file_data = test_file_data.copy()
        file_data["user_id"] = test_user_data["id"]
        file_record = FileRecord(**file_data)
        db_session.add(file_record)
        await db_session.commit()
        
        # Mock S3 service
        with patch('app.api.v1.files.s3_service') as mock_s3:
            from unittest.mock import AsyncMock
            mock_s3.generate_presigned_url = AsyncMock(return_value="https://presigned-url.com")
            
            response = await download_file(
                file_id=test_file_data["id"],
                current_user=user,
                db=db_session
            )
        
        assert response["download_url"] == "https://presigned-url.com"
        assert response["expires_in"] == 3600

    @pytest.mark.asyncio
    async def test_download_file_s3_failure(
        self,
        db_session: AsyncSession,
        test_user_data,
        test_file_data
    ):
        """Test download URL generation with S3 failure."""
        from app.api.v1.files import download_file
        from app.models.user import User
        from fastapi import HTTPException
        
        # Create user and file in database
        user = User(id=test_user_data["id"], email=test_user_data["email"])
        db_session.add(user)
        await db_session.commit()
        
        # Create file record with the same user_id as the test user
        file_data = test_file_data.copy()
        file_data["user_id"] = test_user_data["id"]
        file_record = FileRecord(**file_data)
        db_session.add(file_record)
        await db_session.commit()
        
        # Mock S3 service failure
        with patch('app.api.v1.files.s3_service') as mock_s3:
            from unittest.mock import AsyncMock
            mock_s3.generate_presigned_url = AsyncMock(return_value=None)
            
            with pytest.raises(HTTPException) as exc_info:
                await download_file(
                    file_id=test_file_data["id"],
                    current_user=user,
                    db=db_session
                )
        
        assert exc_info.value.status_code == 500
        assert "Failed to generate download URL" in str(exc_info.value.detail)