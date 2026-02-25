#!/usr/bin/env sh
set -e

if [ "${RUN_DB_MIGRATIONS:-true}" = "true" ]; then
  python manage.py upgrade head
fi

if [ "${RUN_SEED:-false}" = "true" ]; then
  python manage.py seed
fi

exec "$@"
