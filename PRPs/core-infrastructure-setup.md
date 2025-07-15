name: "Core Infrastructure & Setup - Phase 1"
description: |

## Purpose
Implement the foundational infrastructure for CheckGuard AI's fraud detection system, including Next.js frontend with camera/file upload capabilities, FastAPI backend with S3 integration, PostgreSQL database, and Clerk authentication.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
Build a complete full-stack infrastructure for CheckGuard AI's check image analysis system with mobile-friendly camera capture, secure file upload, user authentication, and database persistence.

## Why
- **Business value**: Enables users to capture and upload check images for fraud detection analysis
- **Integration foundation**: Provides the base infrastructure for Phase 2 image analysis features
- **Security**: Implements proper authentication and secure file handling for sensitive financial documents
- **Scalability**: Uses cloud-native architecture (AWS S3, PostgreSQL, Clerk) for production readiness

## What
Full-stack application with:
- Next.js frontend with Tailwind CSS for responsive design
- Camera capture and file upload components using react-webcam
- FastAPI backend with secure file upload endpoints
- PostgreSQL database with SQLAlchemy ORM
- AWS S3 integration for secure file storage
- Clerk authentication for user management
- Basic PDF generation capabilities using jsPDF

### Success Criteria
- [ ] Users can capture check images using mobile camera with real-time framing
- [ ] Users can upload JPG, PNG, PDF files via drag-and-drop interface
- [ ] Files are securely stored in AWS S3 with proper authentication
- [ ] User authentication works with Clerk (signup, login, session management)
- [ ] Database stores user information and file metadata
- [ ] Backend API endpoints handle file uploads and user operations
- [ ] Mobile-responsive design works on phones and tablets
- [ ] Basic PDF generation functionality is implemented
- [ ] All tests pass and code follows project standards

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://nextjs.org/docs/app/building-your-application/routing/route-handlers
  why: File upload handling in Next.js App Router
  critical: Use FormData for file uploads, handle multipart/form-data

- url: https://www.npmjs.com/package/react-webcam
  why: Camera capture implementation patterns
  critical: Use useRef for webcam reference, getScreenshot() for capture

- url: https://blog.logrocket.com/using-react-webcam-capture-display-images/
  why: Mobile-friendly camera implementation examples
  critical: videoConstraints for mobile cameras, facingMode settings

- url: https://fastapi.tiangolo.com/tutorial/request-files/
  why: FastAPI file upload handling
  critical: Use UploadFile type, async file handling

- url: https://medium.com/@mybytecode/simplified-aws-fastapi-s3-file-upload-3db69431f806
  why: FastAPI S3 integration patterns
  critical: Use boto3 client, handle file streams properly

- url: https://fastapi.tiangolo.com/tutorial/sql-databases/
  why: Official FastAPI SQLAlchemy integration
  critical: Use dependency injection for database sessions

- url: https://berkkaraal.com/blog/2024/09/19/setup-fastapi-project-with-async-sqlalchemy-2-alembic-postgresql-and-docker/
  why: Modern async SQLAlchemy 2.0 setup patterns
  critical: Use async engines, asyncpg driver, proper session management

- url: https://medium.com/@didierlacroix/building-with-clerk-authentication-user-management-part-2-implementing-a-protected-fastapi-f0a727c038e9
  why: Clerk FastAPI integration patterns
  critical: Bearer token validation, dependency injection for auth

- url: https://www.nutrient.io/blog/how-to-convert-html-to-pdf-using-react/
  why: jsPDF implementation in React
  critical: Use dynamic imports in Next.js, disable SSR for client-side PDF

- url: https://github.com/cnndabbler/clerk_fastapi
  why: Working Clerk FastAPI example repository
  critical: Session validation patterns, middleware implementation

- url: https://pypi.org/project/fastapi-clerk-auth/
  why: FastAPI Clerk authentication middleware
  critical: JWT token validation, protected route patterns
```

### Current Codebase tree
```bash
.
├── CLAUDE.md
├── INITIAL.md
├── PROJECT.md
└── PRPs
    └── templates
        └── prp_base.md

