# DrawTwo - Card Game Backend

A Django-based backend for a card game, built with PostgreSQL and Docker.

## Features

- Django 5.1 with Django REST Framework
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
├── docker-entrypoint.sh     # Docker entrypoint script
├── manage.py                # Django management script
└── requirements.txt         # Python dependencies

Root files:
├── .env.example            # Environment variables template
├── .gitignore             # Git ignore patterns
├── .vscode/               # VS Code configuration
├── docker-compose.yml     # Docker Compose orchestration
├── LICENSE                # MIT License
├── Makefile              # Development commands
├── README.md             # This file
├── requirements-dev.txt  # Development dependencies
└── venv/                 # Local virtual environment (gitignored)
```

## Quick Start

### Prerequisites

- Docker
- Docker Compose
- Python 3.10+ (for local development environment)

### Setup

1. **Clone and navigate to the project:**
   ```bash
   cd /path/to/drawtwo
   ```

2. **Set up local development environment (for IDE support):**
   ```bash
   # Create and activate virtual environment
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # venv\Scripts\activate   # On Windows

   # Install development dependencies
   pip install -r requirements-dev.txt
   ```

3. **Create environment file:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your preferred settings.

4. **Build and start the services:**
   ```bash
   make build
   make up
   ```

5. **Run migrations:**
   ```bash
   make migrate
   ```

6. **Create a superuser (optional):**
   ```bash
   make createsuperuser
   ```

7. **Access the application:**
   - Backend API: http://localhost:8000
   - Health check: http://localhost:8000/api/health/
   - Admin interface: http://localhost:8000/admin/

## IDE Setup

### VS Code/Cursor Setup

1. **Install Python extension** if not already installed
2. **Select Python interpreter:**
   - Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux)
   - Type "Python: Select Interpreter"
   - Choose `./venv/bin/python`

The project includes VS Code settings (`.vscode/settings.json`) that will:
- Use the local virtual environment
- Enable Django support
- Configure code formatting with Black
- Enable linting with Flake8

### Why Local Virtual Environment?

Even though the app runs in Docker, we maintain a local virtual environment because:
- ✅ **IDE Support**: Full IntelliSense, autocomplete, and error detection
- ✅ **Code Navigation**: Jump to definitions, find references
- ✅ **Debugging**: Better debugging experience
- ✅ **Linting**: Real-time code quality checks
- ✅ **No Performance Impact**: Your app still runs in Docker

The local environment is only for development tooling - your actual application runs in the Docker containers.

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

## Code Quality

The project includes several code quality tools:

```bash
# Format code with Black
source venv/bin/activate
black backend/

# Check code style with Flake8
flake8 backend/

# Sort imports with isort
isort backend/
```

## What's New in Django 5.1

This project uses Django 5.1, which includes several great new features:
- **{% querystring %} template tag** - Easier URL parameter manipulation
- **PostgreSQL Connection Pools** - Better database performance
- **LoginRequiredMiddleware** - Easier authentication enforcement
- **Improved admin interface** - Better accessibility and UX
- **Enhanced security** - Stronger password hashing defaults

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