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

# Note: AWS S3 bucket should already exist
print_warning "Ensure your AWS S3 bucket exists and credentials are configured"

print_success "Services restarted!"
echo ""
echo "Now you can start the servers:"
echo "1. Backend: ./scripts/start-backend.sh"
echo "2. Frontend: ./scripts/start-frontend.sh (in another terminal)"
