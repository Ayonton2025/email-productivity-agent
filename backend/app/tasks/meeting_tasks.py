"""
Meeting intelligence background tasks.
"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import and_, select

from app.tasks.celery_app import celery_app as celery
from app.tasks.async_runner import run_async
from app.models.database import AsyncSessionLocal
from app.models.meeting_models import MeetingRecord


@celery.task(bind=True, max_retries=2)
def meeting_followup_task(self):
    return run_async(_meeting_followup_task(self))


async def _meeting_followup_task(self):
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MeetingRecord).where(and_(MeetingRecord.status == "scheduled"))
            )
            meetings = list(result.scalars().all())
            updated = 0
            for m in meetings:
                if not m.post_summary:
                    m.post_summary = (
                        f"Automated follow-up: Meeting '{m.title}' summary pending. "
                        "Please confirm decisions, owners, and due dates."
                    )
                    m.updated_at = datetime.utcnow()
                    updated += 1
            await session.commit()
            return {"success": True, "updated": updated}
    except Exception as exc:
        try:
            self.retry(exc=exc, countdown=300)
        except Exception:
            raise
