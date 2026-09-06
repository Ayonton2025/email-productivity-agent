#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
compose=(docker compose -f docker-compose.test.yml -p "email-agent-verify-${GITHUB_RUN_ID:-local}")
cleanup() {
  result=$?
  if (( result != 0 )); then
    "${compose[@]}" ps -a || true
    "${compose[@]}" logs --no-color || true
  fi
  "${compose[@]}" down --remove-orphans || {
    cleanup_result=$?
    if (( result == 0 )); then result=$cleanup_result; fi
  }
  exit "$result"
}
trap cleanup EXIT
"${compose[@]}" config --quiet
"${compose[@]}" build
"${compose[@]}" up -d --wait --wait-timeout 180 backend frontend
curl --fail --retry 10 --retry-delay 2 --retry-all-errors "http://localhost:${TEST_BACKEND_PORT:-8000}/ready"
curl --fail --retry 10 --retry-delay 2 --retry-all-errors "http://localhost:${TEST_BACKEND_PORT:-8000}/health"
curl --fail --retry 10 --retry-delay 2 --retry-all-errors "http://localhost:${TEST_FRONTEND_PORT:-3000}/"
# Prove that the browser's relative API URL reaches the backend through Vite.
curl --fail --retry-all-errors --retry 5 --retry-delay 2 "http://localhost:${TEST_FRONTEND_PORT:-3000}/api/v1/health"
"${compose[@]}" run --rm backend-tests
"${compose[@]}" run --rm frontend-tests