3 directories, 4 files
```

### Desired Codebase tree with files to be added and responsibility of file
```bash
.
├── CLAUDE.md
├── INITIAL.md
├── PROJECT.md
├── PRPs/
│   ├── templates/
│   │   └── prp_base.md
│   └── core-infrastructure-setup.md
├── frontend/                          # Next.js application
│   ├── package.json                   # Frontend dependencies
│   ├── next.config.js                 # Next.js configuration
│   ├── tailwind.config.js             # Tailwind CSS configuration
│   ├── tsconfig.json                  # TypeScript configuration
│   ├── .env.local                     # Environment variables
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx             # Root layout with Clerk provider
│   │   │   ├── page.tsx               # Home page
│   │   │   ├── upload/
│   │   │   │   └── page.tsx           # Upload page with camera/file upload
│   │   │   └── api/
│   │   │       └── upload/
│   │   │           └── route.ts       # File upload API route
│   │   ├── components/
│   │   │   ├── CameraCapture.tsx      # Camera capture component
│   │   │   ├── FileUpload.tsx         # Drag-and-drop file upload
│   │   │   ├── PDFGenerator.tsx       # PDF generation component
│   │   │   └── ui/                    # Reusable UI components
│   │   │       ├── Button.tsx
│   │   │       └── Card.tsx
│   │   ├── lib/
│   │   │   ├── s3.ts                  # S3 client configuration
│   │   │   └── utils.ts               # Utility functions
│   │   └── types/
│   │       └── index.ts               # TypeScript type definitions
│   └── public/
│       └── images/
├── backend/                           # FastAPI application
│   ├── requirements.txt               # Python dependencies
│   ├── .env                           # Environment variables
│   ├── alembic.ini                    # Database migration config
│   ├── main.py                        # FastAPI application entry point
│   ├── app/
│   │   ├── __init__.py
│   │   ├── database.py                # Database connection and session
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py                # User model
│   │   │   └── file.py                # File metadata model
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── user.py                # User Pydantic schemas
│   │   │   └── file.py                # File Pydantic schemas
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py                # Dependencies (auth, database)
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── api.py             # API router
│   │   │       ├── auth.py            # Authentication endpoints
│   │   │       └── files.py           # File upload endpoints
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py              # Configuration settings
│   │   │   ├── security.py            # Security utilities
│   │   │   └── s3.py                  # S3 client and operations
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── helpers.py             # Utility functions
│   ├── alembic/                       # Database migrations
│   │   ├── versions/
│   │   └── env.py
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py                # Test configuration
│       ├── test_auth.py               # Authentication tests
│       └── test_files.py              # File upload tests
├── docker-compose.yml                 # Local development with PostgreSQL
├── .gitignore                         # Git ignore file
└── README.md                          # Project documentation
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: Next.js App Router requires specific file structures
# Example: API routes must be in app/api/[route]/route.ts format

# CRITICAL: react-webcam requires client-side rendering
# Example: Use dynamic imports with { ssr: false } in Next.js

# CRITICAL: FastAPI UploadFile uses SpooledTemporaryFile
# Example: File gets closed after reading, must handle properly for S3 upload

# CRITICAL: Clerk requires specific environment variables
# Example: NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY for frontend, CLERK_SECRET_KEY for backend

# CRITICAL: SQLAlchemy 2.0 async syntax is different
# Example: Use async with session patterns, not context managers from 1.x

# CRITICAL: AWS S3 boto3 requires proper credentials
# Example: Use AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables

# CRITICAL: jsPDF requires dynamic imports in Next.js
# Example: const jsPDF = (await import('jspdf')).jsPDF in component

# CRITICAL: PostgreSQL requires asyncpg driver for async operations
# Example: Use postgresql+asyncpg:// connection string, not postgresql://

# CRITICAL: Tailwind CSS requires proper configuration for Next.js
# Example: Include ./src/**/*.{js,ts,jsx,tsx} in tailwind.config.js content

