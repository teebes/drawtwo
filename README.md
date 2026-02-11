# DrawTwo

An open-source engine for building online trading card games.

## Stack

Docker & Docker Compose orchestration

### Backend
- Django 5.1 with Django REST Framework
- PostgreSQL database
- **Celery Task Queue** with Redis broker for asynchronous processing
- Django Channels for Websockets
- Environment-based configuration

### Frontend
- Vue 3 with Composition API
- Vite for fast development and building
- Modern, responsive UI
- API integration with backend
- Hot module replacement for development
- Production-ready builds


## Quick Start

### Prerequisites

- Docker
- Docker Compose
- Python 3.10+ (for local development environment)
- Redis (automatically started with Docker Compose)

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
   - Backend API: http://localhost:8002
   - Health check: http://localhost:8002/api/health/
   - Admin interface: http://localhost:8002/admin/
   - Redis: localhost:6381 (for external access)
   - Celery Flower (monitoring): http://localhost:5555 (run `make celery-flower`)

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

### Celery Task Queue
```bash
make celery-dev        # Start backend with Celery (db + backend + redis + celery)
make logs-celery       # View Celery worker logs
make logs-redis        # View Redis logs
make celery-shell      # Access Celery worker container bash
make celery-flower     # Start Celery Flower monitoring
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

**Note:** When running independently, make sure the backend is available at `http://localhost:8002` for the frontend to work properly, or set `VITE_API_BASE_URL` to your backend URL.

## Environment Variables

Key environment variables (see `local.env.template` or `production.env.template` for full list):

### Core Settings
- `SECRET_KEY`: Django secret key
- `DEBUG`: Enable/disable debug mode
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`: Database configuration
- `ALLOWED_HOSTS`: Allowed hosts for production
- `CELERY_BROKER_URL`: Redis URL for Celery message broker (Docker Compose default: `redis://redis:6379/0`, host access: `redis://localhost:6381/0`)
- `CELERY_RESULT_BACKEND`: Redis URL for Celery result backend (Docker Compose default: `redis://redis:6379/0`, host access: `redis://localhost:6381/0`)

