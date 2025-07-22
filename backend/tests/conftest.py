import pytest
import pytest_asyncio
import asyncio
import uuid
from typing import AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from app.main import app
from app.database import Base, get_db
from app.core.config import settings


# Override settings for testing
test_settings = settings.model_copy()
test_settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create test database engine."""
    engine = create_async_engine(
        test_settings.DATABASE_URL,
        echo=False,
        future=True,
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
def client(db_session: AsyncSession):
    """Create test client with test database."""
    import time
    import random
    
    # Create unique user ID for this test
    unique_suffix = f"{int(time.time() * 1000000)}-{random.randint(1000, 9999)}"
    unique_user_id = f"test-user-{unique_suffix}"
    
    async def override_get_db():
        yield db_session
    
    def override_get_current_user():
        from app.models.user import User
        from datetime import datetime, timezone
        return User(
            id=unique_user_id, 
            email=f"{unique_user_id}@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    
    from app.api.deps import get_current_user
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_s3_service():
    """Mock S3 service for testing."""
    with patch('app.api.v1.files.s3_service') as mock_s3:
        # Mock sync methods
        mock_s3.validate_file.return_value = True
        mock_s3.delete_file.return_value = True
        
        # Mock async methods
        from unittest.mock import AsyncMock
        mock_s3.upload_file = AsyncMock(return_value={
            's3_key': 'test/key.jpg',
            's3_url': 'https://test-bucket.s3.amazonaws.com/test/key.jpg',
            'file_size': 1024,
            'content_type': 'image/jpeg'
        })
        mock_s3.generate_presigned_url = AsyncMock(return_value='https://presigned-url.com')
        yield mock_s3


@pytest.fixture
def authenticated_client(db_session: AsyncSession):
    """Create test client with test database and automatic authentication."""
    async def override_get_db():
        yield db_session
    
    def override_get_current_user():
        from app.models.user import User
        from datetime import datetime, timezone
        # Use unique user ID for each test to ensure isolation
        import uuid
        unique_user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        return User(
            id=unique_user_id, 
            email=f"{unique_user_id}@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    
    from app.api.deps import get_current_user
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    # Also mock the verification function
    with patch('app.core.security.verify_clerk_token') as mock_verify:
        mock_verify.return_value = {
            'user_id': 'test-user-id',
            'id': 'test-user-id',
            'email': 'test@example.com'
        }
        
        with TestClient(app) as test_client:
            yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def setup_auth_for_all_tests():
    """Setup authentication for all tests automatically."""
    with patch('app.core.security.verify_clerk_token') as mock_verify:
        mock_verify.return_value = {
            'user_id': 'test-user-id',
            'id': 'test-user-id', 
            'email': 'test@example.com'
        }
        yield mock_verify


@pytest.fixture
def test_user_data():
    """Test user data with consistent identifiers."""
    import uuid
    user_id = f"test-user-{uuid.uuid4().hex[:8]}"
    return {
        'id': user_id,
        'email': f'{user_id}@example.com'
    }


@pytest.fixture
def test_file_data():
    """Test file data."""
    # Generate unique file ID and user ID for each test
    file_id = f"test-file-{uuid.uuid4().hex[:8]}"
    user_id = f"test-user-{uuid.uuid4().hex[:8]}"
    
    return {
        'id': file_id,
        'user_id': user_id,
        'filename': 'test-check.jpg',
        's3_key': f'uploads/{user_id}/{file_id}_test-check.jpg',
        's3_url': f'https://test-bucket.s3.amazonaws.com/uploads/{user_id}/{file_id}_test-check.jpg',
        'file_size': 1024,
        'mime_type': 'image/jpeg'
    }


@pytest.fixture
def auth_headers():
    """Authentication headers for test requests."""
    return {'Authorization': 'Bearer test-token'}


@pytest.fixture
def sample_image_file():
    """Sample image file for testing."""
    import io
    from PIL import Image
    
    # Create a simple test image
    image = Image.new('RGB', (100, 100), color='red')
    image_bytes = io.BytesIO()
    image.save(image_bytes, format='JPEG')
    image_bytes.seek(0)
    
    return ('test-image.jpg', image_bytes, 'image/jpeg')


@pytest.fixture
def sample_pdf_file():
    """Sample PDF file for testing."""
    import io
    
    # Create a simple PDF content
    pdf_content = b'%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<</Size 4/Root 1 0 R>>\nstartxref\n174\n%%EOF'
    
    return ('test-document.pdf', io.BytesIO(pdf_content), 'application/pdf')