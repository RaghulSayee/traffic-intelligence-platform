#!/usr/bin/env bash

set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

PASSED=0
FAILED=0

run_check() {
  local title="$1"
  shift

  echo
  echo "=================================================="
  echo "Checking: $title"
  echo "=================================================="

  if "$@"; then
    echo "✅ PASS: $title"
    PASSED=$((PASSED + 1))
  else
    echo "❌ FAIL: $title"
    FAILED=$((FAILED + 1))
  fi
}

echo "Traffic Intelligence Platform"
echo "Pre-deployment validation"
echo "Project: $ROOT_DIR"

run_check \
  "Backend Ruff validation" \
  bash -c "cd '$BACKEND_DIR' && uv run ruff check ."

run_check \
  "Backend automated tests" \
  bash -c "cd '$BACKEND_DIR' && uv run pytest -q"

run_check \
  "Frontend ESLint validation" \
  bash -c "cd '$FRONTEND_DIR' && npm run lint"

run_check \
  "Frontend production build" \
  bash -c "cd '$FRONTEND_DIR' && npm run build"

run_check \
  "Backend OpenAPI readiness" \
  curl \
    --fail \
    --silent \
    --show-error \
    --max-time 10 \
    http://localhost:8000/openapi.json

run_check \
  "Cameras API" \
  curl \
    --fail \
    --silent \
    --show-error \
    --max-time 10 \
    "http://localhost:8000/api/v1/cameras?offset=0&limit=1"

run_check \
  "Videos API" \
  curl \
    --fail \
    --silent \
    --show-error \
    --max-time 10 \
    "http://localhost:8000/api/v1/videos?offset=0&limit=1"

run_check \
  "Processing Jobs API" \
  curl \
    --fail \
    --silent \
    --show-error \
    --max-time 10 \
    "http://localhost:8000/api/v1/jobs?offset=0&limit=1"

run_check \
  "Violations API" \
  curl \
    --fail \
    --silent \
    --show-error \
    --max-time 10 \
    "http://localhost:8000/api/v1/violations?offset=0&limit=1"

echo
echo "=================================================="
echo "Validation summary"
echo "=================================================="
echo "Passed: $PASSED"
echo "Failed: $FAILED"

if [ "$FAILED" -gt 0 ]; then
  echo
  echo "Pre-deployment validation failed."
  exit 1
fi

echo
echo "All automated checks passed."
