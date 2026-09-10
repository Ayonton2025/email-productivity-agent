# Phase 10: Remaining oversized-file review

Reviewed against repository-specific Phase 10 in draft.docx, at Phase 9 commit `35beb11`, on branch `phase-10-refactor-review`.

## Scope decision

The feedback says “However, don't do these all immediately,” prioritizes the evaluator-named files first, and then explicitly assigns the mixed endpoint module to Phase 11 and Gmail ingestion to Phase 12. Phase 10 therefore delivers the inventory, responsibility boundaries, dependency review, and test prerequisites below. It does not claim the remaining files have already been refactored. This preserves the requested phase-by-phase review and commit checkpoints.

The earlier broad plan's Phase 10 test-suite guidance is not the numbering sequence being followed. Backend tests already exist, and Phase 9 completed the Insights component-test work.

## Measured baseline

Physical line counts include comments and blank lines and were measured from the current checkout, rather than copied from the feedback.

| File | Lines | Priority and disposition |
| --- | ---: | --- |
| `backend/app/models/database.py` | 275 | Evaluator priority completed in Phase 3; retain model identity/schema compatibility. |
| `backend/app/api/ai_endpoints.py` | 249 | Evaluator priority completed in Phase 4; retain schemas and orchestration boundary. |
| `frontend/src/components/insights/InsightsDashboard.jsx` | 136 | Evaluator priority completed in Phases 8–9; retain the five tested tabs. |
| `backend/app/api/endpoints.py` | 668 | Next implementation: Phase 11. |
| `backend/app/services/gmail_ingestion_service.py` | 652 | Next service implementation: Phase 12. |
| `backend/app/services/document_analysis_service.py` | 547 | Next backend extraction after Gmail, with separate review. |
| `backend/app/api/campaign_endpoints.py` | 505 | Backend backlog after the explicitly ranked hotspots; included because it appears in the initial list even though the feedback omits it from the later ordering. |
| `frontend/src/components/landing/LandingPage.jsx` | 565 | Frontend maintainability work after backend hotspots. |
| `frontend/src/components/billing/BillingUpgrade.jsx` | 549 | Frontend maintainability work; establish checkout behavior tests before moving logic. |
| `frontend/src/components/auth/Register.jsx` | 515 | Frontend maintainability work; establish both registration-flow tests first. |

## 1. Mixed API endpoints — Phase 11

`endpoints.py` contains 29 decorated routes: 28 HTTP routes and one WebSocket. Responsibilities include user inbox, prompt testing and CRUD, account connection/debugging, email retrieval and categorization, mock loading, drafts, reply generation, agent processing/chat/status, WebSocket handling, database/AI health, and API information.

**Dependencies and compatibility:** `core/router_loader.py` registers this router with `/api/v1` and the `api` tag. It also separately registers existing `inbox_endpoints.py`, `agent_endpoints.py`, account routers, and other API modules. Do not overwrite these modules with the feedback's illustrative filenames. A dedicated package such as `api/legacy/` can house extracted groups while `endpoints.py` remains the compatibility aggregator. Final names should reflect the actual grouping chosen in Phase 11.

**Extraction sequence:**

1. Record HTTP route methods/paths, operation IDs, response schemas, dependency requirements, registration order, and the WebSocket path from the live assembled app.
2. Start with a small coherent group such as health/info or drafts. Preserve handler signatures and route order when including child routers.
3. Extract prompt, account/email, and agent groups separately. Preserve static-path precedence over parameter paths such as `/emails/{email_id}`.
4. Keep `/emails/my-inbox` ownership filtering, authentication, safe failure response, structured logging, and request/user context from Phases 5–6 intact.
5. Check whether callers/tests import handler symbols from the old module; either preserve explicit exports or update callers deliberately.

**Validation:** existing `test_inbox_endpoint.py`, `test_request_logging.py`, `test_router_loader.py`, service tests, and the Phase 4 OpenAPI fixture provide starting evidence. Add route inventory/WebSocket checks and behavior tests for the groups actually moved. OpenAPI alone cannot verify authentication, tenant isolation, database failures, WebSockets, or route-order behavior. Run backend lint, format, mypy, coverage/security gates, and the relevant frontend API-domain checks after the extraction.

