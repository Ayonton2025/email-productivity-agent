# Phase 1: CI visibility and fresh-clone reproducibility

Scope agreed for this phase: combine fresh-clone reproducibility from the first
roadmap with explicit CI quality gates from the later repository-specific plan.

## Project boundaries reviewed

Bylix is a React/Vite and FastAPI email productivity platform. Its API routers
cover authentication, email accounts, inboxes, AI assistance, workflows,
campaigns, billing, team collaboration and administration. Services coordinate
SQLAlchemy persistence and provider integrations; Celery/Redis handle background
work. Mock mode uses SQLite and deterministic provider responses. Startup,
router registration, frontend routing/API access, configuration, database domains,
worker scheduling, test fixtures, deployment files and verification scripts were
reviewed before these changes.

## Changes and acceptance

| Requirement | Result |
| --- | --- |
| Explicit backend CI steps | Backend Quality exposes pytest, all three coverage gates, Ruff lint/format, mypy, Bandit and pip-audit. |
| Explicit frontend CI steps | Frontend Quality exposes npm ci, coverage tests, lint, formatting, typecheck, build and audit. |
| Retain reproducibility scripts | Bash, PowerShell and Python runners remain; Windows/Linux matrix, secrets scanning and deployment checks remain. |
| Preserve quality thresholds | Existing commands and thresholds match the runner; no new gate is conditional or allowed to fail. |
| Complete environment template | Every Settings field is represented, duplicate assignments removed, optional credential placeholders blanked. Effective noncredential values are preserved. |
| Protect environment contract | Regression test checks completeness, uniqueness and SQLite/mock/offline defaults. |
| Document install and verification | README provides clone URL, Python 3.11 selection, backend environment-file location, pinned installation and clean-checkout requirements. Development/testing guides align with the runner. |

## Local evidence (2026-09-07)

Verification used a separate Git clone of baseline `3d43a68` with only the Phase 1
file changes applied. No existing .env, Python environment or node_modules was
copied. The canonical Windows runner created a new Python environment, installed
the pinned tooling and lockfile, and ran npm ci. Package download caches may be
reused; installed dependency directories were fresh.

- Full Windows runner: passed (exit 0).
- Backend whole-application run: 196 tests passed, 34.31% coverage (31% required).
- Maintained-domain run, including the new template regression: 197 tests passed,
  80.42% coverage (50% required).
- Security-boundary run: 24 tests passed, 97.72% coverage (90% required).
- Ruff lint/format, mypy and Bandit: passed.
- Python dependency audit: no known vulnerabilities.
- Frontend: 111 tests passed; 43.11% lines/statements, 38.37% functions,
  54.32% branches. Formatting, zero-warning lint, typecheck and build passed.
- npm audit: zero vulnerabilities.
- Startup smoke test: example configuration initialized a new disposable SQLite
  database; /health and /ready returned 200; every configured API router loaded.
- Parsed workflow validation: explicit commands match all checks in verify.py,
  and the Windows/Linux matrix is preserved.
- Linux Docker deployment verification: passed (exit 0). All four images built;
  backend readiness/health, frontend page and frontend API proxy passed. Backend:
  197 tests passed, 34.30% application coverage. Frontend: 111 tests passed, with
  43.11% lines/statements, 38.37% functions and 54.32% branches. The script removed
  its own containers and network successfully.

## Publication checkpoint and later phases

Hosted GitHub Actions results for these changes are pending commit/push. Local
Docker results do not substitute for the hosted Windows/Linux workflow runs.
The configured publication destination is
https://github.com/Ayonton2025/email-productivity-agent.git.

Dependency-manifest synchronization, canonical ORM model consolidation, API and
Insights refactoring, inbox error handling, observability improvements and release
versioning remain for subsequent phases. No production application module,
existing database, provider account or deployment configuration was changed.
