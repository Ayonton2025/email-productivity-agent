#!/usr/bin/env bash
set -Eeuo pipefail
repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if command -v python3.11 >/dev/null 2>&1; then
  exec python3.11 "$repository_root/scripts/verify.py"
fi
exec python3 "$repository_root/scripts/verify.py"
