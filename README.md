# Bylix Email - Email Productivity Agent

Last updated from codebase: March 8, 2026.

This README reflects the current implementation in this repository across backend, frontend, workers, billing, payments, AI orchestration, hosted email, and collaboration modules.

## Advanced AI Expansion Status (Requested 20 Features)

Status key:
- `Implemented`: production-ready or existing substantial implementation.
- `Implemented (MVP foundation)`: integrated API/model/task scaffold aligned to current architecture and ready for provider-specific hardening.

1. AI Email Negotiation Agent: `Implemented (MVP foundation)`
- Added negotiation fields on agents: `strategy_prompt`, `approval_threshold`.
- Added endpoint: `POST /api/v1/agents/{id}/negotiate`.
- Uses existing approval queue pattern via draft metadata (`approval_status=pending`).

2. AI Calendar & Meeting Intelligence: `Implemented (MVP foundation)`
- Added meeting model: `backend/app/models/meeting_models.py`.
- Added endpoints: `/api/v1/meetings/detect`, `/propose-slots`, `/{meeting_id}/agenda`, `/{meeting_id}/post-summary`.
- Added Celery task: `meeting_followup_task()`.

3. Voice Email Assistant: `Implemented (MVP foundation)`
- Added endpoints: `POST /api/v1/voice/read-email`, `POST /api/v1/voice/reply`.
- Includes STT/TTS integration points (Whisper/HF + Google TTS hints).

4. AI Email Security & Scam Detection: `Implemented (MVP foundation)`
- Added model: `backend/app/models/security_models.py`.
- Added endpoint: `POST /api/v1/security/scan-email` with scam/phishing signals.

5. Emotion & Relationship AI: `Implemented (extended)`
- Extended `Contact` with `trust_score`, `stress_level`, `loyalty_score`.
- Added heatmap endpoint: `GET /api/v1/insights/relationships/heatmap`.

6. AI Legal & Contract Analyzer: `Implemented (MVP foundation)`
- Added endpoint: `POST /api/v1/legal/analyze` (obligations/penalties/deadlines extraction).
- Added legal billing action cost: `legal_analysis`.

7. Smart Email Knowledge Base: `Implemented (MVP foundation)`
- Added model: `backend/app/models/knowledge_models.py`.
- Added endpoints: `POST /api/v1/knowledge/ingest`, `GET /api/v1/knowledge/search`.
- Embedding storage uses JSON fallback; pgvector can be swapped in production.

8. AI Multi-Language Communication: `Implemented (MVP foundation)`
- Added user setting: `preferred_language`.
- Added endpoints: `POST /api/v1/language/translate`, `PUT /api/v1/language/preferred-language`.

9. AI Personality Customization: `Implemented (MVP foundation)`
- Added table/model: `persona_profiles` in `backend/app/models/persona_models.py`.
- Added endpoints under `/api/v1/personas`.

10. AI Task Manager From Emails: `Implemented (MVP foundation)`
- Added model: `backend/app/models/task_models.py`.
- Added Kanban-friendly endpoints under `/api/v1/tasks`.

11. AI Email Priority Predictor: `Implemented (MVP foundation)`
- Added field: `emails.future_priority_score`.
- Added endpoint: `POST /api/v1/priority/predict`.

12. AI Deliverability Auto-Fixer: `Implemented (MVP foundation)`
- Extended deliverability router with: `POST /api/v1/deliverability/fix`.

13. AI Sales Pipeline Integration: `Implemented (MVP foundation)`
- Added endpoint: `POST /api/v1/sales/crm/sync-email` (HubSpot/Salesforce bridge point).

14. AI Social Media Cross-Posting: `Implemented (MVP foundation)`
- Added endpoint: `POST /api/v1/social/cross-post` (approval-aware publish flow).

15. AI Email Memory Timeline: `Implemented (MVP foundation)`
- Added model: `backend/app/models/timeline_models.py`.
- Added endpoints: `POST /api/v1/timeline/events`, `GET /api/v1/timeline/{contact_id}`.

16. AI Offline Mode: `Implemented (MVP foundation)`
- Added model: `backend/app/models/offline_models.py`.
- Added endpoints: `POST /api/v1/offline/sync-queue`, `POST /api/v1/offline/sync-queue/process`, `GET /api/v1/offline/sync-queue`.

17. AI Ethics & Bias Monitor: `Implemented (MVP foundation)`
- Added endpoint: `POST /api/v1/ethics/moderate-reply`.
- Designed as pre-send moderation gate.

18. AI Email Simulator for Training: `Implemented (MVP foundation)`
- Added endpoint: `POST /api/v1/simulator/generate-inbox`.

