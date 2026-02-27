#!/bin/sh
set -e

mkdir -p /app/data

echo "==> Running database migrations..."
python -m alembic upgrade head

echo "==> Starting AssetTrack..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
