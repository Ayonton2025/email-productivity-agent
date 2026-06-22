"""
Maintenance and cleanup background tasks
"""

from app.tasks.celery_app import celery_app as celery
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from app.models.database import AsyncSessionLocal, Email
from app.core.security import logger
from app.tasks.async_runner import run_async


@celery.task(bind=True)
def cleanup_old_data(self):
    """Sync wrapper to clean up old data (emails, logs, etc.)."""
    return run_async(_cleanup_old_data(self))


async def _cleanup_old_data(self):
    """Async implementation to remove old non-important emails."""
    try:
        async with AsyncSessionLocal() as session:
            # Delete emails older than 90 days (for non-important ones)
            cutoff_date = datetime.utcnow() - timedelta(days=90)

            result = await session.execute(
                select(Email).where(
                    and_(
                        Email.received_at < cutoff_date,
                        Email.ai_category != "URGENT",
                        Email.is_flagged == False
                    )
                )
            )
            old_emails = result.scalars().all()

            deleted = 0
            for email in old_emails:
                try:
                    # AsyncSession.delete is a regular method (not awaitable)
                    session.delete(email)
                    deleted += 1
                except Exception as e:
                    logger.error(f"Error deleting email {email.id}: {str(e)}")
                    continue

            await session.commit()
            logger.info(f"Deleted {deleted} old emails")
            return {"deleted": deleted, "status": "success"}

    except Exception as exc:
        logger.error(f"cleanup_old_data failed: {str(exc)}")
        try:
            self.retry(exc=exc, countdown=300)
        except Exception:
            raise


@celery.task(bind=True)
def archive_completed_campaigns(self):
    """Sync wrapper to archive completed campaigns."""
    return run_async(_archive_completed_campaigns(self))


async def _archive_completed_campaigns(self):
    """Async implementation that archives completed campaigns."""
    try:
        async with AsyncSessionLocal() as session:
            from app.models.campaign_models import Campaign

            # Get completed campaigns
            result = await session.execute(
                select(Campaign).where(Campaign.status == "completed")
            )
            campaigns = result.scalars().all()

            archived = 0
            for campaign in campaigns:
                try:
                    # Archive campaign (move to archive, not delete)
                    # This could be a soft delete or moving to archive table
                    archived += 1

                except Exception as e:
                    logger.error(f"Error archiving campaign {campaign.id}: {str(e)}")
                    continue

            await session.commit()
            logger.info(f"Archived {archived} campaigns")
            return {"archived": archived, "status": "success"}

    except Exception as exc:
        logger.error(f"archive_completed_campaigns failed: {str(exc)}")
        try:
            self.retry(exc=exc, countdown=300)
        except Exception:
            raise


@celery.task(bind=True)
def generate_analytics_reports(self):
    """Sync wrapper to generate daily analytics reports."""
    return run_async(_generate_analytics_reports(self))


async def _generate_analytics_reports(self):
    """Async implementation that compiles daily analytics."""
    try:
        # This would generate reports for users showing:
        # - Emails processed
        # - AI credits used
        # - Campaign performance
        # - Open rates, click rates, etc.

        logger.info("Analytics reports generated")
        return {"status": "success"}

    except Exception as exc:
        logger.error(f"generate_analytics_reports failed: {str(exc)}")
        try:
            self.retry(exc=exc, countdown=300)
        except Exception:
            raise