# CRITICAL: File upload validation must happen on both client and server
# Example: Check file size, type, and dimensions on both ends
```

## Implementation Blueprint

### Data models and structure

Create the core data models to ensure type safety and consistency.
```python
# SQLAlchemy ORM models
class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True)  # Clerk user ID
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
class FileRecord(Base):
    __tablename__ = "files"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String, nullable=False)
    s3_key: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    upload_timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# Pydantic schemas for API
class FileUploadResponse(BaseModel):
    file_id: str
    s3_url: str
    upload_timestamp: datetime
    
class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime
```

### List of tasks to be completed to fulfill the PRP in the order they should be completed

```yaml
Task 1: Project Structure Setup
CREATE frontend/ and backend/ directories:
  - Initialize Next.js project with TypeScript and Tailwind CSS
  - Initialize FastAPI project with proper directory structure
  - Set up package.json and requirements.txt with dependencies
  - Create .env files for environment variables

Task 2: Database Setup and Models
CREATE backend/app/database.py:
  - Set up async SQLAlchemy 2.0 with PostgreSQL
  - Configure connection pooling and session management
  - PATTERN: Use async engine with asyncpg driver

CREATE backend/app/models/:
  - Implement User and FileRecord models
  - Set up proper relationships and indexes
  - PATTERN: Use SQLAlchemy 2.0 Mapped annotations

CREATE backend/alembic/:
  - Configure Alembic for database migrations
  - Generate initial migration for User and FileRecord tables
  - PATTERN: Use async migration environment

Task 3: Authentication Setup
CREATE backend/app/core/security.py:
  - Implement Clerk JWT token validation
  - Set up authentication dependencies
  - PATTERN: Use fastapi-clerk-auth middleware patterns

CREATE backend/app/api/deps.py:
  - Create dependency injection for authentication
  - Set up database session dependencies
  - PATTERN: Use FastAPI Depends() for auth and DB

CREATE frontend/src/app/layout.tsx:
  - Set up Clerk provider for authentication
  - Configure authentication wrapper
  - PATTERN: Use ClerkProvider with publishable key

Task 4: AWS S3 Integration
CREATE backend/app/core/s3.py:
  - Set up boto3 S3 client with proper configuration
  - Implement file upload and retrieval functions
  - PATTERN: Use async file handling with proper error handling

CREATE backend/app/api/v1/files.py:
  - Implement file upload endpoint with S3 integration
  - Add file validation and metadata storage
  - PATTERN: Use UploadFile type, handle file streams properly

Task 5: Frontend Camera and File Upload
CREATE frontend/src/components/CameraCapture.tsx:
  - Implement camera capture with react-webcam
  - Add mobile-friendly camera constraints
  - PATTERN: Use useRef for webcam, getScreenshot() for capture

CREATE frontend/src/components/FileUpload.tsx:
  - Implement drag-and-drop file upload
  - Add file validation and preview
  - PATTERN: Use HTML5 file API with proper validation

CREATE frontend/src/app/upload/page.tsx:
  - Combine camera and file upload components
  - Add upload progress and error handling
  - PATTERN: Use React hooks for state management

Task 6: API Integration
CREATE frontend/src/lib/api.ts:
  - Set up API client with proper authentication
  - Implement file upload API calls
  - PATTERN: Use fetch with Bearer token authentication

CREATE backend/app/api/v1/api.py:
  - Set up main API router
  - Include authentication and file routes
  - PATTERN: Use FastAPI router includes

Task 7: PDF Generation
CREATE frontend/src/components/PDFGenerator.tsx:
  - Implement jsPDF with dynamic imports
  - Add PDF generation for reports
  - PATTERN: Use dynamic imports with SSR disabled

Task 8: UI Components and Styling
CREATE frontend/src/components/ui/:
  - Implement reusable UI components
  - Add Tailwind CSS styling
  - PATTERN: Use consistent design system

Task 9: Testing Setup
CREATE backend/tests/:
  - Set up pytest configuration
  - Implement tests for authentication and file upload
  - PATTERN: Use async test patterns with test database