19. AI Customer Support Auto-Resolver: `Implemented (MVP foundation)`
- Added endpoint: `POST /api/v1/support/auto-resolve`.
- Integrates with draft queue for approval-first sending.

20. AI Predictive Business Insights: `Implemented (MVP foundation)`
- Extended insights with forecast endpoint: `GET /api/v1/insights/forecast`.

## What This Project Is

Bylix Email is a full-stack email intelligence platform built around:

- Multi-account email ingestion and sending (Gmail, Outlook, IMAP/SMTP, hosted mail).
- AI-driven classification, extraction, summarization, reply drafting, relationship analysis, and workspace assistance.
- Operational layers for workflows, campaigns, follow-ups, shared inbox, deliverability, and executive insights.
- Subscription billing with credit-based metering, Paystack + PayPal payment flows, and webhook reconciliation.
- Background processing through Celery worker/beat with Redis broker and PostgreSQL persistence in Docker mode.

## High-Level Architecture

```text
Frontend (React + Vite)
  -> Backend API (FastAPI, async SQLAlchemy)
  -> WebSocket realtime endpoints

Backend Services
  -> PostgreSQL (primary persistence)
  -> Redis (Celery broker/result + cache use cases)
  -> Celery worker/beat (scheduled and async jobs)
  -> External providers:
     - LLM providers (Google, OpenAI-compatible, Anthropic, HuggingFace, Ollama, Groq, OpenRouter)
     - Payment providers (Paystack, PayPal, Coinbase Commerce, Bybit Pay, optional Stripe)
     - Email providers (Gmail/Outlook OAuth, IMAP/SMTP, hosted provider abstraction)
```

## Tech Stack

- Backend: FastAPI, SQLAlchemy 2.x async, PostgreSQL/SQLite, Celery, Redis, Alembic.
- Frontend: React 18, React Router, Axios, Vite, Tailwind, Lucide.
- AI/LLM: google-generativeai, openai, anthropic, provider orchestration/fallback logic.
- Integrations: Google APIs, MSAL, Paystack, PayPal, Stripe (optional), Coinbase/Bybit (crypto optional).

## Implemented Backend Domains

The backend is modularized by domain router. Main router registration is in `backend/app/main.py`.

- Authentication and account lifecycle:
  - `backend/app/api/auth_endpoints.py`
  - register, login, token refresh, logout, forgot/reset password, verification.
- OAuth and provider auth:
  - `backend/app/api/oauth_endpoints.py`
  - Google and Microsoft OAuth callback/auth-url status flow.
- Email accounts and provider connectivity:
  - `backend/app/api/user_email_endpoints.py`
  - `backend/app/api/email_provider_endpoints.py`
  - `backend/app/api/multi_provider_endpoints.py`
- Inbox and bulk operations:
  - `backend/app/api/inbox_endpoints.py`
  - `backend/app/api/bulk_email_endpoints.py`
  - `backend/app/api/search_endpoints.py`
  - `backend/app/api/sync_history_endpoints.py`
  - `backend/app/api/attachment_endpoints.py`
- AI intelligence and assistant:
  - `backend/app/api/ai_endpoints.py`
  - `backend/app/api/admin_llm_endpoints.py`
- Automation and execution:
  - workflows: `backend/app/api/workflow_endpoints.py`
  - agents: `backend/app/api/agent_endpoints.py`
  - campaigns: `backend/app/api/campaign_endpoints.py`
  - auto-reply: `backend/app/api/auto_reply_endpoints.py`
  - follow-ups: `backend/app/api/followup_endpoints.py`
- Insights and operational analytics:
  - `backend/app/api/insights_endpoints.py`
  - `backend/app/api/analytics_endpoints.py`
  - `backend/app/api/briefing_endpoints.py`
  - `backend/app/api/executive_endpoints.py`
  - `backend/app/api/deliverability_endpoints.py`
- Collaboration and shared ownership:
  - `backend/app/api/shared_inbox_endpoints.py`
- Billing and payments:
  - `backend/app/api/billing_endpoints.py`
  - upgrade, plans, credits, top-ups, history, admin reports, payment methods, webhooks.
- Usage and feature-access controls:
  - `backend/app/api/usage_endpoints.py`
  - `backend/app/api/admin_usage_endpoints.py`
- Contact and lead intake:
  - `backend/app/api/contact_endpoints.py`
- External webhook endpoints:
  - `backend/app/api/webhook_endpoints.py`
- Realtime:
  - `backend/app/api/realtime_endpoints.py`

## Implemented Frontend Domains

Main app shell and routing are in `frontend/src/App.jsx`.

Primary frontend areas implemented:

- Auth: login/register/verify/forgot/reset/OAuth callback.
- Inbox UI: list/detail, provider connection, loading mock inbox.
- Billing upgrade and payment method selection flow.
- AI prompt management and email agent screens.
- Campaign builder and campaign management.
- Workflow builder and workflow center.
- Auto-reply rule management.
- Insights dashboard and detail drilldowns (contact/company/risk/opportunity).
- Relationships center.
- Daily briefing center.
- Follow-up center.
- Hosted email center.
- Shared inbox center.
- Deliverability center.
- Executive command center.
- Attachment intelligence UI (download, per-file analysis, analyze-all from email detail).
- Super admin dashboard.
- Workspace assistant panel integrated into app pages.

## Billing and Payments (Current Implementation)

### Subscription and Credit Model

Implemented plan constants in `backend/app/models/billing_models.py`:

- Free (`personal`): 50 AI credits/day, 1 email account.
- Plus: $12/month, 1,500 AI credits/month, 3 email accounts.
- Professional: $29/month, 5,000 AI credits/month, unlimited email accounts.
- Enterprise: starts at $99+ (customized contracts).

Credit packs:

- 1,000 credits = $4.
- 5,000 credits = $15.
- 10,000 credits = $25.

Credit definition exposed by API:

- `1 AI Credit = 1 email processed (or 1,000 tokens)`.

### Credit Enforcement

Implemented in `backend/app/services/billing_service.py` and used by LLM orchestration:

- Pre-check for required credits per AI action.
- Deduction after successful AI calls.
- Action-based costs (`AI_ACTION_COSTS`) including summary/reply/classification style actions.
- Credit transaction logging.
- Usage logging with action, token, and credit fields.

### Billing Cadence

Implemented Celery reset behavior:

- Daily reset for free plan credits.
- Monthly reset for paid plan credits.

Files:

- `backend/app/tasks/billing_tasks.py`
- `backend/app/tasks/celery_app.py`

### Payment Providers

Implemented in `backend/app/services/billing_service.py`:

- Paystack primary flows (initialize/verify).
- PayPal order flow and capture handling.
- Optional Coinbase Commerce and Bybit Pay crypto flow.
- Optional Stripe checkout support.

### Webhooks

`backend/app/api/billing_endpoints.py` handles:

- Paystack:
  - `charge.success`
  - `subscription.create`
  - `subscription.disable`
- PayPal:
  - `PAYMENT.SALE.COMPLETED`
  - `BILLING.SUBSCRIPTION.ACTIVATED`
  - `BILLING.SUBSCRIPTION.CANCELLED`
- Coinbase webhook reconciliation for crypto charge completion.

### Billing Abuse Controls

Implemented controls include:

- Billing endpoint IP request throttling for upgrade/top-up routes.
- Daily AI usage cap check in orchestration flow (`200 emails/day` equivalent credit usage limit).
- Payment webhook signature verification for Paystack.

## AI and LLM Orchestration

Core logic: `backend/app/services/llm_orchestration_service.py`.

Implemented capabilities:

- Provider runtime config loading from DB.
- Provider priority and fallback chain.
- Model routing profile behavior (cheap/fast vs strong quality).
- OpenAI-compatible providers plus Google/Anthropic/HF/Ollama support.
- Optional semantic cache keys for LLM responses.
- Per-call token estimation and usage/cost logging.
- Credit gate + credit deduction integration with billing service.
- Workspace assistant helpers for page-specific structured outputs.

## Hosted Email and Abuse Controls

Hosted email service and API are implemented:

- Endpoints:
  - availability, provision, signup, limits.
- Provider abstraction modules:
  - Mailcow, Postal, Mailu, Resend, SendGrid patterns.
- Daily send limits and anti-abuse controls in config and services.

Relevant files:

- `backend/app/api/hosted_email_endpoints.py`
- `backend/app/services/hosted_email_provider_service.py`
- `backend/app/services/hosted_email_abuse_service.py`

## Background Jobs and Scheduling

Celery app configuration: `backend/app/tasks/celery_app.py`.

Implemented scheduled categories:

- Email ingestion/sync jobs.
- AI processing jobs.
- Campaign send/reply/warmup jobs.
- Workflow execution and reminders.
- Integration sync jobs.
- Billing jobs (monthly + daily credit resets, renewals, charging hooks).
- Maintenance cleanup/archive jobs.
- Phase-1 jobs (briefings, follow-up processing).

## Database and Models

Primary model modules include:

