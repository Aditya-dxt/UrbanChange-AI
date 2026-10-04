#!/usr/bin/env bash
set -e

echo "[entrypoint] Running database migrations..."
alembic upgrade head

echo "[entrypoint] Starting UrbanChange AI Backend API..."
exec "$@"
