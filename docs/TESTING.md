# Testing

## Quality strategy

Tests cover request contracts, authentication, billing, email services, architecture boundaries, security middleware, exceptions, health/readiness, manifest drift and frontend user flows. CI repeats tests, formatting, lint, typing, security audits and Docker builds on pushes and pull requests.

## Backend

```bash
cd backend
python -m venv .venv
python -m pip install -r requirements-lock.txt
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

CI enforces coverage:

```bash
python -m pytest tests --cov=app --cov-report=term-missing --cov-fail-under=31 -q
python -m pytest tests --cov=app.core --cov=app.models --cov=app.utils --cov=app.services.email_service --cov=app.services.llm_orchestration_service --cov=app.services.model_registry --cov=app.services.prompt_registry --cov-report=term-missing --cov-fail-under=50 -q
```

The repository has three explicit coverage layers:

- A 31% whole-application ratchet measures every API, background task, and external-provider adapter.
- A 50% maintained-domain gate covers `app.core`, `app.models`, `app.utils`, email processing, LLM orchestration, and the model and prompt registries.
- A 90% gate protects request schemas and input-validation security boundaries.

The maintained-domain scope identifies code expected to be deterministic in local and CI environments. External email, payment, and AI adapters remain visible in the whole-application report and are tested through mocks and contracts rather than live credentials. Raise either threshold only alongside tests that make it pass; never exclude production modules merely to manufacture a percentage.

Utility tests cover safe parsing, email/header validation, active-content sanitization, URL allowlists, nested JSON contracts, priority scoring, formatting boundaries, and asynchronous retry behavior. Email and LLM tests use in-memory SQLite and mocked providers to verify duplicate detection, typed failures, cache hits, provider fallback, and missing-provider responses.

Local formatting is enforced through `.pre-commit-config.yaml`. After installing `pre-commit`, enable it once with `pre-commit install`; the hooks run Ruff, ESLint and Prettier using the committed configuration.

## Frontend

Use Node 20 and always use `npm ci`, not `npm install`, for verification:

```bash
cd frontend
npm ci
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
```

## Security and dependencies

```bash
cd backend
python -m bandit -c pyproject.toml -r app --severity-level medium
python -m pip_audit

cd ../frontend
npm audit --audit-level=high
```

Dependabot checks pip, npm and GitHub Actions weekly. Contract tests ensure direct and pyproject dependencies remain in `requirements-lock.txt`, and `package.json` stays aligned with `package-lock.json`.

## Containers

```bash
docker compose -f docker-compose.test.yml build
docker compose -f docker-compose.test.yml run --rm backend-tests
docker compose -f docker-compose.test.yml run --rm frontend-tests
```

Tests use mock mode and isolated SQLite where practical. Never use production credentials, customer mailboxes or live payment keys.
