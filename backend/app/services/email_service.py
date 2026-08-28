"""Compatibility facade for the decomposed email service.

New code should import from :mod:`app.services.email`.
"""

from app.services.email import EmailService, EmailValidationError, validate_email_payload

__all__ = ["EmailService", "EmailValidationError", "validate_email_payload"]
