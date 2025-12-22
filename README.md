# FraudCheck

**Advanced Document Fraud Detection & Analysis System**

FraudCheck is a comprehensive document forensics and fraud detection platform that uses AI, image analysis, and malware scanning to verify the authenticity of checks and other financial documents. The system provides real-time analysis with detailed risk scoring and forensic reports.

## 📹 Demo Video

Watch the system in action: **[fraudcheck.mp4](./fraudcheck.mp4)**

This video demonstrates the full workflow including document upload, real-time analysis, risk assessment, and report generation.

## ✨ Key Features

- **🔍 Advanced Forensics Analysis**
  - Document forgery detection
  - Image manipulation identification
  - Metadata extraction and verification
  - Alteration detection using image processing

- **🛡️ Multi-Layer Security**
  - Malware scanning with ClamAV
  - File type validation
  - Size and format restrictions
  - Secure file storage with S3

- **🤖 AI-Powered Detection**
  - Google Generative AI integration
  - OCR text extraction
  - Pattern recognition
  - Anomaly detection

- **📊 Comprehensive Risk Scoring**
  - Configurable scoring rules
  - Multiple fraud indicators
  - Detailed forensics reports
  - Historical analysis tracking

- **⚡ Real-Time Processing**
  - Asynchronous task processing with Celery
  - Task status monitoring
  - Streaming analysis results
  - Redis-based caching

- **📱 Modern Web Interface**
  - Responsive design
  - Camera capture support
  - Real-time status updates
  - Interactive dashboards
  - PDF report generation

## 🏗️ Architecture

```
┌─────────────────┐
│   Frontend      │
│   (Next.js)     │
└────────┬────────┘
         │
         ↓
┌─────────────────┐      ┌──────────────┐
│   Backend API   │◄────►│   Redis      │
│   (FastAPI)     │      │   Cache      │
└────────┬────────┘      └──────────────┘
         │
         ↓
┌─────────────────┐      ┌──────────────┐
│  Celery Worker  │◄────►│  PostgreSQL  │
│  (Background)   │      │  Database    │
└────────┬────────┘      └──────────────┘
         │
         ├──────────────►┌──────────────┐
         │               │  LocalStack  │
         │               │  (S3)        │
         │               └──────────────┘
         │
         └──────────────►┌──────────────┐
                         │   ClamAV     │
                         │   Scanner    │
                         └──────────────┘
```

## 🛠️ Technology Stack

### Backend
- **FastAPI** - High-performance async API framework
- **SQLAlchemy** - ORM with PostgreSQL
- **Celery** - Distributed task queue
- **Redis** - Caching and message broker
- **Alembic** - Database migrations
- **Clerk** - Authentication & user management

### AI & Image Processing
- **Google Generative AI** - Document analysis
- **OpenCV** - Image processing
- **Pillow** - Image manipulation
- **PyMuPDF** - PDF processing
- **scikit-image** - Advanced image analysis
- **scikit-learn** - Machine learning algorithms

### Security
- **ClamAV** - Antivirus scanning
- **python-magic** - File type detection
- **boto3** - Secure S3 storage

### Frontend
- **Next.js 15** - React framework
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **Clerk** - Authentication
- **Radix UI** - Accessible components
- **Lucide React** - Icons
- **jsPDF** - PDF generation

### Infrastructure
- **Docker** - Containerization
- **PostgreSQL** - Primary database
- **LocalStack** - Local AWS services
- **Nginx** - Reverse proxy (production)

## 📋 Prerequisites

- **Docker** & **Docker Compose**
- **Node.js** 20+ (for local frontend development)
- **Python** 3.11+ (for local backend development)
- **Clerk Account** (for authentication)
- **Google AI API Key** (for AI features)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/FraudCheck.git
cd FraudCheck
```

### 2. Set Up Environment Variables

Create a `.env.development` file in the root directory:

```bash
# Clerk Authentication
CLERK_SECRET_KEY=your_clerk_secret_key
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up

# Google AI
GOOGLE_AI_API_KEY=your_google_ai_api_key

# API URLs
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
API_BASE_URL=http://backend:8000

