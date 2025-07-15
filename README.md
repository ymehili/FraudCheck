# CheckGuard AI - Fraud Detection System

AI-powered check fraud detection through advanced image analysis and machine learning.

## Overview

CheckGuard AI is a comprehensive fraud detection system that analyzes check images for signs of tampering, alteration, or forgery. The system combines computer vision, OCR technology, and machine learning to provide accurate risk assessments and detailed analysis reports.

## Features

- **📸 Image Capture**: Mobile-friendly camera capture with real-time framing
- **📁 File Upload**: Drag-and-drop interface for JPG, PNG, and PDF files
- **🔍 Image Analysis**: Advanced computer vision algorithms for fraud detection
- **📝 OCR Extraction**: Automatic extraction of key check information
- **📊 Risk Scoring**: Comprehensive risk assessment (0-100 scale)
- **📋 Detailed Reports**: JSON reports and downloadable PDFs
- **🔐 Secure Authentication**: Clerk-based user authentication
- **☁️ Cloud Storage**: Secure AWS S3 file storage
- **📱 Mobile Responsive**: Works seamlessly on phones and tablets

## Technology Stack

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **react-webcam** - Camera capture functionality
- **jsPDF** - PDF generation
- **Clerk** - Authentication and user management

### Backend
- **FastAPI** - High-performance Python web framework
- **SQLAlchemy 2.0** - Async ORM with PostgreSQL
- **Alembic** - Database migrations
- **boto3** - AWS S3 integration
- **Pydantic** - Data validation and serialization

### Infrastructure
- **PostgreSQL** - Primary database
- **LocalStack** - Local AWS services simulation (S3, etc.)
- **AWS S3** - File storage (production)
- **Redis** - Caching (optional)
- **Docker** - Containerization for development

## Quick Start (Automated)

### Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- Docker and Docker Compose
- Clerk account (for authentication)

### 🚀 One-Command Setup

**🎯 Ultimate Quick Start (Recommended)**
```bash
git clone <repository-url>
cd CheckGuard
./scripts/quickstart.sh
# Then in another terminal: ./scripts/start-frontend.sh
```

**Option 1: Using Scripts**
```bash
git clone <repository-url>
cd CheckGuard
./scripts/setup.sh
```

**Option 2: Using Make**
```bash
git clone <repository-url>
cd CheckGuard
make setup
```

**Option 3: Complete Dev Setup**
```bash
git clone <repository-url>
cd CheckGuard
make dev  # Setup + start backend (start frontend separately)
```

This automated script will:
- ✅ Check all prerequisites
- ✅ Start Docker services (PostgreSQL, LocalStack, Redis, pgAdmin)
- ✅ Create Python virtual environment
- ✅ Install all backend dependencies
- ✅ Run database migrations
- ✅ Create S3 bucket in LocalStack
- ✅ Install frontend dependencies

### 🎯 Start Development

After setup, start the servers:

**Using Make:**
```bash
# Terminal 1: Start backend
make start-backend

# Terminal 2: Start frontend  
make start-frontend
```

**All Available Commands:**
```bash
make help              # Show all available commands
make setup             # Complete project setup
make start-backend     # Start backend server
make start-frontend    # Start frontend server
make restart           # Restart Docker services
make test              # Run all tests
make clean             # Clean everything
make dev               # Setup + start backend
```

### 🔧 Useful Scripts

**Scripts (./scripts/):**
```bash
./scripts/setup.sh          # Complete setup from scratch
./scripts/start-backend.sh   # Start backend server
./scripts/start-frontend.sh  # Start frontend server  
./scripts/restart.sh         # Restart services (if something goes wrong)
./scripts/test.sh            # Run tests
./scripts/cleanup.sh         # Clean everything (reset to fresh state)
```

**Make Commands:**
```bash
make help                    # Show all available commands
make setup                   # Complete project setup
make dev                     # Setup + start backend
make start-backend          # Start backend server
make start-frontend         # Start frontend server
make restart                # Restart Docker services
make test                   # Run all tests
make clean                  # Clean everything
```

### 🌐 Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **pgAdmin**: http://localhost:8080 (admin@checkguard.com / admin)
- **LocalStack Dashboard**: http://localhost:4566 (for S3 debugging)

## Manual Setup (Alternative)

If you prefer manual setup or need to customize the configuration:

<details>
<summary>Click to expand manual setup instructions</summary>

### Environment Files

Create these files manually:

