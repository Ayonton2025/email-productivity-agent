"""Reply generation and asynchronous email intelligence."""

import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.database import Email

logger = logging.getLogger(__name__)


class EmailIntelligenceMixin:
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

        except Exception as e:
            logger.error(f"❌ [EmailService] Error generating reply draft: {e}")
            sender_hint = "there"
            try:
                if user_id:
                    email = await self.get_email_by_id(email_id, user_id)
                    sender_hint = (email or {}).get("sender", "there").split("@")[0]
            except Exception:
                pass
            return {
                "subject": "Re: Your email",
                "body": f"""Dear {sender_hint},

Thank you for your email. I received your message and will respond shortly.

Best regards,
{(user_name or "Team")}""",
                "ai_generated": False,
                "mock": True,
                "mock_warning": "AI service is temporarily unavailable. A safe template reply was generated instead.",
                "error": str(e),
            }

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

        except Exception as e:
            logger.error(f"❌ [EmailService] Error ensuring user has emails: {e}")
            return False

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
        except Exception as e:
            logger.error(f"❌ [EmailService] Error in get_active_email_accounts: {e}")
            return []

    async def get_pending_emails(self, session: AsyncSession = None, limit: int = 100):
        """Return pending emails to be processed by background tasks."""
        try:
            db = session or self.db
            result = await db.execute(
                select(Email).where(Email.processing_status == "pending").order_by(Email.received_at.asc()).limit(limit)
            )
            emails = result.scalars().all()
            return emails
        except Exception as e:
            logger.error(f"❌ [EmailService] Error in get_pending_emails: {e}")
            return []

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
            except Exception:
                summary = None

            if summary:
                email.ai_summary = summary

            email.processing_status = "completed"
            await db.commit()
            return {"success": True}

        except Exception as e:
            logger.error(f"❌ [EmailService] Error in process_email_intelligence: {e}")
            try:
                await db.rollback()
            except Exception:
                pass
            return {"success": False, "error": str(e)}

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

        except Exception as e:
            logger.error(f"❌ [EmailService] Error in sync_account: {e}")
            try:
                await db.rollback()
            except Exception:
                pass
            return {"success": False, "error": str(e)}