- `backend/app/models/database.py` (base DB models and initialization).
- `backend/app/models/billing_models.py` (subscriptions, credits, transactions, payments, usage).
- `backend/app/models/campaign_models.py`
- `backend/app/models/workflow_models.py`
- `backend/app/models/agent_models.py`
- `backend/app/models/auto_reply_models.py`
- `backend/app/models/contact_models.py`
- `backend/app/models/commitment_models.py`
- `backend/app/models/collaboration_models.py`
- `backend/app/models/hosted_email_models.py`
- `backend/app/models/llm_provider_models.py`

DB initialization:

- Startup tasks in `backend/app/main.py`.
- One-off init script in `backend/app/scripts/init_db.py`.
- Additive schema guards in `init_db()` for resilient bootstrapping.

## API Inventory by Prefix

Main API prefixes currently implemented:

- `/api/v1/auth/*`
- `/api/v1/ai/*`
- `/api/v1/billing/*`
- `/api/v1/admin/llm/*`
- `/api/v1/email-accounts/*`
- `/api/v1/email-providers/*`
- `/api/v1/emails/*`
- `/api/v1/emails/bulk/*`
- `/api/v1/emails/search/*`
- `/api/v1/emails/sync/*`
- `/api/v1/attachments/*`
- `/api/v1/workflows/*`
- `/api/v1/agents/*`
- `/api/v1/campaigns/*`
- `/api/v1/auto-reply/*`
- `/api/v1/followups/*`
- `/api/v1/insights/*`
- `/api/v1/analytics/*`
- `/api/v1/briefings/*`
- `/api/v1/executive/*`
- `/api/v1/shared-inboxes/*`
- `/api/v1/hosted-email/*`
- `/api/v1/deliverability/*`
- `/api/v1/meetings/*`
- `/api/v1/voice/*`
- `/api/v1/security/*`
- `/api/v1/legal/*`
- `/api/v1/knowledge/*`
- `/api/v1/language/*`
- `/api/v1/personas/*`
- `/api/v1/tasks/*`
- `/api/v1/priority/*`
- `/api/v1/sales/*`
- `/api/v1/social/*`
- `/api/v1/timeline/*`
- `/api/v1/offline/*`
- `/api/v1/ethics/*`
- `/api/v1/simulator/*`
- `/api/v1/support/*`
- `/api/v1/contact/*`
- `/api/v1/webhooks/*`
- `/api/v1/usage/*`
- `/ws/*` (realtime/websocket)

## Compact Endpoint Tables (Major Routers)

Note: Paths below are shown as full external paths.

### Authentication (`auth_endpoints`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/debug/users` | Debug user records |
| GET | `/api/v1/debug/database` | Debug DB connectivity/table state |
| POST | `/api/v1/register` | Register user and issue token |
| POST | `/api/v1/verify-email` | Verify email token |
| POST | `/api/v1/login` | Login and issue access token |
| POST | `/api/v1/forgot-password` | Start password reset flow |
| POST | `/api/v1/reset-password` | Complete password reset |
| GET | `/api/v1/me` | Current authenticated user |
| POST | `/api/v1/logout` | Logout acknowledgement |
| POST | `/api/v1/refresh` | Refresh bearer token |

### AI Intelligence (`ai_endpoints`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/ai/classify` | Classify email category |
| POST | `/api/v1/ai/extract-actions` | Extract tasks/deadlines |
| POST | `/api/v1/ai/sentiment` | Sentiment and tone analysis |
| POST | `/api/v1/ai/summarize` | Summarize thread/content |
| POST | `/api/v1/ai/relationship-analysis` | Relationship scoring |
| GET | `/api/v1/ai/models` | Available AI models |
| GET | `/api/v1/ai/prompts` | Prompt metadata listing |
| GET | `/api/v1/ai/health` | AI service health |
| POST | `/api/v1/ai/assistant/assist` | Workspace assistant actions |

### Billing and Payments (`billing_endpoints`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/billing/subscription` | Current subscription |
| POST | `/api/v1/billing/upgrade` | Start upgrade checkout |
| GET | `/api/v1/billing/plans` | List plan catalog |
| GET | `/api/v1/billing/payment-methods/{country_code}` | Country-aware payment methods |
| GET | `/api/v1/billing/payment-methods` | Default payment methods |
| POST | `/api/v1/billing/cancel` | Cancel subscription |
| PUT | `/api/v1/billing/payment-method` | Update saved payment method |
| GET | `/api/v1/billing/history` | User billing history |
| GET | `/api/v1/billing/admin/overview` | Admin billing metrics |
| GET | `/api/v1/billing/admin/transactions` | Admin transaction list |
| GET | `/api/v1/billing/admin/reports/revenue-by-currency` | Revenue report by currency |
| POST | `/api/v1/billing/coupon/validate` | Validate coupon |
| POST | `/api/v1/billing/coupon/apply` | Apply coupon |
| GET | `/api/v1/billing/credits` | Credit balance/details |
| POST | `/api/v1/billing/credits/topup` | Initialize credit top-up |
| GET | `/api/v1/billing/credits/topup/{reference}` | Check top-up status |
| POST | `/api/v1/billing/webhook/paystack` | Paystack webhook |
| POST | `/api/v1/billing/webhook/paypal` | PayPal webhook |
| POST | `/api/v1/billing/webhook/coinbase` | Coinbase webhook |
| GET | `/api/v1/billing/features/{feature_name}` | Feature access check |
| GET | `/api/v1/billing/features` | Plan feature map |

