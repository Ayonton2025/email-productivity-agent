import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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


class PayPalService:
    """Integration with PayPal for global payments (fallback)"""

    def __init__(self):
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_CLIENT_SECRET
        self.client = httpx.AsyncClient(timeout=30.0)
        self.mode = getattr(settings, "PAYPAL_MODE", "sandbox")  # sandbox or live

        # Use environment variables for API URLs
        if self.mode == "sandbox":
            self.base_url = settings.PAYPAL_API_BASE_URL  # https://api-m.sandbox.paypal.com by default
        else:
            self.base_url = settings.PAYPAL_API_BASE_URL_LIVE  # https://api-m.paypal.com for live

    async def get_access_token(self) -> Optional[str]:
        """Get PayPal OAuth token"""
        try:
            auth = (self.client_id, self.client_secret)
            response = await self.client.post(
                f"{self.base_url}/v1/oauth2/token", data={"grant_type": "client_credentials"}, auth=auth
            )
            response.raise_for_status()
            data = response.json()
            return data.get("access_token")
        except Exception as e:
            logger.error(f"PayPal token error: {str(e)}")
            return None

    async def create_order(
        self, user_email: str, plan_id: str, plan_name: str, amount_usd: float, user_id: str, return_url: str = None
    ) -> Dict[str, Any]:
        """
        Create a PayPal order for subscription upgrade

        Args:
            user_email: Customer email
            plan_id: Subscription plan ID
            plan_name: Display name of the plan
            amount_usd: Amount in USD
            user_id: User ID for tracking
            return_url: Return URL after payment (base URL)

        Returns:
            Order data with approval link
        """
        try:
            if not self.client_id or not self.client_secret:
                return {"success": False, "message": "PayPal is not configured"}

            token = await self.get_access_token()
            if not token:
                return {"success": False, "message": "Failed to get PayPal token"}

            return_url = return_url or settings.FRONTEND_URL

            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

            payload = {
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "amount": {"currency_code": "USD", "value": str(amount_usd)},
                        "description": f"Premium subscription: {plan_name}",
                        "custom_id": user_id,
                        "reference_id": f"{user_id}-{plan_id}",
                    }
                ],
                "payer": {"email_address": user_email},
                "application_context": {
                    "brand_name": "Bylix Email",
                    "locale": "en-US",
                    "landing_page": "LOGIN",
                    "return_url": f"{return_url}/billing?payment=success",
                    "cancel_url": f"{return_url}/billing",
                    "user_action": "PAY_NOW",
                },
            }

            response = await self.client.post(f"{self.base_url}/v2/checkout/orders", json=payload, headers=headers)

            response.raise_for_status()
            data = response.json()

            # Extract approval link
            approval_link = None
            for link in data.get("links", []):
                if link.get("rel") == "approve":
                    approval_link = link.get("href")
                    break

            if data.get("status") == "CREATED" and approval_link:
                return {
                    "success": True,
                    "order_id": data.get("id"),
                    "approval_url": approval_link,
                    "amount": amount_usd,
                }
            else:
                return {"success": False, "message": "Failed to create PayPal order"}

        except Exception as e:
            logger.error(f"PayPal order creation error: {str(e)}")
            return {"success": False, "message": str(e)}

    async def capture_order(self, order_id: str) -> Dict[str, Any]:
        """
        Capture a PayPal order after user approves

        Args:
            order_id: PayPal order ID

        Returns:
            Capture result
        """
        try:
            token = await self.get_access_token()
            if not token:
                return {"success": False, "message": "Failed to get PayPal token"}

            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

            response = await self.client.post(
                f"{self.base_url}/v2/checkout/orders/{order_id}/capture", json={}, headers=headers
            )

            response.raise_for_status()
            data = response.json()

            if data.get("status") == "COMPLETED":
                payer = data.get("payer", {})
                amount = data.get("purchase_units", [{}])[0].get("amount", {})

                return {
                    "success": True,
                    "order_id": order_id,
                    "status": "completed",
                    "amount": amount.get("value"),
                    "email": payer.get("email_address"),
                    "capture_id": data.get("id"),
                }
            else:
                return {"success": False, "message": f"Order status: {data.get('status')}"}

        except Exception as e:
            logger.error(f"PayPal capture error: {str(e)}")
            return {"success": False, "message": str(e)}


