# backend/app/services/email_service.py
import asyncio
import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.exceptions import EmailDataLoadError, EmailPersistenceError
from app.core.monitoring import capture_exception
from app.models.database import Email

logger = structlog.get_logger(__name__)


class EmailProcessingMixin:
    async def load_mock_emails(self, user_id: str) -> List[Dict[str, Any]]:
        """Load mock emails from JSON file into database for a specific user"""
        try:
            logger.info("mock_email_load_started", user_id=user_id, operation="load_mock_emails")

            # First, check if user already has emails to avoid duplicates - MORE ROBUST CHECK
            existing_emails = await self.get_user_emails(user_id)
            if existing_emails and len(existing_emails) >= 5:  # Changed from 0 to 5 to be more conservative
                logger.info(
                    "mock_email_load_skipped",
                    user_id=user_id,
                    operation="load_mock_emails",
                    reason="existing_email_threshold",
                    existing_count=len(existing_emails),
                )
                return existing_emails

            mock_emails = self.mock_email_loader.load()

            logger.info("mock_emails_discovered", user_id=user_id, email_count=len(mock_emails))

            # CRITICAL FIX: Check for duplicates by email content before loading
            processed_emails = []
            duplicate_count = 0

            for email_data in mock_emails:
                # Check if similar email already exists for this user
                existing_similar = await self._check_duplicate_email(user_id, email_data)

                if existing_similar:
                    duplicate_count += 1
                    logger.info(
                        "mock_email_duplicate_skipped",
                        user_id=user_id,
                        subject=email_data.get("subject", "No Subject"),
                    )
                    processed_emails.append(existing_similar)
                    continue

                processed_email = await self.process_single_email(email_data, user_id)
                processed_emails.append(processed_email)

            if duplicate_count > 0:
                logger.info("mock_email_duplicates_skipped", user_id=user_id, duplicate_count=duplicate_count)

            logger.info("mock_email_load_completed", user_id=user_id, email_count=len(processed_emails))
            return processed_emails

        except SQLAlchemyError as exc:
            logger.exception("mock_email_persistence_failed", user_id=user_id, operation="load_mock_emails")
            raise EmailPersistenceError("Unable to load mock emails from the database") from exc
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            logger.exception("mock_email_load_failed", user_id=user_id, operation="load_mock_emails", error=str(exc))
            raise EmailDataLoadError("Unable to load mock email data") from exc

    async def process_single_email(self, email_data: Dict[str, Any], user_id: str = None) -> Dict[str, Any]:
        """Process a single email and save to database"""
        if not isinstance(email_data, dict):
            raise ValueError("email_data must be a dictionary")

        try:
            logger.info(
                "email_processing_started",
                user_id=user_id,
                operation="process_single_email",
                subject=email_data.get("subject", "No Subject"),
            )

            # Handle timestamp conversion
            raw_ts = email_data.get("timestamp", datetime.utcnow().isoformat())
            if isinstance(raw_ts, str) and raw_ts.endswith("Z"):
                raw_ts = raw_ts.replace("Z", "+00:00")
            timestamp = datetime.fromisoformat(raw_ts)

            # Use existing AI-generated data or generate new
            category = email_data.get("category", "Uncategorized")
            action_items = email_data.get("action_items", [])
            summary = email_data.get("summary", "")

            # If we have an LLM service and want to regenerate AI data
            if self.llm_service and not category:
                categorization_prompt = await self.prompt_service.get_active_prompt("categorization")
                action_prompt = await self.prompt_service.get_active_prompt("action_extraction")
                summary_prompt = await self.prompt_service.get_active_prompt("summary")

                email_content = f"From: {email_data.get('sender', '')}\nSubject: {email_data.get('subject', '')}\nBody: {email_data.get('body', '')}"

                # Run AI processing in parallel
                tasks = [
                    self.llm_service.process_prompt(categorization_prompt.template, email_content),
                    self.llm_service.process_prompt(action_prompt.template, email_content),
                    self.llm_service.process_prompt(summary_prompt.template, email_content),
                ]

                category, action_items_raw, summary = await asyncio.gather(*tasks)

                # Parse action items
                try:
                    if action_items_raw.strip().startswith("{") or action_items_raw.strip().startswith("["):
                        action_items = json.loads(action_items_raw)
                    else:
                        action_items = [{"task": action_items_raw, "deadline": None}]
                except (TypeError, ValueError, json.JSONDecodeError):
                    action_items = [{"task": action_items_raw, "deadline": None}]

            # Create email record
            source_id = str(email_data.get("id") or email_data.get("message_id") or "")
            stable_key = source_id or f"{email_data.get('sender', '')}|{email_data.get('subject', '')}|{raw_ts}"
            uid = email_data.get("uid")
            if uid is None:
                uid = int(hashlib.sha256(stable_key.encode("utf-8")).hexdigest()[:15], 16)

            email = Email(
                account_id=str(email_data.get("account_id") or f"mock-{user_id}"),
                user_id=user_id,
                message_id=str(email_data.get("message_id") or f"<mock-{stable_key}@local>"),
                uid=int(uid),
                sender=email_data.get("sender", ""),
                recipients=email_data.get("recipients", []),
                subject=email_data.get("subject", ""),
                body_text=email_data.get("body_text", email_data.get("body", "")),
                body_html=email_data.get("body_html"),
                received_at=timestamp,
                ai_category=category,
                priority=email_data.get("priority", "medium"),
                is_read=email_data.get("is_read", False),
                is_archived=email_data.get("is_archived", False),
                is_flagged=email_data.get("is_flagged", email_data.get("is_starred", False)),
                action_items=action_items,
                ai_summary=summary,
            )

            self.db.add(email)
            await self.db.commit()
            await self.db.refresh(email)

            logger.info("email_processing_completed", user_id=user_id, email_id=email.id)
            return email.to_dict()

        except (ValueError, TypeError, KeyError) as exc:
            logger.exception(
                "email_processing_failed",
                user_id=user_id,
                operation="process_single_email",
                email_id=email_data.get("id"),
                error=str(exc),
                error_type=type(exc).__name__,
            )
            capture_exception(exc, user_id=user_id, operation="process_single_email")
            raise
        except SQLAlchemyError as exc:
            await self._rollback_after_failure(self.db)
            logger.exception(
                "email_processing_failed",
                user_id=user_id,
                operation="process_single_email",
                email_id=email_data.get("id"),
                error=str(exc),
                error_type=type(exc).__name__,
            )
            capture_exception(exc, user_id=user_id, operation="process_single_email")
            raise EmailPersistenceError("Unable to persist email") from exc

    async def ensure_user_has_emails(self, user_id: str) -> bool:
        """Ensure a user has emails (load mock data if empty)"""
        try:
            # More conservative check - only load if user has very few emails
            existing_emails = await self.get_user_emails(user_id)
            if existing_emails and len(existing_emails) >= 5:  # Changed from 0 to 5
                logger.info(
                    f"📧 [EmailService] User {user_id} already has {len(existing_emails)} emails, skipping mock load"
                )
                return True
            else:
                logger.info(
                    f"📧 [EmailService] User {user_id} has only {len(existing_emails)} emails, loading mock data"
                )
                await self.load_mock_emails(user_id)
                return True

        except SQLAlchemyError as exc:
            logger.exception("ensure_user_emails_failed", user_id=user_id)
            raise EmailPersistenceError("Unable to ensure user emails") from exc

    async def process_email_intelligence(self, email_id: str, session: AsyncSession = None) -> dict:
        """Lightweight processing for an email: mark processing, optionally call LLM, then complete."""
        try:
            db = session or self.db
            result = await db.execute(select(Email).where(Email.id == email_id))
            email = result.scalar_one_or_none()
            if not email:
                return {"success": False, "error": "not_found"}

            email.processing_status = "processing"
            await db.commit()

            # Minimal AI processing: if LLM service available, attempt to summarize
            summary = None
            if self.llm_service:
                prompt = await self.prompt_service.get_active_prompt("summary")
                resp = await self.llm_service.process_prompt(prompt.template, email.body_text or email.body_html or "")
                summary = resp if isinstance(resp, str) else (resp.get("text") if isinstance(resp, dict) else None)

            if summary:
                email.ai_summary = summary

            email.processing_status = "completed"
            await db.commit()
            return {"success": True}

        except SQLAlchemyError as exc:
            logger.exception("email_intelligence_persistence_failed", email_id=email_id)
            await self._rollback_after_failure(db)
            raise EmailPersistenceError("Unable to process email intelligence") from exc

    async def sync_account(self, account_id: str, session: AsyncSession = None) -> dict:
        """Perform a minimal sync operation for a user email account (updates last_sync)."""
        try:
            db = session or self.db
            from datetime import datetime

            from app.models.database import UserEmailAccount

            result = await db.execute(select(UserEmailAccount).where(UserEmailAccount.id == account_id))
            account = result.scalar_one_or_none()
            if not account:
                return {"success": False, "error": "account_not_found"}

            account.last_sync = datetime.utcnow()
            account.last_sync_status = "success"
            await db.commit()
            return {"success": True}

        except SQLAlchemyError as exc:
            logger.exception("email_account_sync_failed", account_id=account_id)
            await self._rollback_after_failure(db)
            raise EmailPersistenceError("Unable to sync email account") from exc
