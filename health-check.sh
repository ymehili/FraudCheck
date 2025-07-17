#!/bin/bash

# CheckGuard Health Check Script
# This script checks the health of all services and provides a status report

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
FRONTEND_URL="http://localhost:3000"
BACKEND_URL="http://localhost:8000"
API_HEALTH_URL="http://localhost:8000/health"
POSTGRES_HOST="localhost"
POSTGRES_PORT="5432"
REDIS_HOST="localhost"
REDIS_PORT="6379"
LOCALSTACK_URL="http://localhost:4566"

echo -e "${BLUE}CheckGuard Health Check Report${NC}"
echo -e "${BLUE}==============================${NC}"
echo ""

# Function to check HTTP endpoint
check_http() {
    local url=$1
    local name=$2
    local timeout=${3:-10}
    
    if curl -f -s --max-time $timeout "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $name is healthy${NC}"
        return 0
    else
        echo -e "${RED}❌ $name is not responding${NC}"
        return 1
    fi
}

# Function to check TCP port
check_tcp() {
    local host=$1
    local port=$2
    local name=$3
    local timeout=${4:-5}
    
    if timeout $timeout bash -c "</dev/tcp/$host/$port"; then
        echo -e "${GREEN}✅ $name is healthy${NC}"
        return 0
    else
        echo -e "${RED}❌ $name is not responding${NC}"
        return 1
    fi
}

# Function to check Docker service
check_docker_service() {
    local service=$1
    local status=$(docker-compose ps -q "$service" 2>/dev/null | xargs docker inspect --format='{{.State.Status}}' 2>/dev/null)
    
    if [ "$status" = "running" ]; then
        echo -e "${GREEN}✅ $service container is running${NC}"
        return 0
    else
        echo -e "${RED}❌ $service container is not running (status: $status)${NC}"
        return 1
    fi
}

# Function to check disk space
check_disk_space() {
    local threshold=80
    local usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$usage" -lt "$threshold" ]; then
        echo -e "${GREEN}✅ Disk space is adequate ($usage% used)${NC}"
        return 0
    else
        echo -e "${RED}❌ Disk space is running low ($usage% used)${NC}"
        return 1
    fi
}

# Function to check memory usage
check_memory() {
    local threshold=80
    local usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    
    if [ "$usage" -lt "$threshold" ]; then
        echo -e "${GREEN}✅ Memory usage is normal ($usage% used)${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️ Memory usage is high ($usage% used)${NC}"
        return 1
    fi
}

# Initialize counters
TOTAL_CHECKS=0
FAILED_CHECKS=0

# Docker Services Check
echo -e "${YELLOW}Checking Docker services...${NC}"
for service in postgres redis localstack backend frontend; do
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if ! check_docker_service "$service"; then
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
done

echo ""

# HTTP Services Check
echo -e "${YELLOW}Checking HTTP endpoints...${NC}"

TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if ! check_http "$API_HEALTH_URL" "Backend API Health"; then
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if ! check_http "$FRONTEND_URL" "Frontend" 15; then
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if ! check_http "$LOCALSTACK_URL/_localstack/health" "LocalStack"; then
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo ""

# Database and Cache Check
echo -e "${YELLOW}Checking database and cache...${NC}"

TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if ! check_tcp "$POSTGRES_HOST" "$POSTGRES_PORT" "PostgreSQL"; then
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if ! check_tcp "$REDIS_HOST" "$REDIS_PORT" "Redis"; then
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo ""

# System Resources Check
echo -e "${YELLOW}Checking system resources...${NC}"

TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if ! check_disk_space; then
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if ! check_memory; then
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo ""

# API Functionality Check
echo -e "${YELLOW}Checking API functionality...${NC}"

TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if curl -f -s "$BACKEND_URL/docs" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API documentation is accessible${NC}"
else
    echo -e "${RED}❌ API documentation is not accessible${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo ""

# Summary
echo -e "${BLUE}Health Check Summary${NC}"
echo -e "${BLUE}==================${NC}"

PASSED_CHECKS=$((TOTAL_CHECKS - FAILED_CHECKS))
SUCCESS_RATE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))

echo -e "Total checks: $TOTAL_CHECKS"
echo -e "${GREEN}Passed: $PASSED_CHECKS${NC}"
echo -e "${RED}Failed: $FAILED_CHECKS${NC}"
echo -e "Success rate: $SUCCESS_RATE%"

echo ""

if [ "$FAILED_CHECKS" -eq 0 ]; then
    echo -e "${GREEN}🎉 All systems are healthy!${NC}"
    exit 0
elif [ "$FAILED_CHECKS" -le 2 ]; then
    echo -e "${YELLOW}⚠️ Some issues detected but system is mostly operational${NC}"
    exit 1
else
    echo -e "${RED}❌ Multiple issues detected - immediate attention required${NC}"
    exit 2
fi
