#!/bin/sh
# Throwaway backend for the browser tests: fresh SQLite database, seeded, served on E2E_BACKEND_PORT.
set -e
cd "$(dirname "$0")/../../backend"
PY="${E2E_PYTHON:-.venv/bin/python}"
export DJANGO_SETTINGS_MODULE=config.settings.e2e
export SECRET_KEY="${SECRET_KEY:-e2e-only-secret-key-not-for-production-use}"
export DATABASE_URL="sqlite:///$PWD/e2e.sqlite3"
export RATELIMIT_ANON=100000/minute RATELIMIT_USER=100000/minute RATELIMIT_AUTH=100000/minute
export RATELIMIT_SENSITIVE=100000/minute RATELIMIT_HEALTH=100000/minute RATELIMIT_LOCATION=100000/minute
rm -f e2e.sqlite3
"$PY" manage.py migrate --noinput
"$PY" manage.py e2e_seed
exec "$PY" manage.py runserver "127.0.0.1:${E2E_BACKEND_PORT:-8100}" --noreload
