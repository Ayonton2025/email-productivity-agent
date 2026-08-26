"""Typed exceptions shared by API and service layers."""

from __future__ import annotations

from typing import Any


class ApplicationError(Exception):
    status_code = 500
    code = "application_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class PaymentError(ApplicationError):
    status_code = 502
    code = "payment_error"


class SubscriptionError(ApplicationError, ValueError):
    status_code = 400
    code = "subscription_error"


class EmailDeliveryError(ApplicationError):
    status_code = 502
    code = "email_delivery_error"