### Card Assets (Cloudflare R2)
- `CARD_ASSETS_BASE_URL`: Public URL for card assets (e.g., https://assets.drawtwo.com)
- `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`: R2 API credentials (optional for local dev)
- `R2_BUCKET_NAME`: R2 bucket name (default: drawtwo-assets)

### Google Authentication
- `GOOGLE_OAUTH2_CLIENT_ID` / `GOOGLE_OAUTH2_CLIENT_SECRET`: OAuth credentials used by Django/allauth.
- `VITE_GOOGLE_CLIENT_ID`: Exposed to the frontend build (usually the same value as `GOOGLE_OAUTH2_CLIENT_ID`).

See `docs/R2_SETUP.md` for detailed configuration instructions.

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
- Port: `5432` (container) / `5433` (host)

## Celery Task Queue

The project includes Celery for handling asynchronous tasks and background jobs.

### Architecture
- **Message Broker**: Redis (localhost:6381 on host, redis:6379 in Docker network)
- **Result Backend**: Redis + Django Database
- **Worker**: Processes background tasks
- **Beat**: Schedules periodic tasks
- **Flower**: Optional monitoring interface

### Available Tasks
The project includes example tasks in `backend/apps/core/tasks.py`:
- `send_email_task` - Asynchronous email sending with retries
- `cleanup_old_data` - Periodic cleanup task
- `process_background_job` - Generic background processing

### Using Tasks in Your Code
```python
from apps.core.tasks import send_email_task, process_background_job

# Queue a task asynchronously
send_email_task.delay(
    subject="Welcome!",
    message="Thanks for signing up",
    recipient_list=["user@example.com"]
)

# Process background job
result = process_background_job.delay({"id": "job_123", "data": "some_data"})
```

### Creating New Tasks
Create tasks in any app's `tasks.py` file:
```python
from celery import shared_task

@shared_task
def your_custom_task(param1, param2):
    # Your task logic here
    return "Task completed"
```

### Monitoring Tasks
- **Logs**: Use `make logs-celery` to view worker logs
- **Flower**: Use `make celery-flower` to start the monitoring interface
- **Django Admin**: Periodic tasks can be managed through Django admin

### Production Considerations
- Configure Redis with persistence and clustering for production
- Set up proper monitoring and alerting for failed tasks
- Use separate queues for different task types if needed
- Consider using `CELERY_TASK_ROUTES` for task routing

## Game Engine Architecture

DrawTwo uses an event-driven game engine based on a Command-Effect-Result pattern. This architecture provides a robust, testable, and extensible way to handle game logic.

### Core Concepts

#### 1. Commands
Player actions that enter the system (e.g., "Play Card", "Use Hero Power", "End Turn").

```python
# Commands are validated at the entry point
PlayCardCommand(card_id="card_123", position=0, target_id="hero_1")
```

#### 2. Effects
Internal game operations that mutate state. Commands are compiled into Effects, which are then queued and processed.

```python
# Effects are the atomic units of game state change
PlayEffect(side="side_a", source_id="card_123", position=0)
DamageEffect(target_id="hero_1", amount=3)
```

#### 3. Results
Every Effect resolution returns one of four Result types:

**Success** ✅
- The effect resolved normally and state was mutated
- Domain events are emitted (e.g., "CardPlayed", "DamageDealt")
- Child effects may be enqueued (e.g., Battlecry triggers)
- System continues processing the queue

**Rejected** 🚫
- The effect violated domain rules (at enqueue OR resolution time)
- Examples: not enough mana, target is exhausted, invalid target
- User receives feedback: "Not enough energy", "Target is exhausted"
- No state change, queue continues processing
- This is **not** a bug - it's valid domain behavior

**Prevented** 🛡️
- An active game effect intervened (e.g., immunity, counter-spell)
- Examples: "Immune to damage", "Divine Shield absorbed damage"
- Domain event emitted for UI feedback
- No state change, queue continues processing

**Fault** ⚠️
- The engine itself failed (bug, unhandled exception, data corruption)
- **NOT** for validation failures - use Rejected for those
- System logs error, may retry if recoverable
- Generic error shown to user: "Something went wrong"
- This **is** a bug that needs fixing

### Processing Flow

```
1. Player Action (WebSocket)
   ↓
2. Command validated & compiled to Effects
   ↓
3. Effects enqueued
   ↓
4. Celery task processes queue (async)
   ↓
5. Each Effect resolved → Result
   ↓
6. Updates sent to clients (WebSocket)
   ↓
7. Frontend displays changes
```

### Example: Playing a Card

```python
# 1. Frontend sends command
ws.send({"type": "cmd_play_card", "card_id": "card_123"})

# 2. Backend compiles to effect
effect = PlayEffect(side="side_a", source_id="card_123", position=0)

# 3. Effect handler validates and resolves
if card.cost > available_mana:
    return Rejected(reason="Not enough energy to play the card")

# 4. Success: state mutates, events emitted
return Success(
    new_state=updated_state,
    events=[PlayEvent(card_id="card_123")],
    child_effects=[BattlecryEffect(...)]  # Triggers queued
)
```

### Why This Architecture?

- **Separation of concerns**: Commands (player intent) vs Effects (game operations)
- **Testability**: Pure functions that take state and return new state
- **Robustness**: Backend validates everything, frontend can't cheat
- **Extensibility**: New card abilities = new Effects + handlers
- **Debuggability**: Full event history for replay/debugging
- **Async processing**: Celery handles complex AI and game logic without blocking

### Key Files

- `backend/apps/gameplay/schemas/commands.py` - Command definitions
- `backend/apps/gameplay/schemas/effects.py` - Effect definitions
- `backend/apps/gameplay/schemas/engine.py` - Result types
- `backend/apps/gameplay/engine/handlers.py` - Effect resolution logic
- `backend/apps/gameplay/services.py` - Game service layer
- `backend/apps/gameplay/consumers.py` - WebSocket handling

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
