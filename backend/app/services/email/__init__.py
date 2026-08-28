"""Public email-service package."""

from .service import EmailService
from .validators import EmailValidationError, validate_email_payload

__all__ = ["EmailService", "EmailValidationError", "validate_email_payload"]
