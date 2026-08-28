"""Compatibility facade for the refactored billing package."""

from app.services.billing.credits import CreditService, FeatureGatingService
from app.services.billing.invoices import CreditPurchaseMixin, PaymentFinalizeMixin
from app.services.billing.payments import PaymentInfrastructureMixin
from app.services.billing.paypal import (
    BybitPayService,
    CoinbaseCommerceService,
    PayPalService,
    StripeService,
)
from app.services.billing.paystack import PaymentRequiredError, PaystackService
from app.services.billing.subscriptions import SubscriptionService
from app.services.billing.upgrades import UpgradeSessionMixin


class PaymentService(
    PaymentInfrastructureMixin,
    CreditPurchaseMixin,
    UpgradeSessionMixin,
    PaymentFinalizeMixin,
):
    """Payment facade retaining the original public API."""


__all__ = [
    "BybitPayService",
    "CoinbaseCommerceService",
    "CreditService",
    "FeatureGatingService",
    "PaymentRequiredError",
    "PaymentService",
    "PayPalService",
    "PaystackService",
    "StripeService",
    "SubscriptionService",
]
