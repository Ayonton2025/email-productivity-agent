"""Validation at the email-processing boundary."""

import re
from typing import Any, Dict

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class EmailValidationError(ValueError):
    """Raised when an email payload cannot safely be processed."""


def validate_email_address(value: str, field: str = "email") -> str:
    normalized = (value or "").strip().lower()
    if not EMAIL_PATTERN.fullmatch(normalized):
        raise EmailValidationError(f"Invalid {field} address")
    return normalized


def validate_email_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return a normalized copy of an inbound email payload."""
    normalized = dict(payload)
    normalized["sender"] = validate_email_address(str(normalized.get("sender", "")), "sender")
    if "recipient" in normalized:
        normalized["recipient"] = validate_email_address(str(normalized["recipient"]), "recipient")
    return normalized
