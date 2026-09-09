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
- Python 3.11
- Node.js 24 and npm
- Docker Desktop with Compose v2 for the isolated stack

### Clone the repository

```bash
git clone https://github.com/Ayonton2025/email-productivity-agent.git
cd email-productivity-agent
```

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

### Local backend installation

```powershell
Set-Location backend
Copy-Item ..\.env.example .env
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade -r requirements-tooling.txt
python -m pip install -r requirements-lock.txt
```

On macOS/Linux, use `cp ../.env.example .env`, `python3.11 -m venv .venv`,
and `source .venv/bin/activate` instead. The lockfile is the
single supported install input for a clean checkout; do not install the runtime
and development manifests in addition to it.

### Local backend

```powershell
Set-Location backend
python -m uvicorn app.main:app --reload
```

`requirements.txt` declares runtime dependencies, `requirements-dev.txt` declares local test and quality tools, and `requirements-lock.txt` pins the complete reproducible CI environment. `requirements-tooling.txt` pins patched packaging tools. Fresh-clone verification installs the tooling pins before the application lockfile and runs `pip check`. The runtime manifest mirrors `pyproject.toml` and uses the lockfile as constraints. See [dependency installation and update modes](docs/DEVELOPMENT.md#dependency-policy).

### Local frontend installation

```powershell
Set-Location frontend
Copy-Item .env.example .env
npm ci
```

### Local frontend

```powershell
Set-Location frontend
npm run dev
```

The frontend runs at `http://localhost:3000`.

## Verification

### Fresh-clone verification

Start from a new clone without copying `.env`, `.venv`, or `node_modules` from
an existing checkout. From its root, run the platform-specific verification script. It
creates a temporary Python 3.11 environment, installs the committed backend
lockfile, runs the backend suite and quality checks, performs `npm ci`, and
then runs the frontend suite, lint, formatting, typecheck, and production
build. The temporary backend environment is removed when the script finishes.

PowerShell:

```powershell
.\scripts\verify-fresh-clone.ps1
```

macOS/Linux:

```bash
bash scripts/verify-fresh-clone.sh
```

This is the canonical clean-checkout verification command. It requires Python
3.11, Node.js 24, and npm; it does not require Docker, an `.env` file, or provider
credentials. Dependency installation and security audits require internet access;
application tests use mock providers.

Run backend checks from `backend/`:

```powershell
python -m pytest tests --cov=app --cov-report=term-missing
python -m pytest tests --cov=app.core --cov=app.models --cov=app.utils --cov=app.services.email_service --cov=app.services.email --cov=app.services.mock_email_loader --cov=app.services.llm_orchestration_service --cov=app.services.model_registry --cov=app.services.prompt_registry --cov-report=term-missing --cov-fail-under=50
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m bandit -c pyproject.toml -r app --severity-level medium
python -m pip_audit
```

Run frontend checks from `frontend/`:

```powershell
npm ci
npm run test:coverage
npm run lint
npm run format:check
npm run typecheck
npm run build
npm audit --audit-level=high
```

The GitHub Actions workflow exposes each check in the Backend Quality and
Frontend Quality jobs on every push and pull request. Separate Windows and Linux
fresh-clone jobs retain the complete verification scripts. Dependabot checks both Python and npm dependencies weekly.

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

Licensed under [Apache License 2.0](LICENSE). See the [code of conduct](CODE_OF_CONDUCT.md) and [security policy](docs/SECURITY.md). Third-party dependencies retain their respective licenses.

## Verification contract

Both fresh-clone entry points invoke `scripts/verify.py` with Python 3.11 and Node 24. The runner creates an isolated backend environment, installs the backend lockfile and runs `npm ci`, then enforces backend tests and all three coverage gates, Ruff, mypy, Bandit, dependency audits, frontend coverage, zero-warning lint, formatting, type checking, and the production build. The environment is removed on success or failure. GitHub runs this contract on Windows and Linux.

Frontend coverage includes all application JS/JSX, including files that tests do not import. Minimums are 40% lines/statements, 35% functions, and 30% branches. Test files are excluded. Reports are written under `frontend/coverage/`.

Run `bash scripts/verify-compose.sh` to build and test the isolated Docker deployment. It verifies application health, the frontend and its API proxy, and both test-container exit codes, then shuts down its own Compose project. Failure logs are printed before cleanup. Docker must be running and ports 8000 and 3000 must be available. Initial builds may take several minutes depending on download speed.

The browser uses relative API paths during development. Docker sets `VITE_PROXY_TARGET=http://backend:8000` and `VITE_WS_PROXY_TARGET=ws://backend:8000` for traffic forwarded by the frontend container; browser-facing URLs remain host-accessible.

Use `TEST_BACKEND_PORT` and `TEST_FRONTEND_PORT` to select alternate ports for isolated verification when the defaults are in use. For example, on Bash: `TEST_BACKEND_PORT=18000 TEST_FRONTEND_PORT=13000 bash scripts/verify-compose.sh`.

The example files intentionally leave `ENCRYPTION_KEY` and payment-provider credentials empty. Generate a unique encryption key for each environment and obtain payment credentials from the provider. Never reuse values from repository history. See [the completion audit](docs/COMPLETION_AUDIT.md) for the historical credential findings and remediation status.

Attachment files use `ATTACHMENT_STORAGE_PATH` (default `storage/attachments` relative to the backend working directory). Docker keeps its existing `/app/storage/attachments` volume. Local attachment data is ignored by Git; tests use disposable temporary directories.
