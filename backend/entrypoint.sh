#!/bin/bash
# Backend Entrypoint Script for CheckGuard
# This script handles initialization and starts the backend service

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}🚀 Starting CheckGuard Backend...${NC}"

# If this is the first run or if INIT_DB is set, run initialization
if [ "$INIT_DB" = "true" ] || [ ! -f /app/.initialized ]; then
    echo -e "${YELLOW}🔧 Running initialization...${NC}"
    
    # Run database initialization script
    if [ -f "/app/init-db.sh" ]; then
        bash /app/init-db.sh
    else
        echo -e "${RED}❌ Initialization script not found${NC}"
        exit 1
    fi
    
    # Mark as initialized
    touch /app/.initialized
    echo -e "${GREEN}✅ Initialization completed${NC}"
else
    echo -e "${YELLOW}⏭️ Skipping initialization (already done)${NC}"
fi

# Check if we should run migrations instead of starting the server
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo -e "${YELLOW}🔄 Running database migrations...${NC}"
    cd /app
    
    # Verify alembic.ini exists
    if [ ! -f "alembic.ini" ]; then
        echo -e "${RED}❌ alembic.ini not found in /app${NC}"
        exit 1
    fi
    
    # Verify alembic directory exists
    if [ ! -d "alembic" ]; then
        echo -e "${RED}❌ alembic directory not found in /app${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}📁 Current directory: $(pwd)${NC}"
    echo -e "${YELLOW}📄 Files: $(ls -la)${NC}"
    
    # Run migrations with explicit configuration file
    python -m alembic -c alembic.ini upgrade head
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Database migrations completed successfully${NC}"
        exit 0
    else
        echo -e "${RED}❌ Database migrations failed${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}🌟 Starting FastAPI server...${NC}"

# Start the application
exec "$@"
