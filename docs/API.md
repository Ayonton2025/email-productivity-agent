# API

## Overview

The FastAPI service exposes a versioned JSON API at `/api/v1`, WebSocket functionality and root operational endpoints. The running application is authoritative:

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`
- Liveness: `/health`
- Readiness: `/ready`

## Authentication

Protected routes use `Authorization: Bearer <access-token>`. Tokens identify a user; dependencies load the active account and enforce feature-specific permissions. Treat `401` as authentication failure and `403` as a permission or entitlement failure.

## Major resources

| Area | Representative prefix | Capabilities |
|---|---|---|
| Identity | `/api/v1` authentication routes | Registration, login and password recovery |
| Inbox | `/api/v1/emails` | Search, categorize, flag, bulk operations and attachments |
| Providers | `/api/v1/email-accounts`, `/api/v1/email-providers` | OAuth, IMAP/SMTP, sync and send |
| Intelligence | `/api/v1/ai`, `/api/v1/agents`, `/api/v1/insights` | Classification, drafting, summaries and analytics |
| Automation | `/api/v1/workflows`, `/api/v1/auto-reply`, `/api/v1/followups` | Rules, steps and follow-ups |
| Collaboration | `/api/v1/shared-inboxes`, `/api/v1/contact` | Shared access and relationships |
| Delivery | `/api/v1/campaigns`, `/api/v1/deliverability`, `/api/v1/hosted-email` | Sequences, sending and abuse controls |
| Billing | `/api/v1/billing`, `/api/v1/usage` | Plans, checkout, webhooks, credits and usage |
| Administration | `/api/v1/admin/llm`, `/api/v1/admin/usage` | Provider pools, health and access overrides |

OpenAPI enumerates the complete route and schema set.

## Conventions

- Send JSON unless an upload endpoint specifies multipart data.
- Validated requests reject unknown, unsafe or oversized values.
- Pagination uses bounded `limit` and `offset` parameters.
- Clients may send `X-Request-ID`; otherwise the server generates and returns one.
- Rate limits return `429`, `Retry-After` and quota headers.
- Validation errors use FastAPI's `422` field-error response.

Application errors are normalized and request-correlated; credentials, tokens and traces must not be exposed. Backward-compatible additions may ship within `/api/v1`; breaking changes require a new version or migration window.

```bash
curl -H "Authorization: Bearer ${TOKEN}" \
     -H "X-Request-ID: buyer-demo-001" \
     "https://api.example.com/api/v1/emails?limit=25"
```
