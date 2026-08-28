"""Email ingestion coordinator."""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Email
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService

from .duplicate_checker import DuplicateCheckerMixin
from .intelligence import EmailIntelligenceMixin
from .mock_data import MockEmailCatalogMixin
from .repository import EmailRepositoryMixin
from .validators import validate_email_payload

logger = logging.getLogger(__name__)


class EmailService(
    DuplicateCheckerMixin,
    MockEmailCatalogMixin,
    EmailRepositoryMixin,
    EmailIntelligenceMixin,
):
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = LLMService()
        self.prompt_service = PromptService(db)

    async def load_mock_emails(self, user_id: str) -> List[Dict[str, Any]]:
        """Load mock emails from JSON file into database for a specific user"""
        try:
            logger.info(f"📧 [EmailService] Loading mock emails for user: {user_id}")

            # First, check if user already has emails to avoid duplicates - MORE ROBUST CHECK
            existing_emails = await self.get_user_emails(user_id)
            if (
                existing_emails and len(existing_emails) >= 5
            ):  # Changed from 0 to 5 to be more conservative
                logger.info(
                    f"📧 [EmailService] User already has {len(existing_emails)} emails, skipping mock load"
                )
                return existing_emails

            # Try multiple possible paths for the mock data file
            possible_paths = [
                "data/mock_inbox.json",
                "./data/mock_inbox.json",
                "backend/data/mock_inbox.json",
                "./backend/data/mock_inbox.json",
                "../data/mock_inbox.json",
                "./../data/mock_inbox.json",
            ]

            mock_emails = []
            file_found = False

            for file_path in possible_paths:
                if os.path.exists(file_path):
                    logger.info(f"✅ [EmailService] Found mock data file: {file_path}")
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            mock_emails = json.load(f)
                        file_found = True
                        break
                    except Exception as e:
                        logger.error(f"❌ [EmailService] Error reading {file_path}: {e}")
                        continue

            if not file_found:
                logger.error(
                    f"❌ [EmailService] Mock data file not found in any location. Tried: {possible_paths}"
                )
                # Use hardcoded mock data as fallback - WITH ALL 20 EMAILS
                mock_emails = self._get_hardcoded_mock_emails()

            logger.info(f"📧 [EmailService] Found {len(mock_emails)} mock emails to load")

            # CRITICAL FIX: Check for duplicates by email content before loading
            processed_emails = []
            duplicate_count = 0

            for email_data in mock_emails:
                # Check if similar email already exists for this user
                existing_similar = await self._check_duplicate_email(user_id, email_data)

                if existing_similar:
                    duplicate_count += 1
                    logger.info(
                        f"⚠️ [EmailService] Skipping duplicate email: {email_data.get('subject', 'No Subject')}"
                    )
                    processed_emails.append(existing_similar)
                    continue

                # Ensure each email has required fields for processing
                if "category" not in email_data:
                    email_data["category"] = "Uncategorized"
                if "priority" not in email_data:
                    email_data["priority"] = "medium"
                if "is_read" not in email_data:
                    email_data["is_read"] = False
                if "is_archived" not in email_data:
                    email_data["is_archived"] = False
                if "is_starred" not in email_data:
                    email_data["is_starred"] = False
                if "action_items" not in email_data:
                    email_data["action_items"] = []
                if "summary" not in email_data:
                    email_data["summary"] = ""

                processed_email = await self.process_single_email(email_data, user_id)
                processed_emails.append(processed_email)

            if duplicate_count > 0:
                logger.info(f"⚠️ [EmailService] Skipped {duplicate_count} duplicate emails")

            logger.info(
                f"✅ [EmailService] Successfully loaded {len(processed_emails)} mock emails"
            )
            return processed_emails

        except Exception as e:
            logger.error(f"❌ [EmailService] Error loading mock emails: {e}")
            import traceback

            logger.info(f"❌ [EmailService] Stack trace: {traceback.format_exc()}")
            return []

    async def process_email(
        self, email_data: Dict[str, Any], user_id: str = None
    ) -> Dict[str, Any]:
        """Validate, deduplicate, and persist one inbound email."""
        normalized = validate_email_payload(email_data)
        duplicate = await self._check_duplicate_email(user_id, normalized)
        if duplicate:
            return duplicate
        return await self.process_single_email(normalized, user_id)

    async def process_single_email(
        self, email_data: Dict[str, Any], user_id: str = None
    ) -> Dict[str, Any]:
        """Process a single email and save to database"""
        try:
            logger.info(
                f"📧 [EmailService] Processing email: {email_data.get('subject', 'No Subject')}"
            )

            # Handle timestamp conversion
            raw_ts = email_data.get("timestamp", datetime.utcnow().isoformat())
            if isinstance(raw_ts, str) and raw_ts.endswith("Z"):
                raw_ts = raw_ts.replace("Z", "+00:00")
            timestamp = datetime.fromisoformat(raw_ts)

            # Use existing AI-generated data or generate new
            category = email_data.get("category", "Uncategorized")
            action_items = email_data.get("action_items", [])
            summary = email_data.get("summary", "")

            # If we have an LLM service and want to regenerate AI data
            if self.llm_service and not category:
                try:
                    categorization_prompt = await self.prompt_service.get_active_prompt(
                        "categorization"
                    )
                    action_prompt = await self.prompt_service.get_active_prompt("action_extraction")
                    summary_prompt = await self.prompt_service.get_active_prompt("summary")

                    email_content = f"From: {email_data.get('sender', '')}\nSubject: {email_data.get('subject', '')}\nBody: {email_data.get('body', '')}"

                    # Run AI processing in parallel
                    tasks = [
                        self.llm_service.process_prompt(
                            categorization_prompt.template, email_content
                        ),
                        self.llm_service.process_prompt(action_prompt.template, email_content),
                        self.llm_service.process_prompt(summary_prompt.template, email_content),
                    ]

                    category, action_items_raw, summary = await asyncio.gather(*tasks)

                    # Parse action items
                    try:
                        if action_items_raw.strip().startswith(
                            "{"
                        ) or action_items_raw.strip().startswith("["):
                            action_items = json.loads(action_items_raw)
                        else:
                            action_items = [{"task": action_items_raw, "deadline": None}]
                    except:
                        action_items = [{"task": action_items_raw, "deadline": None}]

                except Exception as e:
                    logger.error(f"⚠️ [EmailService] AI processing failed, using provided data: {e}")

            # Create email record
            email = Email(
                user_id=user_id,
                sender=email_data.get("sender", ""),
                subject=email_data.get("subject", ""),
                body=email_data.get("body", ""),
                timestamp=timestamp,
                category=category,
                priority=email_data.get("priority", "medium"),
                is_read=email_data.get("is_read", False),
                is_archived=email_data.get("is_archived", False),
                is_starred=email_data.get("is_starred", False),
                action_items=action_items,
                summary=summary,
                email_metadata=email_data.get("metadata", {}),
            )

            self.db.add(email)
            await self.db.commit()
            await self.db.refresh(email)

            logger.info(f"✅ [EmailService] Email saved with ID: {email.id}")
            return email.to_dict()

        except Exception as e:
            logger.error(f"❌ [EmailService] Error processing single email: {e}")
            import traceback

            logger.info(f"❌ [EmailService] Stack trace: {traceback.format_exc()}")
            # Return the original data as fallback
            return email_data
