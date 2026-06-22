"""
Compatibility analytics endpoints used by the frontend.
"""

from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.models.database import Email, get_db
from app.models.user_models import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/stats", response_model=Dict[str, Any])
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return lightweight inbox stats for dashboard widgets."""
    try:
        total = (
            await db.execute(select(func.count(Email.id)).where(Email.user_id == current_user.id))
        ).scalar() or 0
        unread = (
            await db.execute(
                select(func.count(Email.id)).where(
                    Email.user_id == current_user.id,
                    Email.is_read.is_(False),
                )
            )
        ).scalar() or 0
        flagged = (
            await db.execute(
                select(func.count(Email.id)).where(
                    Email.user_id == current_user.id,
                    Email.is_flagged.is_(True),
                )
            )
        ).scalar() or 0
        actionable = (
            await db.execute(
                select(func.count(Email.id)).where(
                    Email.user_id == current_user.id,
                    Email.ai_category == "To-Do",
                )
            )
        ).scalar() or 0

        return {
            "total_emails": int(total),
            "unread_emails": int(unread),
            "flagged_emails": int(flagged),
            "actionable_emails": int(actionable),
            "read_rate": round(((total - unread) / total) * 100, 2) if total else 0.0,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(exc)}")


@router.get("/productivity", response_model=Dict[str, Any])
async def get_productivity(
    period: str = "week",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a compact productivity summary by period."""
    try:
        period = (period or "week").lower()
        day_window = {"day": 1, "week": 7, "month": 30}.get(period, 7)
        start = datetime.utcnow() - timedelta(days=day_window)

        processed = (
            await db.execute(
                select(func.count(Email.id)).where(
                    Email.user_id == current_user.id,
                    Email.created_at >= start,
                )
            )
        ).scalar() or 0
        unread = (
            await db.execute(
                select(func.count(Email.id)).where(
                    Email.user_id == current_user.id,
                    Email.created_at >= start,
                    Email.is_read.is_(False),
                )
            )
        ).scalar() or 0
        todo = (
            await db.execute(
                select(func.count(Email.id)).where(
                    Email.user_id == current_user.id,
                    Email.created_at >= start,
                    Email.ai_category == "To-Do",
                )
            )
        ).scalar() or 0

        return {
            "period": period,
            "window_days": day_window,
            "emails_processed": int(processed),
            "emails_unread": int(unread),
            "todo_emails": int(todo),
            "daily_average_processed": round(processed / day_window, 2),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch productivity: {str(exc)}")
