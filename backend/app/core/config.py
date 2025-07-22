from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator
from typing import List, Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-2"
    S3_BUCKET_NAME: str
    AWS_ENDPOINT_URL: Optional[str] = None  # For LocalStack development only
    
    # Clerk Authentication
    CLERK_SECRET_KEY: str
    CLERK_PUBLISHABLE_KEY: str
    
    # Gemini API
    GEMINI_API_KEY: str
    
    @field_validator('DATABASE_URL', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 
                     'S3_BUCKET_NAME', 'CLERK_SECRET_KEY', 'CLERK_PUBLISHABLE_KEY', 
                     'GEMINI_API_KEY', mode='before')
    @classmethod
    def validate_required_secrets(cls, v, info):
        if not v or v in ['', 'test', 'changeme', 'default']:
            raise ValueError(f'{info.field_name} must be set in environment variables and cannot be empty or use default values')
        return v
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "CheckGuard AI"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "https://your-production-domain.com"]
    
    # File Upload & Security
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB (increased for high-res images)
    ALLOWED_FILE_TYPES: List[str] = ["image/jpeg", "image/png", "image/tiff", "image/bmp", "image/webp", "application/pdf"]
    
    # Security Settings
    MALWARE_SCANNING_ENABLED: bool = True
    CONTENT_VALIDATION_ENABLED: bool = True
    SECURE_FILE_NAMING: bool = True
    
    # File Type Specific Limits
    MAX_IMAGE_SIZE: int = 50 * 1024 * 1024  # 50MB for images
    MAX_PDF_SIZE: int = 20 * 1024 * 1024    # 20MB for PDFs
    MAX_IMAGE_DIMENSIONS: int = 50000       # Maximum width/height in pixels
    
    # Additional properties for test compatibility
    project_name: str = "CheckGuard AI"
    debug: bool = False
    secret_key: str
    algorithm: str = "HS256"  # JWT algorithm
    
    @field_validator('secret_key', mode='before')
    @classmethod
    def validate_secret_key(cls, v):
        if not v or v in ['', 'test', 'test-secret-key-for-development', 'changeme', 'default']:
            raise ValueError('secret_key must be set in environment variables and cannot be empty or use default values')
        return v
    
    model_config = ConfigDict(env_file=".env")


settings = Settings()