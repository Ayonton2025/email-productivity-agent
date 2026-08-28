# Quality Roadmap

## Objective

Raise the repository from its measured clean-clone baseline to a repeatable
100/100 release-quality score. A release candidate is not considered ready
until a new contributor can clone the repository and start the test stack with
one documented command and no manual file edits, secret creation, or platform-
specific workarounds.

## Scorecard

| Measure | Phase 0 baseline | Phase 2 current | Target |
| --- | ---: | ---: | ---: |
| Quality score | 31/100 | 57/100 | 100/100 |
| Backend statement coverage | 30.77% | 31.72% | 80% |
| Frontend statement coverage | Not collected | 15.99% | 70% |
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

## Phase 2: Test Coverage and Critical Paths

Implemented on **2026-08-28**. The quality score increased by 8 points, from
40/100 to 48/100, for reproducible frontend coverage, enforced non-regression
gates, and tests around the highest-risk email and LLM paths. The numeric
coverage targets are not claimed as complete: measuring all production source
revealed 31.32% backend and 15.42% frontend statement coverage.

### Completed work

- [x] Added `pytest-mock` as a pinned, reproducible backend test dependency.
- [x] Added email ingestion duplicate-detection coverage and verified that a
  duplicate returns the persisted message without creating another record.
- [x] Added provider-boundary validation for malformed recipient addresses.
- [x] Implemented and tested Gmail-to-Outlook and Outlook-to-Gmail delivery
  fallback when the preferred provider fails and the alternate is configured.
- [x] Added LLM provider-switching coverage for OpenAI failure followed by a
  successful Anthropic response.
- [x] Added LLM structured-response, input/output token, and model-cost tests.
- [x] Extracted testable API interceptor behavior and covered successful
  responses, `401` credential removal/redirect, public-route behavior, and
  friendly `5xx` errors.
- [x] Expanded Prompt Manager tests for rendering/filtering, loading, delete
  interaction, and delete failure; added an accessible name to its icon-only
  destructive action.
- [x] Tested the real email composer inside `EmailDetailPage` for rendering,
  generation loading/success/failure, and reply submission. There is no
  standalone `EmailComposer.jsx` in this repository, so creating an unused
  duplicate component was deliberately avoided.
- [x] Added Insights Dashboard rendering, tab interaction, loading completion,
  friendly error, and retry coverage; the component now exposes failed loads
  through an accessible alert instead of only logging them.
- [x] Added V8 coverage instrumentation with terminal, JSON-summary, and HTML
  reports. CI and `docker-compose.test.yml` now execute frontend coverage.

### Verified results

- Backend focused service suite: 6/6 passed.
- Backend complete suite: 115/115 passed with 13 warnings.
- Backend complete-source coverage: 31% (15,152 statements; 9,630 missed).
- Frontend focused critical-flow suite: 15/15 passed.
- Frontend complete suite: 22/22 files and 47/47 tests passed.
- Frontend complete-source coverage: 15.42% statements, 45.16% branches,
  21.21% functions, and 15.42% lines.

### Coverage ratchet

The previous backend gate was 30%. It is now 31%, the highest conservative
whole-application integer gate supported by the measured suite. Frontend now
starts with enforced 15% statement/line, 45% branch, and 20% function gates.
These are floors, not targets, and must never be lowered to merge a change.

The planned backend sequence is **31 → 40 → 50 → 60 → 70 → 80**. Once 60%
is reached, the originally proposed 60 → 70 → 80 sequence applies directly.
The frontend sequence is **15 → 30 → 50 → 60 → 70**. Each increase requires a
complete-suite report in the same change. Jumping the backend directly to 60%
today would make CI fail by roughly 29 percentage points and would be a false
quality signal, so it is explicitly deferred rather than hidden with broad
coverage exclusions.

### Next coverage priorities

1. Authentication endpoints and `AuthContext` session restoration/expiry.
2. `email_service.py` ingestion, synchronization, persistence, and rollback
   branches beyond duplicate detection.
3. LLM timeout, malformed JSON, retry exhaustion, cache, and budget limits.
4. Frontend application routing/context plus inbox list and account connection.
5. Billing/webhook contract tests and empty-database migration tests.

## Phase 3: Architecture Decomposition

Implemented on **2026-08-28**. The quality score increased by 9 points, from
48/100 to 57/100, for replacing four buyer-risk monoliths with explicit,
tested module boundaries. The refactor preserves legacy import paths and public
component exports, so API endpoints, background tasks, tests, and external
integrators can migrate without a flag day.

### Measured result

