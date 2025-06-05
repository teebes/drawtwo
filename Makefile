.PHONY: help build up down restart logs shell migrate makemigrations collectstatic createsuperuser test clean ci-check ci-check-docker lint lint-docker format format-docker

# Default target
help:
	@echo "Available commands:"
	@echo ""
	@echo "Full Stack:"
	@echo "  dev            - Start the full development stack (backend + frontend)"
	@echo "  build          - Build all Docker containers"
	@echo "  up             - Start all services"
	@echo "  down           - Stop all services"
	@echo "  restart        - Restart all services"
	@echo "  logs           - View logs from all services"
	@echo ""
	@echo "Backend Only:"
	@echo "  backend-dev    - Start only backend services (db + backend)"
	@echo "  logs-backend   - View logs from backend service"
	@echo "  logs-db        - View logs from database service"
	@echo "  shell          - Access Django shell"
	@echo "  bash           - Access backend container bash"
	@echo "  migrate        - Run Django migrations"
	@echo "  makemigrations - Create Django migrations"
	@echo "  collectstatic  - Collect static files"
	@echo "  createsuperuser - Create Django superuser"
	@echo "  test           - Run backend tests"
	@echo ""
	@echo "Frontend Only:"
	@echo "  frontend-dev   - Start only frontend development server"
	@echo "  frontend-build - Build frontend for production"
	@echo "  frontend-logs  - View logs from frontend service"
	@echo ""
	@echo "CI/Code Quality:"
	@echo "  ci-check       - Run full CI pipeline locally"
	@echo "  ci-check-docker - Run CI checks in Docker container"
	@echo "  lint           - Run code quality checks only"
	@echo "  lint-docker    - Run code quality checks in Docker"
	@echo "  format         - Auto-format code (Black + isort)"
	@echo "  format-docker  - Auto-format code in Docker"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean          - Remove containers and volumes"

# Full Stack Development
dev:
	docker-compose up

# Docker commands
build:
	docker-compose build

up:
	docker-compose up

down:
	docker-compose down

restart:
	docker-compose down && docker-compose up

# Logs
logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-db:
	docker-compose logs -f db

logs-frontend:
	docker-compose logs -f frontend

# Backend Only Development
backend-dev:
	docker-compose up db backend

# Frontend Only Development
frontend-dev:
	docker-compose up frontend

frontend-build:
	docker-compose exec frontend npm run build

# Django commands
shell:
	docker-compose exec backend python manage.py shell

bash:
	docker-compose exec backend bash

migrate:
	docker-compose exec backend python manage.py migrate

makemigrations:
	docker-compose exec backend python manage.py makemigrations

collectstatic:
	docker-compose exec backend python manage.py collectstatic --noinput

createsuperuser:
	docker-compose exec backend python manage.py createsuperuser

test:
	docker-compose exec backend python manage.py test

# CI/Code Quality
ci-check:
	./scripts/run-ci-checks.sh

ci-check-docker:
	@echo "Running CI checks in Docker..."
	docker-compose run --rm backend sh -c "black --check . && isort --check-only . && flake8 . --max-line-length=88 --extend-ignore=E203,W503 --exclude=migrations"
	@echo "✅ All Docker CI checks passed!"

lint:
	@echo "Running code quality checks..."
	black --check backend/
	isort --check-only backend/
	flake8 backend/
	@echo "✅ All linting checks passed!"

lint-docker:
	@echo "Running code quality checks in Docker..."
	docker-compose run --rm backend sh -c "black --check . && isort --check-only . && flake8 . --max-line-length=88 --extend-ignore=E203,W503 --exclude=migrations"
	@echo "✅ All Docker linting checks passed!"

format:
	@echo "Auto-formatting code..."
	black backend/
	isort backend/
	@echo "✅ Code formatted!"

format-docker:
	@echo "Auto-formatting code in Docker..."
	docker-compose run --rm backend sh -c "black . && isort ."
	@echo "✅ Code formatted in Docker!"

# Cleanup
clean:
	docker-compose down -v
	docker system prune -f