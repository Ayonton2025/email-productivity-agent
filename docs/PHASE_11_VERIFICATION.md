# Phase 11: Split the mixed API router

This phase follows the repository-specific Phase 11 in draft.docx, continuing from Phase 10 commit `d66502d` on `phase-11-api-routes`.

## Requirement-by-requirement review

The original `backend/app/api/endpoints.py` contained 28 HTTP routes and one WebSocket route across unrelated domains. All handlers are now extracted into `backend/app/api/legacy/`:

| Module | Responsibility | Lines |
| --- | --- | ---: |
| `inbox_endpoints.py` | Authenticated inbox filtering, sorting, pagination, and safe logging/errors | 85 |
| `prompt_endpoints.py` | User/system prompts, prompt testing and CRUD | 114 |
| `account_endpoints.py` | Account listing, simple Gmail connection, account diagnostics | 105 |
| `email_endpoints.py` | Sync response, email retrieval/category updates, mock loading | 111 |
| `draft_endpoints.py` | Draft list/create/update/delete | 53 |
| `reply_endpoints.py` | Reply generation and draft persistence | 95 |
| `agent_endpoints.py` | Agent processing/chat/status and WebSocket dispatch | 126 |
| `health_endpoints.py` | Database/AI health and API information | 75 |

The dedicated package avoids overwriting existing inbox, account, and agent routers already registered elsewhere. `endpoints.py` is now a 127-line compatibility entry point. It preserves explicit handler exports, the service-class imports used by existing tests/callers, and the original route order. The router loader retains the same module, `/api/v1` prefix, and `api` tags.

All 29 handler syntax trees (signatures, decorators, and bodies) were compared with the parent commit and found identical after extraction and formatting. Loggers retain the established `app.api.endpoints` category, including the Phase 5 privacy-safe inbox events. No request models, schema defaults, provider behavior, database models, or frontend code changed.

The pinned FastAPI version defers `include_router` entries. Assembly therefore uses the public `APIRouter(routes=...)` constructor with the existing domain route objects sorted into their original order; it does not sort deferred router wrappers or depend on FastAPI private classes.

## WebSocket defect exposed during verification

The new lifecycle test reproduced an existing circular self-import in `app/api/websockets.py`: importing `manager` from the module itself before that name was defined raised `ImportError`. Removing that single import allows the existing manager implementation to load. The WebSocket handler itself is unchanged. The regression test imports the real manager module and substitutes its methods to verify connection acceptance, client-ID/message forwarding, and disconnect cleanup through the assembled application's WebSocket route without contacting an AI provider.

## Regression evidence

Before moving handlers, a fixture captured the legacy router's ordered paths, methods, operation IDs and dependency trees, plus a digest of directly registered application routes. The digest intentionally covers direct routes only, because FastAPI's included routers are deferred. The existing full-application OpenAPI comparison covers all HTTP paths/schemas; actual HTTP/WebSocket tests verify the application mounting and behavior.

New checks cover compatibility-export identity, draft ownership/payload serialization, missing-auth rejection across protected groups, missing-email 404/user scoping, partial prompt updates/404, account owner filtering, reply/draft context and plan forwarding, custom agent prompts, health/info, and the WebSocket lifecycle. Existing inbox tests continue to verify error privacy, authentication, pagination, filtering, sorting, and logging context.

## Validation

- Focused backend route, WebSocket, inbox, logging, OpenAPI, and router-loader checks: **61 passed**.
- Frontend API-wrapper checks: **39 passed**.
- Windows lint, formatting (250 files), and mypy (19 configured source files): passed.
- Windows whole-backend run: **291 passed, 2 failed**; both failures were existing monitoring cold-process tests exceeding their unchanged 180-second timeout. Application coverage was **37.71%**, above the 31% gate. This run is not claimed green.
- Linux native-filesystem whole-backend run: **293 passed**, including both unchanged monitoring subprocess tests; coverage **37.71%** (31% required).
- Linux maintained-module gate: **293 passed**, coverage **84.77%** (50% required).
- Linux security/schema gate: **24 passed**, coverage **98.28%** (90% required).
- Linux lint, formatting, mypy, and Bandit configured gate: passed.
- Dependency audit: **no known vulnerabilities** after installing the repository's existing pinned packaging tools; pip compatibility check passed. The reused image initially had older pip/setuptools with audit findings; repository manifests did not need changes.
- Final diff whitespace and handler syntax parity: passed.

The initial read-only Windows-mounted Linux run also had one monitoring startup timeout (292 tests passed). The final Linux runs copied the source and complete repository layout into temporary native container storage; both full-suite gates then passed with the original 180-second timeout. This supports filesystem/environment overhead as the timeout explanation but does not turn the failed Windows run into a pass.

Linux verification reused the existing isolated image and installed the Phase 7 pinned Jinja2 dependency under the lock constraints. The audit alone was rerun after installing `requirements-tooling.txt` (pip 26.2.1, setuptools 84.0.0, wheel 0.48.0). Source was mounted read-only and all copies/installations/output were confined to disposable containers. This was not a new full dependency installation or a fresh clone.

## Scope limits and outstanding issues

Existing authentication dependencies and error semantics were preserved rather than redesigned. In particular, legacy public/demo prompt operations, draft mutations without a user dependency, and WebSocket authentication policy require a separate security review; this extraction does not establish their safety or add authorization. Some legacy endpoints also retain their existing broad exception/error-detail behavior outside the previously fixed inbox route.

The earlier hosted CI failures and hosted Sentry delivery remain unresolved. Local tests use mocks/in-memory services and cannot establish production credentials, provider delivery, or hosted CI status. No release, deployment, or schema migration is part of this phase.

Phase 11 extraction and final validation review are complete. All requested responsibility groups are covered, and the user approved committing and pushing this phase. Hosted CI remains to be verified after the push.
