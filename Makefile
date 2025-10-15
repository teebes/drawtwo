.PHONY: help build up down restart logs shell migrate makemigrations collectstatic createsuperuser test clean ci-check ci-check-docker lint lint-docker format format-docker cleanup-emails cleanup-emails-dry celery-dev logs-celery logs-redis

# Default target
help:
	@echo "Available commands:"
	@echo ""
	@echo "Full Stack:"
	@echo "  dev            - Start the full development stack (backend + frontend + celery)"
	@echo "  build          - Build all Docker containers"
	@echo "  build-prod     - Build for production"
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
	@echo "Celery Task Queue:"
	@echo "  celery-dev     - Start backend services with Celery (db + backend + redis + celery)"
	@echo "  logs-celery    - View Celery worker logs"
	@echo "  logs-redis     - View Redis logs"
	@echo "  celery-shell   - Access Celery worker container bash"
	@echo "  celery-flower  - Start Celery Flower monitoring (visit http://localhost:5555)"
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
	@echo "Database:"
	@echo "  reset-db       - Reset database to fresh state (with 5s warning)"
	@echo "  reset-db-with-superuser - Reset database and create superuser"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean          - Remove containers and volumes"
	@echo "  cleanup-emails-dry - Show old email confirmations that would be deleted"
	@echo "  cleanup-emails - Delete old email confirmations (7+ days old)"

# Full Stack Development
dev:
	docker-compose up

# Docker commands
build:
	docker-compose build

build-prod:
	docker build -t teebes/drawtwo-backend:latest ./backend
	docker build -t teebes/drawtwo-frontend:latest -f frontend/Dockerfile.production ./frontend
	docker push teebes/drawtwo-backend:latest
	docker push teebes/drawtwo-frontend:latest

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

# Celery Development
celery-dev:
	docker-compose up db redis backend celery-worker celery-beat

logs-celery:
	docker-compose logs -f celery-worker celery-beat

logs-redis:
	docker-compose logs -f redis

celery-shell:
	docker-compose exec celery-worker bash

celery-flower:
	@echo "Starting Celery Flower monitoring..."
	@echo "Access Flower at: http://localhost:5555"
	docker-compose exec celery-worker celery -A config flower --port=5555 --broker=redis://redis:6379/0

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
	docker-compose exec backend python manage.py test --settings=config.settings.test

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

# Database Reset
reset-db:
	@echo "⚠️  WARNING: This will DELETE ALL DATABASE DATA!"
	@echo "Press Ctrl+C within 5 seconds to cancel..."
	@sleep 5
	@echo "Stopping services..."
	docker-compose down
	@echo "Removing database volume..."
	docker volume rm drawtwo_postgres_data 2>/dev/null || true
	@echo "Starting database..."
	docker-compose up -d db
	@echo "Waiting for database to be ready..."
	@sleep 5
	@echo "Running migrations..."
	docker-compose run --rm backend python manage.py migrate
	@echo "✅ Database reset complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  make createsuperuser  - Create admin user"
	@echo "  make dev              - Start full development stack"

reset-db-with-superuser:
	@echo "⚠️  WARNING: This will DELETE ALL DATABASE DATA!"
	@echo "Press Ctrl+C within 5 seconds to cancel..."
	@sleep 5
	@echo "Stopping services..."
	docker-compose down
	@echo "Removing database volume..."
	docker volume rm drawtwo_postgres_data 2>/dev/null || true
	@echo "Starting database..."
	docker-compose up -d db
	@echo "Waiting for database to be ready..."
	@sleep 5
	@echo "Running migrations..."
	docker-compose run --rm backend python manage.py migrate
	@echo "Creating superuser..."
	docker-compose run --rm backend python manage.py createsuperuser
	@echo "✅ Database reset complete with superuser!"

# Cleanup
clean:
	docker-compose down -v
	docker system prune -f

cleanup-emails-dry:
	docker-compose run --rm backend python manage.py cleanup_email_confirmations --dry-run

cleanup-emails:
	docker-compose run --rm backend python manage.py cleanup_email_confirmations