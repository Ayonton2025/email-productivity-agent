# Phase 3: Canonical database models

This phase follows the repository-specific model consolidation plan in the supplied
feedback, starting from Phase 2 commit `20d3a1d` on branch `phase-3-models`.

## Requirement-by-requirement results

1. **Shared metadata:** all mapped classes use `models/base.py`. Duplicate Base,
   User, UserEmailAccount, Email, provider configuration and sync history mappings
   are replaced with canonical classes and compatibility aliases.
2. **User ownership:** `user_models.py` owns the complete canonical user schema,
   including billing and language fields, password helpers and token generation.
3. **Email ownership:** `email_models.py` owns mailbox accounts, messages and drafts.
   OAuth, hosted accounts, sending limits, message metadata, JSON and serialization
   fields from the canonical database schema are retained.
4. **Other ownership:** prompts, provider configuration/history and system settings
   have dedicated modules. Existing domain models share the same Base.
5. **Lifecycle separation:** `database.py` is 275 lines, containing lifecycle code
   and compatibility exports. Explicit registration loads all 58 table mappings
   before initialization; domain imports do not construct an engine.
6. **Import migration:** 69 API, service, task and other non-model application files
   now import canonical models. AST comparison confirms their changes are imports
   only. Historical model import paths remain aliases, covered by identity tests.
7. **Schema preservation:** fingerprints captured before extraction match all 58
   tables after consolidation, covering PostgreSQL/SQLite DDL, indexes and Python
   defaults. This phase introduces no schema migration.
8. **Regression tests:** 17 new tests cover metadata/import order, password hashing,
   token claims and expiry, full authentication flow, serialization, persistence,
   foreign keys, prompt uniqueness, initialization and transaction cleanup.

The authentication integration test exposed verification tokens generated before
SQLAlchemy assigned a new user's ID. Token helpers now assign a UUID when the ID
is absent, preserving existing IDs and schema defaults. Registration, verification,
login, current-user lookup, password reset and reset-token replay rejection pass.
The test stubs outbound mail and uses an isolated database.

## Verification (2026-09-09)

- Focused Phase 3 tests: 17 passed.
- Windows full backend suite: 219 passed; application coverage 35.24% (31% required).
- Maintained-module gate: 219 passed; coverage 83.71% (50% required).
- Security/schema gate: 24 passed; coverage 97.72% (90% required).
- Linux full suite in the existing test image with current sources mounted read-only:
  219 passed; application coverage 35.24%.
- Ruff lint and formatting: passed (227 files formatted).
- Mypy: passed for its configured 13 source files.
- Bandit: configured medium-or-higher gate passed.
- Dependency audit: no known vulnerabilities; retried after a DNS failure.
- Disposable PostgreSQL 15 validation: initialization and repeated initialization
  passed for all 58 tables; user and OAuth data survived, orphan accounts were
  rejected by the foreign key, and failed transactions rolled back. The initial
  probe used incorrect account keyword names; the corrected probe passed.
- Diff whitespace check: passed.

These runs use existing locked development environments. Fresh installations were
validated in Phase 2; dependency manifests are unchanged in this phase.

## Review checkpoint

Final review matched the repository-specific Phase 3 requirements against the
implementation. AST comparison confirmed all seven extracted non-user model
definitions are unchanged; lifecycle functions are unchanged except for explicit
model registration. No remaining Phase 3 gaps were identified.

Phase 3 is approved for commit and push to `phase-3-models`. Hosted CI results
are tracked separately after publication.
Phase 4 remains outside this change. Production databases and provider accounts
were not accessed during validation.
