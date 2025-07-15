#!/bin/bash
set -e

echo "🧪 CheckGuard AI - Test Runner"
echo "=============================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    print_error "Please run this script from the CheckGuard project root directory"
    exit 1
fi

# Test backend
print_status "Running backend tests..."
cd backend

if [ ! -d ".venv" ]; then
    print_error "Backend not set up. Please run ./scripts/setup.sh first"
    exit 1
fi

source .venv/bin/activate

# Set test environment variables
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_REGION=us-east-1
export S3_BUCKET_NAME=checkguard-uploads-test
export AWS_ENDPOINT_URL=http://localhost:4566
export CLERK_SECRET_KEY=REDACTED_CLERK_KEY_2
export CLERK_PUBLISHABLE_KEY=pk_test_c2hpbmluZy10b2FkLTg1LmNsZXJrLmFjY291bnRzLmRldiQ
export PYTHONPATH=$(pwd)

# Run backend tests
python -m pytest tests/ -v --cov=app --cov-report=term-missing

if [ $? -eq 0 ]; then
    print_success "Backend tests passed!"
else
    print_error "Backend tests failed!"
    exit 1
fi

cd ..

# Test frontend
print_status "Running frontend tests..."
cd frontend

if [ ! -d "node_modules" ]; then
    print_error "Frontend not set up. Please run ./scripts/setup.sh first"
    exit 1
fi

# Run frontend tests (if they exist)
if [ -f "package.json" ] && grep -q '"test"' package.json; then
    npm test
    if [ $? -eq 0 ]; then
        print_success "Frontend tests passed!"
    else
        print_error "Frontend tests failed!"
        exit 1
    fi
else
    print_status "No frontend tests configured yet"
fi

cd ..

print_success "All tests completed successfully!"
