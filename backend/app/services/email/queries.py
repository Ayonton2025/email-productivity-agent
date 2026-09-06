# backend/app/services/email_service.py
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.exceptions import EmailPersistenceError
from app.models.database import Email

logger = structlog.get_logger(__name__)


class EmailQueriesMixin:
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
                .order_by(Email.received_at.desc())
                .limit(limit)
                .offset(offset)
            )
            emails = result.scalars().all()

            logger.info(f"📧 [EmailService] Found {len(emails)} emails in database")

            return [email.to_dict() for email in emails]

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

    async def update_email_category(self, email_id: str, category: str, user_id: str = None) -> bool:
        """Update email category"""
        try:
            query = select(Email).where(Email.id == email_id)
            if user_id:
                query = query.where(Email.user_id == user_id)

            result = await self.db.execute(query)
            email = result.scalar_one_or_none()

            if email:
                email.ai_category = category
                await self.db.commit()
                return True
            return False
        except SQLAlchemyError as exc:
            await self._rollback_after_failure(self.db)
            logger.exception("email_category_update_failed", email_id=email_id, user_id=user_id)
            raise EmailPersistenceError("Unable to update email category") from exc

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
