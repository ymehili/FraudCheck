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

    def generate_s3_key(self, user_id: str, filename: str, file_hash: str = None) -> str:
        """Generate a secure S3 key for the file."""
        import re
        from pathlib import Path
        
        # Generate unique file ID
        file_id = uuid.uuid4().hex
        
        # Sanitize filename - remove dangerous characters and normalize
        safe_filename = re.sub(r'[^\w\-_\.]', '_', filename)
        safe_filename = safe_filename.strip('._')  # Remove leading/trailing dots and underscores
        
        # Limit filename length
        if len(safe_filename) > 100:
            name, ext = os.path.splitext(safe_filename)
            safe_filename = name[:95] + ext
        
        # Ensure we have a valid extension
        if not Path(safe_filename).suffix:
            safe_filename += '.bin'
        
        # Create secure path structure
        # Use first 2 chars of file_id for sharding to avoid too many files in one directory
        shard = file_id[:2]
        
        # Include file hash in path if provided for additional uniqueness
        if file_hash:
            hash_prefix = file_hash[:8]
            return f"secure-uploads/{user_id}/{shard}/{hash_prefix}_{file_id}_{safe_filename}"
        else:
            return f"secure-uploads/{user_id}/{shard}/{file_id}_{safe_filename}"

    async def upload_file(self, file: UploadFile, user_id: str, file_hash: str = None) -> dict:
        """Upload file to S3 and return file information."""
        try:
            # Generate secure S3 key
            s3_key = self.generate_s3_key(user_id, file.filename, file_hash)
            
            # Reset file pointer
            file.file.seek(0)
            
            # Upload to S3 with enhanced security settings
            self.s3_client.upload_fileobj(
                file.file,
                settings.S3_BUCKET_NAME,
                s3_key,
                ExtraArgs={
                    'ContentType': file.content_type,
                    'ServerSideEncryption': 'AES256',
                    'Metadata': {
                        'upload-user': user_id,
                        'file-hash': file_hash or 'unknown',
                        'upload-timestamp': str(uuid.uuid4().hex)  # Additional entropy
                    },
                    'ContentDisposition': 'attachment'  # Force download, don't execute in browser
                }
            )
            
            # Generate S3 URL (this should be presigned for access, not public)
            s3_url = f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
            
            return {
                's3_key': s3_key,
                's3_url': s3_url,
                'file_size': file.size,
                'content_type': file.content_type,
                'file_hash': file_hash
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

    async def validate_file(self, file: UploadFile) -> dict:
        """Validate file using comprehensive security checks."""
        from ..utils.security_validation import validate_upload_security, SecurityValidationError
        
        try:
            # Perform comprehensive security validation
            validation_result = await validate_upload_security(file)
            
            logger.info(f"File validation passed for: {file.filename}")
            return validation_result
            
        except SecurityValidationError as e:
            logger.warning(f"Security validation failed for {file.filename}: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Security validation failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"File validation failed: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"File validation failed: {str(e)}"
            )

# Create global S3 service instance
s3_service = S3Service()