## 2. Gmail ingestion — Phase 12

The service has 12 methods covering OAuth client creation, retrieval, MIME/body parsing, HTML conversion/sanitization, attachment metadata, CID resolution, persistence, AI processing, and push setup. `store_emails` also coordinates attachment downloads and document-analysis tasks before its final commit.

**Callers:** account OAuth (`api/email_accounts/oauth.py`), multi-provider sync (`api/multi_provider_endpoints.py`), and Gmail webhooks (`api/webhook_endpoints.py`) construct `GmailIngestionService`. Attachment integration and the optional document-analysis task handler are further dependencies.

**Proposed boundaries:** extract pure message/body parsing and sanitization first; then Gmail API access; then persistence/attachment orchestration; retain the public service as coordinator. Reuse existing `services/email/`, `email_attachment_integration`, and `attachment_service` responsibilities instead of creating duplicate storage implementations.

**Characterization tests needed before extraction:** multipart and nested MIME, text/HTML alternatives, base64 decoding, missing headers, attachment/CID handling, sanitizer availability, empty fetch results and provider failures; stored IDs, duplicates, attachment/message association, commit and rollback behavior; absent prompts, AI failure fallback, already-completed messages, and push registration payloads. Use synthetic Gmail responses and mocked providers/tasks, with database tests for persistence.

**Observed issues to investigate independently of mechanical moves:** the duplicate lookup currently uses message ID without a user/account filter; UID conversion parses a portion of `external_id` as decimal; attachment association uses list indices; analysis tasks may be queued before the final commit; logs include subjects. These are inspection findings, not reproduced failures or fixes. Establish actual provider/model contracts and tenant/privacy expectations before deciding corrections. Do not silently bless potentially unsafe behavior with preservation tests or mix its correction into an undocumented extraction.

No direct Gmail-ingestion test module/reference was found in the searched backend tests; generic email-service tests are not evidence that this class is covered.

## 3. Document analysis — next backend extraction

Three existing classes already provide useful boundaries:

- `DocumentAnalysisEngine`: analysis record creation, free-tier metadata path, paid LLM calls, response decoding, confidence conversion, and status updates.
- `DocumentTextExtractor`: PDF, DOCX, CSV, XLSX, PPTX, and general text dispatch with optional dependency handling.
- `DocumentAnalysisBackgroundTask`: attachment lookup, existing-analysis lookup, file reading, extraction/analysis coordination, commit/rollback, and per-email iteration.

**Proposed extraction:** move the classes into separate modules under a document-analysis package, leaving explicit compatibility exports in `document_analysis_service.py`. `tasks/document_analysis_task.py` imports the background class and must continue to initialize it. Keep dependency direction extractor/engine → coordinator → task adapter to avoid circular imports.

**Validation prerequisites:** synthetic byte fixtures for each available format, missing optional library behavior, extraction errors, unsupported types, free/paid and short-text branches, valid/fenced/malformed JSON, failed LLM calls, confidence conversions, duplicate/missing attachments, missing file data, commit/rollback and batch continuation. Review attachment ownership enforcement at the calling boundary; a lookup by attachment ID alone does not establish authorization. Content-bearing debug logs also need a separate privacy review. No direct service test references were found in the searched backend suite; attachment storage tests cover a neighboring responsibility.

## 4. Campaign endpoints — retained in the backlog

The module combines five request-model classes, sender scoring, and 11 routes for sender recommendation, campaign CRUD, sequences, bulk leads, lead listing, and start/pause transitions. The loader supplies `/api/v1`; the router supplies `/campaigns`.

**Proposed boundaries:** extract request schemas first, preserving names/defaults/OpenAPI; then sender selection as a small service; finally split campaign, sequence/lead, and execution routes if still warranted. Preserve feature gating through `FeatureGatingService`, campaign ownership checks, status filters, and transaction boundaries. Check existing API schema-package conventions before selecting destinations.

