#!/bin/bash
set -e

echo "🔄 CheckGuard AI - Development Restart Script"
echo "============================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Stop any running servers
print_status "Stopping any running servers..."
pkill -f "uvicorn.*8000" 2>/dev/null || true
pkill -f "next.*3000" 2>/dev/null || true

# Restart Docker services
print_status "Restarting Docker services..."
docker-compose restart

# Wait for services
print_status "Waiting for services to be ready..."
sleep 5

# Recreate S3 bucket if needed
print_status "Ensuring S3 bucket exists in LocalStack..."
cd backend
source .venv/bin/activate 2>/dev/null || true
python3 -c "
import boto3
try:
    s3_client = boto3.client('s3', endpoint_url='http://localhost:4566', aws_access_key_id='test', aws_secret_access_key='test', region_name='us-east-1')
    s3_client.create_bucket(Bucket='checkguard-uploads')
    print('✅ S3 bucket created')
except Exception as e:
    print(f'ℹ️  S3 bucket: {e}')
" 2>/dev/null || print_warning "Could not create S3 bucket (might already exist)"

cd ..

print_success "Services restarted!"
echo ""
echo "Now you can start the servers:"
echo "1. Backend: ./scripts/start-backend.sh"
echo "2. Frontend: ./scripts/start-frontend.sh (in another terminal)"
