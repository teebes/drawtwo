#!/bin/bash
# Local CI pipeline script
# Run this before pushing to GitHub to catch issues early

set -e  # Exit on any error

echo "🚀 Running local CI checks..."
echo ""

# Activate virtual environment if needed
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

echo "1️⃣ Code formatting check (Black)..."
black --check backend/
echo "✅ Black formatting: PASSED"
echo ""

echo "2️⃣ Import sorting check (isort)..."
isort --check-only backend/
echo "✅ Import sorting: PASSED"
echo ""

echo "3️⃣ Code style check (flake8)..."
flake8 backend/
echo "✅ Code style: PASSED"
echo ""

echo "4️⃣ Django system checks..."
cd backend
# Use SQLite for system checks to avoid database connection issues
export SECRET_KEY="test-secret-key-for-ci"
export DEBUG="False"
export DB_ENGINE="django.db.backends.sqlite3"
export DB_NAME=":memory:"
export DJANGO_SETTINGS_MODULE="config.settings.development"
python manage.py check --deploy
cd ..
echo "✅ Django system checks: PASSED"
echo ""

echo "5️⃣ Running Django tests..."
docker-compose exec backend python manage.py test
echo "✅ Django tests: PASSED"
echo ""

echo "6️⃣ Testing Docker build..."
docker-compose build --quiet
echo "✅ Docker build: PASSED"
echo ""

echo "7️⃣ Security checks..."
echo "  - Checking for vulnerable dependencies..."
safety check -r requirements-dev.txt --short-report || echo "⚠️  Safety check found issues (review manually)"

echo "  - Running security analysis..."
bandit -r backend/ -x backend/*/tests/ -f json -o bandit-report.json --quiet || echo "⚠️  Bandit found issues (check bandit-report.json)"
echo "✅ Security checks: COMPLETED"
echo ""

echo "🎉 All CI checks completed successfully!"
echo "Your code is ready to push to GitHub! 🚀"