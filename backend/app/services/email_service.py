"""Public email service facade; existing callers retain the same methods."""

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.email.drafts import EmailDraftsMixin
from app.services.email.processing import EmailProcessingMixin
from app.services.email.queries import EmailQueriesMixin
from app.services.llm_service import LLMService
from app.services.mock_email_loader import MockEmailLoader
from app.services.prompt_service import PromptService

logger = structlog.get_logger(__name__)


class EmailService(EmailQueriesMixin, EmailProcessingMixin, EmailDraftsMixin):
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = LLMService()
        self.prompt_service = PromptService(db)
        self.mock_email_loader = MockEmailLoader()

    @staticmethod
    async def _rollback_after_failure(db: AsyncSession) -> None:
        """Keep the original database error as the caller-visible cause."""
        try:
            await db.rollback()
        except SQLAlchemyError:
            logger.exception("email_rollback_failed")
