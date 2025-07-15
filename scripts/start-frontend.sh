#!/bin/bash
set -e

echo "🌐 Starting CheckGuard AI Frontend Server"
echo "========================================="

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
if [ ! -f "frontend/package.json" ]; then
    echo "Please run this script from the CheckGuard project root directory"
    exit 1
fi

cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Node modules not found. Please run ./scripts/setup.sh first"
    exit 1
fi

print_success "Environment configured!"

# Start the development server
print_status "Starting Next.js development server on http://localhost:3000..."
npm run dev
