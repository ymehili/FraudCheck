import boto3
import uuid
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import HTTPException, UploadFile
from typing import Optional
import logging

from .config import settings

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        try:
            # Configure S3 client with optional endpoint URL for LocalStack
            client_config = {
                'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
                'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
                'region_name': settings.AWS_REGION
            }
            
            if settings.AWS_ENDPOINT_URL:
                client_config['endpoint_url'] = settings.AWS_ENDPOINT_URL
                
            self.s3_client = boto3.client('s3', **client_config)
            self.client = self.s3_client  # Alias for tests
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise HTTPException(
                status_code=500,
                detail="AWS credentials not configured"
            )
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize S3 service"
            )

    def generate_s3_key(self, user_id: str, filename: str) -> str:
        """Generate a unique S3 key for the file."""
        file_id = uuid.uuid4().hex
        # Remove any path separators for security
        safe_filename = filename.replace('/', '_').replace('\\', '_')
        return f"uploads/{user_id}/{file_id}_{safe_filename}"

    async def upload_file(self, file: UploadFile, user_id: str) -> dict:
        """Upload file to S3 and return file information."""
        try:
            # Generate S3 key
            s3_key = self.generate_s3_key(user_id, file.filename)
            
            # Reset file pointer
            file.file.seek(0)
            
            # Upload to S3
            self.s3_client.upload_fileobj(
                file.file,
                settings.S3_BUCKET_NAME,
                s3_key,
                ExtraArgs={
                    'ContentType': file.content_type,
                    'ServerSideEncryption': 'AES256'
                }
            )
            
            # Generate S3 URL
            s3_url = f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
            
            return {
                's3_key': s3_key,
                's3_url': s3_url,
                'file_size': file.size,
                'content_type': file.content_type
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"S3 upload failed: {error_code} - {e}")
            
            if error_code == 'NoSuchBucket':
                raise HTTPException(
                    status_code=500,
                    detail="S3 bucket not found"
                )
            elif error_code == 'AccessDenied':
                raise HTTPException(
                    status_code=500,
                    detail="Access denied to S3 bucket"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upload file to S3: {error_code}"
                )
        except Exception as e:
            logger.error(f"Unexpected error during S3 upload: {e}")
            raise HTTPException(
                status_code=500,
                detail="Unexpected error during file upload"
            )

    async def delete_file(self, s3_key: str) -> bool:
        """Delete file from S3."""
        try:
            self.s3_client.delete_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=s3_key
            )
            return True
        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during S3 deletion: {e}")
            return False

    async def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """Generate a presigned URL for file access."""
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.S3_BUCKET_NAME,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL: {e}")
            return None

    def validate_file(self, file: UploadFile) -> bool:
        """Validate file type and size."""
        from ..utils.file_utils import validate_file_upload, FileValidationError
        
        try:
            # Use the unified file validation
            validate_file_upload(file.filename, file.content_type, file.size)
            return True
            
        except FileValidationError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"File validation failed: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"File validation failed: {str(e)}"
            )

# Create global S3 service instance
s3_service = S3Service()