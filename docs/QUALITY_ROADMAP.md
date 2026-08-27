# Quality Roadmap

## Objective

Raise the repository from its measured clean-clone baseline to a repeatable
100/100 release-quality score. A release candidate is not considered ready
until a new contributor can clone the repository and start the test stack with
one documented command and no manual file edits, secret creation, or platform-
specific workarounds.

## Scorecard

| Measure | Phase 0 baseline | Phase 1 current | Target |
| --- | ---: | ---: | ---: |
| Quality score | 31/100 | 40/100 | 100/100 |
| Backend statement coverage | 30.77% | 30.77% | 100% |
| Frontend coverage | Not collected | Not collected | 100% |
| Clean-clone Compose startup | Fail | Pass | Pass |
| Backend health endpoint | Unavailable | HTTP 200 | HTTP 200 |
| Frontend application | Unavailable | HTTP 200 | HTTP 200 |

The initial quality score is a deliberately conservative, reproducible proxy:
the rounded backend coverage percentage (30.77% -> 31). It is not presented as
an industry-standard aggregate. Future revisions should replace it with a
documented weighted score that includes tests, coverage, lint/type checks,
security, architecture, accessibility, performance, documentation, and clean-
environment operability. Until that rubric exists, increases to this score must
be backed by coverage output and completed acceptance criteria in this file.

## Phase 0 Baseline

Baseline captured on **2026-08-27** in a separate clean clone:

- Source: `https://github.com/Ayonton2025/email-productivity-agent.git`
- Clean-clone directory: `email-productivity-agent-clean`
- Commit: `d8647bf` (`fix: validate and persist draft metadata`)
- Starting branch: `main`, tracking `origin/main`
- Quality branch: `improvement/score-100`
- Docker: 29.7.2, build a7dcaa6
- Docker Compose: v5.4.0
- Command: `docker compose -f docker-compose.test.yml up --build`
- Compose configuration validation: passed
- Image builds: backend, backend-tests, frontend, and frontend-tests passed

### Failures and diagnostics

1. **Backend container cannot execute its entrypoint.**
   The container prints `exec /wait-for-db.sh: no such file or directory` and
   exits with code 255. The file is present in the image, but the source file
   uses CRLF line endings. Its first bytes are
   `23 21 2f 62 69 6e 2f 73 68 0d 0a`, so Linux interprets the shebang as
   `/bin/sh\r` instead of `/bin/sh`.
2. **Backend health is unavailable.**
   A direct request to `http://localhost:8000/health` is refused because the
   backend container has exited.
3. **Frontend is unavailable.**
   The frontend remains in the `Created` state because Compose requires a
   healthy backend. A direct request to `http://localhost:3000` is refused.
4. **The top-level Compose command fails.**
   Compose reports `dependency failed to start: container ... backend-1 exited
   (255)` and returns exit code 1 even though both test containers pass.
5. **Frontend coverage is not measured.**
   `npm test` runs Vitest without a coverage flag or report, so a frontend
   coverage percentage cannot be truthfully reported.
6. **Frontend dependency metadata is stale.**
   Vitest reports that `caniuse-lite` browser data is eight months old. This is
   non-blocking but should be handled through a reviewed dependency update.
7. **Container build emits root-install warnings.**
   pip warns about installing packages as root. This is non-blocking in the
   current multi-stage container build, but the image design should explicitly
   document or remove the warning.

### Passing baseline checks

- Backend: 109/109 tests passed with 13 warnings.
- Backend coverage: 30.77%; configured 30% minimum is satisfied.
- Frontend: 19/19 test files and 33/33 tests passed.
- Test images and application images build successfully from the clean clone.

## Completed fixes and quality work

- [x] Captured the baseline from a completely separate clean clone.
- [x] Recorded source commit and tool versions for reproducibility.
- [x] Validated the Compose configuration before runtime startup.
- [x] Built all four test-stack images without manual source changes.
- [x] Ran and recorded backend and frontend test results.
- [x] Probed both required URLs independently.
- [x] Identified the backend startup failure down to CRLF bytes in the shebang.
- [x] Created `improvement/score-100`.
- [x] Added this quality roadmap.

No product-code fix is included in Phase 0; preserving the observed baseline is
intentional. Remediation begins in the next phase and must add a regression
check for each corrected failure.

## Phase 1: Fresh Installation

Completed on **2026-08-27**. The quality score increased by 9 points, from
31/100 to 40/100, within the planned +8 to +10 range. This score change reflects
verified fresh-install operability and documentation/tooling improvements; test
coverage itself remains unchanged.

### Completed work

- [x] Added every environment variable found through backend `os.getenv`,
  `os.environ`, frontend `import.meta.env`, and frontend build-time
  `process.env` access. The audit found 33 user-configurable keys and zero
  missing keys after the update.
- [x] Added the scanner-requested `ENV`, `VITE_APP_NAME`, `RELOAD`,
  `REACT_APP_API_URL`, and `INIT_DB_RETRY_DELAY_SEC` values.
- [x] Added `VITE_CONTACT_EMAIL`, `VITE_OAUTH_REDIRECT_URI`, and
  `VITE_PAYSTACK_PUBLIC_KEY`, which were also used by frontend code.
