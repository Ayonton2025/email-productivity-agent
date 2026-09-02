# Deployment

## Reference topology

Production separates frontend and backend containers, PostgreSQL, Redis, Celery workers, Celery Beat and a one-off migration/bootstrap job. `docker-compose.yml` is intended for local/integration use; production should use managed data services and ingress.

## Local containers

1. Copy `.env.example` to `backend/.env` and replace placeholders.
2. Set exact `ALLOWED_ORIGINS` and `TRUSTED_HOSTS`.
3. Run `docker compose up --build`.
4. Verify `/health`, `/ready`, and the frontend on port 3000.

Never expose the example database or admin passwords.

## Release pipeline

`.github/workflows/release.yml` runs for tags such as `v2.1.0` or manual dispatch with a SemVer input. Manual releases create an annotated tag; an existing tag is never overwritten.

It publishes:

- `ghcr.io/<owner>/email-productivity-agent-backend:<version>`
- `ghcr.io/<owner>/email-productivity-agent-frontend:<version>`
- immutable commit-SHA tags
- `latest` only for stable releases

Images carry OCI metadata, SBOMs and build provenance. Publication uses scoped `contents: write` and `packages: write` permissions through `GITHUB_TOKEN`.

## Production rollout

1. Back up PostgreSQL and validate the restore point.
2. Run additive migrations from the immutable backend image.
3. Deploy APIs and confirm readiness.
4. Deploy workers, then one scheduler.
5. Deploy frontend assets.
6. Smoke-test authentication, inbox, sending, AI and billing.
7. Monitor errors, queue depth, connections and provider failures.

Rollback containers to their prior SHA tag. Database rollback needs a migration-specific plan; prefer forward fixes once production data changes.

## Operations

- `/health` provides liveness and `/ready` provides traffic readiness.
- JSON logs include timestamps and request IDs.
- Sentry starts only when `SENTRY_DSN` is configured.
- `/debug/error` is unavailable unless debug mode is enabled and must remain disabled in production.
- `.env.example` inventories required and optional configuration.
