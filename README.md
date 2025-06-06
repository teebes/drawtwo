# DrawTwo - Full Stack Card Game

A full-stack card game application with a Django backend and Vue.js frontend.

## Features

### Backend
- Django 5.1 with Django REST Framework
- PostgreSQL database
- Docker & Docker Compose for easy development
- Environment-based configuration
- Separate settings for development and production
- Pre-configured CORS headers for frontend integration
- Health check endpoint
- Comprehensive logging
- Security best practices
- **GitHub Actions CI/CD** - Automated testing and deployment

### Frontend
- Vue 3 with Composition API
- Vite for fast development and building
- Modern, responsive UI
- API integration with backend
- Hot module replacement for development
- Production-ready builds

### Full Stack
- Unified development commands
- Independent or combined service execution
- Docker Compose orchestration
- Frontend/backend communication via API proxy

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
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - Health check: http://localhost:8000/api/health/
   - Admin interface: http://localhost:8000/admin/

## GitHub Actions CI/CD

This project includes automated testing and deployment workflows using GitHub Actions.

### What's Included

**CI Pipeline** (`.github/workflows/ci.yml`):
- ✅ **Django Tests**: Full test suite with PostgreSQL
- ✅ **Security Scans**: Dependency vulnerability checks with Safety + Bandit
- ✅ **Docker Build**: Ensures containers build correctly
- ✅ **System Checks**: Django deployment checks

**Code Quality Pipeline** (`.github/workflows/code-quality.yml`):
- 🎨 **Optional**: Black formatting, isort imports, flake8 linting
- 🔧 **Manual trigger**: Run when you want to check code quality
- 📅 **Weekly schedule**: Automated weekly checks (non-blocking)

**Deploy Pipeline** (`.github/workflows/deploy.yml`):
- ✅ **Production Tests**: Final test run before deployment
- ✅ **Docker Build**: Production-ready container builds
- ✅ **Deployment Ready**: Template for your preferred hosting provider

### How It Works

1. **On Pull Requests**: CI runs all tests and checks
2. **On Push to Main**: CI runs + deployment workflow triggers
3. **Manual Trigger**: Deploy workflow can be run manually from GitHub UI

### GitHub Actions Pricing

- **FREE**: 2,000 minutes/month for private repos, unlimited for public repos
- **GitHub Pro**: 3,000 minutes/month for private repos
- Most Django projects use ~10-50 minutes per workflow run

### Setting Up CI/CD

**For existing GitHub repo:**
1. Push the `.github/workflows/` files to your repo
2. GitHub automatically detects and runs the workflows
3. Check the "Actions" tab in your GitHub repo

**For new GitHub repo:**
```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Add Django 5.1 project with CI/CD"

# Add GitHub remote and push
git branch -M main
git remote add origin https://github.com/yourusername/drawtwo.git
git push -u origin main
```

**Adding Deployment Secrets:**
1. Go to your GitHub repo → Settings → Secrets and variables → Actions
2. Add secrets like `SECRET_KEY` for production deployment
3. Update the deploy workflow with your hosting provider commands

### Local Testing

Before pushing to GitHub, you can run the same CI checks locally to catch issues early:

```bash
# Quick code quality checks
make lint              # Black, isort, flake8 checks
make format            # Auto-format code with Black + isort

# Full CI pipeline locally
make ci-check          # Runs everything CI does

# Individual checks
make test              # Django tests only
docker-compose build   # Docker build test only
```

For detailed local testing instructions, see **[docs/local-ci-testing.md](docs/local-ci-testing.md)**.

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

### Full Stack Development
```bash
make help              # Show all available commands
make dev               # Start full stack (frontend + backend + db)
make build             # Build all Docker containers
make up                # Start all services
make down              # Stop all services
make restart           # Restart all services
make logs              # View logs from all services
```

### Backend Only
```bash
make backend-dev       # Start only backend services (db + backend)
make logs-backend      # View backend logs
make logs-db           # View database logs
make shell             # Access Django shell
make bash              # Access backend container bash
make migrate           # Run migrations
make makemigrations    # Create migrations
make collectstatic     # Collect static files
make createsuperuser   # Create superuser
make test              # Run backend tests
```

### Frontend Only
```bash
make frontend-dev      # Start only frontend development server
make frontend-build    # Build frontend for production
make logs-frontend     # View frontend logs
```

### Cleanup
```bash
make clean             # Remove containers and volumes
```

## Independent Development

You can also run the frontend and backend independently:

### Backend Only
```bash
cd backend
# Set up virtual environment and install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start database with Docker
docker-compose up db

# Run Django development server
python manage.py runserver
```

### Frontend Only
```bash
cd frontend
npm install
npm run dev
```

**Note:** When running independently, make sure the backend is available at `http://localhost:8000` for the frontend to work properly.

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

## Production Deployment

1. Set environment variables for production
2. Use `config.settings.production` as your `DJANGO_SETTINGS_MODULE`
3. Set `DEBUG=False`
4. Configure `ALLOWED_HOSTS`
5. Set up proper SSL certificates
6. Use a production-grade WSGI server (Gunicorn is included)

### Maintenance Tasks

**Email Confirmations Cleanup** - Run periodically to prevent database bloat:
```bash
# Check what would be deleted (safe)
make cleanup-emails-dry

# Clean up confirmations older than 7 days
make cleanup-emails
```
Consider setting up a cron job to run this weekly in production.

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