"""
AI and intelligence processing background tasks
"""

from app.tasks.celery_app import celery_app as celery
from app.services.llm_orchestration_service import llm_service
from app.core.security import logger
from app.models.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.database import Email
from app.tasks.async_runner import run_async

@celery.task(bind=True, max_retries=2)
def process_email_intelligence(self):
    """Synchronous Celery wrapper for processing email intelligence."""
    return run_async(_process_email_intelligence(self))

async def _process_email_intelligence(self):
    """Actual async implementation that queries emails and calls LLM services."""
    try:
        async with AsyncSessionLocal() as session:
            # Get emails with processing_status = "pending"
            result = await session.execute(
                select(Email).where(Email.processing_status == "pending").limit(100)
            )
            emails = result.scalars().all()

            processed = 0
            for email in emails:
                try:
                    # Classify email
                    classification = await llm_service.classify_email(
                        sender=email.sender,
                        subject=email.subject or "",
                        body=email.body_text or "",
                        tenant_id=email.user_id,  # Use user_id as tenant for now
                        session=session
                    )

                    # Extract actions
                    actions = await llm_service.extract_actions(
                        email_body=email.body_text or "",
                        user_id=email.user_id,
                        session=session
                    )

                    # Analyze sentiment
                    sentiment = await llm_service.analyze_sentiment(
                        email_body=f"{email.subject}\n{email.body_text}",
                        user_id=email.user_id,
                        session=session
                    )

                    # Update email with results (be defensive about returned shapes)
                    email.ai_category = (classification.get("category") if isinstance(classification, dict) else None) or "FYI"
                    email.action_items = (actions.get("actions") if isinstance(actions, dict) else []) or []
                    email.sentiment = (sentiment.get("sentiment") if isinstance(sentiment, dict) else None) or "neutral"
                    email.processing_status = "completed"

                    processed += 1

                except Exception as e:
                    logger.error(f"Error processing email intelligence for {email.id}: {str(e)}")
                    email.processing_status = "failed"
                    continue

            await session.commit()
            logger.info(f"Processed intelligence for {processed} emails")
            return {"processed": processed, "status": "success"}

    except Exception as exc:
        logger.error(f"process_email_intelligence failed: {str(exc)}")
        # Retry via celery if available
        try:
            self.retry(exc=exc, countdown=10)
        except Exception:
            raise


@celery.task(bind=True)
def summarize_email_thread(self, thread_id: str):
    """Synchronous Celery wrapper to summarize an email thread."""
    return run_async(_summarize_email_thread(self, thread_id))

async def _summarize_email_thread(self, thread_id: str):
    """Async implementation that builds thread content and calls LLM summarizer."""
    try:
        async with AsyncSessionLocal() as session:
            # Get all emails in thread
            result = await session.execute(
                select(Email).where(Email.thread_id == thread_id).order_by(Email.received_at)
            )
            emails = result.scalars().all()

            if not emails:
                return {"success": False, "message": "No emails found in thread"}

            # Build thread content
            thread_content = "\n\n---\n\n".join([
                f"From: {email.sender}\nTo: {', '.join(email.recipients)}\nSubject: {email.subject}\n\n{email.body_text}"
                for email in emails
            ])

            # Generate summary
            summary = await llm_service.summarize_thread(
                thread_body=thread_content,
                user_id=emails[0].user_id,
                session=session
            )

            # Store summary in first email
            emails[0].ai_summary = (summary if isinstance(summary, str) else (summary.get("summary") if isinstance(summary, dict) else None))
            await session.commit()

            return {"success": True, "summary": summary}

    except Exception as exc:
        logger.error(f"summarize_email_thread failed: {str(exc)}")
        raise
