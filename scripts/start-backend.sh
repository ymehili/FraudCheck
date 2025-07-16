#!/bin/bash
set -e

echo "🔧 Starting CheckGuard AI Backend Server"
echo "======================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "backend/main.py" ]; then
    echo "Please run this script from the CheckGuard project root directory"
    exit 1
fi

cd backend

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Please run ./scripts/setup.sh first"
    exit 1
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source .venv/bin/activate

# Start the server
print_status "Starting FastAPI server on http://localhost:8000..."
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
