# Development and reproducibility

The default development configuration is deliberately offline. It uses SQLite
and deterministic mock billing, AI, and email delivery, so no external account
or API key is needed.

## Prerequisites

- Git
- Python 3.11
- Node.js 24 and npm
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
python3.11 -m venv .venv  # Windows: py -3.11 -m venv .venv
```

Activate the environment (`.venv/Scripts/activate` on Windows or
`source .venv/bin/activate` on macOS/Linux), then run:

```bash
python -m pip install --upgrade -r requirements-tooling.txt
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

## Local frontend

Run these commands from `frontend/`:

```bash
cp .env.example .env
npm ci
npm run dev
npm test -- --run
npm run build
```

## Fresh-clone verification

From the repository root, run `scripts/verify-fresh-clone.ps1` on Windows or
`bash scripts/verify-fresh-clone.sh` on macOS/Linux. The script creates a
temporary Python 3.11 environment, installs both committed lockfiles, runs
backend and frontend tests, lint, formatting, typecheck, and the frontend
production build, then removes the temporary backend environment.

## Dependency policy

- `backend/pyproject.toml` is the source of truth for direct runtime dependencies,
  development extras and backend package metadata. The package version remains
  `1.0.0`, matching the frontend package metadata; runtime `APP_VERSION` is a
  separate configurable application label. Release versioning is a later phase.
- `backend/requirements.txt` mirrors the runtime versions and extras. It applies
  `requirements-lock.txt` as constraints so transitive versions stay reproducible
  without installing development tools into a runtime-only environment.
- `backend/requirements-dev.txt` includes the runtime file and mirrors the `dev`
  extra, keeping development tools separate from runtime requirements.
- `backend/requirements-lock.txt` pins the tested runtime/development environment.
  Docker and the full verification runner install it directly.
- `backend/requirements-tooling.txt` pins packaging tools separately.
- `frontend/package-lock.json` is installed with `npm ci`.

From a fresh Python 3.11 environment in `backend/`, install the tooling first:

```bash
python -m pip install --upgrade -r requirements-tooling.txt
```

Choose one installation mode:

```bash
# Runtime only (the requirements file applies the committed constraints)
python -m pip install -r requirements.txt

# Runtime plus development tools
python -m pip install -r requirements-dev.txt

# Editable package with development tools and the same constraints
python -m pip install --no-build-isolation -c requirements-lock.txt -e ".[dev]"
```

`--no-build-isolation` uses the packaging tools installed above. After installation,
run `python -m pip check`. For development modes, also run
`python -m pytest tests/test_dependency_manifests.py -q` and the full backend checks.
Tests reject manifest drift in names, versions, extras and markers, duplicate
requirements, incompatible lock pins, and build-tool inconsistencies.

### Intentional dependency updates

Change direct dependencies in both pyproject.toml and the matching requirements
file. Do not promote every transitive lock entry into a direct dependency.

To resolve an updated graph, use another fresh Python 3.11 environment with the
pinned packaging tools. Install the editable development extra without the old
constraints only when intentionally updating the lock. Generate a candidate file
instead of overwriting the reviewed lockfile:

```bash
python -m pip install --no-build-isolation -e ".[dev]"
python -m pip check
python -c "import pathlib, subprocess, sys; pathlib.Path('requirements-lock.next.txt').write_bytes(subprocess.check_output([sys.executable, '-m', 'pip', 'freeze', '--exclude-editable', '--exclude', 'pip', '--exclude', 'setuptools', '--exclude', 'wheel']))"
```

This includes development dependencies and excludes the local editable path and
separately pinned build tools. Review the candidate against the committed lock;
resolve on Windows and Linux and preserve platform markers for platform-specific
packages. A freeze from only one platform is not a complete cross-platform lock.
Then validate fresh installs, tests and audits before replacing the lockfile.
Never generate the snapshot from a global or reused development environment.

Pip documents the distinction between requirements and
[constraints](https://pip.pypa.io/en/stable/user_guide/#constraints-files), and
[`pip check`](https://pip.pypa.io/en/stable/cli/pip_check/) validates installed
dependency compatibility.

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
