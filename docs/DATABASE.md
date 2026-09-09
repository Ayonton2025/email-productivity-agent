# Database

## Overview

PostgreSQL is the production system of record, accessed asynchronously through SQLAlchemy and `asyncpg`. SQLite with `aiosqlite` supports isolated tests. Redis is not a second system of record; it provides Celery brokerage, results and ephemeral coordination.

## Logical data domains

| Domain | Representative tables | Purpose |
|---|---|---|
| Identity | `users`, `user_email_accounts`, `email_provider_configs` | Accounts and encrypted provider configuration |
| Inbox | `emails`, `email_attachments`, `document_analysis`, `sync_history` | Messages, ingestion and attachment intelligence |
| Productivity | `email_drafts`, `prompt_templates`, `commitments`, `risks`, `opportunities`, `email_tasks` | Drafting, decisions and tasks |
| Automation | `agents`, `agent_memory`, `workflows`, `workflow_steps`, `workflow_executions`, `auto_reply_rules` | Configurable automation and execution history |
| Collaboration | `shared_inboxes`, `shared_inbox_members`, `contacts`, `companies` | Team inboxes and relationship intelligence |
| Revenue | `subscriptions`, `payments`, `credit_transactions`, `usage_logs`, `monthly_billing_snapshots` | Entitlements, payments and usage evidence |
| Growth | `campaigns`, `campaign_sequences`, `leads`, `hosted_email_send_logs` | Campaign and hosted-email operations |
| Governance | `llm_provider_configs`, `knowledge_entries`, `email_security_scans`, `persona_profiles` | AI configuration, knowledge and safety records |

## Relationship view

```mermaid
erDiagram
    USERS ||--o{ USER_EMAIL_ACCOUNTS : owns
    USERS ||--o{ EMAILS : receives
    EMAILS ||--o{ EMAIL_ATTACHMENTS : contains
    EMAIL_ATTACHMENTS ||--o| DOCUMENT_ANALYSIS : produces
    USERS ||--o{ EMAIL_DRAFTS : creates
    USERS ||--o{ SUBSCRIPTIONS : holds
    USERS ||--o{ USAGE_LOGS : generates
    USERS ||--o{ WORKFLOWS : configures
    WORKFLOWS ||--o{ WORKFLOW_STEPS : contains
    WORKFLOWS ||--o{ WORKFLOW_EXECUTIONS : runs
    SHARED_INBOXES ||--o{ SHARED_INBOX_MEMBERS : grants
    CAMPAIGNS ||--o{ CAMPAIGN_SEQUENCES : schedules
    CAMPAIGNS ||--o{ LEADS : targets
```

The SQLAlchemy models and migrations are authoritative for columns and constraints.

## Lifecycle and resilience

- Alembic revisions live in `backend/alembic/versions`.
- Compose uses an `init_db` job before API/worker startup.
- Prefer additive, backward-compatible migrations and forward fixes after data-changing releases.
- Production should use point-in-time recovery, encrypted backups and regularly tested restores.
- Attachment storage requires an independent backup and retention policy.
- Customer deletion must cover messages, attachments, logs, sync history and derived AI data.

## Canonical model ownership

Every mapped class uses `app.models.base.Base`. Import models from their owning
module; import sessions and initialization from `app.models.database`.

| Module in `backend/app/models` | Responsibility |
|---|---|
| `base.py` | Shared declarative base and metadata |
| `user_models.py` | User, password helpers and verification/reset tokens |
| `email_models.py` | UserEmailAccount, Email and EmailDraft |
| `prompt_models.py` | PromptTemplate |
| `provider_models.py` | EmailProviderConfig and SyncHistory |
| `system_models.py` | SystemSetting |
| Other domain model modules | Their existing domain tables, using the same Base |
| `database.py` | Engine, session factory, initialization and session dependency |

`register_models()` in `models/__init__.py` explicitly loads all domain mappings;
`init_db()` calls it before creating tables. Importing domain models alone does
not initialize the database engine. Register a new domain module here when adding
one. Historical imports from `database.py`, `email_provider_models.py`, and
`user_models.UserEmailAccount` remain aliases of the canonical classes.

Phase 3 preserves the existing canonical schema. The regression snapshot in
`backend/tests/fixtures/model_schema.json` fingerprints all 58 tables from commit
`20d3a1d`, including PostgreSQL/SQLite DDL, indexes and Python defaults. A deliberate
future schema change must review that baseline alongside its migration; do not
regenerate the snapshot merely to make a failing test pass.

See [Phase 3 verification](PHASE_3_VERIFICATION.md) for consolidation checks.
