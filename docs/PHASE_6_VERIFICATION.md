# Phase 6: Authenticated user logging context

This phase follows the repository-specific Phase 6 in the supplied feedback,
starting from Phase 5 commit `81f95ea` on branch `phase-6-user-log-context`.

## Implementation and boundaries

- Retains the existing structlog configuration, JSON processors, request-ID
  generation/response header and middleware context cleanup.
- Adds `bind_authenticated_user` to the existing request logging module. Both
  authentication dependencies call it only after token validation, database user
  lookup and the active-account check succeed. It binds the canonical database
  user's ID as a string; client headers and unverified claims cannot set it.
- Covers the shared security dependency and the separate account dependency used
  by `/me` and token refresh. Authentication checks, status codes and return values
  remain unchanged; AST comparison confirms this for both implementations.
- Keeps direct dependency calls compatible through an optional Request argument.
  FastAPI injects the request for HTTP calls; direct callers can still provide only
  credentials and session, as exercised by the existing authentication tests.
- Shares the verified ID through request state because BaseHTTPMiddleware runs
  downstream application code in a separate async context. The middleware binds
  that verified ID before completion/failure logs. It does not authenticate users
  or derive identity from headers. Public and rejected requests remain anonymous.
- Extends the existing request logging tests rather than replacing the logging
  infrastructure. Fourteen new cases cover both authentication paths: downstream
  and completion logs, invalid tokens, missing/inactive accounts, sequential and
  concurrent isolation, spoofed identity headers, failures and context cleanup.

## Verification (2026-09-10)

- Focused Windows logging/authentication/inbox checks: 31 passed.
- Focused Linux logging/authentication/inbox checks: 31 passed.
- Full Windows backend suite: 274 passed; application coverage 36.74% (31% required).
- Maintained-module gate: 274 passed; coverage 84.23% (50% required).
- Security/schema gate: 24 passed; coverage 98.28% (90% required).
- Bandit: configured gate passed with no medium/high findings.
- Dependency audit: no known vulnerabilities.
- Diff whitespace check: passed.
- Ruff lint and formatting: passed (239 files checked for formatting).
- Mypy: passed for the configured 19 source files.
- AST review: validation, queries and response behavior in both authentication
  dependencies are preserved; only request injection and context binding are added.

## Review checkpoint

Final review confirmed the Phase 6 requirement is covered for both authentication
dependencies, including request completion/failure logs and context isolation.
No remaining Phase 6 gaps were identified. Existing environments were used;
dependencies, database schemas and the logging formatter are unchanged.

Phase 6 is approved for commit and push to `phase-6-user-log-context`. Hosted CI
results are tracked separately after publication. Tests use generated test tokens,
mocked account lookups and isolated databases; no production credentials, databases
or provider accounts are accessed. Later phases remain outside this change.
