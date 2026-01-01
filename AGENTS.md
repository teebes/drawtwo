# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: Django app (API, game engine, Celery, Channels). Apps live in `backend/apps/` with domain modules like `gameplay`, `builder`, and `authentication`.
- `frontend/`: Vue 3 + Vite + TypeScript client. Source in `frontend/src/`, views in `frontend/src/views/`, components in `frontend/src/components/`.
- `frontend/public/`: Static assets (logos, icons).
- `docs/`: Local documentation and runbooks (e.g., CI checks, R2 setup).
- `nginx/`, `docker-compose.yml`: Deployment and local stack configuration.
- `scripts/`: Utility scripts, CI helpers.

## Build, Test, and Development Commands
Run commands inside Docker containers (preferred workflow uses `make` targets).
- `make dev`: Start full stack (backend + frontend + db + redis + celery).
- `make backend-dev`: Backend + db only.
- `make frontend-dev`: Frontend dev server (backend must be running separately).
- `make test`: Django test suite with test settings.
- `make ci-check`: Run the full local CI checks.
- `make lint` / `make format`: Black, isort, and flake8 checks or auto-formatting.

## Coding Style & Naming Conventions
- Python: Black (line length 88), isort (Black profile), flake8 with E203/W503 ignored. Config lives in `backend/pyproject.toml`.
- Django apps: keep app modules under `backend/apps/<app_name>/` and use explicit `apps.*` imports.
- Frontend: TypeScript-first (`.ts` / `.vue` SFCs). Follow the component/view separation under `frontend/src/`.

## Testing Guidelines
- Backend tests use Django’s test runner (`manage.py test`) and live alongside apps, e.g., `backend/apps/gameplay/tests/` and `backend/apps/<app>/tests.py`.
- Run specific tests with `make test-debug TEST=apps.gameplay.tests.test_traits.TestBuffAction`.
- No frontend test runner is configured; keep UI changes validated via manual smoke testing.

## Commit & Pull Request Guidelines
- Commit history uses short, imperative, sentence-case messages (e.g., “Fix bug with …”, “Implement …”). Include issue/PR references like `(#12)` when available.
- PRs should describe the change, list test commands run, and include screenshots/GIFs for UI updates. Link related issues and mention any required env/config updates.

## Agent-Specific Notes
- Commands are expected to run inside Docker containers; avoid host-only workflows.
- Refer to `frontend/src/views/DesignReference.vue` for frontend styling guidance.
