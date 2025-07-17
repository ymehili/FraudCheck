#!/bin/bash

# CheckGuard Development Setup Script
# This script helps you get started with CheckGuard development quickly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project info
PROJECT_NAME="CheckGuard"
REQUIRED_DOCKER_VERSION="20.0.0"
REQUIRED_DOCKER_COMPOSE_VERSION="2.0.0"

echo -e "${BLUE}$PROJECT_NAME Development Setup${NC}"
echo -e "${BLUE}===============================${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to compare versions
version_ge() {
    printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

# Check dependencies
echo -e "${YELLOW}Checking dependencies...${NC}"

# Check Docker
if ! command_exists docker; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo -e "${YELLOW}Please install Docker from: https://docs.docker.com/get-docker/${NC}"
    exit 1
fi

DOCKER_VERSION=$(docker --version | sed 's/Docker version //' | sed 's/,.*//')
echo -e "${GREEN}✅ Docker found: $DOCKER_VERSION${NC}"

# Check Docker Compose
if ! command_exists docker-compose; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    echo -e "${YELLOW}Please install Docker Compose from: https://docs.docker.com/compose/install/${NC}"
    exit 1
fi

COMPOSE_VERSION=$(docker-compose --version | sed 's/docker-compose version //' | sed 's/,.*//')
echo -e "${GREEN}✅ Docker Compose found: $COMPOSE_VERSION${NC}"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    echo -e "${YELLOW}Please start Docker and try again${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker is running${NC}"

# Check Make
if ! command_exists make; then
    echo -e "${YELLOW}⚠️ Make is not installed (optional but recommended)${NC}"
    echo -e "${YELLOW}You can still use docker-compose commands directly${NC}"
fi

echo ""

# Setup project
echo -e "${YELLOW}Setting up project...${NC}"

# Create directories
echo -e "${YELLOW}Creating necessary directories...${NC}"
mkdir -p backups logs

# Setup environment files
echo -e "${YELLOW}Setting up environment files...${NC}"

if [ ! -f .env.production ]; then
    cp .env.production.template .env.production
    echo -e "${GREEN}✅ Created .env.production from template${NC}"
    echo -e "${RED}⚠️ Please update .env.production with your production values before deploying${NC}"
fi

# Check if ports are available
echo -e "${YELLOW}Checking port availability...${NC}"

check_port() {
    local port=$1
    local service=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${RED}❌ Port $port is already in use (needed for $service)${NC}"
        echo -e "${YELLOW}Please stop the service using port $port or change the port in docker-compose.yml${NC}"
        return 1
    else
        echo -e "${GREEN}✅ Port $port is available ($service)${NC}"
        return 0
    fi
}

PORTS_OK=true
check_port 3000 "Frontend" || PORTS_OK=false
check_port 8000 "Backend API" || PORTS_OK=false
check_port 5432 "PostgreSQL" || PORTS_OK=false
check_port 6379 "Redis" || PORTS_OK=false
check_port 4566 "LocalStack" || PORTS_OK=false
check_port 8080 "pgAdmin" || PORTS_OK=false

if [ "$PORTS_OK" = false ]; then
    echo ""
    echo -e "${RED}Some ports are already in use. Please resolve port conflicts before continuing.${NC}"
    exit 1
fi

echo ""

# Build and start services
echo -e "${YELLOW}Building Docker images...${NC}"
docker-compose build

echo ""
echo -e "${YELLOW}Starting services...${NC}"
docker-compose up -d

echo ""
echo -e "${YELLOW}Waiting for services to be ready...${NC}"

# Wait for database
echo -e "${YELLOW}Waiting for database...${NC}"
timeout 60 bash -c 'until docker-compose exec -T postgres pg_isready -U checkguard; do sleep 2; done'

# Wait for backend
echo -e "${YELLOW}Waiting for backend API...${NC}"
timeout 60 bash -c 'until curl -f http://localhost:8000/health >/dev/null 2>&1; do sleep 2; done'

# Wait for frontend
echo -e "${YELLOW}Waiting for frontend...${NC}"
timeout 60 bash -c 'until curl -f http://localhost:3000 >/dev/null 2>&1; do sleep 2; done'

echo ""
echo -e "${GREEN}🎉 $PROJECT_NAME development environment is ready!${NC}"
echo ""
echo -e "${BLUE}Services:${NC}"
echo -e "  ${GREEN}Frontend:${NC}     http://localhost:3000"
echo -e "  ${GREEN}Backend API:${NC}  http://localhost:8000"
echo -e "  ${GREEN}API Docs:${NC}     http://localhost:8000/docs"
echo -e "  ${GREEN}pgAdmin:${NC}      http://localhost:8080 (admin@checkguard.com / admin)"
echo -e "  ${GREEN}LocalStack:${NC}   http://localhost:4566"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
if command_exists make; then
    echo -e "  ${YELLOW}make logs${NC}           - View all logs"
    echo -e "  ${YELLOW}make status${NC}         - Check service status"
    echo -e "  ${YELLOW}make test${NC}           - Run tests"
    echo -e "  ${YELLOW}make down${NC}           - Stop all services"
    echo -e "  ${YELLOW}make help${NC}           - Show all available commands"
else
    echo -e "  ${YELLOW}docker-compose logs${NC}     - View all logs"
    echo -e "  ${YELLOW}docker-compose ps${NC}       - Check service status"
    echo -e "  ${YELLOW}docker-compose down${NC}     - Stop all services"
fi
echo ""
echo -e "${GREEN}Happy coding! 🚀${NC}"
