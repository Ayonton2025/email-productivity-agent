# Phase 12: Gmail ingestion responsibilities and regressions

This follows the repository-specific Phase 12 in draft.docx and starts from Phase 11 commit `fecda6a` on branch `phase-12-gmail-ingestion`. Earlier work is retained in the branch history and summarized in [the amendment progress record](AMENDMENT_PROGRESS.md).

## Requirement coverage

| Responsibility | Implementation |
| --- | --- |
| Caller compatibility and coordination | `gmail_ingestion_service.py`: 69-line facade, reduced from 652 lines. All original public/private method names, parameters, defaults, async behavior, and annotations are retained. |
| OAuth credentials and Gmail retrieval | `email/gmail_client.py` (112 lines): credential construction, full-message retrieval, individual-fetch failure handling, and watch registration. |
| Message/MIME parsing | `email/gmail_message_parser.py` (197 lines): headers, recipients, UTC dates, text/HTML extraction, attachment metadata, flags, and numeric timestamp conversion. |
| HTML and CID handling | `email/gmail_html.py` (158 lines): existing optional bleach path, fallback sanitization, and CID behavior separated from persistence. |
| Persistence and deduplication | `email/gmail_persistence.py` (155 lines): mailbox-scoped lookup, email storage, existing attachment-integration calls, transaction ownership, and post-commit analysis dispatch. |
| AI categorization | `email/gmail_processing.py` (101 lines): prompt lookup, category/summary fallback, processing status, and database failure rollback. |

The existing attachment integration/storage and document-analysis task handler are reused. A second attachment-storage implementation was not introduced. OAuth bootstrap, multi-provider sync, and webhook source files require no changes. Incremental history retrieval remains in the existing webhook controller; watch history ID/expiration persistence remains in the extracted client.

## Confirmed defects and corrections

Before extraction, three regression tests failed against the original implementation: plain-text and HTML fields were reversed, and an ordinary hexadecimal Gmail message ID raised `ValueError` during storage.

- Corrected the parser's unpacking of `(body_text, body_html)`. Nested multipart extraction and HTML-to-text fallback now reach the correct model fields.
- Kept Gmail IDs opaque. Numeric `uid` now uses Gmail `internalDate` epoch milliseconds, with a UTC received-date fallback for missing/invalid/out-of-range input. This matches the existing BigInteger model's timestamp purpose. Google's [Message resource documentation](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages) distinguishes the string ID from the `internalDate` timestamp. No schema migration is required.
- Deduplication now filters on user, account, and message ID together. Database tests verify repeat ingestion is skipped within a mailbox while the same provider ID can be stored for other accounts/users.
- Attachment retrieval uses the parsed record's own external/message ID. The old `message_ids` argument remains accepted for caller compatibility but no longer controls positional matching after partial provider fetches.
- Analysis is scheduled only when attachments were actually stored and dispatched after email/attachment commit. Commit failures roll back without dispatch. Queue failures do not undo committed mail; attachment retrieval failures remain isolated from otherwise valid email storage.
- AI database errors now propagate through rollback instead of referencing an uninitialized or previous-loop email object. Existing provider-category fallback and completed-message skipping remain intact.
- Extracted service logs retain their category but avoid echoing subjects, account email addresses, generated categories, or raw exception messages. Downstream services/controllers were not comprehensively audited for content-bearing logs.

These corrections affect future ingestion. Previously stored reversed body fields are not automatically rewritten. No live mailbox, OAuth token, payment, deployment, or production data was modified.

## Tests

- Parser regressions cover plain text, HTML fallback, nested MIME, attachments, labels, recipients, UTC dates, malformed/missing timestamp handling, and invalid payload errors.
- Provider tests mock Google client/credentials, empty results, partial-fetch failures, list failure, watch history and expiration, and watch failure.
- HTML tests cover the existing optional bleach configuration, fallback script/event removal, and unresolved CID behavior without real attachment data.
- Database tests cover mailbox-scoped duplicates, hexadecimal IDs, persisted content, and the facade's complete parse/store/AI/deduplicate flow.
- Transaction tests verify correct attachment identity, commit-before-queue, rollback/no-queue on commit failure, attachment failure/empty downloads, queue failure isolation, and AI database failure rollback.
- AI tests cover missing prompts, missing/completed emails, category failure fallback, summary persistence, and completed status.
- Syntax-tree comparison confirms the facade's original method signatures and annotations are preserved.

The first focused Windows run passed 26 tests; one additional database-backed facade pipeline test was then added for full-suite validation. Tests use synthetic messages, in-memory SQLite, and mocked provider/task boundaries.

## Validation results

- Focused Phase 12 suite: 26 passed in 9.94 seconds under the fresh Python 3.11 environment (`test_gmail_components.py`, `test_gmail_ingestion_regressions.py`, and `test_gmail_persistence.py`).
- Ruff lint and formatting checks passed for all Phase 12 source and test files.
- Full Linux backend test run: 319 passed, 39.46% total coverage, and the configured 31% threshold passed.
- A later full backend gate reached 318 passed and 85.11% coverage, but failed one existing `tests/test_model_compatibility.py::test_cold_model_import_order_has_no_duplicate_registry_or_database_side_effect` test. Bandit, pip-audit, the focused schema/input/security gate, and the 50% coverage threshold passed. This failure is outside the Gmail ingestion change and was not modified.
- Frontend email rendering/parser checks: 6 passed.

No thresholds or monitoring-test timeouts were relaxed. Hosted Gmail delivery, GitHub CI, Sentry ingestion, and the unrelated model-import failure remain separate verification items.

## Remaining limits

- This phase preserves the existing bounded fetch behavior (at most 50 IDs per request); it does not add pagination or redesign webhook history processing.
- HTML fallback sanitization and CID placeholder logic are inherited behavior, not a claim of comprehensive XSS protection or complete inline-image downloading. Dedicated sanitizer/CID hardening remains separate work.
- Deduplication remains a query-based check, not a database uniqueness guarantee against concurrent sync workers. Task dispatch remains best effort rather than a transactional outbox with guaranteed retry.
- Optional document-analysis and bleach availability behavior remains optional. No dependency manifests were changed.
- Full hosted Gmail sync/watch delivery, hosted Sentry ingestion, and GitHub CI remain unverified. Earlier hosted CI failures remain outstanding; local validation cannot resolve those deployment checks.

Phase 12 implementation is ready for final validation review. It has not been committed or pushed.
