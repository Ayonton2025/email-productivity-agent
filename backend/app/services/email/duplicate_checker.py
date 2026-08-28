"""Database-backed duplicate detection."""

import logging
from typing import Any, Dict, Optional

from app.models.database import Email

logger = logging.getLogger(__name__)


class DuplicateCheckerMixin:
    async def _check_duplicate_email(
        self, user_id: str, email_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
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

        except Exception as e:
            logger.error(f"⚠️ [EmailService] Error checking duplicate: {e}")
            return None
