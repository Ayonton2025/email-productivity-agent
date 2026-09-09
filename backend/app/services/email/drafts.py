# backend/app/services/email_service.py
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select

from app.core.exceptions import EmailPersistenceError
from app.models.email_models import EmailDraft

logger = structlog.get_logger(__name__)


class EmailDraftsMixin:
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

    async def create_draft(self, draft_data: Dict[str, Any], user_id: str = None) -> Dict[str, Any]:
        """Create a new email draft"""
        draft_data = dict(draft_data)
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
            await self._rollback_after_failure(self.db)
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
        draft_data = dict(draft_data)
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
            await self._rollback_after_failure(self.db)
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
            await self._rollback_after_failure(self.db)
            logger.exception("draft_delete_failed", draft_id=draft_id)
            raise EmailPersistenceError("Unable to delete draft") from exc
