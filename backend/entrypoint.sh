#!/bin/sh
set -e

echo "==> Ejecutando migraciones Alembic..."
alembic upgrade head

echo "==> Iniciando servidor Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
