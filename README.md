# DrawTwo - Card Game Backend

A Django-based backend for a card game, built with PostgreSQL and Docker.

## Features

- Django 4.2 with Django REST Framework
- PostgreSQL database
- Docker & Docker Compose for easy development
- Environment-based configuration
- Separate settings for development and production
- Pre-configured CORS headers for frontend integration
- Health check endpoint
- Comprehensive logging
- Security best practices

## Project Structure

```
/backend
├── apps/                     # Django apps will go here
├── config/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py          # Base settings
│   │   ├── development.py   # Development settings
│   │   └── production.py    # Production settings
│   ├── asgi.py              # ASGI configuration
│   ├── urls.py              # Main URL configuration
│   └── wsgi.py              # WSGI configuration
├── Dockerfile               # Docker configuration for backend
├── manage.py                # Django management script
└── requirements.txt         # Python dependencies
.env.example                 # Example environment variables
.gitignore                   # Git ignore file
docker-compose.yml           # Docker Compose configuration
LICENSE                      # Project license
Makefile                     # Common development commands
README.md                    # This file
```

## Quick Start

### Prerequisites

- Docker
- Docker Compose

### Setup

1. **Clone and navigate to the project:**
   ```bash
   cd /path/to/drawtwo
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your preferred settings.

3. **Build and start the services:**
   ```bash
   make build
   make up
   ```

4. **Run migrations:**
   ```bash
   make migrate
   ```

5. **Create a superuser (optional):**
   ```bash
   make createsuperuser
   ```

6. **Access the application:**
   - Backend API: http://localhost:8000
   - Health check: http://localhost:8000/api/health/
   - Admin interface: http://localhost:8000/admin/

## Development Commands

Use the Makefile for common development tasks:

```bash
make help              # Show available commands
make build             # Build Docker containers
make up                # Start services
make down              # Stop services
make restart           # Restart services
make logs              # View all logs
make logs-backend      # View backend logs
make logs-db           # View database logs
make shell             # Access Django shell
make bash              # Access backend container bash
make migrate           # Run migrations
make makemigrations    # Create migrations
make collectstatic     # Collect static files
make createsuperuser   # Create superuser
make test              # Run tests
make clean             # Remove containers and volumes
```

## Environment Variables

Key environment variables (see `.env.example` for full list):

- `SECRET_KEY`: Django secret key
- `DEBUG`: Enable/disable debug mode
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`: Database configuration
- `ALLOWED_HOSTS`: Allowed hosts for production

## API Endpoints

- `GET /api/health/` - Health check endpoint
- `GET /admin/` - Django admin interface

## Creating New Apps

To create a new Django app:

```bash
make bash
cd apps
python ../manage.py startapp your_app_name
```

Then add the app to `INSTALLED_APPS` in `config/settings/base.py`.

## Database

The project uses PostgreSQL with the following default configuration:
- Database: `drawtwo`
- User: `postgres`
- Password: `postgres`
- Host: `db` (Docker service name)
- Port: `5432`

## Production Deployment

1. Set environment variables for production
2. Use `config.settings.production` as your `DJANGO_SETTINGS_MODULE`
3. Set `DEBUG=False`
4. Configure `ALLOWED_HOSTS`
5. Set up proper SSL certificates
6. Use a production-grade WSGI server (Gunicorn is included)

## Security Notes

- Never commit `.env` files to version control
- Use strong, unique `SECRET_KEY` in production
- Set `DEBUG=False` in production
- Configure proper `ALLOWED_HOSTS`
- Use HTTPS in production
- Regularly update dependencies

## Contributing

1. Create a new branch for your feature
2. Make your changes
3. Run tests: `make test`
4. Create a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.