# Phase 4: AI endpoints and schema ownership

This phase follows the repository-specific Phase 4 in the supplied feedback,
starting from Phase 3 commit `ee7a77e` on branch `phase-4-ai-refactor`.

## Requirement-by-requirement results

1. **AI schemas:** all 11 request/response models moved from `ai_endpoints.py` to
   `api/schemas/ai_schemas.py`. Field constraints, defaults and response shapes
   are unchanged.
2. **Existing schemas:** replaced the single `schemas.py` file with a package.
   Auth, email, prompt, agent and shared contracts have explicit ownership.
   Package exports preserve every previously defined public schema and password
   validation helper. Existing callers retain their import paths.
3. **Focused routes:** `ai_endpoints.py` is 249 lines, below the 400-line target.
   It retains routes, authentication, service calls and response handling.
4. **Workspace extraction:** separate modules own orchestration/quota accounting,
   confirmation-token validation and confirmed draft persistence. Existing tenant
   binding, ten-minute token validity, admin checks, usage accounting and
   transaction boundaries are preserved.
5. **Tooling:** mypy now targets the schemas package. Existing coverage commands
   continue to cover `app.api.schemas` without changing thresholds.
6. **Schema tests:** new tests cover valid requests, defaults, nested drafts,
   missing/empty/oversized fields and invalid values. Test IDs are shortened to
   avoid Windows environment-variable limits for oversized payload cases.
7. **Behavior tests:** existing AI HTTP tests remain; new workspace tests cover
   preview/confirmation, bad signatures, wrong users, changed drafts, expiration,
   missing confirmation, quota/admin behavior, upstream failures, live provider
   health permissions, persistence for all four builders and rollback on failure.
8. **Compatibility review:** AST comparison verifies that all moved class/function
   definitions retain their logic. Only the workspace route delegates to a service;
   its service signature receives the authenticated user/session explicitly.
   Hashes captured before editing verify every OpenAPI path and schema component.

## Verification (2026-09-09)

- Focused schema/API checks: 28 passed, including full API contract comparison.
- Workspace behavior checks: 15 passed against mocked providers and isolated SQLite.
- Windows full backend suite: 252 passed; application coverage 36.32% (31% required).
- Maintained-module gate: 252 passed; coverage 83.71% (50% required).
- Security/schema gate: 24 passed; coverage 98.28% (90% required).
- Ruff lint and formatting: passed (238 files checked for formatting).
- Mypy: passed for its configured 19 source files.
- Bandit: no medium/high findings; the configured gate passed.
- Dependency audit: no known vulnerabilities.
- Linux initial run: 251 passed with one 120-second cold-import subprocess timeout.
  Isolated rerun of all three model compatibility checks passed in 26.61 seconds,
  retaining the original timeout and assertions.
- Final Linux full suite, after the Windows workload finished: 252 passed;
  application coverage 36.32%. No timeout or assertion changes were needed.
- Diff whitespace check: passed.

Validation uses the existing development environments and Linux test image with
current sources mounted read-only. Dependencies and database schemas are unchanged.

## Review checkpoint

Final review matched all four repository-specific Phase 4 steps against the
implementation. Definition comparison passed again, public schema exports are
preserved, and no remaining Phase 4 gaps were identified.

Phase 4 is approved for commit and push to `phase-4-ai-refactor`. Hosted CI results
are tracked separately after publication. Production databases and external
provider accounts were not used. Phase 5 remains outside this change.