### Email Accounts (`user_email_endpoints`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/email-accounts/gmail/auth-url` | Gmail OAuth URL (auth user) |
| GET | `/api/v1/email-accounts/gmail/auth-url/public` | Gmail OAuth URL (public flow) |
| POST | `/api/v1/email-accounts/gmail/code` | Exchange Gmail code |
| POST | `/api/v1/email-accounts/test-connection` | Validate IMAP/SMTP credentials |
| POST | `/api/v1/email-accounts/connect` | Connect generic provider account |
| POST | `/api/v1/email-accounts/outlook` | Connect Outlook account |
| GET | `/api/v1/email-accounts/list` | List linked accounts |
| GET | `/api/v1/email-accounts/` | List linked accounts (alt) |
| GET | `/api/v1/email-accounts/{account_id}` | Account detail |
| DELETE | `/api/v1/email-accounts/{account_id}` | Disconnect account |
| POST | `/api/v1/email-accounts/{account_id}/sync` | Trigger sync |
| GET | `/api/v1/email-accounts/{account_id}/inbox` | Account inbox |
| GET | `/api/v1/email-accounts/{account_id}/email/{email_id}` | Account email detail |
| POST | `/api/v1/email-accounts/{account_id}/send` | Send email |
| GET | `/api/v1/email-accounts/{account_id}/folders` | List folders |

### Inbox and Email Ops

`inbox_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/emails/inbox` | Paginated inbox feed |
| GET | `/api/v1/emails/unread` | Unread-only view |
| GET | `/api/v1/emails/{email_id}` | Email detail |
| GET | `/api/v1/emails/search/query` | Query search |
| PATCH | `/api/v1/emails/{email_id}/read` | Mark read/unread |
| PATCH | `/api/v1/emails/{email_id}/flag` | Flag/unflag |
| GET | `/api/v1/emails/categories/stats` | Category aggregates |

