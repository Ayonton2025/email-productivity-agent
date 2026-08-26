# Current-State Audit

Audit date: 2026-08-25  
Workspace: `email-productivity-agent-main`  
Scope: repository audit and safe starting point only; no application code was changed.

## Executive summary

This checkout is a large FastAPI/React email productivity platform with billing, AI, email-provider, automation, and collaboration features. The source is organized into recognizable API, service, model, task, context, component, and client-service layers, but several oversized modules concentrate risk and the automated test surface is very small.

The application cannot currently be reproduced from this machine using the documented local commands:

- The directory is **not a Git working tree** (`fatal: not a git repository`), so a `production-hardening` branch could not be created safely. Initializing a new repository would discard the original history context and was intentionally not done.
- `uvicorn app.main:app --reload`, run from `backend/`, starts Uvicorn's reloader but its application subprocess exits with `ModuleNotFoundError: No module named 'dotenv'` at `backend/app/main.py:8`.
- Python 3.11.9 is installed, but `pytest` is not installed or available on `PATH`.
- Node.js, npm, and Docker are not installed or available on `PATH`. Consequently `npm install`, `npm run dev`, frontend build/tests, and Compose startup could not run.

The supplied third-party repository report is partly stale or inaccurate for this checkout: `backend/requirements.txt`, backend and frontend lockfiles, two backend test files, one frontend test file, and both Dockerfiles are present. There is still no visible CI configuration, lint configuration, Python lockfile, or meaningful test coverage.

## Safe starting point

### Git status

Requested command:

```powershell
git checkout -b production-hardening
```

Result: blocked before execution because neither the workspace nor a parent directory contains `.git`. Before code changes, obtain a clone that includes `.git` (preferred), or explicitly approve initializing a new repository if original history is unavailable. Once restored, check for uncommitted work and then create the branch.

No application source files were edited during this audit.

## Startup audit

### Backend

Command run from `backend/`:

```powershell
uvicorn app.main:app --reload
```

Observed result:

1. Uvicorn binds its reloader to `http://127.0.0.1:8000`.
2. The child process imports `app.main`.
3. Import stops at `from dotenv import load_dotenv`.
4. Python raises `ModuleNotFoundError: No module named 'dotenv'`.

This is an environment/dependency installation failure, not proof of a broken declared dependency: `python-dotenv==1.0.0` is listed in `backend/requirements.txt`. Because import stops immediately, router imports, database initialization, Redis connectivity, health endpoints, and third-party API behavior remain unverified.

Additional backend observations:

- Default database configuration is local SQLite (`sqlite+aiosqlite:///./email_agent.db`), while Compose overrides it with PostgreSQL/asyncpg.
- The FastAPI lifespan initializes or verifies the database. Compose sets `SKIP_DB_INIT=true` for the API and delegates bootstrap to a separate `init_db` service.
- Compose depends on PostgreSQL and Redis health checks. Celery worker and beat depend on the API, Redis, database, and initialization service.
- `SECRET_KEY` and `ENCRYPTION_KEY` default to empty strings. Validation exists, but execution never reached the point where its startup effect could be observed.
- Mock mode defaults to enabled, but startup still requires installed packages and database initialization behavior. Mock mode does not by itself prove zero-network operation.
- `/health` checks database and Redis dependencies; `/api/v1/health` is also defined. Neither could be called because application import failed.

### Frontend

Requested commands from `frontend/`:

```powershell
npm install
npm run dev
```

Observed result: `npm` is not recognized as a command. Node.js is also unavailable. Dependency installation and Vite startup therefore did not begin.

The frontend declares Vite development, build, preview, and Vitest commands. `frontend/package-lock.json` is committed, so clean/CI installation should ultimately use `npm ci` rather than `npm install` after the lockfile is validated.

Potential configuration issue to verify once Vite runs: API URL defaults are inconsistent. `frontend/.env.example` uses `http://localhost:8000/api/v1`; `services/api.js` falls back to `http://127.0.0.1:8000/api/v1`; several components use `/api/v1`; and `main.jsx` can fall back to `http://localhost:8000`. Compose sets `VITE_API_URL=http://backend:8000`, which may omit the `/api/v1` prefix expected by some clients and is a container-only hostname that a browser on the host cannot resolve. This requires an integration test before changing it.

### Test status

- Backend: two pytest files are present, but `pytest` is unavailable, so no tests were collected or run.
- Frontend: one Vitest spec is present, but Node/npm is unavailable, so no tests were run.
- No coverage configuration or enforced threshold was found.
- No `.github/workflows` CI configuration was found in this checkout.

## Architecture overview

### Runtime topology

```text
Browser / React + Vite
  -> REST client (Axios plus several direct fetch wrappers)
  -> WebSocket client
      -> FastAPI application and routers
          -> domain services
              -> SQLAlchemy async database (SQLite locally / PostgreSQL in Compose)
              -> Redis + Celery worker/beat
              -> email providers (Gmail, Outlook, IMAP, SMTP, hosted providers)
              -> LLM providers (Google, OpenAI, Anthropic, OpenRouter, etc.)
              -> billing providers (Paystack, PayPal, Stripe, Coinbase, Bybit)
```

