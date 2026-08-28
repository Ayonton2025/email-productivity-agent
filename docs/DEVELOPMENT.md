# Development and reproducibility

The default development configuration is deliberately offline. It uses SQLite
and deterministic mock billing, AI, and email delivery, so no external account
or API key is needed.

## Prerequisites

- Git
- Python 3.11
- Node.js 20 and npm
- Docker with Compose v2 (recommended for the one-command path)

## One-command isolated environment

From the repository root:

```bash
cp .env.example .env
docker compose -f docker-compose.test.yml up --build
```

Open the frontend at <http://localhost:3000> and backend health at
<http://localhost:8000/health>. The stack contains no PostgreSQL or Redis and
does not need payment, email, OAuth, or LLM credentials. It also runs backend
and frontend test containers. Stop it with:

```bash
docker compose -f docker-compose.test.yml down
```

## Local backend

Run these commands from `backend/`:

```bash
python -m venv .venv
```

Activate the environment (`.venv/Scripts/activate` on Windows or
`source .venv/bin/activate` on macOS/Linux), then run:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt
python -m uvicorn app.main:app --reload
```

Before starting from `backend/`, copy the root template to `backend/.env`
(`Copy-Item ..\.env.example .env` in PowerShell or `cp ../.env.example .env` on
macOS/Linux). Pydantic then reads the configuration from that local file.

Run backend checks:

```bash
python -m pytest tests --cov=app --cov-report=term-missing
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

Ruff enforces pycodestyle errors, Pyflakes, import sorting, and bugbear rules
at a 100-column line length. Mypy applies strict defaults to the typed migration
boundary declared in `pyproject.toml`. Its named legacy exceptions remain
visible beside the strict setting and should be removed individually as generic
parameters, third-party stubs, and function annotations are completed.

## Local frontend

Run these commands from `frontend/`:

```bash
cp .env.example .env
npm ci
npm run dev
npm run format:check
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

Prettier is the formatting authority for JavaScript, JSX, and CSS. ESLint owns
code-quality and React Hooks rules and extends `eslint-config-prettier` last so
the tools cannot issue conflicting style rules. `npm run lint` enforces the
recorded legacy warning ceiling; `npm run lint:strict` is the zero-warning
target for new and progressively cleaned code.

## Dependency policy

- `backend/pyproject.toml` documents package metadata, Python compatibility,
  tool configuration, and dependency groups.
- `backend/requirements.txt` is the reviewed direct dependency list.
- `backend/requirements-lock.txt` is the exact installation input used by the
  backend image.
- `frontend/package-lock.json` is installed with `npm ci`.

After changing Python dependencies, rebuild a clean Python 3.11 virtual
environment and regenerate the lock snapshot:

```bash
python -m pip install -r requirements.txt
python -m pip freeze --local > requirements-lock.txt
```

Review the resulting diff and run all checks before committing it. Do not run
the freeze command from a global Python environment.

## Mock-mode contract

With `ENABLE_MOCK_MODE=true`:

- AI returns deterministic JSON from the in-process mock provider.
- Paystack initialization and verification return successful local responses.
- available payment methods include the mock Paystack path without credentials.
- SMTP delivery returns success before decrypting credentials or opening a
  socket.
- live FX and GeoIP lookups are bypassed.
- the scheduled LLM provider health monitor is not started.
- SQLite is used by the provided environment and Compose configuration.

Mock responses include a `mock` marker where the existing response shape allows
one. Never use mock mode to validate real provider integrations or production
billing behavior.

## Connected mode

Set `ENABLE_MOCK_MODE=false`, choose a production-grade `DATABASE_URL`, enable
Redis/Celery if needed, and fill only the provider credentials used by the
deployment. `SECRET_KEY` and `ENCRYPTION_KEY` must be unique strong secrets.
Provider integrations must be tested separately because the isolated test stack
intentionally makes no external calls.
