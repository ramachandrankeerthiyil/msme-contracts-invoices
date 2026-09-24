#!/bin/sh
# Apply migrations (retrying while the database starts up), then start the API.
set -e

attempt=1
until alembic upgrade head; do
  if [ "$attempt" -ge 10 ]; then
    echo '{"level":"error","event":"db.migration_failed","message":"Giving up on migrations after 10 attempts"}'
    exit 1
  fi
  echo "{\"level\":\"warning\",\"event\":\"db.migration_retry\",\"message\":\"Migration attempt $attempt failed; retrying\",\"attempt\":$attempt}"
  sleep $((attempt * 2))
  attempt=$((attempt + 1))
done

exec python -m uvicorn app.main:create_app --factory \
  --host 0.0.0.0 --port "${PORT}" --no-access-log --proxy-headers