class CoinbaseCommerceService:
    """Minimal Coinbase Commerce (crypto) integration to create hosted charges."""

    def __init__(self):
        self.api_key = settings.COINBASE_COMMERCE_API_KEY
        self.base = settings.COINBASE_COMMERCE_API_BASE
        self.client = httpx.AsyncClient(timeout=30.0)
        if not self.api_key:
            logger.warning("⚠️ [CoinbaseCommerce] COINBASE_COMMERCE_API_KEY not configured - crypto payments disabled")
        else:
            logger.info("Coinbase Commerce service initialized")

    async def create_charge(
        self, name: str, description: str, amount_usd: float, metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a hosted Coinbase Commerce charge for a fixed USD amount.

        Returns: { success: bool, hosted_url, charge_id, pricing }
        """
        if not self.api_key:
            return {"success": False, "message": "Coinbase Commerce API key not configured"}

        payload = {
            "name": name,
            "description": description,
            "pricing_type": "fixed_price",
            "local_price": {"amount": f"{amount_usd:.2f}", "currency": "USD"},
            "metadata": metadata or {},
        }

        headers = {"X-CC-Api-Key": self.api_key, "X-CC-Version": "2018-03-22", "Content-Type": "application/json"}

        try:
            resp = await self.client.post(f"{self.base}/charges", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            hosted_url = data.get("data", {}).get("hosted_url")
            charge_id = data.get("data", {}).get("id")
            return {"success": True, "hosted_url": hosted_url, "charge_id": charge_id, "data": data.get("data")}
        except Exception as e:
            logger.error(f"❌ [CoinbaseCommerce] create_charge error: {str(e)}")
            try:
                return {"success": False, "message": resp.json()}
            except Exception:
                return {"success": False, "message": str(e)}


class BybitPayService:
    """Minimal Bybit Pay integration (crypto checkout order creation)."""

    def __init__(self):
        self.api_key = settings.BYBIT_PAY_API_KEY
        self.api_secret = settings.BYBIT_PAY_API_SECRET
        self.merchant_id = settings.BYBIT_PAY_MERCHANT_ID
        self.base = settings.BYBIT_PAY_API_BASE
        self.client = httpx.AsyncClient(timeout=30.0)

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret and self.merchant_id)

    async def create_order(self, order_id: str, amount_usd: float, return_url: str) -> Dict[str, Any]:
        """
        Create a Bybit Pay order.
        Notes:
        - API payload/headers can vary by account tier; this implementation is intentionally minimal.
        - It returns a checkout URL when Bybit accepts the order.
        """
        if not self.is_configured():
            return {"success": False, "message": "Bybit Pay is not configured"}

        payload = {
            "merchantId": self.merchant_id,
            "merchantOrderNo": order_id,
            "currency": "USD",
            "amount": f"{amount_usd:.2f}",
            "orderDescription": "Subscription upgrade",
            "returnUrl": f"{return_url}/billing?payment=success",
            "cancelUrl": f"{return_url}/billing",
        }
        headers = {
            "Content-Type": "application/json",
            "X-BAPI-API-KEY": self.api_key,
        }
        try:
            resp = await self.client.post(f"{self.base}/v5/pay/order/create", json=payload, headers=headers)
            data = resp.json() if resp.content else {}
            if resp.status_code >= 400:
                return {
                    "success": False,
                    "message": data.get("retMsg") or data.get("message") or f"HTTP {resp.status_code}",
                }

            result = data.get("result", {}) if isinstance(data, dict) else {}
            checkout_url = result.get("payUrl") or result.get("url")
            if checkout_url:
                return {"success": True, "checkout_url": checkout_url, "raw": data}
            return {"success": False, "message": data.get("retMsg") or "Bybit order creation failed"}
        except Exception as e:
            return {"success": False, "message": str(e)}


# -----------------------------
# Stripe (optional) integration
# -----------------------------
try:
    import stripe  # type: ignore
except Exception:
    stripe = None


class StripeService:
    """Minimal Stripe Checkout integration (creates a checkout session)."""

    def __init__(self):
        self.api_key = settings.STRIPE_API_KEY
        if stripe and self.api_key:
            stripe.api_key = self.api_key
            logger.info("Stripe service initialized")
        else:
            if not stripe:
                logger.warning("⚠️ [StripeService] stripe package not available in environment")
            else:
                logger.warning("⚠️ [StripeService] STRIPE_API_KEY not configured - Stripe disabled")

    def is_configured(self) -> bool:
        return bool(stripe and self.api_key)

    def create_checkout_session(
        self,
        amount_usd: float,
        currency: str = "USD",
        success_url: str = None,
        cancel_url: str = None,
        metadata: Dict[str, Any] = None,
    ):
        """Create a Stripe Checkout Session for one-time subscription upgrade flow (simple flow).

        Returns: {success: True, session_id: 'cs_...'} or {success: False, message: str}
        """
        if not self.is_configured():
            return {"success": False, "message": "Stripe is not configured"}

        try:
            # Stripe expects amount in cents
            amount_cents = int(round(amount_usd * 100))
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="payment",
                line_items=[
                    {
                        "price_data": {
                            "currency": currency.lower(),
                            "product_data": {"name": f"Upgrade - ${amount_usd:.2f}"},
                            "unit_amount": amount_cents,
                        },
                        "quantity": 1,
                    }
                ],
                success_url=success_url or settings.FRONTEND_URL + "/billing?payment=success",
                cancel_url=cancel_url or settings.FRONTEND_URL + "/billing",
                metadata=metadata or {},
            )
            return {"success": True, "session_id": session.id, "checkout_url": session.url}
        except Exception as e:
            logger.error(f"❌ [StripeService] create_checkout_session error: {str(e)}")
            return {"success": False, "message": str(e)}
