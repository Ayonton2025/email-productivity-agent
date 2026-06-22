"""
Phase 1 background tasks:
- Daily briefing generation
- Auto follow-up processing
"""

from app.tasks.async_runner import run_async
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.security import logger
from app.models.database import AsyncSessionLocal, User
from app.models.phase1_models import UserDigestPreference
from app.services.daily_briefing_service import DailyBriefingService
from app.services.follow_up_service import FollowUpService
from app.tasks.celery_app import celery_app as celery


@celery.task(bind=True, max_retries=1)
def generate_daily_briefings_for_due_users(self):
    return run_async(_generate_daily_briefings_for_due_users(self))


async def _generate_daily_briefings_for_due_users(self):
    briefing_service = DailyBriefingService()
    generated = 0

    try:
        async with AsyncSessionLocal() as session:
            users_result = await session.execute(select(User.id))
            user_ids = [row[0] for row in users_result.all()]

            for user_id in user_ids:
                try:
                    pref_result = await session.execute(
                        select(UserDigestPreference).where(UserDigestPreference.user_id == user_id)
                    )
                    pref = pref_result.scalar_one_or_none()
                    if not pref:
                        pref = await briefing_service.get_or_create_preference(user_id=user_id, session=session)

                    if not pref.enabled:
                        continue

                    tz = ZoneInfo(pref.timezone or "UTC")
                    local_now = datetime.now(tz)
                    if int(local_now.hour) != int(pref.send_hour):
                        continue

                    await briefing_service.generate_daily_briefing(
                        user_id=user_id,
                        session=session,
                        target_date=local_now.date(),
                        force_regenerate=False,
                    )
                    generated += 1
                except Exception as user_error:
                    logger.error("Daily briefing dispatch failed for user %s: %s", user_id, str(user_error))

            await session.commit()
            return {"success": True, "generated": generated}
    except Exception as exc:
        logger.error("generate_daily_briefings_for_due_users failed: %s", str(exc))
        try:
            self.retry(exc=exc, countdown=60)
        except Exception:
            raise


@celery.task(bind=True, max_retries=2)
def process_auto_followups(self):
    return run_async(_process_auto_followups(self))


async def _process_auto_followups(self):
    followup_service = FollowUpService()
    try:
        async with AsyncSessionLocal() as session:
            stats = await followup_service.process_due_followups(session=session, limit=150)
            await session.commit()
            return {"success": True, "stats": stats}
    except Exception as exc:
        logger.error("process_auto_followups failed: %s", str(exc))
        try:
            self.retry(exc=exc, countdown=30)
        except Exception:
            raise
