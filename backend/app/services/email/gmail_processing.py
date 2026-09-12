"""Gmail processing."""

import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.email_models import Email

logger = logging.getLogger("app.services.gmail_ingestion_service")


class GmailAIProcessor:
    def __init__(self, db, llm_service, prompt_service):
        self.db = db
        self.llm_service = llm_service
        self.prompt_service = prompt_service

    async def process_emails_with_ai(self, email_ids: List[str]) -> int:
        """
        Run AI categorization on emails.

        Args:
            email_ids: List of email IDs to process

        Returns:
            Number of successfully processed emails
        """
        try:
            processed_count = 0

            # Get active prompts
            categorization_prompt = await self.prompt_service.get_active_prompt("categorization")
            summary_prompt = await self.prompt_service.get_active_prompt("summary")

            if not categorization_prompt or not summary_prompt:
                logger.warning("⚠️ AI prompts not found, skipping AI processing")
                return 0

            for email_id in email_ids:
                email = None
                try:
                    # Fetch email
                    result = await self.db.execute(select(Email).where(Email.id == email_id))
                    email = result.scalar_one_or_none()

                    if not email:
                        logger.warning(f"⚠️ Email {email_id} not found")
                        continue

                    # Skip if already processed
                    if email.processing_status == "completed":
                        continue

                    # Prepare content for AI
                    email_content = (
                        f"From: {email.sender}\nSubject: {email.subject}\nBody: {email.body_text or email.body_html}"
                    )

                    # Categorize
                    try:
                        category = await self.llm_service.process_prompt(
                            categorization_prompt.template, email_content, max_tokens=50
                        )
                        email.ai_category = category.strip()
                    except Exception as e:
                        logger.error(f"❌ Categorization failed for {email_id}: {type(e).__name__}")
                        email.ai_category = "Uncategorized"

                    # Summarize
                    try:
                        summary = await self.llm_service.process_prompt(
                            summary_prompt.template, email_content, max_tokens=150
                        )
                        email.ai_summary = summary.strip()
                    except Exception as e:
                        logger.error(f"❌ Summarization failed for {email_id}: {type(e).__name__}")

                    email.processing_status = "completed"
                    processed_count += 1
                    logger.debug(f"✅ Processed email {email_id}")

                except SQLAlchemyError:
                    raise
                except Exception as e:
                    logger.error(f"❌ Error processing email {email_id}: {type(e).__name__}")
                    if email is not None:
                        email.processing_status = "failed"
                    continue

            if processed_count > 0:
                await self.db.commit()
                logger.info(f"✅ AI processing completed for {processed_count} emails")

            return processed_count

        except Exception as e:
            logger.error(f"❌ Error in AI processing pipeline: {type(e).__name__}")
            await self.db.rollback()
            raise
