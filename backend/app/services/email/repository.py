"""Email and draft persistence operations."""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.future import select

from app.models.database import Email, EmailDraft

logger = logging.getLogger(__name__)


class EmailRepositoryMixin:
    async def get_all_emails(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all emails with pagination"""
        try:
            result = await self.db.execute(
                select(Email).order_by(Email.timestamp.desc()).limit(limit).offset(offset)
            )
            emails = result.scalars().all()
            return [email.to_dict() for email in emails]
        except Exception as e:
            logger.error(f"❌ [EmailService] Error in get_all_emails: {e}")
            return []

    async def get_user_emails(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
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
                except Exception as e:
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

        except Exception as e:
            logger.error(f"❌ [EmailService] Error in get_user_emails: {e}")
            import traceback

            logger.info(f"❌ [EmailService] Stack trace: {traceback.format_exc()}")
            return []

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

        except Exception as e:
            logger.error(f"❌ [EmailService] Error getting email by ID: {e}")
            return None

    async def update_email_category(
        self, email_id: str, category: str, user_id: str = None
    ) -> bool:
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
        except Exception as e:
            logger.error(f"❌ [EmailService] Error updating email category: {e}")
            return False

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
        except Exception as e:
            logger.error(f"❌ [EmailService] Error creating draft: {e}")
            raise

    async def get_drafts(self) -> List[Dict[str, Any]]:
        """Get all email drafts"""
        try:
            result = await self.db.execute(
                select(EmailDraft).order_by(EmailDraft.updated_at.desc())
            )
            drafts = result.scalars().all()
            return [draft.to_dict() for draft in drafts]
        except Exception as e:
            logger.error(f"❌ [EmailService] Error getting drafts: {e}")
            return []

    async def get_user_drafts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get drafts for a specific user"""
        try:
            result = await self.db.execute(
                select(EmailDraft)
                .where(EmailDraft.user_id == user_id)
                .order_by(EmailDraft.updated_at.desc())
            )
            drafts = result.scalars().all()
            return [draft.to_dict() for draft in drafts]
        except Exception as e:
            logger.error(f"❌ [EmailService] Error getting user drafts: {e}")
            return []

    async def update_draft(
        self, draft_id: str, draft_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
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
        except Exception as e:
            logger.error(f"❌ [EmailService] Error updating draft: {e}")
            return None

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
        except Exception as e:
            logger.error(f"❌ [EmailService] Error deleting draft: {e}")
            return False
