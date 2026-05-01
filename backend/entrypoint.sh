#!/bin/sh
set -e

echo "Waiting for Postgres to be ready..."
until pg_isready -h postgres -p 5432; do
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
