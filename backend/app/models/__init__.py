"""Canonical model exports and explicit domain registration."""

from importlib import import_module

from app.models.base import Base
from app.models.document_models import DocumentAnalysis, EmailAttachment
from app.models.email_models import Email, UserEmailAccount
from app.models.user_models import User

__all__ = ["Base", "User", "Email", "UserEmailAccount", "EmailAttachment", "DocumentAnalysis", "register_models"]


def register_models():
    """Load every domain mapping before schema initialization."""
    for name in (
        "agent_models",
        "auto_reply_models",
        "billing_models",
        "campaign_models",
        "collaboration_models",
        "commitment_models",
        "contact_models",
        "document_models",
        "email_models",
        "email_provider_models",
        "hosted_email_models",
        "knowledge_models",
        "llm_provider_models",
        "meeting_models",
        "offline_models",
        "persona_models",
        "phase1_models",
        "prompt_models",
        "provider_models",
        "security_models",
        "system_models",
        "task_models",
        "timeline_models",
        "user_models",
        "workflow_models",
    ):
        import_module(f"app.models.{name}")
