#!/usr/bin/env bash

set -euo pipefail

BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL:-http://localhost:8000/health}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
CURL_TIMEOUT_SECONDS="${HEALTHCHECK_TIMEOUT_SECONDS:-10}"
HEALTHCHECK_RETRIES="${HEALTHCHECK_RETRIES:-30}"
HEALTHCHECK_RETRY_DELAY_SECONDS="${HEALTHCHECK_RETRY_DELAY_SECONDS:-2}"

check_url() {
    local name="$1"
    local url="$2"

    local attempt=1

    printf 'Checking %s at %s...\n' "$name" "$url"
    while [ "$attempt" -le "$HEALTHCHECK_RETRIES" ]; do
        if curl --fail --silent --show-error \
            --connect-timeout "$CURL_TIMEOUT_SECONDS" \
            --max-time "$CURL_TIMEOUT_SECONDS" \
            "$url" >/dev/null; then
            printf '%s is healthy.\n' "$name"
            return 0
        fi

        if [ "$attempt" -lt "$HEALTHCHECK_RETRIES" ]; then
            printf '%s is not ready (attempt %s/%s); retrying in %ss...\n' \
                "$name" "$attempt" "$HEALTHCHECK_RETRIES" "$HEALTHCHECK_RETRY_DELAY_SECONDS"
            sleep "$HEALTHCHECK_RETRY_DELAY_SECONDS"
        fi
        attempt=$((attempt + 1))
    done

    printf '%s failed after %s attempts.\n' "$name" "$HEALTHCHECK_RETRIES" >&2
    return 1
}

check_url "backend" "$BACKEND_HEALTH_URL"
check_url "frontend" "$FRONTEND_URL"
printf 'All application health checks passed.\n'