`bulk_email_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| PATCH | `/api/v1/emails/bulk/mark-read` | Bulk read/unread |
| PATCH | `/api/v1/emails/bulk/flag` | Bulk flag updates |
| PATCH | `/api/v1/emails/bulk/categorize` | Bulk categorization |
| DELETE | `/api/v1/emails/bulk/` | Bulk delete |
| GET | `/api/v1/emails/bulk/statistics` | Bulk operation stats |

`search_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/emails/search/full-text` | Full-text search |
| GET | `/api/v1/emails/search/suggestions` | Search suggestions |
| GET | `/api/v1/emails/search/advanced` | Advanced search filters |

`sync_history_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/emails/sync/history` | Sync run history |
| GET | `/api/v1/emails/sync/stats` | Sync stats |
| GET | `/api/v1/emails/sync/{sync_id}` | Sync run detail |

`attachment_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/attachments/{attachment_id}/info` | Attachment metadata and download URL |
| GET | `/api/v1/attachments/{attachment_id}/download` | Download attachment file |
| GET | `/api/v1/attachments/{attachment_id}/analysis` | Get attachment AI analysis |
| POST | `/api/v1/attachments/{attachment_id}/analyze` | Trigger single attachment analysis |
| GET | `/api/v1/emails/{email_id}/attachments` | List email attachments (optional analysis status) |
| GET | `/api/v1/emails/{email_id}/attachments/count` | Attachment count for badges/UI |
| POST | `/api/v1/emails/{email_id}/attachments/analyze-all` | Queue analysis for all email attachments |

### Workflows, Campaigns, Agents

`workflow_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/workflows/` | List workflows |
| GET | `/api/v1/workflows/{workflow_id}` | Workflow detail |
| POST | `/api/v1/workflows/` | Create workflow |
| PUT | `/api/v1/workflows/{workflow_id}` | Update workflow |
| DELETE | `/api/v1/workflows/{workflow_id}` | Delete workflow |
| POST | `/api/v1/workflows/{workflow_id}/steps` | Add workflow step |
| PUT | `/api/v1/workflows/steps/{step_id}` | Update step |
| DELETE | `/api/v1/workflows/steps/{step_id}` | Delete step |
| GET | `/api/v1/workflows/{workflow_id}/executions` | Execution history |
| POST | `/api/v1/workflows/{workflow_id}/execute` | Execute workflow now |

`campaign_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/campaigns/` | List campaigns |
| GET | `/api/v1/campaigns/{campaign_id}` | Campaign detail |
| POST | `/api/v1/campaigns/` | Create campaign |
| PUT | `/api/v1/campaigns/{campaign_id}` | Update campaign |
| DELETE | `/api/v1/campaigns/{campaign_id}` | Delete campaign |
| POST | `/api/v1/campaigns/{campaign_id}/sequences` | Add sequence |
| POST | `/api/v1/campaigns/{campaign_id}/leads/bulk` | Bulk import leads |
| GET | `/api/v1/campaigns/{campaign_id}/leads` | List campaign leads |
| POST | `/api/v1/campaigns/{campaign_id}/start` | Start campaign |
| POST | `/api/v1/campaigns/{campaign_id}/pause` | Pause campaign |

`agent_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/agents/` | List agents |
| GET | `/api/v1/agents/{agent_id}` | Agent detail |
| POST | `/api/v1/agents/` | Create agent |
| PUT | `/api/v1/agents/{agent_id}` | Update agent |
| DELETE | `/api/v1/agents/{agent_id}` | Delete agent |
| GET | `/api/v1/agents/{agent_id}/activities` | Agent activities |
| GET | `/api/v1/agents/{agent_id}/memory` | Agent memory records |
| POST | `/api/v1/agents/{agent_id}/negotiate` | Negotiation proposal + approval queue draft |

### Auto Reply, Follow-Up, Briefings

`auto_reply_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/auto-reply/` | List rules |
| POST | `/api/v1/auto-reply/` | Create rule |
| PUT | `/api/v1/auto-reply/{rule_id}` | Update rule |
| DELETE | `/api/v1/auto-reply/{rule_id}` | Delete rule |
| GET | `/api/v1/auto-reply/away` | Get away settings |
| PUT | `/api/v1/auto-reply/away` | Update away settings |
| GET | `/api/v1/auto-reply/approval-queue` | Pending approvals |
| POST | `/api/v1/auto-reply/approval-queue/{draft_id}/approve` | Approve draft |
| POST | `/api/v1/auto-reply/approval-queue/{draft_id}/reject` | Reject draft |

`followup_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/followups/policy` | Get follow-up policy |
| PUT | `/api/v1/followups/policy` | Update follow-up policy |
| POST | `/api/v1/followups/{email_id}/schedule` | Schedule follow-up |
| POST | `/api/v1/followups/{email_id}/disable` | Disable follow-up |
| GET | `/api/v1/followups/queue` | Review queue |
| POST | `/api/v1/followups/queue/{execution_id}/approve` | Approve queued action |
| POST | `/api/v1/followups/process-due` | Process due items now |

`briefing_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/briefings/today` | Get today's briefing |
| POST | `/api/v1/briefings/regenerate` | Regenerate briefing |
| GET | `/api/v1/briefings/preferences` | Get briefing prefs |
| PUT | `/api/v1/briefings/preferences` | Update briefing prefs |

### Insights, Analytics, Executive

`insights_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/insights/risks` | Risk insights |
| GET | `/api/v1/insights/opportunities` | Opportunity insights |
| GET | `/api/v1/insights/deadlines` | Deadline insights |
| GET | `/api/v1/insights/relationships` | Relationship metrics |
| GET | `/api/v1/insights/relationships/heatmap` | Relationship heatmap scores |
| GET | `/api/v1/insights/analytics` | Insights analytics |
| GET | `/api/v1/insights/forecast` | Predictive risk/opportunity outlook |
| GET | `/api/v1/insights/contacts/{contact_id}` | Contact detail |
| GET | `/api/v1/insights/companies/{company_id}` | Company detail |

`analytics_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/analytics/stats` | Platform stats |
| GET | `/api/v1/analytics/productivity` | Productivity metrics |

`executive_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/executive/summary` | Executive summary |
| POST | `/api/v1/executive/command` | Natural language executive command |

### Collaboration and Hosted

`shared_inbox_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/shared-inboxes/` | List shared inboxes |
| POST | `/api/v1/shared-inboxes/` | Create shared inbox |
| GET | `/api/v1/shared-inboxes/{inbox_id}/members` | List members |
| POST | `/api/v1/shared-inboxes/{inbox_id}/members` | Add member |
| POST | `/api/v1/shared-inboxes/{inbox_id}/emails/{email_id}` | Assign/route email |
| GET | `/api/v1/shared-inboxes/{inbox_id}/emails` | List inbox emails |
| PATCH | `/api/v1/shared-inboxes/{inbox_id}/emails/{email_id}` | Update assignment/status |

`hosted_email_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/hosted-email/availability` | Username/domain availability |
| POST | `/api/v1/hosted-email/provision` | Provision mailbox |
| POST | `/api/v1/hosted-email/signup` | Public signup (if enabled) |
| GET | `/api/v1/hosted-email/limits` | Send/abuse limits |

`deliverability_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/deliverability/score` | Deliverability scoring |
| POST | `/api/v1/deliverability/fix` | Queue SPF/DKIM/warmup remediation |

### Provider and OAuth Utilities

`multi_provider_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/email-providers/config/{provider}` | Provider config template |
| POST | `/api/v1/email-providers/connect/{provider}` | Connect provider |
| GET | `/api/v1/email-providers/accounts` | List provider accounts |
| PATCH | `/api/v1/email-providers/accounts/{account_id}/sync` | Toggle/update sync |
| DELETE | `/api/v1/email-providers/accounts/{account_id}` | Remove account |

`email_provider_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/providers/gmail/auth-url` | Gmail auth URL |
| POST | `/api/v1/providers/gmail/authenticate` | Gmail auth exchange |
| POST | `/api/v1/providers/gmail/authenticate-token` | Gmail token auth |
| POST | `/api/v1/providers/gmail/authenticate-legacy` | Legacy Gmail auth |
| POST | `/api/v1/providers/outlook/authenticate` | Outlook auth |
| POST | `/api/v1/providers/{provider}/authenticate` | Generic provider auth |
| POST | `/api/v1/providers/{provider}/sync` | Trigger provider sync |
| GET | `/api/v1/providers` | List provider types |

`oauth_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/oauth/google/callback` | Google OAuth callback |
| POST | `/api/v1/oauth/microsoft/callback` | Microsoft OAuth callback |
| GET | `/api/v1/oauth/google/auth-url` | Google auth URL |
| GET | `/api/v1/oauth/microsoft/auth-url` | Microsoft auth URL |
| POST | `/api/v1/oauth/callback` | Generic OAuth callback |
| GET | `/api/v1/oauth/status` | OAuth status |

### Admin LLM and External Webhooks

`admin_llm_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/admin/llm/providers` | Provider settings view |
| PUT | `/api/v1/admin/llm/providers/{provider}` | Update provider config |
| POST | `/api/v1/admin/llm/providers/{provider}/keys/rotate` | Rotate provider keys |
| POST | `/api/v1/admin/llm/providers/health-check` | Provider health check |
| POST | `/api/v1/admin/llm/providers/live-test` | Live inference test |
| GET | `/api/v1/admin/llm/providers/diagnostic` | Diagnostic details |
| POST | `/api/v1/admin/llm/providers/keys/rotate-all` | Rotate all provider keys |

`admin_usage_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/admin/usage/dismissals/reset` | Reset global premium prompt dismissals |
| GET | `/api/v1/admin/usage/user-access/{email}` | Inspect user features/plan/status by email |
| PUT | `/api/v1/admin/usage/user-access/{email}` | Allow/limit user and set payment bypass |

`usage_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/usage/dismissals/reset` | Read last global premium prompt dismissal-reset timestamp |

`webhook_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/webhooks/gmail` | Gmail Pub/Sub webhook intake |

`contact_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/contact/send-email` | Contact form email relay |
| POST | `/api/v1/contact` | Store contact submission |

### Newly Added Advanced Feature Routers

`meeting_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/meetings/detect` | Detect meeting intent from email |
| POST | `/api/v1/meetings/propose-slots` | Propose meeting time slots |
| POST | `/api/v1/meetings/{meeting_id}/agenda` | Generate/update agenda |
| POST | `/api/v1/meetings/{meeting_id}/post-summary` | Save post-meeting summary |

`voice_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/voice/read-email` | Read email content for voice assistant |
| POST | `/api/v1/voice/reply` | Create draft from spoken response |

`security_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/security/scan-email` | Scam/phishing signal scan |

`legal_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/legal/analyze` | Contract/legal clause risk extraction |

`knowledge_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/knowledge/ingest` | Ingest email/manual content to knowledge base |
| GET | `/api/v1/knowledge/search` | Search knowledge entries (RAG-ready) |

`language_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/language/translate` | Translate draft/content |
| PUT | `/api/v1/language/preferred-language` | Set user preferred language |

`persona_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/personas/` | List persona profiles |
| POST | `/api/v1/personas/` | Create persona profile |
| DELETE | `/api/v1/personas/{persona_id}` | Delete persona profile |

`task_manager_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/tasks/` | List tasks |
| POST | `/api/v1/tasks/` | Create task |
| PUT | `/api/v1/tasks/{task_id}` | Update task (kanban/status/reminders) |

`priority_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/priority/predict` | Predict future priority score |

`sales_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/sales/crm/sync-email` | Queue CRM stage update from email |

`social_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/social/cross-post` | Generate/queue social post from email |

`timeline_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/timeline/events` | Add timeline event |
| GET | `/api/v1/timeline/{contact_id}` | Fetch relationship timeline |

`offline_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/offline/sync-queue` | Queue offline action |
| POST | `/api/v1/offline/sync-queue/process` | Process queued actions |
| GET | `/api/v1/offline/sync-queue` | List queued/synced actions |

`ethics_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/ethics/moderate-reply` | Bias/toxicity moderation before send |

`simulator_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/simulator/generate-inbox` | Generate training inbox |

`support_endpoints`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/support/auto-resolve` | Draft auto-resolution for support email |

