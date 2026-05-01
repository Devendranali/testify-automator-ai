#!/bin/sh
set -e

DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"

echo "Waiting for Postgres to be ready at ${DB_HOST}:${DB_PORT}..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT"; do
  sleep 2
done

echo "Postgres is ready"

if [ "${AUTO_MIGRATE:-false}" = "true" ] || [ "${AUTO_MIGRATE:-false}" = "1" ] || [ "${AUTO_MIGRATE:-false}" = "yes" ] || [ "${AUTO_MIGRATE:-false}" = "on" ]; then
  echo "AUTO_MIGRATE enabled. Running Alembic migrations..."
  alembic -c /app/database/alembic.ini upgrade head
else
  echo "AUTO_MIGRATE disabled. Skipping Alembic migrations at container startup."
fi

echo "Starting backend services..."
exec "$@"
