from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://checkguard:checkguard@localhost:5432/checkguard"
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str = "test"
    AWS_SECRET_ACCESS_KEY: str = "test"
    AWS_REGION: str = "us-east-2"
    S3_BUCKET_NAME: str = "checkguard-ai-bucket"
    AWS_ENDPOINT_URL: Optional[str] = "http://localhost:4566"  # For LocalStack
    
    # Clerk Authentication
    CLERK_SECRET_KEY: str = "REDACTED_CLERK_KEY_2"
    CLERK_PUBLISHABLE_KEY: str = "pk_test_c2hpbmluZy10b2FkLTg1LmNsZXJrLmFjY291bnRzLmRldiQ"
    
    # Gemini API
    GEMINI_API_KEY: str = "REDACTED_GEMINI_KEY"
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "CheckGuard AI"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "https://your-production-domain.com"]
    
    # File Upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = ["image/jpeg", "image/png", "application/pdf"]
    
    # Additional properties for test compatibility
    project_name: str = "CheckGuard AI"
    database_url: str = "postgresql+asyncpg://checkguard:checkguard@localhost:5432/checkguard"
    debug: bool = False
    secret_key: str = "test-secret-key-for-development"
    algorithm: str = "HS256"  # JWT algorithm
    
    model_config = ConfigDict(env_file=".env")


settings = Settings()