## Local Development Setup

### Prerequisites

- Python 3.11+ recommended.
- Node.js 18+ recommended.
- Docker Desktop (for compose stack).

### Backend (local)

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Backend health:

- `http://localhost:8000/health`
- `http://localhost:8000/api/v1/health`

### Frontend (local)

```bash
cd frontend
npm install
npm run dev
```

Frontend:

- `http://localhost:3000`

## Docker Compose Workflow (Recommended)

Stack definition: `docker-compose.yml`.

Services:

- `postgres`
- `redis`
- `init_db` (one-off schema bootstrap)
- `backend`
- `celery_worker`
- `celery_beat`
- `frontend`

Recommended startup:

```powershell
.\scripts\dev_up.ps1
```

Manual startup:

```bash
docker compose down -v
docker compose build --no-cache backend celery_worker celery_beat frontend
docker compose up -d postgres redis
docker compose run --rm init_db
docker compose up -d
docker compose ps
```

### LLM Providers

Configure external LLM APIs (OpenAI-compatible, Anthropic, Google, Groq, OpenRouter, etc.) via the Admin LLM Ops page. Local `llama.cpp` service is no longer used.

## Important Environment Configuration

Core files:

- Root: `.env`, `.env.example`, `.env.example-payment`
- Backend: `backend/.env`
- Frontend: `frontend/.env.example`