- [x] Aligned all Compose application services on the documented root `.env`;
  no `backend/.env` copy is required.
- [x] Documented the exact clone, environment-copy, and one-command startup
  sequence in the README.
- [x] Added `scripts/healthcheck.sh` with strict error handling, bounded startup
  retries, timeouts, configurable URLs, and an executable Git mode (`100755`).
- [x] Added `install`, `run`, `test`, and `health` Makefile targets.
- [x] Added `.gitattributes` enforcement for LF shell scripts, preventing the
  Windows CRLF entrypoint regression found in Phase 0.
- [x] Normalized the complete backend entrypoint and verified it executes in
  Linux containers.
- [x] Made the default Compose graph a two-service, credential-free mock stack;
  connected PostgreSQL, Redis, initialization, and Celery services are explicit
  opt-ins through the `connected` profile.

### Phase 1 verification

- `docker compose config --quiet`: passed using only root `.env`.
- Default `docker compose up --build`: backend and frontend started without
  manual container fixes.
- `scripts/healthcheck.sh`: backend and frontend checks passed.
- `http://localhost:8000/health`: HTTP 200.
- `http://localhost:3000`: HTTP 200.
- Default Compose services: exactly `backend` and `frontend`.
- Backend regression suite: 109/109 passed with 30.77% coverage.
- Frontend regression suite: 19/19 files and 33/33 tests passed.
- Host note: GNU Make was unavailable on the Windows verification host, so the
  target recipes were verified through their underlying commands; the health
  script itself was executed with Git Bash.

### Remaining known issue

The optional `connected` profile is not yet fresh-database ready. Its
initialization path reaches PostgreSQL successfully but fails while querying the
missing `prompt_templates` relation. This does not affect the default mock-mode
installation verified above; it remains tracked for the database-migration
phase and must be resolved before connected deployment is declared ready.

## Planned remediation

### P0: Restore one-command startup

- [x] Normalize shell scripts used by Linux images to LF in source control.
- [x] Add `.gitattributes` rules (for example, `*.sh text eol=lf`) so Windows
  clones cannot reintroduce CRLF entrypoint failures.
- [x] Rebuild from a clean checkout and require both URLs to return HTTP 200.
- [x] Add an automated Compose smoke test that waits for backend health and then
  requests the frontend root page.
- [ ] Make the Compose command exit semantics explicit: tests must finish and
  application services must remain healthy, with failures propagated.

### P1: Make quality measurable

- [ ] Add frontend coverage collection and publish text plus machine-readable
  reports for both applications.
- [ ] Ratchet coverage thresholds upward in small, enforced increments; do not
  exclude business-critical code merely to improve the percentage.
- [ ] Define the weighted 100-point rubric and record evidence for every point.
- [ ] Separate unit, integration, contract, smoke, and end-to-end test results.
- [ ] Treat test warnings as tracked work and progressively enforce zero
  unexplained warnings.

### P2: Engineering safeguards

- [ ] Enforce formatting, linting, static typing, tests, coverage thresholds,
  dependency auditing, and container smoke tests in CI.
- [ ] Add deterministic database migration tests for empty and upgraded stores.
- [ ] Add boundary tests for authentication, billing, email-provider, webhook,
  attachment, and background-task paths.
- [ ] Add accessibility, responsive-layout, and critical-user-journey browser
  tests for the frontend.
- [ ] Establish dependency-update and vulnerability-response procedures.

## Architecture changes

| Date | Change | Rationale | Verification |
| --- | --- | --- | --- |
| 2026-08-27 | None in Phase 0 | Baseline must be observed before implementation changes | Clean clone and Compose run recorded above |
| 2026-08-27 | Default Compose runs backend/frontend in mock mode; infrastructure and workers moved behind `connected` profile | Make fresh installation credential-free while preserving the connected deployment path | Default service list contains two services; both return HTTP 200 |
| 2026-08-27 | Root `.env` is the shared Compose configuration source | Remove undocumented `backend/.env` copies and ambient-host interpolation conflicts | Compose configuration and runtime settings validated |

Future entries must name affected boundaries, migration or compatibility impact,
and the tests that demonstrate the change. Architecture work should prefer clear
module ownership, dependency direction, replaceable external-provider adapters,
and explicit transaction and failure boundaries.

## Definition of 100/100

The target is achieved only when all of the following are true:

- A fresh clone starts through the documented Compose command without edits.
- `http://localhost:8000/health` and `http://localhost:3000` return HTTP 200.
- All unit, integration, contract, smoke, and end-to-end suites pass.
- Backend and frontend coverage are both measured and meet the agreed threshold.
- CI enforces formatting, linting, typing, tests, coverage, security, and build
  checks on every proposed change.
- No unresolved critical/high security findings or undocumented test warnings
  remain.
- Architecture changes, operational instructions, and buyer-facing evidence are
  current and reproducible.

## Update protocol

Update this document in the same change as each quality improvement. Record the
new score, exact coverage values, completed checklist items, architecture impact,
verification commands, and any remaining failures. Never replace a failed
baseline result with an unverified claim.
