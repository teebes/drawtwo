# Running CI Checks Locally

Testing your code locally before pushing to GitHub saves time and prevents failed CI runs. Here's how to run the same checks that GitHub Actions runs.

## Quick Start

```bash
# Run all CI checks at once
make ci-check

# Or run individual checks
make lint          # Just code quality checks
make format        # Auto-format code
```

## What the CI script checks:

1. **Code formatting** (Black)
2. **Import sorting** (isort)
3. **Code style** (flake8)
4. **Django system checks**
5. **Django tests**
6. **Docker build**
7. **Security scanning** (Safety + Bandit)

## Individual Commands

If you prefer to run checks individually:

```bash
# Activate your virtual environment
source venv/bin/activate

# 1. Check code formatting
black --check backend/

# 2. Check import sorting
isort --check-only backend/

# 3. Check code style
flake8 backend/

# 4. Run Django system checks
cd backend
export SECRET_KEY="test-secret-key-for-ci"
export DEBUG="False"
export DB_ENGINE="django.db.backends.sqlite3"
export DB_NAME=":memory:"
python manage.py check --deploy
cd ..

# 5. Run tests
docker-compose exec backend python manage.py test

# 6. Test Docker build
docker-compose build

# 7. Security checks
safety check -r requirements-dev.txt --short-report
bandit -r backend/ -x backend/*/tests/ -f json -o bandit-report.json
```

## Recommended Development Workflow

```bash
# 1. Make your changes
vim backend/apps/core/views.py

# 2. Quick format check (auto-fixes issues)
make format

# 3. Quick lint check
make lint

# 4. Full CI check before commit
make ci-check

# 5. If everything passes, commit and push
git add .
git commit -m "Add new feature"
git push
```

## Troubleshooting

### Common Issues

1. **Virtual environment not activated**: Make sure you're in your `venv`
2. **Docker not running**: Start Docker Desktop before running `make ci-check`
3. **PostgreSQL connection issues**: The CI script uses SQLite for system checks to avoid database dependencies
4. **Security warnings**: Review the output and update dependencies if needed

### Performance Tips

1. **Use `make format`** to auto-fix formatting issues instead of manually fixing them
2. **Use `make lint`** for quick feedback during development
3. **Run `make ci-check`** before committing to catch all issues at once

## What Each Tool Does

- **Black**: Formats Python code consistently
- **isort**: Sorts and organizes import statements
- **flake8**: Checks for code style issues and potential bugs
- **Django system checks**: Validates Django configuration for production
- **Safety**: Scans for known security vulnerabilities in dependencies
- **Bandit**: Analyzes code for common security issues

This approach catches issues early and ensures your code will pass GitHub Actions!