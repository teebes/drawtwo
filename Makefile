.PHONY: help build up down restart logs shell migrate makemigrations collectstatic createsuperuser test clean

# Default target
help:
	@echo "Available commands:"
	@echo "  build          - Build the Docker containers"
	@echo "  up             - Start the services"
	@echo "  down           - Stop the services"
	@echo "  restart        - Restart the services"
	@echo "  logs           - View logs from all services"
	@echo "  logs-backend   - View logs from backend service"
	@echo "  logs-db        - View logs from database service"
	@echo "  shell          - Access Django shell"
	@echo "  bash           - Access backend container bash"
	@echo "  migrate        - Run Django migrations"
	@echo "  makemigrations - Create Django migrations"
	@echo "  collectstatic  - Collect static files"
	@echo "  createsuperuser - Create Django superuser"
	@echo "  test           - Run tests"
	@echo "  clean          - Remove containers and volumes"

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

# Cleanup
clean:
	docker-compose down -v
	docker system prune -f