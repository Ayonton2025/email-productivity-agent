"""Outbound provider adapters."""

from .base import EmailProviderAdapter
from .gmail import GmailProviderAdapter
from .outlook import OutlookProviderAdapter

__all__ = ["EmailProviderAdapter", "GmailProviderAdapter", "OutlookProviderAdapter"]
