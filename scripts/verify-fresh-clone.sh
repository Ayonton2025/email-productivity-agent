#!/usr/bin/env bash
set -Eeuo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
backend_root="$repository_root/backend"
frontend_root="$repository_root/frontend"
verification_root="$(mktemp -d "${TMPDIR:-/tmp}/email-productivity-agent-verify.XXXXXX")"
backend_venv="$verification_root/backend-venv"

cleanup() {
  rm -rf "$verification_root"
}
trap cleanup EXIT

step() {
  printf '\n==> %s\n' "$1"
}

if command -v python3.11 >/dev/null 2>&1; then
  python_command="python3.11"
elif command -v python3 >/dev/null 2>&1 && [[ "$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" == "3.11" ]]; then
  python_command="python3"
else
  echo 'Python 3.11 is required but was not found.' >&2
  exit 1
fi

step 'Check Python 3.11'
"$python_command" --version

step 'Create backend verification environment'
"$python_command" -m venv "$backend_venv"
backend_python="$backend_venv/bin/python"

if [[ "${SKIP_INSTALL:-false}" != "true" ]]; then
  step 'Install backend lockfile'
  "$backend_python" -m pip install --disable-pip-version-check --no-input -r "$backend_root/requirements-lock.txt"
fi

pushd "$backend_root" >/dev/null
step 'Run backend tests'
"$backend_python" -m pytest tests --cov=app --cov-report=term-missing
step 'Run backend Ruff lint'
"$backend_python" -m ruff check .
step 'Check backend formatting'
"$backend_python" -m ruff format --check .
popd >/dev/null

pushd "$frontend_root" >/dev/null
if [[ "${SKIP_INSTALL:-false}" != "true" ]]; then
  step 'Install frontend lockfile'
  npm ci
fi
step 'Run frontend tests'
npm test -- --run
step 'Run frontend lint'
npm run lint
step 'Check frontend formatting'
npm run format:check
step 'Run frontend typecheck'
npm run typecheck
step 'Build frontend'
npm run build
popd >/dev/null

printf '\nFresh-clone verification passed.\n'
