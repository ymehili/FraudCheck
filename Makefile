# CheckGuard Project Makefile
# This Makefile provides automation for the entire project setup and management

.PHONY: help setup install-deps build up down restart logs clean test lint format \
        dev prod db-migrate db-reset backend-shell frontend-shell health status \
        backup restore security-scan update docs deploy

# Default target
.DEFAULT_GOAL := help

# Colors for output
RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[1;33m
BLUE=\033[0;34m
NC=\033[0m # No Color

# Project configuration
PROJECT_NAME := checkguard
COMPOSE_FILE := docker-compose.yml
COMPOSE_PROD_FILE := docker-compose.prod.yml
BACKUP_DIR := ./backups
LOG_DIR := ./logs

## Help
help: ## Show this help message
	@echo "$(BLUE)CheckGuard Project Management$(NC)"
	@echo "$(BLUE)=============================$(NC)"
	@echo ""
	@echo "$(GREEN)Available commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(BLUE)Examples:$(NC)"
	@echo "  make setup    # Initial project setup"
	@echo "  make dev      # Start development environment"
	@echo "  make test     # Run all tests"
	@echo "  make clean    # Clean up everything"

## Setup and Installation
setup: ## Initial project setup (run this first)
	@echo "$(GREEN)Setting up CheckGuard project...$(NC)"
	@echo "$(YELLOW)1. Checking dependencies...$(NC)"
	@command -v docker >/dev/null 2>&1 || (echo "$(RED)Docker is not installed$(NC)" && exit 1)
	@command -v docker-compose >/dev/null 2>&1 || (echo "$(RED)Docker Compose is not installed$(NC)" && exit 1)
	@echo "$(GREEN)✓ Docker and Docker Compose are available$(NC)"
	@echo "$(YELLOW)2. Creating necessary directories...$(NC)"
	@mkdir -p $(BACKUP_DIR) $(LOG_DIR)
	@echo "$(YELLOW)3. Setting up environment files...$(NC)"
	@if [ ! -f .env.production ]; then \
		cp .env.production.template .env.production; \
		echo "$(YELLOW)✓ Created .env.production from template$(NC)"; \
		echo "$(RED)⚠ Please update .env.production with your production values$(NC)"; \
	fi
	@echo "$(YELLOW)4. Building Docker images...$(NC)"
	@$(MAKE) build
	@echo "$(GREEN)✓ Setup complete! Run 'make dev' to start development environment$(NC)"

install-deps: ## Install dependencies for local development
	@echo "$(YELLOW)Installing backend dependencies...$(NC)"
	@cd backend && pip install -r requirements.txt
	@echo "$(YELLOW)Installing frontend dependencies...$(NC)"
	@cd frontend && npm install
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

## Docker Management
build: ## Build all Docker images
	@echo "$(YELLOW)Building Docker images...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) build --no-cache
	@echo "$(GREEN)✓ Docker images built$(NC)"

build-prod: ## Build production Docker images
	@echo "$(YELLOW)Building production Docker images...$(NC)"
	@docker-compose -f $(COMPOSE_PROD_FILE) build --no-cache
	@echo "$(GREEN)✓ Production Docker images built$(NC)"

up: ## Start all services
	@echo "$(YELLOW)Starting all services...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) up -d
	@echo "$(GREEN)✓ All services started$(NC)"
	@$(MAKE) status

down: ## Stop all services
	@echo "$(YELLOW)Stopping all services...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) down
	@echo "$(GREEN)✓ All services stopped$(NC)"

restart: ## Restart all services
	@echo "$(YELLOW)Restarting all services...$(NC)"
	@$(MAKE) down
	@$(MAKE) up

logs: ## Show logs for all services
	@docker-compose -f $(COMPOSE_FILE) logs -f

logs-backend: ## Show backend logs
	@docker-compose -f $(COMPOSE_FILE) logs -f backend

logs-frontend: ## Show frontend logs
	@docker-compose -f $(COMPOSE_FILE) logs -f frontend

logs-db: ## Show database logs
	@docker-compose -f $(COMPOSE_FILE) logs -f postgres

## Development
dev: ## Start development environment
	@echo "$(GREEN)Starting CheckGuard development environment...$(NC)"
	@$(MAKE) up
	@echo ""
	@echo "$(GREEN)🚀 Development environment is ready!$(NC)"
	@echo "$(BLUE)Frontend:$(NC) http://localhost:3000"
	@echo "$(BLUE)Backend API:$(NC) http://localhost:8000"
	@echo "$(BLUE)API Docs:$(NC) http://localhost:8000/docs"
	@echo "$(BLUE)pgAdmin:$(NC) http://localhost:8080"
	@echo "$(BLUE)LocalStack:$(NC) http://localhost:4566"
	@echo ""
	@echo "$(YELLOW)Use 'make logs' to see all logs or 'make down' to stop$(NC)"

prod: ## Start production environment
	@echo "$(GREEN)Starting CheckGuard production environment...$(NC)"
	@if [ ! -f .env.production ]; then \
		echo "$(RED)Error: .env.production file not found$(NC)"; \
		echo "$(YELLOW)Run 'make setup' first or copy .env.production.template to .env.production$(NC)"; \
		exit 1; \
	fi
	@docker-compose -f $(COMPOSE_PROD_FILE) up -d --build
	@echo "$(GREEN)✓ Production environment started$(NC)"

## Database Management
db-migrate: ## Run database migrations
	@echo "$(YELLOW)Running database migrations...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec backend alembic upgrade head
	@echo "$(GREEN)✓ Database migrations completed$(NC)"

db-init: ## Initialize database and S3 (run this after first setup)
	@echo "$(YELLOW)Initializing database and S3...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec backend bash init-db.sh
	@echo "$(GREEN)✓ Database and S3 initialization completed$(NC)"

db-reset: ## Reset database (WARNING: destroys all data)
	@echo "$(RED)⚠ WARNING: This will destroy all database data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo ""; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(YELLOW)Resetting database...$(NC)"; \
		docker-compose -f $(COMPOSE_FILE) down -v; \
		docker-compose -f $(COMPOSE_FILE) up -d postgres redis localstack; \
		sleep 10; \
		docker-compose -f $(COMPOSE_FILE) up -d backend; \
		sleep 5; \
		$(MAKE) db-init; \
		echo "$(GREEN)✓ Database reset completed$(NC)"; \
	else \
		echo "$(YELLOW)Database reset cancelled$(NC)"; \
	fi

db-backup: ## Backup database
	@echo "$(YELLOW)Creating database backup...$(NC)"
	@mkdir -p $(BACKUP_DIR)
	@docker-compose -f $(COMPOSE_FILE) exec -T postgres pg_dump -U checkguard checkguard > $(BACKUP_DIR)/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✓ Database backup created in $(BACKUP_DIR)$(NC)"

db-restore: ## Restore database from backup (specify BACKUP_FILE=filename)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "$(RED)Error: Please specify BACKUP_FILE=filename$(NC)"; \
		echo "$(YELLOW)Example: make db-restore BACKUP_FILE=backup_20240101_120000.sql$(NC)"; \
		exit 1; \
	fi
	@if [ ! -f "$(BACKUP_DIR)/$(BACKUP_FILE)" ]; then \
		echo "$(RED)Error: Backup file $(BACKUP_DIR)/$(BACKUP_FILE) not found$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Restoring database from $(BACKUP_FILE)...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec -T postgres psql -U checkguard -d checkguard < $(BACKUP_DIR)/$(BACKUP_FILE)
	@echo "$(GREEN)✓ Database restored from $(BACKUP_FILE)$(NC)"

## Testing
test: ## Run all tests
	@echo "$(YELLOW)Running all tests...$(NC)"
	@$(MAKE) test-backend
	@$(MAKE) test-frontend
	@echo "$(GREEN)✓ All tests completed$(NC)"

test-backend: ## Run backend tests
	@echo "$(YELLOW)Running backend tests...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec backend pytest --disable-warnings --tb=short --cov-report=html
	@echo "$(GREEN)✓ Backend tests completed$(NC)"

test-frontend: ## Run frontend tests
	@echo "$(YELLOW)Running frontend tests...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec frontend npm test
	@echo "$(GREEN)✓ Frontend tests completed$(NC)"

test-coverage: ## Run tests with coverage
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec backend pytest --cov=app --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Coverage report generated in backend/htmlcov/$(NC)"

## Code Quality
lint: ## Run linting for all code
	@echo "$(YELLOW)Running linting...$(NC)"
	@$(MAKE) lint-backend
	@$(MAKE) lint-frontend
	@echo "$(GREEN)✓ Linting completed$(NC)"

lint-backend: ## Run backend linting
	@echo "$(YELLOW)Running backend linting...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec backend ruff check .
	@docker-compose -f $(COMPOSE_FILE) exec backend mypy app/

lint-frontend: ## Run frontend linting
	@echo "$(YELLOW)Running frontend linting...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec frontend npm run lint

format: ## Format all code
	@echo "$(YELLOW)Formatting code...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec backend ruff format .
	@docker-compose -f $(COMPOSE_FILE) exec frontend npm run format || echo "$(YELLOW)Note: Frontend formatting not configured$(NC)"
	@echo "$(GREEN)✓ Code formatting completed$(NC)"

## Utility
backend-shell: ## Open shell in backend container
	@docker-compose -f $(COMPOSE_FILE) exec backend /bin/bash

frontend-shell: ## Open shell in frontend container
	@docker-compose -f $(COMPOSE_FILE) exec frontend /bin/sh

health: ## Check health of all services
	@echo "$(YELLOW)Checking service health...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) ps
	@echo ""
	@echo "$(YELLOW)Testing API endpoints...$(NC)"
	@curl -f http://localhost:8000/health 2>/dev/null && echo "$(GREEN)✓ Backend API is healthy$(NC)" || echo "$(RED)✗ Backend API is not responding$(NC)"
	@curl -f http://localhost:3000 2>/dev/null >/dev/null && echo "$(GREEN)✓ Frontend is healthy$(NC)" || echo "$(RED)✗ Frontend is not responding$(NC)"

status: ## Show status of all services
	@echo "$(BLUE)CheckGuard Service Status$(NC)"
	@echo "$(BLUE)========================$(NC)"
	@docker-compose -f $(COMPOSE_FILE) ps

## Cleanup
clean: ## Clean up Docker resources
	@echo "$(YELLOW)Cleaning up Docker resources...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) down -v --remove-orphans
	@docker system prune -f
	@echo "$(GREEN)✓ Cleanup completed$(NC)"

clean-all: ## Clean up everything including images
	@echo "$(RED)⚠ WARNING: This will remove all Docker images and volumes!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo ""; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(YELLOW)Cleaning up everything...$(NC)"; \
		docker-compose -f $(COMPOSE_FILE) down -v --remove-orphans; \
		docker-compose -f $(COMPOSE_PROD_FILE) down -v --remove-orphans 2>/dev/null || true; \
		docker system prune -af; \
		docker volume prune -f; \
		echo "$(GREEN)✓ Everything cleaned up$(NC)"; \
	else \
		echo "$(YELLOW)Cleanup cancelled$(NC)"; \
	fi

## Monitoring
monitor: ## Show resource usage
	@echo "$(BLUE)Docker Resource Usage$(NC)"
	@echo "$(BLUE)=====================$(NC)"
	@docker stats --no-stream

top: ## Show running processes in containers
	@docker-compose -f $(COMPOSE_FILE) top

## Security
security-scan: ## Run security scan
	@echo "$(YELLOW)Running security scan...$(NC)"
	@docker run --rm -v $(PWD):/app -w /app securecodewarrior/docker-security-scan
	@echo "$(GREEN)✓ Security scan completed$(NC)"

## Update
update: ## Update dependencies and rebuild
	@echo "$(YELLOW)Updating dependencies...$(NC)"
	@cd backend && pip install --upgrade -r requirements.txt
	@cd frontend && npm update
	@$(MAKE) build
	@echo "$(GREEN)✓ Dependencies updated$(NC)"

## Documentation
docs: ## Generate and serve documentation
	@echo "$(YELLOW)Starting documentation server...$(NC)"
	@echo "$(BLUE)API Documentation:$(NC) http://localhost:8000/docs"
	@echo "$(BLUE)Alternative API Docs:$(NC) http://localhost:8000/redoc"

## Quick commands
quick-restart: down up ## Quick restart (down then up)

quick-logs: ## Show recent logs
	@docker-compose -f $(COMPOSE_FILE) logs --tail=50

quick-status: ## Quick status check
	@docker-compose -f $(COMPOSE_FILE) ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