Critical areas to configure:

- Database and Redis URLs.
- JWT/secret and encryption keys.
- LLM provider keys and default provider/model (set in Admin LLM Ops).
- OAuth credentials (Google/Outlook).
- Billing provider credentials:
  - Paystack keys.
  - PayPal credentials.
  - Optional Stripe/Coinbase/Bybit keys.
- Billing FX behavior:
  - `BILLING_CHARGE_CURRENCY`, `BILLING_STRICT_USD`, `PAYSTACK_FORCE_CURRENCY`, fallback currency.

## Testing and Validation

Backend test suite examples:

- `backend/tests/test_paystack_parity.py`
- `backend/tests/test_shared_inbox_permissions.py`

Frontend tests:

- `frontend/src/__tests__/BillingUpgrade.test.jsx`

Run:

```bash
# backend
python -m pytest -q

# frontend
cd frontend
npm test
```

## Security and Operational Notes

- Do not commit live API keys, secrets, or payment credentials.
- Rotate any exposed keys immediately.
- Keep webhook signature verification enabled in production.
- Enforce HTTPS and production-safe CORS/allowed origins.
- Review admin endpoint access and `ADMIN_EMAILS`.

## Known Operational Behaviors

- Startup readiness is asynchronous in `backend/app/main.py`; backend can start before all background bootstrap steps complete.
- `init_db` includes resilient/additive migrations for environments without running Alembic upfront.
- Frontend billing UI defaults to hosted checkout redirect returned by backend payment session creation.
- Attachment storage is persisted in Docker volume `email-productivity-agent_attachment_storage` and mounted to `/app/storage/attachments`.
- Attachment AI analysis is background-queued (Celery) and exposed via `/api/v1/attachments/*` + `/api/v1/emails/{email_id}/attachments/*`.

## Project Structure (Current)

```text
email-productivity-agent/
  backend/
    app/
      api/
      core/
      models/
      services/
      tasks/
      scripts/
    alembic/
    requirements.txt
    run.py
  frontend/
    src/
      components/
      context/
      hooks/
      services/
      styles/
    package.json
  data/
  docs/
  llm/
    Dockerfile
  llama.cpp/
  migrations/
  models/
    local_llm/
  scripts/
  docker-compose.yml
```

## License

See repository license file if present.
