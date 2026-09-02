# Troubleshooting

Start with `docker compose ps`, the API `/health` and `/ready` endpoints, and the structured logs. Every API response includes an `X-Request-ID`; use that value to correlate a browser failure with backend JSON logs and Sentry.

## A clean checkout does not install

- Use Python 3.11 and Node 20.
- Run `python -m pip install -r backend/requirements-lock.txt` from the repository root.
- Run `npm ci` in `frontend`; do not use `npm install` in CI or release verification.
- If a registry times out, retry before changing a lockfile. A network timeout is not evidence that a pinned package is invalid.

## The API does not start

1. Copy `.env.example` to `.env` and supply the required database, authentication and provider values.
2. Confirm PostgreSQL and Redis are healthy with `docker compose ps`.
3. Run migrations with `alembic upgrade head` from `backend`.
4. Check `/ready`. A healthy process can still report not-ready when a required dependency is unavailable.

## Requests are rejected

- `400` or `422`: compare the payload with [API.md](API.md); validation rejects malformed addresses, blank text and oversized input.
- `403 Invalid host header`: add the deployed hostname to `TRUSTED_HOSTS`.
- `429`: respect `Retry-After`; the rate limiter is working as designed.
- Browser CORS failure: add the exact frontend origin to `CORS_ORIGINS`. Do not use a wildcard with credentials.

## Sentry has no events

Set `SENTRY_DSN`, use a non-test environment, restart the API, and call the protected `/debug/error` endpoint as a super-admin. Verify outbound HTTPS is allowed. The route is deliberately unavailable when Sentry is not configured.

## Tests or formatting fail

Run the same commands as CI:

```bash
cd backend
python -m ruff check .
python -m ruff format --check .
python -m pytest -q

cd ../frontend
npm ci
npm run format:check
npm run lint
npm run typecheck
npm test
```

Install `pre-commit` and run `pre-commit install` once to enforce Ruff, ESLint and Prettier before every local commit. Gmail-specific diagnosis is in [GMAIL_CONNECTION_TROUBLESHOOTING.md](GMAIL_CONNECTION_TROUBLESHOOTING.md).

