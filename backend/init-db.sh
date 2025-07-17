#!/bin/bash
"""
Database Initialization Script for CheckGuard
This script waits for the database to be ready and runs initial setup
"""

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}🔄 Initializing CheckGuard database...${NC}"

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}⏳ Waiting for PostgreSQL to be ready...${NC}"
while ! pg_isready -h postgres -p 5432 -U checkguard; do
    echo -e "${YELLOW}   PostgreSQL is not ready yet, waiting...${NC}"
    sleep 2
done
echo -e "${GREEN}✅ PostgreSQL is ready${NC}"

# Wait for LocalStack to be ready  
echo -e "${YELLOW}⏳ Waiting for LocalStack to be ready...${NC}"
while ! curl -f http://localstack:4566/_localstack/health >/dev/null 2>&1; do
    echo -e "${YELLOW}   LocalStack is not ready yet, waiting...${NC}"
    sleep 2
done
echo -e "${GREEN}✅ LocalStack is ready${NC}"

# Run database migrations
echo -e "${YELLOW}🔧 Running database migrations...${NC}"
alembic upgrade head
echo -e "${GREEN}✅ Database migrations completed${NC}"

# Initialize S3 bucket
echo -e "${YELLOW}🪣 Initializing S3 bucket...${NC}"
python init-s3.py
echo -e "${GREEN}✅ S3 bucket initialization completed${NC}"

echo -e "${GREEN}🎉 Database initialization completed successfully!${NC}"
