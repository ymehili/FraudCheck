from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://checkguard:checkguard@localhost:5432/checkguard"
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-2"
    S3_BUCKET_NAME: str = "checkguard-uploads"
    AWS_ENDPOINT_URL: Optional[str] = None  # For LocalStack
    
    # Clerk Authentication
    CLERK_SECRET_KEY: str
    CLERK_PUBLISHABLE_KEY: str
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "CheckGuard AI"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # File Upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = ["image/jpeg", "image/png", "application/pdf"]
    
    model_config = ConfigDict(env_file=".env")


settings = Settings()