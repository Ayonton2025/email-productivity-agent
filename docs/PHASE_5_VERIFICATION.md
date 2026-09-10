# Phase 5: Inbox failure handling and safe logging

This phase follows the repository-specific Phase 5 in the supplied feedback,
starting from Phase 4 commit `ae01c53` on branch `phase-5-inbox-errors`.

## Requirement-by-requirement results

1. **Failure response:** `GET /api/v1/emails/my-inbox` now returns HTTP 500 with
   `{"detail": "Unable to retrieve inbox"}` when retrieval or processing fails.
   It no longer disguises an error as a successful empty list. A genuinely empty
   inbox continues to return HTTP 200 with `[]`.
2. **Structured logging:** the endpoint uses the existing `get_logger` factory.
   Stable start, completion and failure events carry user ID, operation, duration,
   result counts and error type as appropriate. Existing middleware adds request ID.
3. **Content privacy:** the inbox path logs neither message contents nor search
   terms, credentials or attachments. Raw exception text, chains and SQL parameters
   are omitted using structured error events with `exc_info=False`. Error type and
   correlation fields remain available for investigation. The called
   `get_user_emails` service also suppresses raw database exceptions in logs while
   preserving its typed exception and cause for callers.
4. **Regression tests:** `test_inbox_endpoint.py` covers the requested RuntimeError
   to HTTP 500 contract, database failures through the real service, safe logs and
   correlation IDs, successful empty results, sorting, filtering, pagination
   forwarding and authentication.

Successful retrieval logic, tenant filtering, pagination, serializers and database
queries are unchanged. The existing frontend API wrapper already rethrows failed
requests. No frontend, dependency or database schema changes are needed.

The feedback illustrates `logger.exception`; privacy tests showed that this
formatter/stdlib bridge reattaches exception information even when that method
receives `exc_info=False`. These two events therefore use `logger.error`, retaining
error severity and structured diagnostics without exposing exception contents.

## Verification (2026-09-09)

- Focused Windows inbox/service/request-logging checks: 21 passed.
- Focused Linux inbox/service/request-logging checks: 21 passed.
- Full Windows backend suite: 260 passed; application coverage 36.51% (31% required).
- Maintained-module gate: 260 passed; coverage 83.78% (50% required).
- Security/schema gate: 24 passed; coverage 98.28% (90% required).
- Bandit: configured gate passed with no medium/high findings.
- Dependency audit: no known vulnerabilities.
- Ruff lint and formatting: passed (239 files checked for formatting).
- Mypy: passed for the configured 19 source files.
- AST review: successful inbox/query logic and every other endpoint function
  definition remain unchanged.
- Final diff whitespace check: passed.

The first privacy tests exposed raw exception leakage through `logger.exception`.
The corrected structured error events pass those tests on both platforms.
Existing environments are used; no dependency or infrastructure changes are made.

## Review checkpoint

Final review on 2026-09-10 confirmed all four Phase 5 requirements are covered.
The completed verification log was reviewed; no additional implementation changes
or repeat test runs were needed. No remaining Phase 5 gaps were identified.

Phase 5 is approved for commit and push to `phase-5-inbox-errors`. Hosted CI
results are tracked separately after publication. Validation uses isolated test
databases and mocked failures; no production database or email provider account
is accessed.
Phase 6 global authenticated-user logging context remains outside this change.