**Validation prerequisites:** schema/default parity, denied feature access, own/other-user campaign behavior, sender ordering/caps, sequence association, bulk-lead association, status transitions, and commit/rollback on failures. Existing frontend API-domain/editor tests, workspace-assistant persistence tests, and the OpenAPI fixture provide indirect coverage; they are not substitutes for direct backend route tests.

## 5. Landing page — frontend maintainability

Responsibilities include scroll state, canvas animation and resize handling, plan data, authentication-dependent calls to action, onboarding links, marketing sections, pricing, demo/footer, and the contact-sales modal.

**Proposed boundaries:** extract pricing data and presentational sections, then canvas behavior into a hook/component. Preserve CSS classes/anchors, standard/hosted onboarding query parameters, authenticated billing destinations, and sales-modal behavior.

**Validation prerequisites:** render the actual landing page (the Home test currently mocks it), exercise authenticated/anonymous actions and pricing, modal open/close, anchor navigation, and animation/listener teardown. Inspection found the resize listener lacks cleanup in the animation effect while the effect reruns on scroll changes; reproduce and fix that separately or explicitly as part of the animation extraction with a regression test. Canvas/layout changes also merit browser verification rather than jsdom assertions alone.

## 6. Billing upgrade — frontend maintainability

Responsibilities include fallback/server plan conversion, health checks, country inference, current-plan restrictions, payment-method retrieval and ordering, a chooser modal, checkout redirects, errors/debug display, FAQ, and navigation.

**Proposed boundaries:** pure plan mapping and constants, checkout state/orchestration hook, plan cards, and payment-method modal. Keep the existing payment service as the provider boundary. Preserve redirect precedence (`authorization_url`, `approval_url`, `checkout_url`), fallback behavior, country options, and pending-plan identity.

**Validation prerequisites:** server and fallback plans, current/free/enterprise handling, method ordering and selection, cancel/confirm, method-fetch failure, each redirect field, invalid/mock success, double-submit controls, and user-visible errors. Use mocked payment responses; no real purchase is necessary. The existing component test checks fallback rendering and checkout copy but does not click through checkout despite its test title. Separate payment-service tests do not establish the component's complete state flow.

## 7. Registration — frontend maintainability

Responsibilities include standard and hosted form state, URL-selected mode, existing-user redirects, validation, password visibility, two submission contracts, success/error display, generated-password messaging, and delayed navigation.

**Proposed boundaries:** standard/hosted form components plus a coordinator or focused hook; extract pure validation only after recording the current API contracts. Keep AuthContext as the authentication boundary.

**Validation prerequisites:** mode query parameters, validation boundaries, trimming/casing for hosted signup, success with/without auto-login, API rejection/exception, pending-state behavior, generated-password messaging, password visibility, authenticated redirect, and timer cleanup. The existing direct test only exercises mismatched standard passwords. Do not change backend password rules or response shapes as a side effect of moving JSX. Review content-bearing registration logs and exception handling separately with explicit tests.

## Cross-cutting completion gates

For each future extraction: establish focused behavioral evidence; move one coherent responsibility; preserve public interfaces or document intended changes; run the affected tests and repository quality checks; inspect the diff for unrelated edits; record results and unresolved risks; stop at the user review/commit checkpoint. Line count is a signal for responsibility review, not a reason to fragment cohesive code.

Use the existing `scripts/verify.py`/fresh-clone workflows for their intended later gates. Do not describe a local test pass as hosted CI success. Phase 7's frontend audit and Linux/Windows fresh-clone failures remain unresolved, and hosted Sentry delivery remains unverified. Those items still block an all-green release claim.

## Verification and checkpoint

This phase used source inspection, Python AST inventories of classes/functions/routes, repository searches for imports and tests, current line counts, and a diff whitespace check. No runtime files changed; no runtime test suites were rerun for this documentation-only review. Previous test results are not represented as new Phase 10 results.

All seven listed candidates are accounted for, the completed evaluator priorities are checked, the implementation sequence respects Phases 11–12, and each candidate has concrete extraction boundaries and test prerequisites. Phase 10 review is complete; the refactors themselves remain future work. The user approved committing and pushing this review report.
