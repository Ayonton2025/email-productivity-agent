# Bylix Email

A full-stack email productivity platform with AI assistance, multi-provider email, billing, automation, and team workflows.

## Installation & Testing

### Backend

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt
pip install -r backend/requirements-lock.txt
cd backend && python -m pytest tests --cov=app --cov-report=term-missing
```

### Frontend

```bash
cd frontend && npm install && npm run build && npm run test
```

## Stack

- Backend: FastAPI, async SQLAlchemy, Alembic, Celery, Redis
- Frontend: React 18, Vite, Tailwind, Lucide
- Persistence: PostgreSQL in connected deployments; SQLite in local mock mode
- Providers: Gmail, Outlook, IMAP/SMTP, Paystack, PayPal, and optional LLM providers

## Quick start

### Prerequisites

- Git
- Python 3.11
- Node.js 24 and npm
- Docker Desktop with Compose v2 for the isolated stack

### Offline development

The default local path requires no provider accounts. It uses SQLite and deterministic mock billing, AI, email, FX, and GeoIP services.

```powershell
Copy-Item .env.example .env
docker compose -f docker-compose.test.yml up --build
```

Open `http://localhost:3000` for the frontend and `http://localhost:8000/health` for backend health. Stop the stack with:

```powershell
docker compose -f docker-compose.test.yml down
```

### Local backend

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m uvicorn app.main:app --reload
```

`requirements.txt` declares runtime dependencies, `requirements-dev.txt` declares local test and quality tools, and `requirements-lock.txt` pins the complete reproducible CI environment. Fresh-clone verification always installs the lockfile.

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
python -m pytest tests --cov=app.core --cov=app.models --cov=app.utils --cov=app.services.email_service --cov=app.services.llm_orchestration_service --cov=app.services.model_registry --cov=app.services.prompt_registry --cov-report=term-missing --cov-fail-under=50
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m bandit -c pyproject.toml -r app --severity-level medium
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

Coverage uses two complementary measurements. The whole-application 31% ratchet reports every API, task, and external-provider integration so legacy coverage cannot regress. A separate 50% maintained-domain gate covers core infrastructure, models, utilities, email processing, LLM orchestration, and the model and prompt registries. The security-critical validation boundary retains its stricter 90% gate. Tests use deterministic mocks and in-memory SQLite; they do not contact customer mailboxes, payment processors, or AI providers.

## Connected deployment

1. Copy `.env.example` to the environment file used by the deployment.
2. Set unique strong values for `SECRET_KEY` and `ENCRYPTION_KEY`.
3. Set `ENABLE_MOCK_MODE=false`.
4. Provide a production PostgreSQL `DATABASE_URL` and Redis URLs when Celery is enabled.
5. Configure only the OAuth, email, AI, and payment providers required by the deployment.
6. Set `ALLOWED_ORIGINS` to trusted HTTPS origins and configure `SENTRY_DSN` if monitoring is desired.
7. Start the connected stack with `docker compose up -d` after preparing `backend/.env`.

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

- [Architecture](docs/ARCHITECTURE.md): topology, runtime boundaries and extensibility
- [Database](docs/DATABASE.md): data domains, relationships and recovery expectations
- [Security](docs/SECURITY.md): implemented controls and production checklist
- [Deployment](docs/DEPLOYMENT.md): releases, GHCR images, rollout and rollback
- [Testing](docs/TESTING.md): local, CI, security and container verification
- [Troubleshooting](docs/TROUBLESHOOTING.md): startup, request, Sentry and clean-install diagnosis
- [API reference](docs/API.md): authentication, resources and conventions
- [Development guide](docs/DEVELOPMENT.md): reproducible setup and mock-mode contract
- [Contributing guide](CONTRIBUTING.md): branch, commit, and testing rules
- [Changelog](CHANGELOG.md): release notes

## License

No license has been declared for this repository.
