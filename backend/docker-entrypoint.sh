#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database..."
while ! pg_isready -h ${DB_HOST:-db} -p ${DB_PORT:-5432} -U ${DB_USER:-postgres}; do
    sleep 1
done
echo "Database is ready!"

# Run migrations only for the service designated as the schema owner.
if [ "${RUN_DJANGO_MIGRATIONS:-1}" = "1" ]; then
    python manage.py migrate
fi

# Keep local Archetype content sufficient for the bundled starter deck. This
# flag is set only on the development backend service.
if [ "${SYNC_ARCHETYPE_DEV_CONTENT:-0}" = "1" ]; then
    python manage.py sync_archetype_dev
fi

# Collect static files
if [ "${RUN_COLLECTSTATIC:-1}" = "1" ]; then
    python manage.py collectstatic --noinput
fi

# Start server
exec "$@"
