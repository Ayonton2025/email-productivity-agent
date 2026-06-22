"""
Email-related background tasks
"""

from app.tasks.async_runner import run_async
from app.tasks.celery_app import celery_app as celery
from app.services.email_service import EmailService
from app.core.security import logger
from app.models.database import AsyncSessionLocal


@celery.task(bind=True, max_retries=3)
def process_new_emails(self):
    """Sync wrapper for processing newly received emails for AI analysis"""
    return run_async(_process_new_emails(self))


async def _process_new_emails(self):
    """Async implementation executed via asyncio.run by the sync wrapper"""
    try:
        async with AsyncSessionLocal() as session:
            # Create service at runtime (avoid import-time DB dependency)
            service = EmailService(session)
            pending_emails = await service.get_pending_emails(session)
            processed = 0
            
            for email in pending_emails:
                try:
                    await service.process_email_intelligence(email.id, session)
                    processed += 1
                except Exception as e:
                    logger.error(f"Error processing email {email.id}: {str(e)}")
                    continue
            
            logger.info(f"Processed {processed} emails")
            return {"processed": processed, "status": "success"}
    
    except Exception as exc:
        logger.error(f"process_new_emails failed: {str(exc)}")
        # Retry with exponential backoff
        self.retry(exc=exc, countdown=5 * (2 ** self.request.retries))


@celery.task(bind=True, max_retries=3)
def sync_email_accounts(self):
    """Sync wrapper for syncing email accounts from IMAP providers"""
    return run_async(_sync_email_accounts(self))


async def _sync_email_accounts(self):
    """Async implementation executed via asyncio.run by the sync wrapper"""
    try:
        async with AsyncSessionLocal() as session:
            # Create service at runtime
            service = EmailService(session)
            accounts = await service.get_active_email_accounts(session)
            synced = 0
            
            for account in accounts:
                try:
                    result = await service.sync_account(account.id, session)
                    if result.get("success"):
                        synced += 1
                except Exception as e:
                    logger.error(f"Error syncing account {account.id}: {str(e)}")
                    continue
            
            logger.info(f"Synced {synced} email accounts")
            return {"synced": synced, "status": "success"}
    
    except Exception as exc:
        logger.error(f"sync_email_accounts failed: {str(exc)}")
        self.retry(exc=exc, countdown=5 * (2 ** self.request.retries))
