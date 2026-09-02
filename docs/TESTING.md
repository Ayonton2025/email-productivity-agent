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
python -m pytest tests --cov=app --cov-report=term-missing --cov-fail-under=30 -q
```

The repository currently has a 30% whole-application ratchet and a 90% gate for the request-schema and input-validation security boundary. The narrower gate protects the highest-risk code while the broad ratchet prevents regressions across the large integration surface. Raise the broad threshold only alongside tests that make it pass; never exclude production modules to manufacture a percentage.

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