**Frontend (.env.local):**
```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_c2hpbmluZy10b2FkLTg1LmNsZXJrLmFjY291bnRzLmRldiQ
CLERK_SECRET_KEY=REDACTED_CLERK_KEY_2
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Backend (.env):**
```bash
# Database
DATABASE_URL=postgresql+asyncpg://checkguard:checkguard@localhost:5432/checkguard

# AWS S3 (LocalStack for development)
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=us-east-1
S3_BUCKET_NAME=checkguard-uploads
AWS_ENDPOINT_URL=http://localhost:4566

# Clerk Authentication
CLERK_SECRET_KEY=REDACTED_CLERK_KEY_2
CLERK_PUBLISHABLE_KEY=pk_test_c2hpbmluZy10b2FkLTg1LmNsZXJrLmFjY291bnRzLmRldiQ

# API Settings
API_V1_STR=/api/v1
PROJECT_NAME=CheckGuard AI

# CORS Settings
ALLOWED_ORIGINS=["http://localhost:3000","https://your-production-domain.com"]

# File Upload Settings
MAX_FILE_SIZE=10485760
ALLOWED_FILE_TYPES=["image/jpeg","image/png","application/pdf"]
```

### Manual Steps

```bash
# Start services
docker-compose up -d

# Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head

# Start backend
export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_REGION=us-east-1 S3_BUCKET_NAME=checkguard-uploads AWS_ENDPOINT_URL=http://localhost:4566 CLERK_SECRET_KEY=REDACTED_CLERK_KEY_2 CLERK_PUBLISHABLE_KEY=pk_test_c2hpbmluZy10b2FkLTg1LmNsZXJrLmFjY291bnRzLmRldiQ PYTHONPATH=$(pwd)
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend setup (in another terminal)
cd frontend
npm install
npm run dev
```

</details>

## API Endpoints

### Authentication
- `GET /api/v1/auth/me` - Get current user
- `POST /api/v1/auth/refresh` - Refresh token

### File Management
- `POST /api/v1/files/upload` - Upload file (requires authentication)
- `POST /api/v1/files/upload-debug` - Upload file (debug endpoint, no auth)
- `GET /api/v1/files/` - List user files
- `GET /api/v1/files/{file_id}` - Get file details
- `DELETE /api/v1/files/{file_id}` - Delete file
- `GET /api/v1/files/{file_id}/download` - Generate download URL

## Current Status

### ✅ Implemented Features
- **Core Infrastructure**: Database, authentication, file storage
- **File Upload System**: Working with LocalStack S3 simulation
- **Authentication**: Clerk integration with JWT validation
- **API Endpoints**: RESTful API with FastAPI
- **Frontend UI**: Next.js with Tailwind CSS styling
- **Database**: PostgreSQL with SQLAlchemy and Alembic migrations
- **Development Environment**: Docker Compose setup

### 🔄 In Development
- **Image Analysis Engine**: OpenCV-based forensic analysis
- **OCR Integration**: Gemini API for text extraction  
- **Rule Engine**: JSON-based fraud detection rules
- **Risk Scoring**: Weighted scoring algorithm
- **Report Generation**: PDF export functionality

### 🎯 Next Steps
1. Implement image forensic analysis features
2. Add OCR text extraction with Gemini API
3. Create fraud detection rule engine
4. Build risk scoring system
5. Add comprehensive reporting features

## Troubleshooting

### Common Issues

**Backend server not starting:**
- Run `./scripts/restart.sh` to restart services
- Check Docker containers: `docker ps`
- Verify environment variables are set
- Try `./scripts/cleanup.sh` and `./scripts/setup.sh` for fresh start

**File upload failing:**
- Restart LocalStack: `docker-compose restart checkguard-localstack`
- Recreate S3 bucket: `./scripts/restart.sh`
- Check authentication: sign in with Clerk first

**Database connection issues:**
- Restart PostgreSQL: `docker-compose restart checkguard-postgres`
- Check logs: `docker-compose logs checkguard-postgres`
- Run migrations: `cd backend && source .venv/bin/activate && alembic upgrade head`

**General issues:**
- Use `./scripts/cleanup.sh` to completely reset
- Check Docker disk space: `docker system df`
- Restart Docker Desktop if needed

## Development

### Backend Development

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v

# Code formatting
python -m ruff check . --fix

# Type checking
python -m mypy .

# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Run tests
npm test

# Type checking
npm run type-check

# Linting
npm run lint

# Build for production
npm run build
```

## Testing

### Backend Tests
```bash
cd backend
python -m pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```