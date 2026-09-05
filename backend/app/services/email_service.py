# backend/app/services/email_service.py
import asyncio
import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.exceptions import EmailDataLoadError, EmailPersistenceError
from app.core.monitoring import capture_exception
from app.models.database import Email, EmailDraft
from app.services.llm_service import LLMService
from app.services.mock_email_loader import MockEmailLoader
from app.services.prompt_service import PromptService

logger = structlog.get_logger(__name__)


class EmailService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = LLMService()
        self.prompt_service = PromptService(db)
        self.mock_email_loader = MockEmailLoader()

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

    async def _check_duplicate_email(self, user_id: str, email_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if a similar email already exists for this user"""
        try:
            from sqlalchemy import select

            # Check by subject and sender (most reliable way to detect duplicates)
            result = await self.db.execute(
                select(Email).where(
                    Email.user_id == user_id,
                    Email.subject == email_data.get("subject", ""),
                    Email.sender == email_data.get("sender", ""),
                )
            )
            existing_email = result.scalar_one_or_none()

            if existing_email:
                return existing_email.to_dict()

            # Also check by ID if present
            if "id" in email_data:
                result = await self.db.execute(
                    select(Email).where(Email.user_id == user_id, Email.id == email_data["id"])
                )
                existing_email = result.scalar_one_or_none()
                if existing_email:
                    return existing_email.to_dict()

            return None

        except SQLAlchemyError as exc:
            logger.warning(
                "duplicate_email_check_failed",
                user_id=user_id,
                operation="check_duplicate_email",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise EmailPersistenceError("Unable to check for duplicate emails") from exc

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
                try:
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

                except SQLAlchemyError as exc:
                    logger.warning(
                        "email_ai_processing_failed",
                        user_id=user_id,
                        operation="process_single_email",
                        error=str(exc),
                        error_type=type(exc).__name__,
                    )

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
            await self.db.rollback()
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

    async def get_all_emails(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all emails with pagination"""
        try:
            result = await self.db.execute(select(Email).order_by(Email.received_at.desc()).limit(limit).offset(offset))
            emails = result.scalars().all()
            return [email.to_dict() for email in emails]
        except SQLAlchemyError as exc:
            logger.exception("email_list_query_failed", operation="get_all_emails")
            raise EmailPersistenceError("Unable to retrieve emails") from exc

    async def get_user_emails(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get emails for a specific user"""
        try:
            logger.info(f"📧 [EmailService] Getting emails for user: {user_id}")

            result = await self.db.execute(
                select(Email)
                .where(Email.user_id == user_id)
                .order_by(Email.timestamp.desc())
                .limit(limit)
                .offset(offset)
            )
            emails = result.scalars().all()

            logger.info(f"📧 [EmailService] Found {len(emails)} emails in database")

            email_list = []
            for email in emails:
                try:
                    email_dict = email.to_dict()
                    email_list.append(email_dict)
                except (AttributeError, KeyError, TypeError, ValueError) as e:
                    logger.error(f"⚠️ [EmailService] Error converting email {email.id}: {e}")
                    email_list.append(
                        {
                            "id": str(email.id),
                            "user_id": str(email.user_id),
                            "sender": email.sender,
                            "subject": email.subject,
                            "body": email.body,
                            "timestamp": email.timestamp.isoformat(),
                            "category": email.category,
                        }
                    )

            return email_list

        except SQLAlchemyError as exc:
            logger.exception("email_list_query_failed", operation="get_user_emails", user_id=user_id)
            raise EmailPersistenceError("Unable to retrieve user emails") from exc

    async def get_email_by_id(self, email_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Get a specific email by ID, optionally filtered by user"""
        try:
            query = select(Email).where(Email.id == email_id)
            if user_id:
                query = query.where(Email.user_id == user_id)

            result = await self.db.execute(query)
            email = result.scalar_one_or_none()

            if email:
                logger.info(f"✅ [EmailService] Found email: {email.id} - {email.subject}")
                return email.to_dict()
            else:
                logger.error(f"❌ [EmailService] Email not found: {email_id} for user: {user_id}")
                return None

        except SQLAlchemyError as exc:
            logger.exception("email_query_failed", operation="get_email_by_id", email_id=email_id, user_id=user_id)
            raise EmailPersistenceError("Unable to retrieve email") from exc

    async def generate_reply_draft(
        self,
        email_id: str,
        user_id: str = None,
        user_plan: str = "personal",
        user_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a reply draft for an email

        Args:
            email_id: Email to reply to
            user_id: User ID for security
            user_plan: User's subscription plan (personal, plus, professional, enterprise)

        Returns:
            Dict with reply data including 'body', 'mock', 'mock_warning' if applicable
        """
        try:
            logger.info(f"📧 [EmailService] Generating reply for email: {email_id}, user_plan: {user_plan}")

            # Get the email
            email = await self.get_email_by_id(email_id, user_id)
            if not email:
                raise ValueError(f"Email not found: {email_id}")

            # Generate reply using LLM
            if self.llm_service:
                reply_data = await self.llm_service.generate_email_reply(
                    {"sender": email.get("sender"), "subject": email.get("subject"), "body": email.get("body")},
                    tone="professional",
                    user_plan=user_plan,
                    user_name=user_name,
                )

                logger.info(
                    f"✅ [EmailService] Generated reply: {len(reply_data.get('body', ''))} characters, mock: {reply_data.get('mock', False)}"
                )
                return reply_data
            else:
                # Fallback reply
                sender_name = email.get("sender", "there").split("@")[0]
                return {
                    "subject": f"Re: {email.get('subject', 'Your email')}",
                    "body": f"""Dear {sender_name},

Thank you for your email regarding "{email.get('subject', 'this matter')}".

I have received your message and will review it carefully. Please expect a response within 24-48 hours.

Best regards,
[Your Name]""",
                    "ai_generated": False,
                    "mock": True,
                }

        except SQLAlchemyError as exc:
            logger.exception("reply_draft_persistence_failed", email_id=email_id, user_id=user_id)
            raise EmailPersistenceError("Unable to load the email for reply drafting") from exc

    async def update_email_category(self, email_id: str, category: str, user_id: str = None) -> bool:
        """Update email category"""
        try:
            query = select(Email).where(Email.id == email_id)
            if user_id:
                query = query.where(Email.user_id == user_id)

            result = await self.db.execute(query)
            email = result.scalar_one_or_none()

            if email:
                email.category = category
                await self.db.commit()
                return True
            return False
        except SQLAlchemyError as exc:
            logger.exception("email_category_update_failed", email_id=email_id, user_id=user_id)
            raise EmailPersistenceError("Unable to update email category") from exc

    async def create_draft(self, draft_data: Dict[str, Any], user_id: str = None) -> Dict[str, Any]:
        """Create a new email draft"""
        try:
            draft_metadata = draft_data.pop("metadata", {})
            draft_data["draft_metadata"] = draft_metadata

            if user_id:
                draft_data["user_id"] = user_id

            draft = EmailDraft(**draft_data)
            self.db.add(draft)
            await self.db.commit()
            await self.db.refresh(draft)
            return draft.to_dict()
        except SQLAlchemyError as exc:
            logger.exception("draft_create_failed", user_id=user_id)
            raise EmailPersistenceError("Unable to create draft") from exc

    async def get_drafts(self) -> List[Dict[str, Any]]:
        """Get all email drafts"""
        try:
            result = await self.db.execute(select(EmailDraft).order_by(EmailDraft.updated_at.desc()))
            drafts = result.scalars().all()
            return [draft.to_dict() for draft in drafts]
        except SQLAlchemyError as exc:
            logger.exception("draft_list_query_failed", operation="get_drafts")
            raise EmailPersistenceError("Unable to retrieve drafts") from exc

    async def get_user_drafts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get drafts for a specific user"""
        try:
            result = await self.db.execute(
                select(EmailDraft).where(EmailDraft.user_id == user_id).order_by(EmailDraft.updated_at.desc())
            )
            drafts = result.scalars().all()
            return [draft.to_dict() for draft in drafts]
        except SQLAlchemyError as exc:
            logger.exception("draft_list_query_failed", operation="get_user_drafts", user_id=user_id)
            raise EmailPersistenceError("Unable to retrieve user drafts") from exc

    async def update_draft(self, draft_id: str, draft_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a draft"""
        try:
            if "metadata" in draft_data:
                draft_data["draft_metadata"] = draft_data.pop("metadata")
            result = await self.db.execute(select(EmailDraft).where(EmailDraft.id == draft_id))
            draft = result.scalar_one_or_none()

            if draft:
                for key, value in draft_data.items():
                    setattr(draft, key, value)
                await self.db.commit()
                await self.db.refresh(draft)
                return draft.to_dict()
            return None
        except SQLAlchemyError as exc:
            logger.exception("draft_update_failed", draft_id=draft_id)
            raise EmailPersistenceError("Unable to update draft") from exc

    async def delete_draft(self, draft_id: str) -> bool:
        """Delete a draft"""
        try:
            result = await self.db.execute(select(EmailDraft).where(EmailDraft.id == draft_id))
            draft = result.scalar_one_or_none()

            if draft:
                await self.db.delete(draft)
                await self.db.commit()
                return True
            return False
        except SQLAlchemyError as exc:
            logger.exception("draft_delete_failed", draft_id=draft_id)
            raise EmailPersistenceError("Unable to delete draft") from exc

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

    async def get_active_email_accounts(self, session: AsyncSession = None):
        """Return active, sync-enabled `UserEmailAccount` rows."""
        try:
            db = session or self.db
            from app.models.database import UserEmailAccount

            result = await db.execute(
                select(UserEmailAccount)
                .where(
                    UserEmailAccount.is_active == True,
                    UserEmailAccount.sync_enabled == True,
                )
                .order_by(UserEmailAccount.is_primary.desc(), UserEmailAccount.created_at.desc())
            )
            accounts = result.scalars().all()
            return accounts
        except SQLAlchemyError as exc:
            logger.exception("email_account_query_failed", operation="get_active_email_accounts")
            raise EmailPersistenceError("Unable to retrieve active email accounts") from exc

    async def get_pending_emails(self, session: AsyncSession = None, limit: int = 100):
        """Return pending emails to be processed by background tasks."""
        try:
            db = session or self.db
            result = await db.execute(
                select(Email).where(Email.processing_status == "pending").order_by(Email.received_at.asc()).limit(limit)
            )
            emails = result.scalars().all()
            return emails
        except SQLAlchemyError as exc:
            logger.exception("pending_email_query_failed")
            raise EmailPersistenceError("Unable to retrieve pending emails") from exc

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
            try:
                if self.llm_service:
                    prompt = await self.prompt_service.get_active_prompt("summary")
                    resp = await self.llm_service.process_prompt(
                        prompt.template, email.body_text or email.body_html or ""
                    )
                    summary = resp if isinstance(resp, str) else (resp.get("text") if isinstance(resp, dict) else None)
            except SQLAlchemyError:
                summary = None

            if summary:
                email.ai_summary = summary

            email.processing_status = "completed"
            await db.commit()
            return {"success": True}

        except SQLAlchemyError as exc:
            logger.exception("email_intelligence_persistence_failed", email_id=email_id)
            try:
                await db.rollback()
            except SQLAlchemyError:
                pass
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
            try:
                await db.rollback()
            except SQLAlchemyError:
                pass
            raise EmailPersistenceError("Unable to sync email account") from exc
