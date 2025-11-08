.PHONY: help install dev build test clean docker-up docker-down migrate seed

help:
	@echo "Shadow Analytics - Available Commands"
	@echo "======================================"
	@echo "install          Install all dependencies"
	@echo "dev              Start development environment"
	@echo "build            Build all services"
	@echo "test             Run all tests"
	@echo "lint             Run linters"
	@echo "format           Format code"
	@echo "clean            Clean build artifacts"
	@echo "docker-up        Start Docker containers"
	@echo "docker-down      Stop Docker containers"
	@echo "migrate          Run database migrations"
	@echo "seed             Seed database with sample data"
	@echo "backend-dev      Start backend development server"
	@echo "frontend-dev     Start frontend development server"

# Installation
install: install-backend install-frontend

install-backend:
	cd backend && pip install -r requirements.txt -r requirements-dev.txt

install-frontend:
	cd frontend && npm install

# Development
dev: docker-up
	@echo "Development environment started!"
	@echo "Backend API: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@echo "PostgreSQL: localhost:5432"
	@echo "Redis: localhost:6379"

backend-dev:
	cd backend && uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

frontend-dev:
	cd frontend && npm run dev

# Build
build: build-backend build-frontend

build-backend:
	cd backend && docker build -t shadower-backend .

build-frontend:
	cd frontend && docker build -t shadower-frontend .

# Testing
test: test-backend test-frontend

test-backend:
	cd backend && pytest -v --cov=src --cov-report=html

test-frontend:
	cd frontend && npm run test

# Linting
lint: lint-backend lint-frontend

lint-backend:
	cd backend && flake8 src/ && black --check src/ && mypy src/

lint-frontend:
	cd frontend && npm run lint

# Formatting
format: format-backend format-frontend

format-backend:
	cd backend && black src/ && isort src/

format-frontend:
	cd frontend && npm run format

# Docker
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-rebuild:
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

# Database
migrate:
	cd backend && alembic upgrade head

migrate-create:
	cd backend && alembic revision --autogenerate -m "$(MSG)"

migrate-rollback:
	cd backend && alembic downgrade -1

seed:
	psql -h localhost -U postgres -d shadower_analytics -f database/seeds/development/sample_data.sql

# Clean
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	cd frontend && rm -rf .next node_modules

# Production
deploy-staging:
	@echo "Deploying to staging..."
	# Add deployment commands here

deploy-production:
	@echo "Deploying to production..."
	# Add deployment commands here
