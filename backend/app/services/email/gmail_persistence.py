"""Gmail persistence."""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.models.email_models import Email
from app.models.user_models import User
from app.services.email_attachment_integration import email_attachment_integration

from .gmail_message_parser import message_uid

try:
    from app.tasks.document_analysis_task import task_handler

    HAS_DOCUMENT_ANALYSIS = True
except ImportError:
    HAS_DOCUMENT_ANALYSIS = False


logger = logging.getLogger("app.services.gmail_ingestion_service")


class GmailEmailPersistence:
    def __init__(self, db):
        self.db = db

    async def store_emails(
        self,
        user_id: str,
        account_id: str,
        parsed_emails: List[Dict[str, Any]],
        gmail_service=None,
        message_ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Store parsed emails in the database and extract attachments.

        message_ids is retained for caller compatibility; each parsed record
        carries the authoritative Gmail ID, avoiding positional mismatches.

        Args:
            user_id: User ID
            account_id: Email account ID
            parsed_emails: List of parsed email dictionaries
            gmail_service: Optional Gmail API service for attachment download
            message_ids: Optional list of Gmail message IDs for attachment download

        Returns:
            List of stored email IDs
        """
        try:
            stored_ids = []
            analysis_jobs = []

            for parsed_email in parsed_emails:
                # Check if email already exists
                result = await self.db.execute(
                    select(Email).where(
                        Email.message_id == parsed_email["message_id"],
                        Email.user_id == user_id,
                        Email.account_id == account_id,
                    )
                )

                if result.scalar_one_or_none():
                    logger.debug(f"📧 Email {parsed_email['message_id']} already exists, skipping")
                    continue

                # Create email record
                email = Email(
                    user_id=user_id,
                    account_id=account_id,
                    message_id=parsed_email["message_id"],
                    uid=message_uid(parsed_email.get("uid"), parsed_email["received_at"]),
                    sender=parsed_email["sender"],
                    recipients=parsed_email.get("recipients", []),
                    cc=parsed_email.get("cc", []),
                    subject=parsed_email["subject"],
                    body_text=parsed_email.get("body_text", ""),
                    body_html=parsed_email.get("body_html", ""),
                    received_at=parsed_email["received_at"],
                    is_read=parsed_email.get("is_read", False),
                    is_flagged=parsed_email.get("is_flagged", False),
                    is_spam=parsed_email.get("is_spam", False),
                    is_draft=parsed_email.get("is_draft", False),
                    thread_id=parsed_email.get("thread_id"),
                    attachments=parsed_email.get("attachments", []),
                    processing_status="pending",  # Will be AI-processed next
                )

                self.db.add(email)
                await self.db.flush()  # Get email.id without committing

                # Process attachments if Gmail service is provided
                if gmail_service:
                    attachments_metadata = parsed_email.get("attachments", [])
                    gmail_message_id = parsed_email.get("external_id") or parsed_email["message_id"]

                    if attachments_metadata:
                        try:
                            downloaded = await email_attachment_integration.process_gmail_attachments(
                                gmail_service, gmail_message_id, email.id, user_id, attachments_metadata, self.db
                            )
                            logger.info(f"✅ Processed attachments for email: {email.id}")

                            # Trigger document analysis for attachments
                            if HAS_DOCUMENT_ANALYSIS and downloaded:
                                try:
                                    # Get user's plan for tiered analysis
                                    user_plan = "free"  # Default plan
                                    user_result = await self.db.execute(select(User).where(User.id == user_id))
                                    user = user_result.scalars().first()
                                    if user:
                                        if getattr(user, "subscription_status", "free") == "active":
                                            user_plan = getattr(user, "plan", "pro") or "pro"
                                        elif (getattr(user, "plan", "") or "").lower() in {
                                            "pro",
                                            "plus",
                                            "professional",
                                            "enterprise",
                                        }:
                                            user_plan = user.plan

                                    # Queue analysis for this email's attachments
                                    analysis_jobs.append((email.id, user_plan))
                                    logger.debug("Document analysis scheduled after commit")
                                except Exception as e:
                                    logger.warning(f"⚠️ Could not queue attachment analysis: {type(e).__name__}")
                                    # Don't fail email sync if analysis queueing fails
                        except Exception as e:
                            logger.error(f"⚠️ Failed to process attachments for {email.id}: {type(e).__name__}")
                            # Don't fail the whole email sync if attachments fail

                stored_ids.append(email.id)

            if stored_ids:
                await self.db.commit()
                logger.info(f"✅ Stored {len(stored_ids)} new emails with attachments")

            # A worker must not see an email/attachment before its transaction commits.
            for email_id, user_plan in analysis_jobs:
                try:
                    await task_handler.analyze_email_attachments(
                        email_id=email_id, user_id=user_id, user_plan=user_plan
                    )
                except Exception as exc:
                    logger.warning("Document analysis queue failed: %s", type(exc).__name__)
            return stored_ids

        except Exception as e:
            logger.error(f"❌ Error storing emails: {type(e).__name__}")
            await self.db.rollback()
            raise
