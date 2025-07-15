#!/bin/bash
set -e

echo "🚀 CheckGuard AI - Automated Setup Script"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    print_error "Please run this script from the CheckGuard project root directory"
    exit 1
fi

# Check prerequisites
print_status "Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker Desktop first."
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.9+ first."
    exit 1
fi

print_success "All prerequisites are installed!"

# Start Docker services
print_status "Starting Docker services (PostgreSQL, LocalStack, Redis, pgAdmin)..."
docker-compose up -d

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 10

# Check if containers are running
if ! docker ps | grep -q checkguard-postgres; then
    print_error "PostgreSQL container failed to start"
    exit 1
fi

if ! docker ps | grep -q checkguard-localstack; then
    print_error "LocalStack container failed to start"
    exit 1
fi

print_success "Docker services are running!"

# Backend setup
print_status "Setting up backend..."
cd backend

python3 -m venv .venv

# Activate virtual environment
print_status "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Wait a bit more for PostgreSQL to be fully ready
print_status "Waiting for PostgreSQL to be fully ready..."
sleep 5

# Create alembic/versions directory if it doesn't exist
if [ ! -d "alembic/versions" ]; then
    print_status "Creating alembic/versions directory..."
    mkdir -p alembic/versions
    print_success "alembic/versions directory created!"
fi

# Check if initial migration exists, create if needed
print_status "Checking database migrations..."
if [ ! "$(ls -A alembic/versions)" ]; then
    print_status "No migrations found, creating initial migration..."
    alembic revision --autogenerate -m "Initial migration"
fi

# Run database migrations
print_status "Running database migrations..."
alembic upgrade head

# Create S3 bucket in LocalStack
print_status "Creating S3 bucket in LocalStack..."
python3 -c "
import boto3
import time
time.sleep(2)  # Give LocalStack a moment
try:
    s3_client = boto3.client('s3', endpoint_url='http://localhost:4566', aws_access_key_id='test', aws_secret_access_key='test', region_name='us-east-1')
    s3_client.create_bucket(Bucket='checkguard-uploads')
    print('✅ S3 bucket created successfully')
except Exception as e:
    print(f'ℹ️  S3 bucket: {e}')
"

print_success "Backend setup completed!"

# Frontend setup
print_status "Setting up frontend..."
cd ../frontend

# Install Node.js dependencies
print_status "Installing Node.js dependencies..."
npm install

print_success "Frontend setup completed!"

# Go back to root
cd ..

print_success "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Start the backend server: ./scripts/start-backend.sh"
echo "2. Start the frontend server: ./scripts/start-frontend.sh"
echo "3. Open your browser to: http://localhost:3000"
echo ""
echo "Useful URLs:"
echo "- Frontend: http://localhost:3000"
echo "- Backend API: http://localhost:8000"
echo "- API Docs: http://localhost:8000/docs"
echo "- pgAdmin: http://localhost:8080"
