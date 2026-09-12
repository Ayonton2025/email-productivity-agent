"""Compatibility facade coordinating Gmail ingestion responsibilities.

OAuth bootstrap, multi-provider sync and webhooks keep the same service API.
Provider access, parsing, persistence and AI processing live in email modules.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_models import UserEmailAccount
from app.services.email.gmail_client import GmailClient
from app.services.email.gmail_html import GmailHtmlProcessor
from app.services.email.gmail_message_parser import GmailMessageParser
from app.services.email.gmail_persistence import GmailEmailPersistence
from app.services.email.gmail_processing import GmailAIProcessor
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService


class GmailIngestionService:
    """Coordinate ingestion while retaining the existing caller interface."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = LLMService()
        self.prompt_service = PromptService(db)

    def build_gmail_service(self, access_token: str):
        return GmailClient(self.db).build_gmail_service(access_token)

    async def fetch_last_n_emails(self, service, n: int = 50, query: str = "") -> List[Dict[str, Any]]:
        return await GmailClient(self.db).fetch_last_n_emails(service, n, query)

    def parse_gmail_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        return GmailMessageParser().parse_gmail_message(message)

    def _extract_body(self, payload: Dict[str, Any]) -> tuple:
        return GmailMessageParser()._extract_body(payload)

    def _html_to_text(self, html: str) -> str:
        return GmailMessageParser()._html_to_text(html)

    def _extract_attachments(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        return GmailMessageParser()._extract_attachments(payload)

    def _sanitize_html(self, html: str) -> str:
        return GmailHtmlProcessor()._sanitize_html(html)

    def _resolve_cid_images(self, html: str, attachments: List[Dict[str, Any]]) -> str:
        return GmailHtmlProcessor()._resolve_cid_images(html, attachments)

    async def store_emails(
        self,
        user_id: str,
        account_id: str,
        parsed_emails: List[Dict[str, Any]],
        gmail_service=None,
        message_ids: Optional[List[str]] = None,
    ) -> List[str]:
        return await GmailEmailPersistence(self.db).store_emails(
            user_id, account_id, parsed_emails, gmail_service, message_ids
        )

    async def process_emails_with_ai(self, email_ids: List[str]) -> int:
        return await GmailAIProcessor(self.db, self.llm_service, self.prompt_service).process_emails_with_ai(email_ids)

    async def setup_gmail_push(self, service, account: UserEmailAccount, topic_name: str) -> bool:
        return await GmailClient(self.db).setup_gmail_push(service, account, topic_name)
