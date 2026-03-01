#!/usr/bin/env sh
set -e

if [ "${RUN_DB_MIGRATIONS:-true}" = "true" ]; then
  python manage.py upgrade head
fi

# Bootstrap admin/vendor on fresh deployments that have no staff users yet.
if [ "${AUTO_BOOTSTRAP_STAFF:-true}" = "true" ]; then
  python manage.py seed-if-needed
fi

if [ "${RUN_SEED:-false}" = "true" ]; then
  python manage.py seed
fi

exec "$@"
