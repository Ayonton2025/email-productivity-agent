# Bylix Email

A full-stack email productivity platform with AI assistance, multi-provider email, billing, automation, and team workflows.

## Stack

- Backend: FastAPI, async SQLAlchemy, Alembic, Celery, Redis
- Frontend: React 18, Vite, Tailwind, Lucide
- Persistence: PostgreSQL in connected deployments; SQLite in local mock mode
- Providers: Gmail, Outlook, IMAP/SMTP, Paystack, PayPal, and optional LLM providers

## Quick start

### Prerequisites

- Git
- Docker Desktop with Docker Compose

### Offline development

The default local path requires no provider accounts. It uses SQLite and deterministic mock billing, AI, email, FX, and GeoIP services.

```sh
git clone https://github.com/Ayonton2025/email-productivity-agent.git
cd email-productivity-agent
cp .env.example .env
docker compose up --build
```

No provider credentials are required for the default mock-mode configuration.
Wait for the services to become healthy, then open `http://localhost:3000` and
verify the backend at `http://localhost:8000/health`. From another terminal, run:

```sh
make health
```

Stop the stack with `docker compose down`. If `make` is unavailable, run
`./scripts/healthcheck.sh` directly from Git Bash, WSL, or another Bash shell.

The first build downloads the application dependencies. Later starts reuse the
Docker build cache.

### Local backend

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m uvicorn app.main:app --reload
```

### Local frontend

```powershell
Set-Location frontend
Copy-Item .env.example .env
npm ci
npm run dev
```

The frontend runs at `http://localhost:3000`.

## Verification

Run backend checks from `backend/`:

```powershell
python -m pytest tests --cov=app --cov-report=term-missing
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m bandit -c pyproject.toml -r app
python -m pip_audit
```

Run frontend checks from `frontend/`:

```powershell
npm ci
npm test -- --run
npm run lint
npm run format:check
npm run typecheck
npm run build
npm audit --audit-level=high
```

The GitHub Actions workflow runs these checks on every push and pull request. Dependabot checks both Python and npm dependencies weekly.

## Connected deployment

1. Copy `.env.example` to the environment file used by the deployment.
2. Set unique strong values for `SECRET_KEY` and `ENCRYPTION_KEY`.
3. Set `ENABLE_MOCK_MODE=false`.
4. Provide a production PostgreSQL `DATABASE_URL` and Redis URLs when Celery is enabled.
5. Configure only the OAuth, email, AI, and payment providers required by the deployment.
6. Set `ALLOWED_ORIGINS` to trusted HTTPS origins and configure `SENTRY_DSN` if monitoring is desired.
7. Start the connected stack with `docker compose --profile connected up -d`
   after preparing the root `.env` file. The profile enables PostgreSQL, Redis,
   database initialization, and Celery services in addition to the application.

Never commit `.env`, credentials, tokens, private keys, database files, dependency directories, or build output.

## Configuration

`.env.example` is the complete configuration reference. Important groups include:

- Runtime: `ENVIRONMENT`, `DEBUG`, `APP_VERSION`, `PORT`, `SERVICE_NAME`
- Security: `SECRET_KEY`, `ENCRYPTION_KEY`, JWT settings, CORS settings
- Data and workers: `DATABASE_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- AI: provider keys, model settings, and `ENABLE_MOCK_MODE`
- Email: OAuth, SMTP, IMAP, hosted-email, and abuse-control settings
- Billing: Paystack, PayPal, Stripe, Coinbase, Bybit, and FX settings
- Operations: logging, health, analytics, and Sentry settings

## Architecture

```text
React/Vite frontend
        |
FastAPI API and WebSockets
        |
Domain routers -> services -> async SQLAlchemy models
        |
PostgreSQL + Redis/Celery       External providers
```

Backend domains live under `backend/app/api`, `backend/app/services`, `backend/app/models`, and `backend/app/tasks`. The frontend is organized under `frontend/src/components`, `context`, `hooks`, `services`, and `utils`.

## Project documents

- [Development guide](docs/DEVELOPMENT.md): reproducible local setup and mock-mode contract
- [API reference](docs/API.md): endpoint details
- [Contributing guide](CONTRIBUTING.md): branch, commit, and testing rules
- [Changelog](CHANGELOG.md): release notes

## License

No license has been declared for this repository.
