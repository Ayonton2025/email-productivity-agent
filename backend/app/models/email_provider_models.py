"""Compatibility exports for the former duplicate provider registry."""

from app.models.base import Base
from app.models.email_models import Email
from app.models.provider_models import EmailProviderConfig, SyncHistory

__all__ = ["Base", "Email", "EmailProviderConfig", "SyncHistory"]