### Backend map

```text
backend/app/
├── api/       FastAPI routers, endpoint request models, WebSockets
├── core/      settings, security, logging
├── models/    SQLAlchemy models and database bootstrap/session logic
├── services/  email, AI, billing, automation, analysis, provider integrations
├── tasks/     Celery application and background/scheduled jobs
├── utils/     validation and helper functions
├── scripts/   database initialization
└── main.py    application lifecycle, router imports/registration, health routes
```

There is no separate `backend/app/schemas/` or `backend/app/database/` directory. Schemas are split between `api/schemas.py`, endpoint-local Pydantic classes, and model modules; database code lives mainly in `models/database.py`. This makes ownership and dependency boundaries less clear than the intended map.

Measured source size: 131 Python files and approximately 32,932 lines under `backend/app`.

### Frontend map

```text
frontend/src/
├── components/  feature UI, pages, forms, inbox, billing, admin
├── context/     authentication, email, account, and prompt state
├── hooks/       subscription/entitlement logic
├── services/    Axios/fetch API clients and payment/attachment/contact adapters
├── utils/       parsing, subscription, and timezone helpers
├── __tests__/   Vitest setup and one billing test
├── App.jsx      route/component composition
└── main.jsx     bootstrap plus substantial runtime/debug behavior
```

There is no distinct `src/pages/` directory; page-level behavior is housed in feature components. Measured source size: 74 JS/JSX/CSS files and approximately 22,517 lines under `frontend/src`.

## Largest and highest-risk files

| Lines | File | Primary risk |
|---:|---|---|
| 2,168 | `backend/app/services/billing_service.py` | Multiple payment providers, plans, subscriptions, credits, FX, and error policies in one module |
| 1,020 | `backend/app/main.py` | Lifecycle, dozens of guarded imports, router registration, health and operational concerns |
| 999 | `backend/app/api/user_email_endpoints.py` | OAuth/account connection, sync, inbox, message and send flows mixed together |
| 993 | `backend/app/api/billing_endpoints.py` | Large public billing surface tied to the god service |
| 917 | `backend/app/services/email_service.py` | Core email behavior and provider/data responsibilities |
| 802 | `backend/app/models/billing_models.py` | Broad billing persistence model surface |
| 778 | `frontend/src/components/prompts/PromptManager.jsx` | Large stateful UI with API interaction |
| 764 | `backend/app/api/ai_endpoints.py` | Large AI endpoint surface and permission/usage behavior |
| 691 | `frontend/src/App.jsx` | Central routing and application composition |
| 687 | `frontend/src/services/api.js` | Authentication, email, billing, WebSocket, token, and generic API concerns |
| 672 | `backend/app/models/database.py` | Engine/session setup, schema bootstrap, and model import coordination |
| 654 | `frontend/src/main.jsx` | Bootstrap mixed with diagnostics, health calls, auth handling, and HMR behavior |
| 653 | `backend/app/services/gmail_ingestion_service.py` | External provider parsing and persistence |
| 634 | `backend/app/services/llm_orchestration_service.py` | Provider selection, fallback, policy, and persistence |

CSS files over 500 lines were excluded from the risk ranking above when they were mostly styling, but they remain maintainability candidates.

## Duplication and code-quality findings

- `main.py` repeats guarded router imports and conditional registrations across dozens of modules. Import failures are sometimes logged and sometimes printed, allowing a partially configured API to boot without a single explicit route manifest.
- API modules repeat broad `except Exception` blocks and translate errors inconsistently. This can hide programming faults as generic HTTP failures.
- Frontend API access is duplicated across a large Axios service and direct `fetch` calls in contexts/components, with inconsistent base-URL construction and error handling.
- Authentication token access and logging are repeated across `AuthContext`, `api.js`, `main.jsx`, OAuth components, and feature components.
- Debug output is pervasive. Static search found many `print(...)` and `console.log(...)` calls, including logging of token presence and token prefixes. Even partial token logging should be removed before production.
- `backend/requirements.txt` duplicates `python-dotenv` and `python-dateutil`, and includes test dependencies in the runtime manifest.
- There is no detected Ruff/Black/isort configuration, ESLint configuration, pre-commit configuration, or CI enforcement.

## External dependency map

### Infrastructure

- SQLAlchemy async persistence; SQLite local default and PostgreSQL/asyncpg in Compose
- Redis as Celery broker/result backend
- Celery worker and beat for email, AI, campaign, workflow, integration, billing, and maintenance queues
- Alembic version files exist, but no `backend/alembic.ini` was found in the mapped files; migration execution needs verification
- Attachment storage uses a Docker volume

### Email and identity

- Gmail APIs and Google OAuth
- Microsoft Outlook/MSAL OAuth
- IMAP and SMTP providers, including hosted Mailcow, Postal, Mailu, Resend, and SendGrid abstractions
- JWT authentication with password hashing and encrypted credentials

### AI and document processing