# Database
DATABASE_URL=postgresql+asyncpg://FraudCheck:FraudCheck@postgres:5432/FraudCheck

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# AWS/S3
AWS_ENDPOINT_URL=http://localstack:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
S3_BUCKET_NAME=fraudcheck-uploads

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# ClamAV
CLAMAV_SOCKET_PATH=/tmp/clamd.sock
```

### 3. Start the Application

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d
```

### 4. Initialize S3 Bucket

```bash
# Wait for services to be healthy, then initialize S3
docker-compose exec backend python init-s3.py
```

### 5. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Flower (Task Monitor)**: http://localhost:5555 (admin/admin)
- **pgAdmin**: http://localhost:8080 (admin@FraudCheck.com/admin)

## 📖 Usage

### Upload & Analyze Documents

1. Navigate to the **Upload** page
2. Either drag-and-drop a check image or use the camera capture
3. Click "Upload & Analyze"
4. Monitor real-time analysis progress
5. View detailed results including:
   - Risk score
   - Fraud indicators
   - Forensic analysis
   - Extracted data

### View Dashboard

Access the dashboard to see:
- Total analyses performed
- Average risk score
- High-risk document count
- Recent analysis trends

### Analysis History

Browse previous analyses with:
- Filtering by risk level
- Search by filename
- Date range selection
- Detailed drill-down

### Generate Reports

Export analysis results as PDF reports containing:
- Document metadata
- Risk assessment
- Forensic findings
- Recommendations

## 🔧 Development

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest

# Code formatting
ruff check --fix .
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Type checking
npm run type-check

# Build for production
npm run build
```

### Celery Worker

```bash
cd backend

# Start Celery worker
celery -A app.tasks.celery_app worker --loglevel=info

# Monitor with Flower
celery -A app.tasks.celery_app flower
```

## 📁 Project Structure

```
FraudCheck/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/               # API routes
│   │   │   └── v1/           # API version 1
│   │   ├── core/             # Core functionality
│   │   │   ├── forensics.py  # Document forensics
│   │   │   ├── scoring.py    # Risk scoring
│   │   │   └── ocr.py        # OCR processing
│   │   ├── models/           # Database models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── tasks/            # Celery tasks
│   │   └── utils/            # Utility functions
│   ├── alembic/              # Database migrations
│   └── requirements.txt      # Python dependencies
│
├── frontend/                  # Next.js frontend
│   ├── src/
│   │   ├── app/              # App router pages
│   │   ├── components/       # React components
│   │   ├── hooks/            # Custom hooks
│   │   ├── lib/              # Utilities
│   │   └── types/            # TypeScript types
│   └── package.json          # Node dependencies
│
├── nginx/                     # Nginx configuration
├── docker-compose.yml        # Docker services
├── Makefile                  # Development commands
└── README.md                 # This file
```

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v --cov=app --cov-report=html
```

### Frontend Tests

```bash
cd frontend
npm test
```

## 🔐 Security Features

- **File Validation**: Multiple layers of file type and content validation
- **Malware Scanning**: Real-time scanning with ClamAV
- **Authentication**: Secure user auth with Clerk
- **Encryption**: Data encryption in transit and at rest
- **Rate Limiting**: API rate limiting to prevent abuse
- **Input Sanitization**: All inputs validated and sanitized

## 🚢 Deployment

### Production Deployment

1. Update environment variables for production
2. Configure proper database credentials
3. Set up real AWS S3 (replace LocalStack)
4. Configure SSL certificates
5. Use production-grade Redis instance
6. Set up monitoring and logging

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start production services
docker-compose -f docker-compose.prod.yml up -d
```

## 📊 Monitoring

- **Flower**: Monitor Celery tasks at http://localhost:5555
- **pgAdmin**: Database management at http://localhost:8080
- **API Docs**: Swagger UI at http://localhost:8000/docs
- **Logs**: View with `docker-compose logs -f [service-name]`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Google Generative AI for document analysis
- ClamAV for malware detection
- OpenCV for image processing capabilities
- FastAPI and Next.js communities

## 📧 Support

For issues, questions, or contributions, please open an issue on GitHub or contact the maintainers.

---

**Built with ❤️ for secure financial document verification**


