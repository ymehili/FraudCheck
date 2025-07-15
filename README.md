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
- **AWS S3** - File storage
- **Redis** - Caching (optional)
- **Docker** - Containerization for development

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- Docker and Docker Compose
- AWS account (for S3 storage)
- Clerk account (for authentication)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd CheckGuard
```

### 2. Environment Setup

Create environment files:

**Frontend (.env.local):**
```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
CLERK_SECRET_KEY=your_clerk_secret_key
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

**Backend (.env):**
```bash
DATABASE_URL=postgresql+asyncpg://checkguard:checkguard@localhost/checkguard
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-s3-bucket-name
CLERK_SECRET_KEY=your_clerk_secret_key
CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
```

### 3. Start Development Services

```bash
# Start PostgreSQL and other services
docker-compose up -d

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start backend server
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, install frontend dependencies
cd ../frontend
npm install

# Start frontend development server
npm run dev
```

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **pgAdmin**: http://localhost:8080 (admin@checkguard.com / admin)

## API Endpoints

### Authentication
- `GET /api/v1/auth/me` - Get current user
- `POST /api/v1/auth/refresh` - Refresh token

### File Management
- `POST /api/v1/files/upload` - Upload file
- `GET /api/v1/files/` - List user files
- `GET /api/v1/files/{file_id}` - Get file details
- `DELETE /api/v1/files/{file_id}` - Delete file
- `GET /api/v1/files/{file_id}/download` - Generate download URL

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
python -m pytest tests/ -v --cov=app --cov-report=html
```

### Frontend Tests
```bash
cd frontend
npm test
```

## Deployment

### Backend (AWS Elastic Beanstalk)

1. Create Elastic Beanstalk application
2. Configure environment variables
3. Deploy using EB CLI:

```bash
eb init
eb create
eb deploy
```

### Frontend (AWS Amplify)

1. Connect GitHub repository to Amplify
2. Configure build settings
3. Set environment variables
4. Deploy automatically on push

## Security

- All API endpoints require authentication
- Files are stored securely in AWS S3
- JWT tokens are validated on every request
- Input validation on all endpoints
- HTTPS enforced in production

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Support

For support, please contact [support@checkguard.com](mailto:support@checkguard.com) or create an issue on GitHub.

## Changelog

### v1.0.0 (Current)
- Initial release
- Core infrastructure setup
- File upload and storage
- Basic authentication
- PDF report generation
- Mobile-responsive design

---

Built with ❤️ by the CheckGuard AI team