#!/usr/bin/env bash

set -Eeuo pipefail

BACKEND_DIR="/app/backend"
FRONTEND_DIR="/app/frontend"

export PYTHONPATH="$BACKEND_DIR"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required."
  exit 1
fi

case "$DATABASE_URL" in
  postgres://*)
    export DATABASE_URL="postgresql+asyncpg://${DATABASE_URL#postgres://}"
    ;;
  postgresql://*)
    export DATABASE_URL="postgresql+asyncpg://${DATABASE_URL#postgresql://}"
    ;;
esac

export VIDEO_STORAGE_PATH="${VIDEO_STORAGE_PATH:-/tmp/traffic-intelligence/videos}"

export EVIDENCE_STORAGE_PATH="${EVIDENCE_STORAGE_PATH:-/tmp/traffic-intelligence/evidence}"

mkdir -p \
  "$VIDEO_STORAGE_PATH" \
  "$EVIDENCE_STORAGE_PATH" \
  /tmp/nginx-client-body \
  /tmp/nginx-proxy \
  /tmp/nginx-fastcgi \
  /tmp/nginx-uwsgi \
  /tmp/nginx-scgi

echo "Applying database migrations..."

cd "$BACKEND_DIR"

"$BACKEND_DIR/.venv/bin/alembic" \
  upgrade head

echo "Creating the initial administrator when needed..."

"$BACKEND_DIR/.venv/bin/python" \
  "$BACKEND_DIR/scripts/bootstrap_admin.py"

echo "Generating Nginx configuration..."

envsubst '${PORT}' \
  < /app/deploy/nginx.conf.template \
  > /tmp/nginx.conf

process_ids=()

cleanup() {
  trap - EXIT INT TERM

  if [ "${#process_ids[@]}" -gt 0 ]; then
    kill "${process_ids[@]}" \
      2>/dev/null || true

    wait "${process_ids[@]}" \
      2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

echo "Starting FastAPI..."

"$BACKEND_DIR/.venv/bin/uvicorn" \
  app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --proxy-headers \
  --forwarded-allow-ips="*" &

process_ids+=("$!")

if [[ "${RUN_VIDEO_WORKER:-true}" == "true" ]]; then
  echo "Starting the video-processing worker..."

  "$BACKEND_DIR/.venv/bin/python" \
    -m app.workers.run &

  process_ids+=("$!")
else
  echo "Video-processing worker is disabled."
fi

echo "Starting Next.js..."

(
  cd "$FRONTEND_DIR"

  PORT=3000 \
  HOSTNAME=127.0.0.1 \
  node server.js
) &

process_ids+=("$!")

echo "Starting Nginx on port ${PORT}..."

nginx \
  -c /tmp/nginx.conf \
  -g "daemon off;" &

process_ids+=("$!")

set +e
wait -n "${process_ids[@]}"
exit_status=$?
set -e

echo "A production process exited with status ${exit_status}."

exit "$exit_status"
