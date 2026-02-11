# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DrawTwo is a full-stack card game application with a Django backend and Vue.js frontend. The project uses Docker for development and includes a sophisticated event-driven game engine with WebSocket support for real-time gameplay.

## Development Setup

**IMPORTANT:** All commands must be run inside Docker containers, not on the host machine.

### Common Development Commands

```bash
# Full stack development
make dev              # Start full stack (frontend + backend + db + redis + celery)
make build            # Build all Docker containers
make down             # Stop all services
make logs             # View logs from all services

# Backend development
make backend-dev      # Start only backend services (db + backend)
make shell            # Access Django shell
make bash             # Access backend container bash
make migrate          # Run migrations
make makemigrations   # Create migrations
make test             # Run backend tests

# Celery (task queue)
make celery-dev       # Start backend with Celery workers
make logs-celery      # View Celery worker logs
make celery-flower    # Start Celery Flower monitoring (http://localhost:5555)

# Frontend development
make frontend-dev     # Start only frontend (requires backend running separately)
make logs-frontend    # View frontend logs

# Code quality
make format           # Auto-format code with Black + isort
make format-docker    # Auto-format code in Docker
make lint             # Run Black, isort, flake8 checks
make lint-docker      # Run code quality checks in Docker
make ci-check         # Run full CI pipeline locally

# Database
make reset-db         # Reset database (WARNING: deletes all data)
make reset-db-with-superuser  # Reset database and create superuser
```

### Running Tests

```bash
# Run all Django tests
make test

# Run tests with verbose output
make test-verbose

# Run a specific test with debug output
make test-debug TEST=apps.gameplay.tests.test_traits.TestBuffAction

# Run tests in a specific app
docker-compose exec backend python manage.py test apps.gameplay --settings=config.settings.test

# Run a single test file
docker-compose exec backend python manage.py test apps.gameplay.tests.TestGameEngine --settings=config.settings.test
```

### Accessing Services

- Frontend: http://localhost:3000
- Backend API: http://localhost:8002
- Django Admin: http://localhost:8002/admin/
- Health check: http://localhost:8002/api/health/
- Celery Flower: http://localhost:5555 (after running `make celery-flower`)

## Architecture

### Backend Structure

The Django backend is organized into apps in `backend/apps/`:

- **authentication** - Custom user model, JWT authentication, passwordless login
- **builder** - Card/deck/hero creation and management
- **collection** - User card collections
- **control** - Site administration and access control
- **core** - Shared utilities, health checks, base models
- **gameplay** - Game engine, WebSocket consumers, game state management

### Game Engine Architecture (Command-Effect-Event System)

DrawTwo uses an event-driven game engine based on a Command-Effect-Result pattern:

#### Core Flow

```
Player Action (WebSocket)
  ↓
Command validated & compiled to Effects
  ↓
Effects enqueued in game queue
  ↓
Celery task processes queue asynchronously
  ↓
Each Effect resolved → Result (Success/Rejected/Prevented/Fault)
  ↓
Updates sent to clients via WebSocket
```

#### Key Concepts

1. **Commands** (`backend/apps/gameplay/schemas/commands.py`)
   - Player actions entering the system (PlayCardCommand, AttackCommand, EndTurnCommand, etc.)
   - Validated at entry point
   - Compiled into Effects by `GameService.compile_cmd()`

2. **Effects** (`backend/apps/gameplay/schemas/effects.py`)
   - Internal game operations that mutate state
   - Atomic units of game state change
   - Queued and processed in order
   - Examples: PlayEffect, DamageEffect, DrawEffect

3. **Results** (`backend/apps/gameplay/schemas/engine.py`)
   - Every Effect resolution returns one of four Result types:

   **Success** ✅
   - Effect resolved normally, state mutated
   - Domain events emitted (e.g., "CardPlayed", "DamageDealt")
   - Child effects may be enqueued (e.g., Battlecry triggers)

   **Rejected** 🚫
   - Effect violated domain rules (not enough mana, invalid target, etc.)
   - User receives feedback
   - No state change, queue continues
   - This is valid domain behavior, not a bug

   **Prevented** 🛡️
   - Active game effect intervened (immunity, counter-spell, etc.)
   - Domain event emitted for UI feedback
   - No state change, queue continues

   **Fault** ⚠️
   - Engine failure (bug, unhandled exception, data corruption)
   - NOT for validation failures (use Rejected)
   - This IS a bug that needs fixing
   - System logs error, may retry if recoverable