CREATE frontend/tests/ (if needed):
  - Set up Jest/Testing Library
  - Implement component tests
  - PATTERN: Use React Testing Library patterns

Task 10: Development Environment
CREATE docker-compose.yml:
  - Set up PostgreSQL container for development
  - Configure environment variables
  - PATTERN: Use Docker Compose for local development

Task 11: Documentation and Configuration
UPDATE README.md:
  - Add setup instructions
  - Document API endpoints
  - Include troubleshooting guide

CREATE .gitignore:
  - Add proper ignore patterns
  - Exclude environment files and dependencies
  - PATTERN: Use standard Node.js and Python ignore patterns
```

### Per task pseudocode as needed added to each task

```python
# Task 2: Database Setup
# database.py pseudocode
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# PATTERN: Use async engine with proper connection pooling
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/db",
    echo=True,
    pool_size=20,
    max_overflow=0
)

# PATTERN: Use async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# PATTERN: Dependency injection for database sessions
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Task 3: Authentication
# security.py pseudocode
from clerk_backend_api import clerk

# PATTERN: Validate JWT tokens with Clerk
async def verify_token(token: str) -> dict:
    try:
        # CRITICAL: Use Clerk's verify_token method
        session = await clerk.sessions.verify_token(token)
        return {"user_id": session.user_id}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

# PATTERN: Authentication dependency
async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    token = authorization.replace("Bearer ", "")
    user_data = await verify_token(token)
    return await get_or_create_user(db, user_data["user_id"])

# Task 4: S3 Integration
# s3.py pseudocode
import boto3
from botocore.exceptions import ClientError

# PATTERN: Initialize S3 client with proper configuration
s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION
)

# PATTERN: Upload file to S3 with proper error handling
async def upload_file_to_s3(file: UploadFile, key: str) -> str:
    try:
        # CRITICAL: Reset file pointer before upload
        file.file.seek(0)
        
        # PATTERN: Use upload_fileobj for streaming
        s3_client.upload_fileobj(
            file.file,
            settings.S3_BUCKET_NAME,
            key,
            ExtraArgs={'ContentType': file.content_type}
        )
        
        return f"https://{settings.S3_BUCKET_NAME}.s3.amazonaws.com/{key}"
    except ClientError as e:
        raise HTTPException(status_code=500, detail="Upload failed")

# Task 5: Camera Capture
# CameraCapture.tsx pseudocode
import { useRef, useState, useCallback } from 'react';
import Webcam from 'react-webcam';

// PATTERN: Mobile-friendly camera constraints
const videoConstraints = {
  width: 1280,
  height: 720,
  facingMode: "environment" // Use rear camera on mobile
};

const CameraCapture = () => {
  const webcamRef = useRef<Webcam>(null);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);

  // PATTERN: Capture image with proper error handling
  const capture = useCallback(() => {
    const imageSrc = webcamRef.current?.getScreenshot();
    if (imageSrc) {
      setCapturedImage(imageSrc);
      // PATTERN: Convert base64 to blob for upload
      const blob = dataURLtoBlob(imageSrc);
      handleUpload(blob);
    }
  }, [webcamRef]);

  return (
    <div className="camera-container">
      <Webcam
        audio={false}
        height={720}
        ref={webcamRef}
        screenshotFormat="image/jpeg"
        width={1280}
        videoConstraints={videoConstraints}
      />
      <button onClick={capture} className="capture-button">
        Capture Photo
      </button>
    </div>
  );
};

# Task 7: PDF Generation
# PDFGenerator.tsx pseudocode
import { useState } from 'react';
import dynamic from 'next/dynamic';

// PATTERN: Dynamic import to avoid SSR issues
const PDFGenerator = dynamic(() => import('./PDFGeneratorComponent'), {
  ssr: false
});

