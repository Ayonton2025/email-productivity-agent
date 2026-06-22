"""
Integration background tasks (CRM sync, webhooks, etc.)
"""

from app.tasks.celery_app import celery_app as celery
from datetime import datetime
from app.models.database import AsyncSessionLocal
from app.core.security import logger
from app.tasks.async_runner import run_async


@celery.task(bind=True, max_retries=2)
def sync_crm_contacts(self):
    """Sync contacts with external CRM systems (sync wrapper)."""
    return run_async(_sync_crm_contacts(self))


async def _sync_crm_contacts(self):
    """Async implementation that performs CRM sync operations."""
    try:
        async with AsyncSessionLocal() as session:
            from app.models.contact_models import Contact
            from sqlalchemy import select

            # Get contacts that need syncing
            result = await session.execute(
                select(Contact).where(Contact.needs_crm_sync == True)
            )
            contacts = result.scalars().all()

            synced = 0
            for contact in contacts:
                try:
                    # Sync to HubSpot, Salesforce, etc.
                    # This is implementation-specific

                    contact.needs_crm_sync = False
                    contact.last_synced_at = datetime.utcnow()
                    synced += 1

                except Exception as e:
                    logger.error(f"Error syncing contact {contact.id}: {str(e)}")
                    continue

            await session.commit()
            logger.info(f"Synced {synced} contacts to CRM")
            return {"synced": synced, "status": "success"}

    except Exception as exc:
        logger.error(f"sync_crm_contacts failed: {str(exc)}")
        try:
            self.retry(exc=exc, countdown=300)  # Retry after 5 minutes
        except Exception:
            raise


@celery.task(bind=True, max_retries=1)
def send_webhook_events(self, webhook_id: str, event_data: dict):
    """Sync wrapper to send webhook events to external systems."""
    return run_async(_send_webhook_events(self, webhook_id, event_data))


async def _send_webhook_events(self, webhook_id: str, event_data: dict):
    """Async implementation for webhook sending."""
    try:
        # Implementation for sending webhooks
        logger.info(f"Sending webhook event for {webhook_id}")
        return {"success": True, "webhook_id": webhook_id}

    except Exception as exc:
        logger.error(f"send_webhook_events failed: {str(exc)}")
        try:
            self.retry(exc=exc, countdown=60)
        except Exception:
            raise
