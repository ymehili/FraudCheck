#!/bin/bash
set -e

echo "🧹 CheckGuard AI - Cleanup Script"
echo "================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Stop and remove Docker containers
print_status "Stopping Docker containers..."
docker-compose down -v

# Remove Docker volumes (this will delete all data)
print_warning "Removing Docker volumes (this will delete database data)..."
docker volume prune -f

# Clean backend
if [ -d "backend/.venv" ]; then
    print_status "Removing Python virtual environment..."
    rm -rf backend/.venv
fi

if [ -d "backend/__pycache__" ]; then
    print_status "Removing Python cache files..."
    find backend -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find backend -name "*.pyc" -delete 2>/dev/null || true
fi

# Clean frontend
if [ -d "frontend/node_modules" ]; then
    print_status "Removing Node.js modules..."
    rm -rf frontend/node_modules
fi

if [ -d "frontend/.next" ]; then
    print_status "Removing Next.js build files..."
    rm -rf frontend/.next
fi

print_success "Cleanup completed!"
echo ""
echo "To set up the project again, run: ./scripts/setup.sh"