const generatePDF = async (data: any) => {
  // PATTERN: Dynamic import jsPDF
  const { jsPDF } = await import('jspdf');
  
  const doc = new jsPDF();
  
  // PATTERN: Add content to PDF
  doc.text('Check Analysis Report', 20, 20);
  doc.text(`File: ${data.filename}`, 20, 40);
  doc.text(`Upload Date: ${data.uploadDate}`, 20, 60);
  
  // PATTERN: Save PDF
  doc.save('check-analysis-report.pdf');
};
```

### Integration Points
```yaml
DATABASE:
  - migration: "Create users and files tables with proper indexes"
  - connection: "Use asyncpg driver with SQLAlchemy 2.0 async patterns"
  
CONFIG:
  - add to: backend/app/core/config.py
  - pattern: "Use pydantic BaseSettings for environment variables"
  
ROUTES:
  - add to: backend/app/api/v1/api.py
  - pattern: "router.include_router(files_router, prefix='/files')"
  
FRONTEND:
  - add to: frontend/src/app/layout.tsx
  - pattern: "Wrap app with ClerkProvider and authentication"
  
MIDDLEWARE:
  - add to: backend/main.py
  - pattern: "Add CORS middleware for frontend communication"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Backend validation
cd backend
pip install -r requirements.txt
python -m ruff check . --fix
python -m mypy .

# Frontend validation
cd frontend
npm install
npm run lint
npm run type-check

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests
```python
# CREATE backend/tests/test_auth.py
import pytest
from fastapi.testclient import TestClient

def test_protected_endpoint_without_auth():
    """Test that protected endpoints require authentication"""
    response = client.get("/api/v1/files/")
    assert response.status_code == 401

def test_file_upload_success():
    """Test successful file upload"""
    with open("test_image.jpg", "rb") as f:
        files = {"file": ("test_image.jpg", f, "image/jpeg")}
        headers = {"Authorization": "Bearer valid_token"}
        response = client.post("/api/v1/files/upload", files=files, headers=headers)
        assert response.status_code == 200
        assert "file_id" in response.json()

def test_s3_upload_failure():
    """Test S3 upload failure handling"""
    with mock.patch('app.core.s3.s3_client.upload_fileobj', side_effect=ClientError({}, 'upload')):
        # Test upload failure scenario
        pass
```

```bash
# Run tests and iterate until passing:
cd backend
python -m pytest tests/ -v
cd ../frontend
npm test

# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: Integration Test
```bash
# Start PostgreSQL
docker-compose up -d postgres

# Run database migrations
cd backend
alembic upgrade head

# Start the backend service
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Start the frontend service
cd ../frontend
npm run dev

# Test the upload endpoint
curl -X POST http://localhost:8000/api/v1/files/upload \
  -H "Authorization: Bearer test_token" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test_image.jpg"

# Test frontend
# Open http://localhost:3000
# Test camera capture and file upload functionality

# Expected: File uploads successfully, stored in S3, metadata in database
```

## Final validation Checklist
- [ ] All backend tests pass: `python -m pytest backend/tests/ -v`
- [ ] All frontend tests pass: `npm test` in frontend directory
- [ ] No linting errors: `ruff check backend/` and `npm run lint` in frontend
- [ ] No type errors: `mypy backend/` and `npm run type-check` in frontend
- [ ] Database migrations run successfully: `alembic upgrade head`
- [ ] File upload works via API: `curl` test successful
- [ ] Frontend camera capture works on mobile device
- [ ] Authentication flow works with Clerk
- [ ] Files are properly stored in S3 bucket
- [ ] Database records are created correctly
- [ ] PDF generation works without errors
- [ ] Responsive design works on mobile and desktop
- [ ] Error handling is graceful and informative
- [ ] Environment variables are properly configured

---

## Anti-Patterns to Avoid
- ❌ Don't use sync database operations in async FastAPI
- ❌ Don't skip file validation on both client and server
- ❌ Don't expose AWS credentials in frontend code
- ❌ Don't use jsPDF with server-side rendering
- ❌ Don't forget to handle file cleanup after S3 upload
- ❌ Don't use hardcoded URLs or configuration values
- ❌ Don't skip proper error handling for network operations
- ❌ Don't ignore mobile-specific camera constraints
- ❌ Don't forget to validate file size and type limits
- ❌ Don't skip proper CORS configuration for API