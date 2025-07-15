.PHONY: help setup start start-backend start-frontend restart test clean

# Default target
help:
	@echo "CheckGuard AI - Development Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup Commands:"
	@echo "  make setup          - Complete project setup"
	@echo "  make clean          - Clean all generated files"
	@echo ""
	@echo "Development Commands:"
	@echo "  make start          - Start both backend and frontend (requires 2 terminals)"
	@echo "  make start-backend  - Start only backend server"
	@echo "  make start-frontend - Start only frontend server"
	@echo "  make restart        - Restart Docker services"
	@echo ""
	@echo "Testing Commands:"
	@echo "  make test           - Run all tests"
	@echo ""
	@echo "Alternative: Use scripts directly:"
	@echo "  ./scripts/setup.sh"
	@echo "  ./scripts/start-backend.sh"
	@echo "  ./scripts/start-frontend.sh"

setup:
	./scripts/setup.sh

start-backend:
	./scripts/start-backend.sh

start-frontend:
	./scripts/start-frontend.sh

restart:
	./scripts/restart.sh

test:
	./scripts/test.sh

clean:
	./scripts/cleanup.sh

# Quick development workflow
dev: setup
	@echo ""
	@echo "🎉 Setup complete! Now run in another terminal:"
	@echo "   make start-frontend"
	@echo ""
	@echo "Starting backend..."
	./scripts/start-backend.sh
