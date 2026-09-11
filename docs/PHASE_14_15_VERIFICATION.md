# Phases 14-15: Fresh clone and verification script

## Fresh clone

A genuine clone of `phase-13-verification` was created from GitHub in a new
temporary directory. The clone contained no `.env`, backend virtualenv, or
frontend `node_modules` before installation.

Using Python 3.11 and Node 24:

- Pinned backend tooling and lockfile dependencies installed successfully.
- Backend dependency check passed.
- Backend suite passed: 319 tests.
- Frontend `npm ci` completed.
- Frontend suite passed: 156 tests across 32 files.
- Frontend lint, typecheck, and production build passed.

The first clean frontend install exposed four npm audit findings: one high
`js-yaml` advisory and three moderate Vitest advisories. The underlying issue
was fixed by updating `js-yaml` through the lockfile and upgrading Vitest and
`@vitest/coverage-v8` to 5.x. The upgraded dependency set was tested in the
fresh clone: all 156 frontend tests, lint, typecheck, build, and audit passed.
The committed lockfile now matches that verified resolution.

The source workspace later showed timing variance in several long UI tests after
the upgrade, while the genuine clean clone passed all 156 tests with the same
Vitest 5 lockfile. No tests were changed to mask that local mounted-workspace
variance; the clean clone is the Phase 14 result.

## Verification script

`scripts/verify.py` was retained and run from the fresh clone. Its backend
quality gates passed: dependency compatibility, Ruff, formatting, mypy, whole
application coverage, maintained-domain coverage, security-boundary coverage,
Bandit, and pip-audit. The frontend gates passed through build; its final npm
audit failed only on the pre-remediation dependency set and was rerun
successfully after the Vitest/js-yaml update.

The final source checkout rerun recorded these frontend statuses:

```text
audit=0 test=0 lint=0 typecheck=0 build=0
```

## Scope and limits

No production credentials, customer mailboxes, payment keys, live Gmail
accounts, or hosted Sentry delivery were used. Local and fresh-clone passes do
not prove GitHub-hosted CI, live provider delivery, deployment behavior, or
hosted monitoring ingestion. Those remain separately reported checks.