4. **Events** (`backend/apps/gameplay/schemas/events.py`)
   - Domain events emitted by successful Effects
   - Converted to Updates for client consumption
   - Examples: PlayEvent, DrawEvent, GameOverEvent

5. **Updates** (`backend/apps/gameplay/schemas/updates.py`)
   - Client-facing messages derived from Events
   - Filtered by side before sending (information hiding)
   - Sent via WebSocket to frontend

#### Key Files

- `backend/apps/gameplay/schemas/commands.py` - Command definitions
- `backend/apps/gameplay/schemas/effects.py` - Effect definitions
- `backend/apps/gameplay/schemas/engine.py` - Result types (Success/Rejected/Prevented/Fault)
- `backend/apps/gameplay/schemas/events.py` - Event definitions
- `backend/apps/gameplay/schemas/updates.py` - Update definitions
- `backend/apps/gameplay/engine/handlers.py` - Effect resolution logic
- `backend/apps/gameplay/engine/dispatcher.py` - Effect dispatcher
- `backend/apps/gameplay/services.py` - Game service layer (step(), compile_cmd())
- `backend/apps/gameplay/consumers.py` - WebSocket handling
- `backend/apps/gameplay/tasks.py` - Celery tasks for async game processing
- `backend/apps/gameplay/notifications.py` - Filters state/updates by side, sends to clients

### WebSocket Communication

Real-time gameplay uses Django Channels with Redis as the channel layer:

- Games have two channel groups: general (`game_{id}`) and side-specific (`game_{id}_side_a`)
- State is filtered per-side to prevent information leaking (e.g., opponent's hand)
- Commands from client → WebSocket → `GameService.process_command()` → Effects enqueued
- Processing happens async via Celery task (`step.apply_async()`)
- Updates sent back via WebSocket to all connected clients

### Frontend Structure

Vue 3 + TypeScript + Vite application in `frontend/`:

- **src/components/** - Reusable UI components
  - `game/` - Game-specific components (cards, board, health bars)
  - `ui/` - Generic UI components (buttons, modals)
  - `layout/` - Layout components (panels, sections)
- **src/views/** - Page components
- **src/stores/** - Pinia stores for state management
- **src/types/** - TypeScript type definitions
- **src/router/** - Vue Router configuration
- **src/config/** - API configuration

#### Design System

Reference `frontend/src/views/DesignReference.vue` for style guidelines including:
- Color palette (brand colors, card rarity colors)
- Typography (Cinzel display, Inter body, JetBrains Mono monospace)
- Component patterns (cards, panels, buttons)
- Animations (card draw, mana pulse, etc.)

**Use TypeScript for all frontend code unless there's a compelling reason not to.**

### Django Configuration

Settings are split into environments:
- `backend/config/settings/base.py` - Shared base settings
- `backend/config/settings/development.py` - Development settings
- `backend/config/settings/production.py` - Production settings
- `backend/config/settings/test.py` - Test settings

Use `DJANGO_SETTINGS_MODULE=config.settings.development` (set in docker-compose.yml)

### Celery Task Queue

- **Broker/Backend:** Redis (redis://redis:6379/0)
- **Workers:** Process game steps asynchronously
- **Beat:** Schedules periodic tasks
- **Flower:** Optional monitoring interface (port 5555)

Main use case: Processing game effect queues without blocking WebSocket connections.

### Django Apps

Apps are organized in `backend/apps/`:

```
apps/
├── authentication/    # User model, JWT auth, passwordless login
├── builder/          # Card/deck/hero builder
├── collection/       # User card collections
├── control/          # Site admin, access control
├── core/            # Shared utilities, health checks
└── gameplay/        # Game engine, WebSocket consumers
    ├── engine/      # Effect handlers and dispatcher
    ├── schemas/     # Pydantic schemas (commands, effects, events, updates, game state)
    ├── consumers.py # WebSocket consumers
    ├── services.py  # Game service layer
    ├── tasks.py     # Celery tasks
    └── models.py    # Game, GameUpdate models
```

### Key Technologies

**Backend:**
- Django 5.1 + Django REST Framework
- PostgreSQL database
- Redis (Celery broker + Django Channels layer)
- Celery for async task processing
- Django Channels for WebSocket support
- Pydantic for schema validation
- JWT authentication (SimpleJWT)

**Frontend:**
- Vue 3 with Composition API
- TypeScript
- Vite
- Pinia (state management)
- Vue Router
- Axios (HTTP client)
- Tailwind CSS

## Working with Game Logic

### Action-Trait System for Card Abilities

Card abilities in DrawTwo are defined using a flexible **Action-Trait** system that combines trigger conditions with effects:

#### Actions

Actions define what happens when a card ability triggers. Available action types:

- **DamageAction** - Deal damage to heroes or creatures (physical or spell damage)
  - `scope`: 'single', 'cleave' (target + adjacent), or 'all'
  - `target`: 'hero', 'creature', or 'enemy'

- **HealAction** - Restore health to heroes or creatures
  - `scope`: 'single', 'cleave', or 'all'
  - `target`: 'hero', 'creature', or 'friendly'

- **BuffAction** - Permanently increase attack or health of creatures
  - `attribute`: 'attack' or 'health'
  - `scope`: 'single', 'cleave', or 'all'
  - Buffs persist until creature dies

- **DrawAction** - Draw cards from deck
- **RemoveAction** - Remove creatures from board
- **ClearAction** - Clear board of creatures ('both', 'own', or 'opponent')
- **SummonAction** - Summon token creatures
- **TempManaBoostAction** - Temporary mana boost for current turn

#### Traits

Traits define when actions trigger. Traits can have associated actions:

- **Battlecry** - Triggers when card is played (actions execute immediately)
- **Deathrattle** - Triggers when creature dies
- **Charge** - Can attack immediately when played
- **Taunt** - Must be attacked before other creatures
- **Ranged** - Can attack without taking damage
- **Stealth** - Cannot be targeted until it attacks
- **Unique** - Only one copy allowed on board

#### Example: Card with Buff Battlecry

```python
from apps.builder.schemas import Card, Battlecry, BuffAction

card = Card(
    name="Battle Mentor",
    card_type="creature",
    cost=3,
    attack=2,
    health=3,
    traits=[
        Battlecry(actions=[
            BuffAction(
                attribute="attack",
                amount=2,
                target="creature",
                scope="single"  # Buff one friendly creature
            )
        ])
    ]
)
```

#### Key Files

- `backend/apps/builder/schemas.py` - Action and Trait definitions (Pydantic schemas)
- `backend/apps/gameplay/services.py` - `compile_action()` converts Actions to Effects
- `backend/apps/gameplay/engine/handlers.py` - Effect handlers (e.g., `@register("effect_buff")`)
- `backend/apps/gameplay/traits.py` - Trait application logic

### Card vs Creature Terminology

**IMPORTANT:** The codebase distinguishes between **cards** and **creatures**:

- **Card**: A card entity that exists in the deck, hand, or graveyard. Generic term for card objects.
- **Creature**: A card that has been played onto the board and is actively in play. This is a specific state of a creature-type card.
- **CardInPlay**: The Pydantic model used for all card instances during a game (has `card_type: 'creature' | 'spell'`)

**Terminology Guidelines:**
- Use `target_type: "creature"` when targeting entities on the board
- Use `target_type: "hero"` when targeting heroes
- **Never use** `target_type: "card"` in new code - this has been deprecated
- Commands, Effects, Events, and Updates all use `"creature"` for board entities
- The `cards` dict in GameState stores all CardInPlay instances (both in hand and on board)
- The `board` dict in GameState contains lists of card_ids that are creatures on the board

**Examples:**
```python
# ✅ Correct - targeting a creature on the board
AttackCommand(
    card_id="card_1",
    target_type="creature",  # Creature on the board
    target_id="card_2"
)

# ✅ Correct - targeting a hero
UseHeroCommand(
    hero_id="hero_1",
    target_type="hero",  # Opposing hero
    target_id="hero_2"
)

# ❌ Incorrect - don't use "card" for board entities
AttackCommand(
    card_id="card_1",
    target_type="card",  # WRONG - use "creature"
    target_id="card_2"
)
```

### Adding New Card Abilities

To add a new card ability to the game:

1. **Define the Action** in `backend/apps/builder/schemas.py`
   - Create a new Action class (e.g., `MyNewAction`)
   - Add it to the `Action` union type
   - Specify parameters and validation

2. **Add Effect** in `backend/apps/gameplay/schemas/effects.py`
   - Create corresponding Effect class (e.g., `MyNewEffect`)
   - Effects are the internal representation of Actions

3. **Compile Action to Effect** in `backend/apps/gameplay/services.py`
   - Add case in `compile_action()` method
   - Handle scope/targeting logic if applicable

4. **Add Effect Handler** in `backend/apps/gameplay/engine/handlers.py`
   - Create handler function with `@register("effect_my_new")` decorator
   - Implement game logic: validate, mutate state, return Result

5. **Add Events** in `backend/apps/gameplay/schemas/events.py`
   - Define event(s) emitted when effect succeeds
   - Events are used for game log and UI feedback

6. **Add Frontend Types** in `frontend/src/types/game.ts`
   - Add action to `CardAction` union type for TypeScript support

7. **Write Tests** in `backend/apps/gameplay/tests/test_traits.py`
   - Test all scopes, edge cases, and integrations

### Testing Game Engine

The game engine is pure functional logic that takes state and returns new state. Write tests by:

```python
from apps.gameplay.engine.dispatcher import resolve
from apps.gameplay.schemas.game import GameState
from apps.gameplay.schemas.effects import DamageEffect

# Setup initial state
state = GameState(...)

# Create effect
effect = DamageEffect(
    side="side_a",
    source_id="card_1",
    target_id="hero_2",
    damage=3
)

# Resolve effect
result = resolve(effect, state)

# Assert result type and state changes
assert isinstance(result, Success)
assert result.new_state.heroes["side_b"].health == original_health - 3
```

### Processing Flow in GameService.step()

1. Lock game row (`select_for_update(nowait=True)`)
2. Pop effects from queue one at a time
3. Resolve each effect with `resolve(effect, game_state)`
4. Handle result:
   - Success: Update state, enqueue child effects, process trait triggers
   - Rejected/Prevented: Emit events, add error messages, continue
   - Fault: Log error, stop if non-retryable
5. Convert events to updates and persist to DB
6. Send filtered updates to clients via WebSocket
7. If queue has AI turn, choose AI move and enqueue
8. If queue not empty, trigger next step with Celery

## Ranked Matchmaking System

DrawTwo includes a complete ranked matchmaking system with ELO ratings, queue management, and real-time notifications.

### Architecture

**MatchmakingQueue Model** (`backend/apps/gameplay/models.py`):
- Stores queue entries with status ('queued', 'matched', 'cancelled')
- Tracks ELO rating for skill-based matching
- Links to user and selected deck

**Matchmaking Flow**:
```
1. User queues with deck → POST /gameplay/matchmaking/queue/
2. MatchmakingQueue entry created (status='queued')
3. Celery periodic task runs every 10s
4. Finds compatible opponents (ELO within range)
5. Creates Game with type='ranked', time_per_turn=60
6. WebSocket notifications sent to both players
7. Frontend auto-navigates to game board
```

**Key Endpoints**:
- `POST /gameplay/matchmaking/queue/` - Join ranked queue
- `GET /gameplay/matchmaking/status/{slug}/` - Check queue status (polling)
- `POST /gameplay/matchmaking/leave/{slug}/` - Leave queue

**Frontend Components**:
- `frontend/src/views/RankedQueue.vue` - Waiting screen with timer, progress bar, and timeout handling
- 60-second timeout with automatic queue cancellation
- Polling every 3 seconds as fallback to WebSocket
- Real-time WebSocket notifications via `/ws/user/`

**WebSocket Notifications**:
```json
{
  "type": "matchmaking_success",
  "game_id": "game-uuid",
  "title_slug": "my-title"
}
```

### Time Control System

Ranked games include turn timers to ensure fair, time-limited matches.

**Game Model Fields**:
- `time_per_turn` - Integer (seconds), nullable. Set to 60 for ranked games, null for casual
- `turn_start_time` - DateTime, nullable. Reserved for future turn enforcement
- `type` - 'casual' or 'ranked' game type

**Implementation**:
- Ranked games automatically get `time_per_turn=60` (1 minute per turn)
- Set in `GameService.process_matchmaking()` when creating matched games
- Future: Backend will enforce turn time limits using `turn_start_time`

**TitleConfig** (`backend/apps/builder/schemas.py`):
- `ranked_time_per_turn` - Configurable time limit per title (default: 60 seconds)

## Development Workflow

### Creating New Django Apps

```bash
make bash
cd apps
python ../manage.py startapp your_app_name
```

Then add to `INSTALLED_APPS` in `config/settings/base.py`.

### Database Migrations

```bash
make makemigrations    # Create migrations
make migrate           # Apply migrations
```

### Code Quality

The project uses:
- **Black** for code formatting (line length: 88)
- **isort** for import sorting
- **flake8** for linting (with E203, W503 ignored)

Format before committing:
```bash
make format
```

### Working with WebSockets (Development)

When testing WebSocket functionality:
1. Start the full stack: `make dev`
2. Backend runs with Daphne ASGI server (not runserver)
3. WebSocket endpoint: `ws://localhost:8002/ws/game/{game_id}/`
4. Authentication via JWT token in query string or headers

## Important Notes

- **All commands run in Docker** - Never run Django/npm commands on host
- **TypeScript first** - Use TypeScript for frontend code
- **Command-Effect pattern** - Don't bypass the game engine; always use Commands → Effects
- **Effect handlers are pure** - They should not have side effects beyond returning Results
- **WebSocket security** - State is filtered per-side; never expose opponent's hidden info
- **Celery is required** - Game processing is async; WebSocket consumers don't block

## Documentation

### Feature Documentation

Major features are documented in markdown files in the project root for permanent reference:

- `BUFF_ACTION_DEMO.md` - Buff action implementation guide
- `RANKED_QUEUE_FLOW.md` - Ranked matchmaking system flow
- `TIME_CONTROL_IMPLEMENTATION.md` - Turn timer implementation
- `PRODUCTION_DEPLOYMENT.md` - Production deployment guide

These files provide implementation details and examples for specific features.

### Session Documentation

When making significant changes, create documentation in `.claude/session-notes/`:

**Purpose:** Session notes help track major refactorings, bug fixes, and architectural decisions made during development sessions.

**Location:** All session documentation should be saved to `.claude/session-notes/`

**When to Create:**
- Major refactorings (e.g., splitting monolithic files, restructuring components)
- Bug fixes that required investigation (e.g., validation issues, state management bugs)
- Architecture changes (e.g., new patterns, standardizations)
- Configuration changes that affect multiple parts of the system

**Format:**
- Use Markdown (.md) files
- Include clear titles and dates
- Document the problem, solution, and files affected
- Include code examples where helpful

**Examples:**
- `REFACTORING_SUMMARY.md` - Document major code reorganizations
- `BUG_FIX_[NAME].md` - Document specific bug fixes with context
- `[FEATURE]_CONFIGURATION.md` - Document new configurations or standards

**Note:** The `.claude/` directory is git-ignored, so session notes are local to each developer's environment.

## Cursor Rules

From `.cursorrules`:
- Run all commands inside Docker, not on host
- Create frontend views/files using TypeScript
- Refer to `frontend/src/views/DesignReference.vue` for style guidelines
- Question premises and think from first principles rather than blindly agreeing
- When creating session documentation, save to `.claude/session-notes/`