- Google Generative AI, OpenAI, Anthropic, Hugging Face, OpenRouter, Groq, and Ollama configuration paths
- PDF, Word, Excel, and PowerPoint parsing

### Billing

- Paystack, PayPal, Stripe, Coinbase Commerce, Bybit Pay
- Geo-IP and exchange-rate HTTP services

Most credentials are optional in settings, but the corresponding user flows will fail or be disabled without provider configuration. Required production secrets include at minimum strong `SECRET_KEY` and `ENCRYPTION_KEY`; real email, LLM, and payment flows require their provider credentials.

## Critical user flows and what needs testing

1. **Authentication:** register, login, token validation/expiry, protected routes, logout, verification, password reset.
2. **Email account connection:** Gmail/Outlook OAuth and IMAP/SMTP credential connection, encryption, disconnect, and failure recovery.
3. **Inbox:** sync, pagination, message detail, attachments, category/read/flag state, and WebSocket updates.
4. **AI processing:** classification, summarization, reply generation, provider selection/fallback, quotas, timeouts, and mock mode.
5. **Sending and automation:** drafts, manual send, auto-reply approval, campaigns, workflows, follow-ups, retries, and idempotency.
6. **Billing:** plan lookup, regional method selection, checkout initialization, webhook authenticity/idempotency, subscription transition, credits, refunds/failures, and frontend upgrade UX.
7. **Background processing:** Celery routing, retry semantics, database session safety, Redis outages, worker health, and scheduled tasks.
8. **Authorization:** shared inbox permissions, admin endpoints, tenant/user data isolation, and entitlement enforcement on both API and UI boundaries.

The highest-priority tests are auth/security boundaries, payment webhook/idempotency behavior, subscription/credit mutations, email credential handling, sync/send idempotency, AI permission/quota behavior, and database migrations. These modules combine money, external side effects, secrets, and persistent state.

## Known failures and unverified areas

### Confirmed failures

- Missing Git metadata prevents branch creation and history inspection.
- Backend local startup fails because declared Python dependencies are not installed.
- Backend tests cannot start because `pytest` is unavailable.
- Frontend dependency installation and startup cannot start because Node/npm are unavailable.
- Docker Compose cannot be tested because Docker is unavailable.

### Unverified because startup was blocked

- Whether a clean install of all pinned Python packages resolves successfully on Python 3.11
- All backend router imports beyond the first missing dependency
- SQLite schema initialization and PostgreSQL migrations
- Redis/Celery connectivity and health behavior
- Frontend compile correctness and runtime routing
- REST/WebSocket URL compatibility between local, Compose, and production configurations
- All live provider APIs and webhook flows
- Whether tests pass at HEAD

## Missing components and technical debt

### Repository/reproducibility

- Git history/metadata in the delivered folder
- Python lockfile or hash-locked reproducible environment
- Separate runtime and development/test dependency manifests
- Verified fresh-clone bootstrap command
- CI workflow and required status checks
- Dependency update/audit automation

### Testing/quality

- Broad unit, integration, migration, contract, and end-to-end suites
- Coverage reporting and thresholds
- External-network isolation and deterministic provider fakes
- Lint, formatting, frontend lint, type checking, and pre-commit hooks
- Tests for startup configuration and route registration

### Architecture/operations

- Decomposition of billing, application bootstrap, email endpoints/services, API client, and frontend bootstrap
- One canonical frontend API/WebSocket URL builder
- Typed domain exceptions and consistent endpoint error translation
- Structured logging throughout and removal of token-related debug logging
- Verified migration configuration and a single documented schema-management strategy
- Explicit readiness versus liveness endpoints and dependency policies
- Error tracking initialization (settings mention Sentry on the frontend example, but no verified integration was found in this audit)

### Documentation

- `CONTRIBUTING.md`
- `CHANGELOG.md`
- Environment-variable reference generated or checked against actual settings and frontend usage
- A local-development prerequisites section with supported Python/Node/Docker versions
- Exact clean-install, test, lint, migration, and troubleshooting commands

## Recommended next phase

1. Restore the repository as a real Git clone and create `production-hardening` before edits.
2. Install documented toolchain prerequisites, then create isolated environments and install from the committed manifests.
3. Re-run backend import/startup, frontend clean install/build/dev startup, and existing tests; append exact versions and results to this audit.
4. Establish a minimal green CI baseline before refactoring: backend import smoke test plus pytest, frontend build plus Vitest, and dependency caching.
5. Add tests around the highest-risk money, authorization, email side-effect, and AI quota flows before splitting god files.

## Completion-criteria assessment

- **How the application starts:** mapped for local and Compose paths; local commands were attempted.
- **What breaks:** first-order environment and backend import failures are documented; deeper runtime failures remain blocked by missing prerequisites.
- **What needs testing:** critical flows and priority test targets are documented.
- **Which modules are risky:** largest/highest-impact modules and reasons are documented.

Phase 1 is complete as a static and constrained-runtime audit, but it is not a successful fresh-clone verification. That verification requires Git metadata plus the missing Node/npm, Python environment dependencies, and Docker toolchain.