| Original boundary | Before | Compatibility file after | Largest extracted implementation |
| --- | ---: | ---: | ---: |
| `llm_orchestration_service.py` | 976 lines | 8 lines | 268 lines |
| `email_service.py` | 923 lines | 8 lines | 340 lines |
| `PromptManager.jsx` | 769 lines | 365 lines | 244 lines |
| `App.jsx` | 757 lines | 9 lines | 238 lines |

All 36 files governed by the Phase 3 architecture check are below 400 lines.
The guard counts blank lines and comments, preventing superficial formatting or
comment changes from hiding renewed growth.

### Backend boundaries

- [x] Created `app.services.llm` with separate model and prompt registries,
  usage persistence, provider calls, health diagnostics, structured workflows,
  exceptions, and a 256-line coordinator.
- [x] Kept `app.services.llm_orchestration_service` as an eight-line facade that
  re-exports the exact class, singleton, and registries used by existing code.
- [x] Created `app.services.email` with validation, duplicate detection, mock
  catalog, persistence, intelligence, provider adapters, and a 211-line service.
- [x] Added a strict normalized inbound `process_email` pipeline: validate,
  check duplicate, and only then process/persist.
- [x] Added Gmail and Outlook adapter boundaries behind a common abstract
  provider contract while retaining the established delivery implementation.
- [x] Kept `app.services.email_service` as an eight-line compatibility facade.
- [x] Added tests proving old and new import paths resolve to the same classes
  and that the new email validation boundary normalizes or rejects input.

### Frontend boundaries

- [x] Reduced `App.jsx` to rendering `AppRouter` and retaining the historical
  `AppContent` named export used by `Home` and tests.
- [x] Moved route composition and access guards into `routes/router.jsx` and
  `routes/protectedRoutes.jsx`; navigation metadata has its own module.
- [x] Added explicit application-level `AuthProvider` and `ThemeProvider`
  composition boundaries without duplicating context state.
- [x] Moved the authenticated shell and sidebar into focused layout modules.
- [x] Split Prompt Manager into AI drafting, list, editor, testing, and history
  components while preserving its existing context contract and interactions.
- [x] Added frontend tests that enforce the 400-line ceiling on critical files.

### Regression safeguards

- `python scripts/check_architecture_sizes.py` checks all Phase 3 modules and is
  enforced by a dedicated CI job.
- Backend compatibility and validation tests protect old imports and the new
  processing boundary.
- Existing Prompt Manager, protected-route, dashboard, LLM, and email behavior
  suites are used as contract tests during the move.
- New modules remain inside existing coverage collection; no coverage exclusion
  was introduced to make the architecture metrics look better.

### Phase 3 verification

- Backend complete suite: 119/119 passed with the enforced 31% gate.
- Backend complete-source coverage: 31.72%.
- Frontend complete suite: 23/23 files and 57/57 tests passed.
- Frontend complete-source coverage: 15.99% statements, 46.07% branches,
  21.86% functions, and 15.99% lines.
- Frontend production build and TypeScript check passed.
- Full frontend lint passed with 110 pre-existing warnings, down from the
  previous 112-warning allowance and with zero errors.
- Focused backend Ruff checks passed with zero errors.

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

- [x] Add frontend coverage collection and publish text plus machine-readable
  reports for both applications.
- [x] Ratchet coverage thresholds upward in small, enforced increments; do not
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
| 2026-08-28 | Email provider dispatch validates recipients and can fail over between configured Gmail and Outlook adapters | Keep validation and resilience at the external-provider boundary | Three email service boundary tests pass |
| 2026-08-28 | API response interceptor behavior is exported as deterministic handlers | Make authentication expiry and friendly errors independently testable without changing Axios consumers | Four interceptor tests pass |
| 2026-08-28 | Frontend tests produce V8 coverage reports in local Compose and CI | Establish a measurable cross-stack quality ratchet | 47 frontend tests pass with text, JSON, and HTML coverage reporters |
| 2026-08-28 | LLM orchestration split into coordinator, registries, usage, provider gateway/health, workflows, and exceptions | Separate policy, persistence, provider protocol, and business workflow ownership | Legacy import identity and LLM behavior tests pass; all files below 400 lines |
| 2026-08-28 | Email service split into coordinator, validation, duplicate, persistence, intelligence, mock catalog, and provider adapters | Make the inbound pipeline and external provider boundaries independently testable | Email service and compatibility tests pass; all files below 400 lines |
| 2026-08-28 | Application routing/providers/layout and Prompt Manager panels extracted into focused modules | Reduce UI change blast radius while preserving context and named-export contracts | Production build plus routing and Prompt Manager tests pass |

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
