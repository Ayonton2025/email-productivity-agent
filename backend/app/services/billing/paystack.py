import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import PaymentError
from app.core.security import logger
from app.models.billing_models import (
    AI_ACTION_COSTS,
    CREDIT_PACK_PRICING_USD,
    SUBSCRIPTION_PLANS,
    AICredits,
    CreditTransaction,
    OutboundCredits,
    Payment,
    PaymentTransaction,
    Subscription,
    UsageLog,
)
from app.models.database import SystemSetting, User


class PaymentRequiredError(PaymentError):
    """Raised when user does not have enough credits."""


class PaystackService:
    """Integration with Paystack payment gateway"""

    def __init__(self):
        # IMPORTANT: Use SECRET_KEY (sk_*) for server-side operations, not PUBLIC_KEY (pk_*)
        self.api_key = settings.PAYSTACK_SECRET_KEY or settings.PAYSTACK_API_KEY
        self.public_key = settings.PAYSTACK_PUBLIC_KEY
        self.base_url = settings.PAYSTACK_API_BASE_URL  # Use env var instead of hardcoded
        self.client = httpx.AsyncClient(timeout=30.0)

        if not self.api_key:
            logger.warning(
                "⚠️ [PaystackService] PAYSTACK_SECRET_KEY not configured in environment - using PAYSTACK_API_KEY as fallback"
            )
            logger.warning("⚠️ [PaystackService] CRITICAL: Payment operations will fail without valid SECRET key (sk_*)")
        else:
            # Log first 10 chars for verification
            key_type = "SECRET" if self.api_key.startswith("sk_") else "unknown"
            logger.info("Paystack service initialized", extra={"key_type": key_type})
            if not self.api_key.startswith("sk_"):
                logger.error(
                    "❌ [PaystackService] API key does not start with 'sk_' - this will cause payment failures!"
                )

    async def initialize_payment(
        self,
        email: str,
        amount: int,  # in kobo/cents
        reference: str,
        metadata: Dict[str, Any] = None,
        currency: str = "USD",
        channels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Initialize a payment

        Args:
            email: Customer email
            amount: Amount in smallest currency unit (kobo for NGN)
            reference: Unique transaction reference
            metadata: Additional data to track

        Returns:
            Payment initialization response with authorization_url
        """
        if settings.ENABLE_MOCK_MODE:
            from app.services.mock_services import mock_payment

            return mock_payment(reference, amount, currency, email)
        try:
            logger.info(f"🔄 [PaystackService] Initialize payment - email={email}, amount={amount}, ref={reference}")

            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

            payload = {
                "email": email,
                "amount": amount,
                "reference": reference,
                "metadata": metadata or {},
                "currency": currency,
            }
            if channels:
                payload["channels"] = channels

            logger.debug(f"🔄 [PaystackService] Payload: {payload}")

            response = await self.client.post(f"{self.base_url}/transaction/initialize", json=payload, headers=headers)

            logger.info(f"🔄 [PaystackService] Response status: {response.status_code}")

            try:
                response.raise_for_status()
            except Exception as http_err:
                # Log HTTP error details
                logger.error(f"❌ [PaystackService] HTTP error {response.status_code}: {str(http_err)}")
                try:
                    error_data = response.json()
                    logger.error(f"❌ [PaystackService] Error response: {error_data}")
                    return {"success": False, "message": error_data.get("message", f"HTTP {response.status_code}")}
                except:
                    logger.error(f"❌ [PaystackService] Response body: {response.text}")
                    return {"success": False, "message": f"HTTP {response.status_code}: {response.text[:200]}"}

            data = response.json()

            logger.debug(f"🔄 [PaystackService] Response data: {data}")

            if data.get("status"):
                logger.info(f"✅ [PaystackService] Payment initialized: {reference}")
                return {
                    "success": True,
                    "authorization_url": data["data"]["authorization_url"],
                    "access_code": data["data"]["access_code"],
                    "reference": reference,
                }
            else:
                error_msg = data.get("message", "Unknown error")
                logger.error(f"❌ [PaystackService] Init failed: {error_msg}")
                return {"success": False, "message": error_msg}

        except Exception as e:
            logger.error(f"❌ [PaystackService] Initialization error: {str(e)}", exc_info=True)
            return {"success": False, "message": str(e)}

    async def initialize_payment_or_raise(self, *args, **kwargs) -> Dict[str, Any]:
        """Typed boundary for payment callers migrating away from result dictionaries."""
        result = await self.initialize_payment(*args, **kwargs)
        if not result.get("success"):
            raise PaymentError(str(result.get("message") or "Payment initialization failed"), details=result)
        return result

    async def verify_payment(self, reference: str) -> Dict[str, Any]:
        """
        Verify a payment was successful

        Args:
            reference: Transaction reference

        Returns:
            Verification result with payment details
        """
        if settings.ENABLE_MOCK_MODE:
            return {
                "success": True,
                "payment_status": "completed",
                "reference": reference,
                "amount": 0,
                "email": "mock@example.test",
                "timestamp": datetime.utcnow().isoformat(),
                "mock": True,
            }
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }

            response = await self.client.get(f"{self.base_url}/transaction/verify/{reference}", headers=headers)

            response.raise_for_status()
            data = response.json()

            if data.get("status") and data["data"]["status"] == "success":
                return {
                    "success": True,
                    "payment_status": "completed",
                    "amount": data["data"]["amount"],
                    "email": data["data"]["customer"]["email"],
                    "reference": reference,
                    "timestamp": data["data"]["paid_at"],
                }
            else:
                return {
                    "success": False,
                    "payment_status": data["data"].get("status", "pending"),
                    "message": "Payment not completed",
                }

        except Exception as e:
            logger.error(f"Paystack verification error: {str(e)}")
            return {"success": False, "message": str(e)}

    async def get_payment_details(self, reference: str) -> Optional[Dict[str, Any]]:
        """Get details of a payment"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = await self.client.get(f"{self.base_url}/transaction/{reference}", headers=headers)
            response.raise_for_status()
            return response.json().get("data")
        except Exception as e:
            logger.error(f"Failed to get payment details: {str(e)}")
            return None
