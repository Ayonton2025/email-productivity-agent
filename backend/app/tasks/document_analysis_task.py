"""
Background tasks for document and attachment analysis
Integrates with Celery for asynchronous processing
"""
import os
import logging
import asyncio
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import select
from dotenv import load_dotenv

load_dotenv()

from app.models.database import AsyncSessionLocal
from app.models.document_models import EmailAttachment, DocumentAnalysis
from app.models.user_models import User
from app.services.document_analysis_service import DocumentAnalysisBackgroundTask
from app.core.security import logger

# Try to import Celery, fall back to simple async handler if not available
try:
    from celery import Celery
    
    # Initialize Celery app
    celery_app = Celery(
        'email_productivity_agent',
        broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
        backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    )
    
    # Configuration
    celery_app.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,  # 30 minutes hard limit
        task_soft_time_limit=25 * 60,  # 25 minutes soft limit
        worker_prefetch_multiplier=4,
        worker_max_tasks_per_child=1000,
    )
    
    CELERY_AVAILABLE = True
    logger.info("✅ Celery initialized for document analysis tasks")
    
except ImportError:
    CELERY_AVAILABLE = False
    celery_app = None
    logger.warning("⚠️  Celery not available, background tasks will use async handler")


class DocumentAnalysisTaskHandler:
    """
    Handles document analysis tasks with Celery or async fallback
    """
    
    def __init__(self):
        self.analysis_task = DocumentAnalysisBackgroundTask()
        self.celery_enabled = CELERY_AVAILABLE
    
    async def analyze_attachment(
        self,
        attachment_id: str,
        user_id: str,
        user_plan: str = "free"
    ):
        """
        Queue or process attachment analysis
        """
        if self.celery_enabled:
            # Queue with Celery
            analyze_attachment_task.apply_async(
                args=[attachment_id, user_id, user_plan],
                queue='document_analysis',
                priority=5
            )
            logger.info(f"📊 Queued Celery task for attachment: {attachment_id}")
        else:
            # Process immediately with async
            async with AsyncSessionLocal() as session:
                try:
                    await self.analysis_task.process_attachment_analysis(
                        session=session,
                        attachment_id=attachment_id,
                        user_id=user_id,
                        user_plan=user_plan
                    )
                    logger.info(f"✅ Analyzed attachment: {attachment_id}")
                except Exception as e:
                    logger.error(f"❌ Error analyzing attachment {attachment_id}: {e}")
    
    async def analyze_email_attachments(
        self,
        email_id: str,
        user_id: str,
        user_plan: str = "free"
    ):
        """
        Queue or process all attachments for an email
        """
        async with AsyncSessionLocal() as session:
            try:
                # Get all attachments for email
                from app.models.database import Email
                
                email = await session.get(Email, email_id)
                if not email:
                    logger.warning(f"Email not found: {email_id}")
                    return
                
                stmt = select(EmailAttachment).where(
                    EmailAttachment.email_id == email_id
                )
                result = await session.execute(stmt)
                attachments = result.scalars().all()
                
                if not attachments:
                    logger.info(f"No attachments found for email: {email_id}")
                    return
                
                # Queue/process each attachment
                for attachment in attachments:
                    await self.analyze_attachment(
                        attachment_id=attachment.id,
                        user_id=user_id,
                        user_plan=user_plan
                    )
                
                logger.info(f"📊 Queued analysis for {len(attachments)} attachments")
                
            except Exception as e:
                logger.error(f"❌ Error queuing email attachments: {e}")


# Celery task definitions (if available)
if CELERY_AVAILABLE:
    
    @celery_app.task(
        name='document_analysis.analyze_attachment',
        bind=True,
        retry_kwargs={'max_retries': 3},
        autoretry_for=(Exception,),
        retry_backoff=True
    )
    def analyze_attachment_task(
        self,
        attachment_id: str,
        user_id: str,
        user_plan: str = "free"
    ):
        """
        Celery task: Analyze a single attachment
        """
        try:
            logger.info(f"🔄 Starting analysis task for attachment: {attachment_id}")
            
            # Run async function in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def run_analysis():
                async with AsyncSessionLocal() as session:
                    analysis_handler = DocumentAnalysisBackgroundTask()
                    return await analysis_handler.process_attachment_analysis(
                        session=session,
                        attachment_id=attachment_id,
                        user_id=user_id,
                        user_plan=user_plan
                    )
            
            result = loop.run_until_complete(run_analysis())
            loop.close()
            
            logger.info(f"✅ Analysis completed for attachment: {attachment_id}")
            return {
                "status": "success",
                "attachment_id": attachment_id,
                "analysis_id": result.id if result else None
            }
            
        except Exception as e:
            logger.error(f"❌ Task failed for attachment {attachment_id}: {e}")
            # Celery will retry based on autoretry_for config
            raise
    
    
    @celery_app.task(
        name='document_analysis.analyze_email_attachments',
        bind=True,
        retry_kwargs={'max_retries': 2},
        autoretry_for=(Exception,),
        retry_backoff=True
    )
    def analyze_email_attachments_task(
        self,
        email_id: str,
        user_id: str,
        user_plan: str = "free"
    ):
        """
        Celery task: Analyze all attachments in an email
        """
        try:
            logger.info(f"🔄 Starting batch analysis for email: {email_id}")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def run_batch():
                async with AsyncSessionLocal() as session:
                    from app.models.database import Email
                    
                    # Get all attachments
                    email = await session.get(Email, email_id)
                    if not email:
                        return 0
                    
                    stmt = select(EmailAttachment).where(
                        EmailAttachment.email_id == email_id
                    )
                    result = await session.execute(stmt)
                    attachments = result.scalars().all()
                    
                    # Process each attachment
                    analysis_handler = DocumentAnalysisBackgroundTask()
                    processed = 0
                    
                    for attachment in attachments:
                        try:
                            await analysis_handler.process_attachment_analysis(
                                session=session,
                                attachment_id=attachment.id,
                                user_id=user_id,
                                user_plan=user_plan
                            )
                            processed += 1
                        except Exception as e:
                            logger.error(f"Error analyzing attachment {attachment.id}: {e}")
                            # Continue with next attachment
                    
                    return processed
            
            count = loop.run_until_complete(run_batch())
            loop.close()
            
            logger.info(f"✅ Batch analysis completed: {count} attachments processed")
            return {
                "status": "success",
                "email_id": email_id,
                "attachments_processed": count
            }
            
        except Exception as e:
            logger.error(f"❌ Batch task failed for email {email_id}: {e}")
            raise


# Global task handler instance
task_handler = DocumentAnalysisTaskHandler()


# Health check task for scheduled monitoring
if CELERY_AVAILABLE:
    @celery_app.task(name='document_analysis.health_check')
    def health_check_task():
        """
        Periodic health check for document analysis system
        """
        try:
            logger.debug("🏥 Document analysis system health check")
            return {
                "status": "healthy",
                "celery_enabled": True
            }
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    
    # Configure beat schedule for periodic tasks (if using Celery Beat)
    from celery.schedules import crontab
    
    celery_app.conf.beat_schedule = {
        'health-check-document-analysis': {
            'task': 'document_analysis.health_check',
            'schedule': crontab(minute='*/5'),  # Every 5 minutes
        },
    }
    
    logger.info("✅ Celery Beat schedule configured for document analysis")
