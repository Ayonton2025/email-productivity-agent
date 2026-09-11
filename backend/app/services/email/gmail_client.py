"""Gmail client."""

import logging
from datetime import datetime
from typing import Any, Dict, List

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.models.email_models import UserEmailAccount

logger = logging.getLogger("app.services.gmail_ingestion_service")


class GmailClient:
    def __init__(self, db):
        self.db = db

    def build_gmail_service(self, access_token: str):
        """Build Gmail service with OAuth credentials"""
        credentials = Credentials(token=access_token)
        return build("gmail", "v1", credentials=credentials)

    async def fetch_last_n_emails(self, service, n: int = 50, query: str = "") -> List[Dict[str, Any]]:
        """
        Fetch the last N emails from Gmail.

        Args:
            service: Gmail API service
            n: Number of emails to fetch
            query: Gmail search query (optional)

        Returns:
            List of parsed email dictionaries
        """
        try:
            logger.info(f"📧 Fetching last {n} emails from Gmail...")

            # Get message IDs
            results = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    maxResults=min(n, 50),  # Gmail API max is 100, we use 50 per request
                    q=query if query else None,
                )
                .execute()
            )

            messages = results.get("messages", [])
            logger.info(f"📧 Found {len(messages)} message IDs")

            if not messages:
                logger.warning("⚠️ No messages found")
                return []

            # Fetch full message details
            full_emails = []
            for msg in messages:
                try:
                    full = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
                    full_emails.append(full)
                except Exception as e:
                    logger.error(f"❌ Failed to fetch message {msg['id']}: {type(e).__name__}")
                    continue

            logger.info(f"✅ Successfully fetched {len(full_emails)} full messages")
            return full_emails

        except Exception as e:
            logger.error(f"❌ Error fetching emails: {type(e).__name__}")
            raise

    async def setup_gmail_push(self, service, account: UserEmailAccount, topic_name: str) -> bool:
        """
        Setup Gmail push notifications via Google Pub/Sub.

        Args:
            service: Gmail API service
            account: UserEmailAccount record
            topic_name: Google Pub/Sub topic name

        Returns:
            True if successful
        """
        try:
            logger.info(f"📢 Setting up Gmail push notifications for {account.id}")

            response = (
                service.users()
                .watch(
                    userId="me",
                    body={
                        "topicName": topic_name,
                        "labelIds": ["INBOX"],  # Watch INBOX label
                    },
                )
                .execute()
            )

            account.history_id = response.get("historyId")
            account.watch_expiration = datetime.utcfromtimestamp(int(response.get("expiration", 0)) / 1000)

            await self.db.commit()
            logger.info(f"✅ Gmail watch enabled. History ID: {account.history_id}")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to setup Gmail push: {type(e).__name__}")
            return False
