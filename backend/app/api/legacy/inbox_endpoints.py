"""Inbox endpoints."""

from time import perf_counter
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import get_current_user
from app.models.database import get_db
from app.models.user_models import User
from app.services.email_service import EmailService

router = APIRouter()
# Preserve the established log category for compatibility with operational filters.
logger = get_logger("app.api.endpoints")


@router.get("/emails/my-inbox", response_model=List[Dict[str, Any]])
async def get_user_inbox(
    category: str = None,
    search: str = None,
    sort_by: str = "newest",
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's inbox emails (requires authentication)"""
    started = perf_counter()
    log_context = {"user_id": str(current_user.id), "operation": "get_user_inbox"}
    try:
        logger.info("inbox_fetch_started", **log_context)

        email_service = EmailService(db)

        # ✅ REMOVED: Don't automatically ensure user has emails here
        # This was causing duplicates on every API call
        # await email_service.ensure_user_has_emails(current_user.id)

        # Use user-specific method to get only current user's emails
        emails = await email_service.get_user_emails(user_id=current_user.id, limit=limit, offset=offset)

        filtered_emails = emails

        if category and category != "all":
            filtered_emails = [email for email in emails if email.get("category") == category]

        if search:
            search_lower = search.lower()
            filtered_emails = [
                email
                for email in filtered_emails
                if search_lower in email.get("subject", "").lower()
                or search_lower in email.get("sender", "").lower()
                or search_lower in email.get("body", "").lower()
            ]

        if sort_by == "newest":
            filtered_emails.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        elif sort_by == "oldest":
            filtered_emails.sort(key=lambda x: x.get("timestamp", ""))
        elif sort_by == "sender":
            filtered_emails.sort(key=lambda x: x.get("sender", ""))

        logger.info(
            "inbox_fetch_completed",
            **log_context,
            fetched_count=len(emails),
            result_count=len(filtered_emails),
            duration_ms=round((perf_counter() - started) * 1000, 2),
        )
        return filtered_emails

    except Exception as exc:
        # Exception messages/chains can contain email data and SQL parameters.
        logger.error(
            "get_user_inbox_failed",
            **log_context,
            error_type=type(exc).__name__,
            duration_ms=round((perf_counter() - started) * 1000, 2),
            exc_info=False,
        )
        raise HTTPException(status_code=500, detail="Unable to retrieve inbox") from None
