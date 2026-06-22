"""
Layer 7: Billing & Monetization Service

Handles:
- Subscription management
- AI and Outbound credit tracking
- Paystack payment integration
- Feature gating based on subscription tier
"""

import httpx
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.core.security import logger
from app.models.database import User, SystemSetting
from app.models.billing_models import (
    Subscription, PaymentTransaction, AICredits, OutboundCredits,
    UsageLog, SUBSCRIPTION_PLANS, AI_ACTION_COSTS, CREDIT_PACK_PRICING_USD,
    CreditTransaction, Payment
)


class PaymentRequiredError(Exception):
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
            logger.warning("⚠️ [PaystackService] PAYSTACK_SECRET_KEY not configured in environment - using PAYSTACK_API_KEY as fallback")
            logger.warning("⚠️ [PaystackService] CRITICAL: Payment operations will fail without valid SECRET key (sk_*)")
        else:
            # Log first 10 chars for verification
            key_type = "SECRET" if self.api_key.startswith("sk_") else "unknown"
            logger.info(f"✅ [PaystackService] Initialized with {key_type} key: {self.api_key[:10]}...")
            if not self.api_key.startswith("sk_"):
                logger.error(f"❌ [PaystackService] API key does not start with 'sk_' - this will cause payment failures!")
    
    
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
        try:
            logger.info(f"🔄 [PaystackService] Initialize payment - email={email}, amount={amount}, ref={reference}")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
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
            
            response = await self.client.post(
                f"{self.base_url}/transaction/initialize",
                json=payload,
                headers=headers
            )
            
            logger.info(f"🔄 [PaystackService] Response status: {response.status_code}")
            
            try:
                response.raise_for_status()
            except Exception as http_err:
                # Log HTTP error details
                logger.error(f"❌ [PaystackService] HTTP error {response.status_code}: {str(http_err)}")
                try:
                    error_data = response.json()
                    logger.error(f"❌ [PaystackService] Error response: {error_data}")
                    return {"success": False, "message": error_data.get('message', f"HTTP {response.status_code}")}
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
                    "reference": reference
                }
            else:
                error_msg = data.get('message', 'Unknown error')
                logger.error(f"❌ [PaystackService] Init failed: {error_msg}")
                return {"success": False, "message": error_msg}
        
        except Exception as e:
            logger.error(f"❌ [PaystackService] Initialization error: {str(e)}", exc_info=True)
            return {"success": False, "message": str(e)}
    
    async def verify_payment(self, reference: str) -> Dict[str, Any]:
        """
        Verify a payment was successful
        
        Args:
            reference: Transaction reference
        
        Returns:
            Verification result with payment details
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }
            
            response = await self.client.get(
                f"{self.base_url}/transaction/verify/{reference}",
                headers=headers
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") and data["data"]["status"] == "success":
                return {
                    "success": True,
                    "payment_status": "completed",
                    "amount": data["data"]["amount"],
                    "email": data["data"]["customer"]["email"],
                    "reference": reference,
                    "timestamp": data["data"]["paid_at"]
                }
            else:
                return {
                    "success": False,
                    "payment_status": data["data"].get("status", "pending"),
                    "message": "Payment not completed"
                }
        
        except Exception as e:
            logger.error(f"Paystack verification error: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def get_payment_details(self, reference: str) -> Optional[Dict[str, Any]]:
        """Get details of a payment"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = await self.client.get(
                f"{self.base_url}/transaction/{reference}",
                headers=headers
            )
            response.raise_for_status()
            return response.json().get("data")
        except Exception as e:
            logger.error(f"Failed to get payment details: {str(e)}")
            return None

class PayPalService:
    """Integration with PayPal for global payments (fallback)"""
    
    def __init__(self):
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_CLIENT_SECRET
        self.client = httpx.AsyncClient(timeout=30.0)
        self.mode = getattr(settings, 'PAYPAL_MODE', 'sandbox')  # sandbox or live
        
        # Use environment variables for API URLs
        if self.mode == 'sandbox':
            self.base_url = settings.PAYPAL_API_BASE_URL  # https://api-m.sandbox.paypal.com by default
        else:
            self.base_url = settings.PAYPAL_API_BASE_URL_LIVE  # https://api-m.paypal.com for live

    async def get_access_token(self) -> Optional[str]:
        """Get PayPal OAuth token"""
        try:
            auth = (self.client_id, self.client_secret)
            response = await self.client.post(
                f"{self.base_url}/v1/oauth2/token",
                data={"grant_type": "client_credentials"},
                auth=auth
            )
            response.raise_for_status()
            data = response.json()
            return data.get("access_token")
        except Exception as e:
            logger.error(f"PayPal token error: {str(e)}")
            return None

    async def create_order(
        self,
        user_email: str,
        plan_id: str,
        plan_name: str,
        amount_usd: float,
        user_id: str,
        return_url: str = None
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
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "intent": "CAPTURE",
                "purchase_units": [{
                    "amount": {
                        "currency_code": "USD",
                        "value": str(amount_usd)
                    },
                    "description": f"Premium subscription: {plan_name}",
                    "custom_id": user_id,
                    "reference_id": f"{user_id}-{plan_id}"
                }],
                "payer": {
                    "email_address": user_email
                },
                "application_context": {
                    "brand_name": "Bylix Email",
                    "locale": "en-US",
                    "landing_page": "LOGIN",
                    "return_url": f"{return_url}/billing?payment=success",
                    "cancel_url": f"{return_url}/billing",
                    "user_action": "PAY_NOW"
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/v2/checkout/orders",
                json=payload,
                headers=headers
            )
            
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
                    "amount": amount_usd
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
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            response = await self.client.post(
                f"{self.base_url}/v2/checkout/orders/{order_id}/capture",
                json={},
                headers=headers
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
                    "capture_id": data.get("id")
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
            logger.info(f"✅ [CoinbaseCommerce] Initialized (key present, first10={self.api_key[:10]}...)")

    async def create_charge(self, name: str, description: str, amount_usd: float, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
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
            "metadata": metadata or {}
        }

        headers = {
            "X-CC-Api-Key": self.api_key,
            "X-CC-Version": "2018-03-22",
            "Content-Type": "application/json"
        }

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
                return {"success": False, "message": data.get("retMsg") or data.get("message") or f"HTTP {resp.status_code}"}

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
            logger.info(f"✅ [StripeService] Initialized (key present, first10={self.api_key[:10]}...)")
        else:
            if not stripe:
                logger.warning("⚠️ [StripeService] stripe package not available in environment")
            else:
                logger.warning("⚠️ [StripeService] STRIPE_API_KEY not configured - Stripe disabled")

    def is_configured(self) -> bool:
        return bool(stripe and self.api_key)

    def create_checkout_session(self, amount_usd: float, currency: str = 'USD', success_url: str = None, cancel_url: str = None, metadata: Dict[str, Any] = None):
        """Create a Stripe Checkout Session for one-time subscription upgrade flow (simple flow).

        Returns: {success: True, session_id: 'cs_...'} or {success: False, message: str}
        """
        if not self.is_configured():
            return {"success": False, "message": "Stripe is not configured"}

        try:
            # Stripe expects amount in cents
            amount_cents = int(round(amount_usd * 100))
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                mode='payment',
                line_items=[{
                    'price_data': {
                        'currency': currency.lower(),
                        'product_data': {'name': f'Upgrade - ${amount_usd:.2f}'},
                        'unit_amount': amount_cents,
                    },
                    'quantity': 1,
                }],
                success_url=success_url or settings.FRONTEND_URL + '/billing?payment=success',
                cancel_url=cancel_url or settings.FRONTEND_URL + '/billing',
                metadata=metadata or {},
            )
            return {"success": True, "session_id": session.id, "checkout_url": session.url}
        except Exception as e:
            logger.error(f"❌ [StripeService] create_checkout_session error: {str(e)}")
            return {"success": False, "message": str(e)}
            logger.error(f"❌ [CoinbaseCommerce] create_charge error: {str(e)}")
            try:
                return {"success": False, "message": resp.json()}
            except Exception:
                return {"success": False, "message": str(e)}

class SubscriptionService:
    """Manage user subscriptions"""
    
    def __init__(self):
        self.paystack = PaystackService()
    
    async def create_subscription(
        self,
        user_id: str,
        tenant_id: str,
        plan_id: str,
        session: AsyncSession
    ) -> Subscription:
        """Create a new subscription"""
        
        if plan_id not in SUBSCRIPTION_PLANS:
            raise ValueError(f"Unknown plan: {plan_id}")
        
        plan = SUBSCRIPTION_PLANS[plan_id]
        
        cycle = plan.get("billing_cycle", "monthly")
        if cycle == "daily":
            period_days = 1
        elif cycle == "annual":
            period_days = 365
        else:
            period_days = 30
        seats_value = plan.get("seats")
        seats_value = seats_value if seats_value is not None else 999
        credits_allocation = plan.get("ai_credits_daily") or plan.get("ai_credits_monthly") or 0
        period_start = datetime.utcnow()
        period_end = period_start + timedelta(days=period_days)

        subscription = Subscription(
            user_id=user_id,
            tenant_id=tenant_id,
            plan_id=plan_id,
            plan_name=plan["name"],
            billing_cycle=plan.get("billing_cycle", "monthly"),
            price_usd=plan.get("price", 0),
            price_per_seat=plan.get("price_per_seat", 0),
            current_period_start=period_start,
            current_period_end=period_end,
            billing_cycle_start=period_start,
            billing_cycle_end=period_end,
            seats_included=seats_value,
            seats_current=min(1, seats_value),
            seats_max=seats_value,
            features=plan.get("features", {}),
            ai_credits_monthly_allocation=credits_allocation,
            outbound_emails_monthly_allocation=plan.get("outbound_emails_monthly") or 0,
            ai_credits_reset_date=period_end,
            credits_total=credits_allocation,
            credits_used=0,
        )
        
        session.add(subscription)
        await session.flush()
        
        # Initialize AI and Outbound credits
        ai_credits = AICredits(
            user_id=user_id,
            tenant_id=tenant_id,
            balance=credits_allocation,
            monthly_allocation=credits_allocation
        )
        
        outbound_credits = OutboundCredits(
            user_id=user_id,
            tenant_id=tenant_id,
            balance=plan.get("outbound_emails_monthly") or 0,
            monthly_allocation=plan.get("outbound_emails_monthly") or 0
        )
        
        session.add(ai_credits)
        session.add(outbound_credits)
        session.add(
            CreditTransaction(
                user_id=user_id,
                credits_added=credits_allocation,
                source="subscription",
            )
        )

        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user:
            user.plan = plan_id
            user.subscription_status = "active" if plan.get("price", 0) > 0 else "free"
        
        return subscription
    
    async def upgrade_subscription(
        self,
        user_id: str,
        new_plan_id: str,
        session: AsyncSession
    ) -> Subscription:
        """Upgrade a subscription to a different plan"""
        
        result = await session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscription = result.scalar()
        
        if not subscription:
            raise ValueError(f"No subscription found for user {user_id}")
        
        plan = SUBSCRIPTION_PLANS[new_plan_id]
        
        # Update subscription
        seats_value = plan.get("seats")
        seats_value = seats_value if seats_value is not None else 999

        subscription.plan_id = new_plan_id
        subscription.plan_name = plan["name"]
        subscription.price_usd = plan.get("price", 0)
        subscription.price_per_seat = plan.get("price_per_seat", 0)
        subscription.seats_included = seats_value
        subscription.seats_max = seats_value
        subscription.features = plan.get("features", {})
        credits_allocation = plan.get("ai_credits_daily") or plan.get("ai_credits_monthly") or 0
        subscription.ai_credits_monthly_allocation = credits_allocation
        subscription.outbound_emails_monthly_allocation = plan.get("outbound_emails_monthly") or 0
        subscription.credits_total = credits_allocation
        subscription.credits_used = 0
        subscription.billing_cycle_start = datetime.utcnow()
        if plan.get("billing_cycle") == "daily":
            subscription.billing_cycle_end = datetime.utcnow() + timedelta(days=1)
        elif plan.get("billing_cycle") == "annual":
            subscription.billing_cycle_end = datetime.utcnow() + timedelta(days=365)
        else:
            subscription.billing_cycle_end = datetime.utcnow() + timedelta(days=30)
        subscription.current_period_start = subscription.billing_cycle_start
        subscription.current_period_end = subscription.billing_cycle_end
        subscription.updated_at = datetime.utcnow()
        
        # Reset monthly usage
        subscription.ai_credits_monthly_used = 0
        subscription.outbound_emails_monthly_used = 0

        ai_result = await session.execute(select(AICredits).where(AICredits.user_id == user_id))
        ai_credits = ai_result.scalar_one_or_none()
        if ai_credits:
            ai_credits.monthly_allocation = credits_allocation
            ai_credits.balance = credits_allocation
            ai_credits.monthly_used = 0

        session.add(
            CreditTransaction(
                user_id=user_id,
                credits_added=credits_allocation,
                source="subscription",
            )
        )

        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user:
            user.plan = new_plan_id
            user.subscription_status = "active" if plan.get("price", 0) > 0 else "free"
        
        await session.flush()
        return subscription
    
    async def cancel_subscription(
        self,
        user_id: str,
        session: AsyncSession
    ) -> Subscription:
        """Cancel a subscription"""
        
        result = await session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscription = result.scalar()
        
        if not subscription:
            raise ValueError(f"No subscription found for user {user_id}")
        
        subscription.status = "cancelled"
        subscription.auto_renew = False
        subscription.updated_at = datetime.utcnow()
        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user:
            user.plan = "personal"
            user.subscription_status = "cancelled"
        
        await session.flush()
        return subscription
    
    async def get_subscription(
        self,
        user_id: str,
        session: AsyncSession
    ) -> Optional[Subscription]:
        """Get user's subscription"""
        result = await session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar()


class CreditService:
    """Manage AI and Outbound credits"""

    @staticmethod
    def _is_super_admin_email(email: Optional[str]) -> bool:
        allowed = {e.strip().lower() for e in (settings.ADMIN_EMAILS or "").split(",") if e.strip()}
        return bool(email and email.lower() in allowed)

    @classmethod
    def _is_super_admin_user(cls, user: Optional[User]) -> bool:
        if not user:
            return False
        if getattr(user, "is_superuser", False) or getattr(user, "is_admin", False):
            return True
        if str(getattr(user, "plan", "")).strip().lower() == "super_admin":
            return True
        return cls._is_super_admin_email(getattr(user, "email", None))

    async def _get_user(self, user_id: str, session: AsyncSession) -> Optional[User]:
        row = await session.execute(select(User).where(User.id == user_id))
        return row.scalar_one_or_none()

    async def _get_user_access_override(self, user_id: str, session: AsyncSession) -> Dict[str, Any]:
        user = await self._get_user(user_id, session)
        if not user or not user.email:
            return {}
        key = "user_access_overrides_v1"
        setting = await session.get(SystemSetting, key)
        if not setting or not setting.value:
            return {}
        try:
            payload = json.loads(setting.value)
            return (payload or {}).get(user.email.lower(), {}) or {}
        except Exception:
            return {}

    async def _has_payment_bypass(self, user_id: str, session: AsyncSession) -> bool:
        user = await self._get_user(user_id, session)
        if self._is_super_admin_user(user):
            return True
        override = await self._get_user_access_override(user_id, session)
        return bool(override.get("payment_bypass") or override.get("allow_all"))

    async def _is_user_blocked(self, user_id: str, session: AsyncSession) -> bool:
        override = await self._get_user_access_override(user_id, session)
        return bool(override.get("block_all"))

    def _credits_for_action(self, action: str) -> int:
        action_key = (action or "").strip().lower()
        if action_key in AI_ACTION_COSTS:
            return int(AI_ACTION_COSTS[action_key]["units"])
        aliases = {
            "email_classification": "categorization",
            "classify": "categorization",
            "summary": "summarization",
            "thread_summarization": "summarization",
            "reply": "reply_drafting",
            "workflow_classification": "categorization",
        }
        mapped = aliases.get(action_key)
        if mapped and mapped in AI_ACTION_COSTS:
            return int(AI_ACTION_COSTS[mapped]["units"])
        return 1

    async def check_credits(
        self,
        user_id: str,
        credits_needed: int,
        session: AsyncSession
    ) -> bool:
        if await self._is_user_blocked(user_id, session):
            raise PaymentRequiredError("Access blocked by admin policy")
        if await self._has_payment_bypass(user_id, session):
            return True
        result = await session.execute(select(AICredits).where(AICredits.user_id == user_id))
        ai_credits = result.scalar_one_or_none()
        if ai_credits and ai_credits.balance >= credits_needed:
            return True
        raise PaymentRequiredError(f"Insufficient credits: need {credits_needed}")

    async def check_credits_for_ai_action(
        self,
        user_id: str,
        action: str,
        session: AsyncSession
    ) -> bool:
        credits_needed = self._credits_for_action(action)
        return await self.check_credits(user_id=user_id, credits_needed=credits_needed, session=session)

    async def deduct_credits(
        self,
        user_id: str,
        feature: str,
        credits: int,
        session: AsyncSession
    ) -> bool:
        """Deduct credits for a feature use"""
        if await self._is_user_blocked(user_id, session):
            logger.warning(f"User {user_id} blocked by admin policy")
            return False
        if await self._has_payment_bypass(user_id, session):
            # Super admin or explicitly bypassed users are not billed.
            return True
        
        result = await session.execute(
            select(AICredits).where(AICredits.user_id == user_id)
        )
        ai_credits = result.scalar()
        
        if not ai_credits or ai_credits.balance < credits:
            logger.warning(f"Insufficient credits for user {user_id}")
            return False
        
        ai_credits.balance -= credits
        ai_credits.monthly_used += credits
        subscription_result = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
        subscription = subscription_result.scalar_one_or_none()
        if subscription:
            subscription.ai_credits_monthly_used += credits
            subscription.credits_used += credits
        
        # Update feature-specific counters
        feature_key = (feature or "").lower()
        if feature_key in {"email_classification", "classify", "categorization"}:
            ai_credits.classification_used += credits
        elif feature_key == "action_extraction":
            ai_credits.extraction_used += credits
        elif feature_key in {"thread_summarization", "summarization", "summary"}:
            ai_credits.summarization_used += credits
        elif feature_key == "sentiment_analysis":
            ai_credits.sentiment_analysis_used += credits
        else:
            ai_credits.other_used += credits
        
        # Log usage
        usage = UsageLog(
            user_id=user_id,
            tenant_id=ai_credits.tenant_id,
            metric=feature,
            quantity=credits,
            action=feature,
            credits_used=credits,
            tokens_used=0,
            timestamp=datetime.utcnow(),
            breakdown={"reason": "feature_use"}
        )
        credit_transaction = CreditTransaction(
            user_id=user_id,
            credits_used=credits,
            source="usage",
        )
        session.add(usage)
        session.add(credit_transaction)
        await session.flush()
        
        return True

    async def deduct_credits_for_ai_action(
        self,
        user_id: str,
        action: str,
        session: AsyncSession,
        tokens_used: int = 0
    ) -> Dict[str, Any]:
        credits = self._credits_for_action(action)
        await self.check_credits(user_id=user_id, credits_needed=credits, session=session)
        ok = await self.deduct_credits(user_id=user_id, feature=action, credits=credits, session=session)
        if not ok:
            raise PaymentRequiredError(f"Insufficient credits: need {credits}")
        return {
            "success": True,
            "credits_used": credits,
            "tokens_used": tokens_used,
        }
    
    async def add_credits(
        self,
        user_id: str,
        credits: int,
        reason: str,
        session: AsyncSession
    ) -> bool:
        """Add credits to a user account"""
        
        result = await session.execute(
            select(AICredits).where(AICredits.user_id == user_id)
        )
        ai_credits = result.scalar()
        
        if not ai_credits:
            logger.error(f"No AI credits account for user {user_id}")
            return False
        
        ai_credits.balance += credits
        
        # Log the addition
        usage = UsageLog(
            user_id=user_id,
            tenant_id=ai_credits.tenant_id,
            metric="credit_addition",
            quantity=-credits,  # Negative for additions
            action="credit_addition",
            credits_used=0,
            tokens_used=0,
            timestamp=datetime.utcnow(),
            breakdown={"reason": reason}
        )
        credit_transaction = CreditTransaction(
            user_id=user_id,
            credits_added=credits,
            source=reason,
        )
        session.add(usage)
        session.add(credit_transaction)
        await session.flush()
        
        return True
    
    async def get_credits(
        self,
        user_id: str,
        session: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Get current credit balance"""
        
        result = await session.execute(
            select(AICredits).where(AICredits.user_id == user_id)
        )
        ai_credits = result.scalar()
        
        if not ai_credits:
            return None
        
        return {
            "ai_credits": ai_credits.to_dict(),
            "balance_usd": round(ai_credits.balance * 0.004, 2),
            "credit_definition": "1 AI Credit = 1 email processed (or 1,000 tokens)"
        }
    
    async def deduct_outbound_credits(
        self,
        user_id: str,
        emails_count: int,
        session: AsyncSession
    ) -> bool:
        """Deduct outbound credits for sending emails"""
        
        result = await session.execute(
            select(OutboundCredits).where(OutboundCredits.user_id == user_id)
        )
        outbound = result.scalar()
        
        if not outbound or outbound.balance < emails_count:
            logger.warning(f"Insufficient outbound credits for user {user_id}")
            return False
        
        outbound.balance -= emails_count
        outbound.monthly_used += emails_count
        
        usage = UsageLog(
            user_id=user_id,
            tenant_id=outbound.tenant_id,
            metric="outbound_email",
            quantity=emails_count,
            breakdown={"reason": "campaign_send"}
        )
        
        session.add(usage)
        await session.flush()
        
        return True


class FeatureGatingService:
    """Enforce feature access based on subscription tier and credits"""

    FEATURE_ALIASES: Dict[str, List[str]] = {
        "email_classification": ["email_classification", "email_categorization", "categorization", "classify"],
        "action_extraction": ["action_extraction"],
        "thread_summarization": ["thread_summarization", "email_summaries", "summarization", "summary"],
        "sentiment_analysis": ["sentiment_analysis"],
        "shared_inbox": ["shared_inbox", "shared_inboxes", "team_shared_inbox"],
        "workflow_automation": ["workflow_automation", "workflows", "workflow_builder", "unlimited_workflows"],
        "crm_sync": ["crm_sync", "crm_lite", "auto_crm"],
        "advanced_analytics": ["advanced_analytics", "analytics_dashboard", "dashboard"],
        "api_access": ["api_access"],
        "outbound_campaigns": ["outbound_campaigns", "outbound_assistant"],
    }

    @classmethod
    def _normalize_feature(cls, feature: str) -> str:
        f = (feature or "").strip().lower()
        for canonical, aliases in cls.FEATURE_ALIASES.items():
            if f == canonical or f in aliases:
                return canonical
        return f

    @classmethod
    def _feature_matches_override(cls, override_map: Dict[str, Any], feature: str) -> Optional[bool]:
        if not override_map:
            return None
        normalized = cls._normalize_feature(feature)
        # Accept both exact and alias keys in stored overrides.
        for key, value in override_map.items():
            if cls._normalize_feature(str(key)) == normalized:
                return bool(value)
        return None

    @classmethod
    def _has_plan_feature(cls, features: Dict[str, Any], feature: str) -> bool:
        normalized = cls._normalize_feature(feature)
        aliases = cls.FEATURE_ALIASES.get(normalized, [normalized])
        return any(bool(features.get(k)) for k in aliases)
    
    async def can_access_feature(
        self,
        user_id: str,
        feature: str,
        session: AsyncSession
    ) -> bool:
        """Check if user can access a feature"""
        user_row = await session.execute(select(User).where(User.id == user_id))
        user = user_row.scalar_one_or_none()
        allowed_admins = {e.strip().lower() for e in (settings.ADMIN_EMAILS or "").split(",") if e.strip()}
        if user and user.email and user.email.lower() in allowed_admins:
            return True

        override_setting = await session.get(SystemSetting, "user_access_overrides_v1")
        override = {}
        if override_setting and override_setting.value and user and user.email:
            try:
                payload = json.loads(override_setting.value)
                override = (payload or {}).get(user.email.lower(), {}) or {}
            except Exception:
                override = {}

        if override.get("block_all"):
            return False
        if override.get("allow_all"):
            return True
        feature_overrides = override.get("feature_overrides") or {}
        override_decision = self._feature_matches_override(feature_overrides, feature)
        if override_decision is not None:
            return override_decision
        
        # Get subscription
        result = await session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscription = result.scalar()

        plan_id = None
        plan_features: Dict[str, Any] = {}
        has_active_subscription = bool(subscription and subscription.status == "active")

        if subscription:
            plan_id = subscription.plan_id
            if isinstance(subscription.features, dict) and subscription.features:
                plan_features = subscription.features
            else:
                plan_features = SUBSCRIPTION_PLANS.get(plan_id, {}).get("features", {}) or {}
        elif user:
            # Fallback for legacy users that may have plan fields but missing Subscription row.
            plan_id = (getattr(user, "plan", None) or "personal").lower()
            plan_features = SUBSCRIPTION_PLANS.get(plan_id, {}).get("features", {}) or {}

        normalized_feature = self._normalize_feature(feature)
        if normalized_feature in {"email_classification", "action_extraction", "thread_summarization", "sentiment_analysis"}:
            # AI capability availability is plan-based. Credit balance enforcement happens in CreditService.
            if has_active_subscription:
                return True
            return plan_id in SUBSCRIPTION_PLANS

        if normalized_feature in {"shared_inbox", "workflow_automation", "crm_sync", "advanced_analytics", "api_access", "outbound_campaigns"}:
            return self._has_plan_feature(plan_features, normalized_feature)

        # Unknown features are allowed by default to avoid hard failures on newly introduced flags.
        return True
    
    async def enforce_team_limit(
        self,
        user_id: str,
        session: AsyncSession
    ) -> bool:
        """Check if user can add more team members"""
        
        result = await session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscription = result.scalar()
        
        if not subscription:
            return False
        
        return (subscription.seats_current or 0) < (subscription.seats_max or subscription.seats_included or 0)


class PaymentService:
    """Handle payment processing with Paystack (primary), PayPal, Coinbase Commerce and Stripe."""
    
    def __init__(self):
        self.paystack = PaystackService()
        self.paypal = PayPalService()
        self.coinbase = CoinbaseCommerceService()
        self.bybit = BybitPayService()
        self.stripe = StripeService()
        self.credit_service = CreditService()
        self._fx_rate_cache: Dict[str, Dict[str, Any]] = {}

    async def _create_payment_row(
        self,
        session: AsyncSession,
        user_id: str,
        provider: str,
        amount_usd: float,
        currency: str,
        reference: Optional[str],
        status: str = "pending",
    ) -> None:
        if not reference:
            return

        existing_res = await session.execute(
            select(Payment).where(Payment.reference == reference)
        )
        if existing_res.scalar_one_or_none():
            return

        payment = Payment(
            user_id=user_id,
            provider=provider,
            amount=amount_usd,
            currency=currency,
            status=status,
            reference=reference,
        )
        session.add(payment)

    def get_credit_pack_price_usd(self, credits: int) -> Optional[float]:
        return CREDIT_PACK_PRICING_USD.get(int(credits))

    def _is_paystack_configured(self) -> bool:
        api_key = self.paystack.api_key or ""
        # Server-side Paystack calls require secret key (sk_*)
        return bool(api_key and api_key.startswith("sk_"))

    def _is_paypal_configured(self) -> bool:
        return bool(self.paypal.client_id and self.paypal.client_secret)

    def _is_coinbase_configured(self) -> bool:
        return bool(self.coinbase.api_key)

    def _is_bybit_configured(self) -> bool:
        return self.bybit.is_configured()

    def _is_stripe_configured(self) -> bool:
        return self.stripe.is_configured()

    def _paystack_supported_currencies(self) -> set:
        raw = (settings.PAYSTACK_SUPPORTED_CURRENCIES or "").strip()
        values = {item.strip().upper() for item in raw.split(",") if item.strip()}
        return values or {"NGN"}

    def _conversion_rate_for_currency_fallback(self, currency: str) -> float:
        rates = {
            "USD": 1,
            "NGN": 1500,
            "KES": 150,
            "GHS": 13,
            "ZAR": 19,
            "UGX": 4000,
            "TZS": 2500,
            "RWF": 1300,
        }
        return float(rates.get((currency or "USD").upper(), 1))

    async def _conversion_rate_for_currency(self, currency: str) -> float:
        target = (currency or "USD").upper()
        if target == "USD":
            return 1.0

        if not settings.ENABLE_LIVE_FX_RATES:
            return self._conversion_rate_for_currency_fallback(target)

        now = datetime.utcnow()
        cache_minutes = max(1, int(getattr(settings, "FX_RATE_CACHE_MINUTES", 15) or 15))
        cached = self._fx_rate_cache.get(target)
        if cached and isinstance(cached.get("ts"), datetime):
            if now - cached["ts"] < timedelta(minutes=cache_minutes):
                return float(cached.get("rate", 1.0))

        try:
            api_base = (settings.FX_RATE_API_BASE_URL or "https://api.exchangerate.host").rstrip("/")
            params = {"from": "USD", "to": target, "amount": 1}
            if settings.FX_RATE_API_KEY:
                params["access_key"] = settings.FX_RATE_API_KEY

            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(f"{api_base}/convert", params=params)
                resp.raise_for_status()
                data = resp.json() or {}

            rate = None
            info = data.get("info") if isinstance(data, dict) else None
            if isinstance(info, dict):
                rate = info.get("rate")
            if rate is None:
                result = data.get("result") if isinstance(data, dict) else None
                if isinstance(result, (int, float)):
                    rate = result

            if isinstance(rate, (int, float)) and float(rate) > 0:
                self._fx_rate_cache[target] = {"rate": float(rate), "ts": now}
                return float(rate)

        except Exception as e:
            logger.warning(
                f"⚠️ [PaymentService] Live FX lookup failed for USD->{target}; using fallback rate. Error={str(e)}"
            )

        return self._conversion_rate_for_currency_fallback(target)

    def _is_currency_unsupported_error(self, message: str) -> bool:
        text = (message or "").lower()
        return "currency" in text and "supported" in text

    def _paystack_charge_currency(self, detected_local_currency: str = "USD") -> str:
        """
        Determine actual currency to send to Paystack.
        If PAYSTACK_FORCE_CURRENCY is set, it always wins (e.g., KES settlement strategy).
        """
        forced = (settings.PAYSTACK_FORCE_CURRENCY or "").strip().upper()
        if forced:
            return forced
        return (detected_local_currency or "USD").upper()

    async def detect_country_code_from_ip(self, ip_address: Optional[str]) -> str:
        """Resolve ISO country code from IP with safe fallback to US."""
        if not settings.ENABLE_GEOIP_DETECTION:
            return "US"

        ip = (ip_address or "").strip()
        if not ip or ip in {"127.0.0.1", "::1", "localhost"}:
            return "US"

        try:
            base = (settings.GEOIP_API_BASE_URL or "https://ipapi.co").rstrip("/")
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(f"{base}/{ip}/json/")
                resp.raise_for_status()
                data = resp.json() or {}
            country = (data.get("country_code") or "US").upper()
            return country if len(country) == 2 else "US"
        except Exception as e:
            logger.warning(f"⚠️ [PaymentService] GeoIP lookup failed for ip={ip}: {str(e)}")
            return "US"
    
    def get_available_payment_methods(self, country_code: str) -> list:
        """
        Get available payment methods based on user's country
        
        Args:
            country_code: ISO 2-letter country code (e.g., "KE", "NG", "US")
        
        Returns:
            List of available payment method dictionaries
        """
        # Paystack coverage: Africa (Nigeria, Kenya, Ghana, South Africa, etc.)
        paystack_countries = {
            "NG": "Nigeria",  # Paystack primary market
            "KE": "Kenya",    # M-Pesa support
            "GH": "Ghana",    # Mobile Money
            "ZA": "South Africa",  # Mobile Money
            "UG": "Uganda",
            "TZ": "Tanzania",
            "RW": "Rwanda",
        }
        
        country_code = country_code.upper() if country_code else "US"
        
        methods = []
        
        # Determine which processors to use
        use_paystack = country_code in paystack_countries and self._is_paystack_configured()
        use_paypal = self._is_paypal_configured()
        
        if use_paystack:
            # Paystack methods by country
            if country_code == "KE":
                methods.extend([
                    {"id": "mpesa", "name": "M-Pesa", "processor": "paystack", "region": "Kenya"},
                    {"id": "card", "name": "Debit/Credit Card", "processor": "paystack", "region": "Global"},
                    {"id": "bank_transfer", "name": "Bank Transfer", "processor": "paystack", "region": "Kenya"},
                ])
            elif country_code == "NG":
                methods.extend([
                    {"id": "card", "name": "Visa/Mastercard/Verve", "processor": "paystack", "region": "Nigeria"},
                    {"id": "ussd", "name": "USSD", "processor": "paystack", "region": "Nigeria"},
                    {"id": "bank_transfer", "name": "Bank Transfer", "processor": "paystack", "region": "Nigeria"},
                    {"id": "qr", "name": "QR Payment", "processor": "paystack", "region": "Nigeria (optional)"},
                ])
            elif country_code == "GH":
                methods.extend([
                    {"id": "card", "name": "Debit/Credit Card", "processor": "paystack", "region": "Ghana"},
                    {"id": "mobile_money", "name": "MTN Mobile Money | AirtelTigo", "processor": "paystack", "region": "Ghana"},
                    {"id": "bank_transfer", "name": "Bank Transfer", "processor": "paystack", "region": "Ghana"},
                ])
            elif country_code == "ZA":
                methods.extend([
                    {"id": "card", "name": "Debit/Credit Card", "processor": "paystack", "region": "South Africa"},
                    {"id": "mobile_money", "name": "Vodacom Mobile Money", "processor": "paystack", "region": "South Africa"},
                    {"id": "bank_transfer", "name": "Bank Transfer", "processor": "paystack", "region": "South Africa"},
                ])
            else:
                # Default Paystack methods for other African countries
                methods.extend([
                    {"id": "card", "name": "Debit/Credit Card", "processor": "paystack", "region": "Africa"},
                    {"id": "mobile_money", "name": "Mobile Money", "processor": "paystack", "region": "Africa"},
                    {"id": "bank_transfer", "name": "Bank Transfer", "processor": "paystack", "region": "Africa"},
                ])
        
        # Global card rails and wallets
        if use_paypal:
            methods.extend([
                {"id": "paypal", "name": "PayPal", "processor": "paypal", "description": "PayPal wallet, cards, bank transfer", "region": "Global"},
                {"id": "apple_pay", "name": "Apple Pay", "processor": "paypal", "description": "Apple Pay via PayPal checkout", "region": "Global"},
                {"id": "google_pay", "name": "Google Pay", "processor": "paypal", "description": "Google Pay via PayPal checkout", "region": "Global"},
            ])
        # Add PayPal as fallback/primary for non-Paystack regions
        if use_paypal:
            methods.append({
                "id": "card_international",
                "name": "International Cards",
                "processor": "paypal",
                "description": "Visa, Mastercard, Amex, Discover",
                "region": "Global"
            })
            methods.extend([
                {"id": "sepa_debit", "name": "SEPA Direct Debit", "processor": "paypal", "region": "Europe"},
                {"id": "ideal", "name": "iDEAL", "processor": "paypal", "region": "Netherlands"},
                {"id": "sofort", "name": "Sofort", "processor": "paypal", "region": "Germany/Austria"},
                {"id": "bancontact", "name": "Bancontact", "processor": "paypal", "region": "Belgium"},
                {"id": "eps", "name": "EPS", "processor": "paypal", "region": "Austria"},
                {"id": "p24", "name": "Przelewy24", "processor": "paypal", "region": "Poland"},
                {"id": "blik", "name": "BLIK", "processor": "paypal", "region": "Poland"},
                {"id": "multibanco", "name": "Multibanco", "processor": "paypal", "region": "Portugal"},
                {"id": "pix", "name": "PIX", "processor": "paypal", "region": "Brazil"},
                {"id": "boleto", "name": "Boleto", "processor": "paypal", "region": "Brazil"},
                {"id": "alipay", "name": "Alipay", "processor": "paypal", "region": "China"},
                {"id": "wechat_pay", "name": "WeChat Pay", "processor": "paypal", "region": "China"},
                {"id": "upi", "name": "UPI", "processor": "paypal", "region": "India"},
                {"id": "net_banking", "name": "NetBanking", "processor": "paypal", "region": "India"},
                {"id": "paytm", "name": "Paytm Wallet", "processor": "paypal", "region": "India"},
                {"id": "grabpay", "name": "GrabPay", "processor": "paypal", "region": "Southeast Asia"},
                {"id": "gcash", "name": "GCash", "processor": "paypal", "region": "Philippines"},
                {"id": "paynow", "name": "PayNow", "processor": "paypal", "region": "Singapore"},
                {"id": "fpx", "name": "FPX", "processor": "paypal", "region": "Malaysia"},
                {"id": "klarna", "name": "Klarna", "processor": "paypal", "region": "Global"},
                {"id": "afterpay", "name": "Afterpay/Clearpay", "processor": "paypal", "region": "Global"},
            ])

        # Add crypto options globally (powered by Bybit Pay when configured)
        if self._is_bybit_configured() or self._is_coinbase_configured():
            methods.extend([
                {
                    "id": "crypto",
                    "name": "Crypto (auto)",
                    "processor": "bybit" if self._is_bybit_configured() else "coinbase",
                    "description": "Pay with supported assets via Bybit Pay",
                    "region": "Global"
                },
                {
                    "id": "crypto_btc",
                    "name": "Bitcoin (BTC)",
                    "processor": "bybit" if self._is_bybit_configured() else "coinbase",
                    "description": "Bitcoin payment",
                    "region": "Global"
                },
                {
                    "id": "crypto_eth",
                    "name": "Ethereum (ETH)",
                    "processor": "bybit" if self._is_bybit_configured() else "coinbase",
                    "description": "Ethereum payment",
                    "region": "Global"
                },
                {
                    "id": "crypto_usdc",
                    "name": "USDC",
                    "processor": "bybit" if self._is_bybit_configured() else "coinbase",
                    "description": "USD Coin stablecoin payment",
                    "region": "Global"
                },
            ])

        # Absolute fallback: if no region-specific option exists but Paystack is configured,
        # still expose card checkout so upgrades can proceed.
        if not methods and self._is_paystack_configured():
            methods.append(
                {"id": "card", "name": "Debit/Credit Card", "processor": "paystack", "region": "Global"}
            )

        return methods
    
    async def get_currency_for_country(self, country_code: str) -> tuple:
        """
        Get the currency and conversion rate for a country
        
        Args:
            country_code: ISO 2-letter country code
        
        Returns:
            Tuple of (currency_code, amount_in_local_currency)
        """
        country_code = country_code.upper() if country_code else "US"
        
        # Currency mappings and approximate USD conversion rates
        currencies = {
            "NG": ("NGN", 1500),  # Nigerian Naira (1 USD = ~1500 NGN)
            "KE": ("KES", 150),   # Kenyan Shilling (1 USD = ~150 KES)
            "GH": ("GHS", 13),    # Ghanaian Cedi (1 USD = ~13 GHS)
            "ZA": ("ZAR", 19),    # South African Rand (1 USD = ~19 ZAR)
            "UG": ("UGX", 4000),  # Ugandan Shilling
            "TZ": ("TZS", 2500),  # Tanzanian Shilling
            "RW": ("RWF", 1300),  # Rwandan Franc
        }
        
        if country_code in currencies:
            currency, _ = currencies[country_code]
            rate = await self._conversion_rate_for_currency(currency)
            return currency, rate
        return "USD", 1  # Default to USD

    def _paystack_channels_for_method(self, payment_method: str) -> Optional[List[str]]:
        """
        Map frontend payment method to Paystack channels.
        """
        channel_map = {
            "card": ["card"],
            "mpesa": ["mobile_money"],
            "mobile_money": ["mobile_money"],
            "bank_transfer": ["bank_transfer"],
            "ussd": ["ussd"],
            "qr": ["qr"],
        }
        return channel_map.get(payment_method)
    async def initialize_credit_purchase(
        self,
        user_id: str,
        email: str,
        credits: int,
        amount_minor: int,
        currency: str,
        amount_usd: float,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Initialize a credit top-up purchase"""
        expected_usd = self.get_credit_pack_price_usd(credits)
        if expected_usd is None:
            return {
                "success": False,
                "message": "Invalid credit pack. Use one of: 1000, 5000, 10000",
            }
        amount_usd = float(expected_usd)

        # Create payment transaction record
        reference = f"{user_id}-{int(datetime.utcnow().timestamp())}"
        transaction = PaymentTransaction(
            user_id=user_id,
            tenant_id=user_id,  # Use user_id as tenant for now
            amount_usd=amount_usd,
            currency=currency,
            payment_method="paystack",
            payment_reference=reference,
            charge_type="credit_topup",
            reference_id=None,
            status="pending"
        )
        transaction.payment_metadata = {
            "credits": credits,
            "local_amount_minor": amount_minor,
            "local_currency": currency
        }
        
        session.add(transaction)
        await self._create_payment_row(
            session=session,
            user_id=user_id,
            provider="paystack",
            amount_usd=amount_usd,
            currency=currency,
            reference=reference,
            status="pending",
        )
        await session.flush()
        
        # Initialize Paystack payment
        result = await self.paystack.initialize_payment(
            email=email,
            amount=amount_minor,
            reference=reference,
            metadata={
                "user_id": user_id,
                "credits": credits,
                "transaction_id": transaction.id
            }
        )
        
        if result.get("success"):
            return {
                "success": True,
                "authorization_url": result["authorization_url"],
                "transaction_id": transaction.id,
                "reference": result["reference"]
            }
        else:
            transaction.status = "failed"
            transaction.failure_reason = result.get("message")
            payment_row = await session.execute(select(Payment).where(Payment.reference == reference))
            payment = payment_row.scalar_one_or_none()
            if payment:
                payment.status = "failed"
            return {"success": False, "message": result.get("message")}
    
    async def handle_payment_callback(
        self,
        reference: str,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Handle Paystack payment callback"""
        
        # Verify payment
        verification = await self.paystack.verify_payment(reference)
        
        if not verification.get("success"):
            return {"success": False, "message": "Payment verification failed"}
        
        # Update transaction
        result = await session.execute(
            select(PaymentTransaction).where(
                PaymentTransaction.payment_reference == reference,
                PaymentTransaction.charge_type == "credit_topup"
            )
        )
        transaction = result.scalar()
        
        if not transaction:
            return {"success": False, "message": "Transaction not found"}
        
        transaction.status = "completed"
        transaction.completed_at = datetime.utcnow()
        payment_row = await session.execute(select(Payment).where(Payment.reference == reference))
        payment = payment_row.scalar_one_or_none()
        if payment:
            payment.status = "completed"
        
        # Add credits
        credits = 0
        if transaction.payment_metadata and transaction.payment_metadata.get("credits"):
            credits = int(transaction.payment_metadata.get("credits"))

        success = await self.credit_service.add_credits(
            transaction.user_id,
            credits,
            "credit_purchase",
            session
        )
        
        if success:
            return {
                "success": True,
                "message": "Credits added successfully",
                "transaction_id": transaction.id,
                "credits_added": credits
            }
        else:
            transaction.status = "failed"
            transaction.failure_reason = "Failed to add credits"
            if payment:
                payment.status = "failed"
            return {"success": False, "message": "Failed to add credits"}

    async def create_upgrade_session(
        self,
        user_id: str,
        user_email: str,
        plan_id: str,
        payment_method: Optional[str],
        session: AsyncSession,
        country_code: str = None,
        frontend_url: str = None,
        prefer_local_currency: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a payment session for subscription upgrade
        
        Supports both Paystack and PayPal with multiple payment methods via Paystack
        
        Args:
            user_id: User ID upgrading
            user_email: User email for payment
            plan_id: Target plan ID
            payment_method: Payment method ID (card, mpesa, bank_transfer, paypal, etc.)
            session: Database session
            country_code: User's country code for region-aware routing
            frontend_url: Frontend base URL for redirects
        
        Returns:
            dict with authorization_url, approval_url, or success flag
        """
        try:
            if plan_id not in SUBSCRIPTION_PLANS:
                return {"success": False, "message": f"Invalid plan: {plan_id}"}
            
            plan = SUBSCRIPTION_PLANS[plan_id]
            amount_usd = plan.get("price", 0)
            plan_name = plan.get("name", "")
            
            # Free plan
            if amount_usd == 0:
                return {"success": False, "message": "Cannot process payment for free plan"}
            
            # Resolve requested method against configured providers.
            requested_payment_method = (payment_method or "auto").strip().lower()
            payment_method = requested_payment_method
            available_methods = self.get_available_payment_methods(country_code or "US")
            available_ids = {m.get("id") for m in available_methods}
            is_auto_request = requested_payment_method in {"", "auto", "default"}

            if not available_methods:
                return {
                    "success": False,
                    "message": (
                        "No payment providers are configured. Configure at least one of: "
                        "Paystack, PayPal, Coinbase Commerce."
                    ),
                }

            if is_auto_request:
                # Default to card, but keep provider-native alternatives available at checkout.
                payment_method = "card" if "card" in available_ids else available_methods[0]["id"]
            elif payment_method not in available_ids:
                payment_method = "card" if "card" in available_ids else available_methods[0]["id"]
                logger.warning(
                    f"⚠️ [PaymentService] Requested method '{requested_payment_method}' is unavailable. "
                    f"Falling back to '{payment_method}'."
                )

            # Special-case: treat "card_international" as a generic card request.
            # Prefer Paystack card flow when Paystack is configured for the region;
            # otherwise leave it to the PayPal branch below as a global card option.
            if payment_method == "card_international":
                if self._is_paystack_configured():
                    logger.info(
                        "🔀 [PaymentService] 'card_international' requested — using Paystack 'card' flow because Paystack is configured."
                    )
                    payment_method = "card"
                else:
                    logger.info(
                        "🔀 [PaymentService] 'card_international' requested — Paystack not configured, will use PayPal card rails."
                    )
            # If the frontend explicitly requested 'card' but the country-specific
            # available_methods didn't include it, prefer Paystack when configured
            # (user explicitly asked for card checkout).
            elif requested_payment_method == "card" and self._is_paystack_configured():
                logger.info(
                    "🔀 [PaymentService] Explicit 'card' requested — routing to Paystack 'card' because Paystack is configured."
                )
                payment_method = "card"

            # Determine processor based on payment method
            paypal_family_methods = {
                "paypal", "apple_pay", "google_pay", "card_international",
                "sepa_debit", "ideal", "sofort", "bancontact", "eps", "p24", "blik", "multibanco",
                "pix", "boleto", "alipay", "wechat_pay", "upi", "net_banking", "paytm",
                "grabpay", "gcash", "paynow", "fpx", "klarna", "afterpay",
            }

            if payment_method in paypal_family_methods:
                logger.info(f"Creating PayPal order for user {user_id} plan {plan_id}")
                
                result = await self.paypal.create_order(
                    user_email=user_email,
                    plan_id=plan_id,
                    plan_name=plan_name,
                    amount_usd=amount_usd,
                    user_id=user_id,
                    return_url=frontend_url or settings.FRONTEND_URL
                )
                
                if result.get("success"):
                    # Record pending transaction
                    transaction = PaymentTransaction(
                        user_id=user_id,
                        tenant_id=user_id,
                        amount_usd=amount_usd,
                        currency="USD",
                        payment_method="paypal",
                        payment_reference=result.get("order_id"),
                        charge_type="subscription_upgrade",
                        reference_id=plan_id,
                        status="pending",
                    )
                    transaction.payment_metadata = {
                        "plan_id": plan_id,
                        "order_id": result.get("order_id"),
                        "payment_method": payment_method
                    }
                    session.add(transaction)
                    await self._create_payment_row(
                        session=session,
                        user_id=user_id,
                        provider="paypal",
                        amount_usd=amount_usd,
                        currency="USD",
                        reference=result.get("order_id"),
                        status="pending",
                    )
                    await session.flush()
                    
                    return {
                        "success": True,
                        "approval_url": result["approval_url"],
                        "order_id": result["order_id"],
                        "amount": amount_usd,
                        "plan_id": plan_id,
                        "processor": "paypal",
                        "requested_payment_method": requested_payment_method,
                        "resolved_payment_method": payment_method,
                    }
                else:
                    return result
            
            # Crypto payment via Bybit Pay (primary) or Coinbase fallback
            elif payment_method in ["crypto", "coinbase", "crypto_btc", "crypto_eth", "crypto_usdc"]:
                order_ref = f"{user_id}-crypto-{plan_id}-{int(datetime.utcnow().timestamp())}"
                result = None
                hosted = None
                charge_id = None
                processor = "coinbase"

                if self._is_bybit_configured():
                    logger.info(f"🔗 [Crypto] Creating Bybit Pay order for user {user_id} plan {plan_id}")
                    bybit_res = await self.bybit.create_order(
                        order_id=order_ref,
                        amount_usd=amount_usd,
                        return_url=frontend_url or settings.FRONTEND_URL,
                    )
                    if bybit_res.get("success"):
                        result = bybit_res
                        hosted = bybit_res.get("checkout_url")
                        charge_id = order_ref
                        processor = "bybit"
                    else:
                        logger.warning(f"⚠️ [Crypto] Bybit unavailable, trying Coinbase fallback: {bybit_res.get('message')}")

                if result is None and self._is_coinbase_configured():
                    logger.info(f"🔗 [Crypto] Creating Coinbase Commerce charge for user {user_id} plan {plan_id}")
                    coinbase_res = await self.coinbase.create_charge(
                        name=f"{plan_name} subscription",
                        description=f"Upgrade to {plan_name} ({plan_id})",
                        amount_usd=amount_usd,
                        metadata={"user_id": user_id, "plan_id": plan_id}
                    )
                    if coinbase_res.get("success"):
                        result = coinbase_res
                        hosted = coinbase_res.get("hosted_url")
                        charge_id = coinbase_res.get("charge_id")
                        processor = "coinbase"
                    else:
                        result = coinbase_res

                if result and result.get("success"):
                    
                    transaction = PaymentTransaction(
                        user_id=user_id,
                        tenant_id=user_id,
                        amount_usd=amount_usd,
                        currency="USD",
                        payment_method="crypto",
                        payment_reference=charge_id or order_ref,
                        charge_type="subscription_upgrade",
                        reference_id=plan_id,
                        status="pending",
                    )
                    transaction.payment_metadata = {
                        "plan_id": plan_id,
                        "charge_id": charge_id,
                        "hosted_url": hosted,
                        "processor": processor,
                    }
                    session.add(transaction)
                    await self._create_payment_row(
                        session=session,
                        user_id=user_id,
                        provider=processor,
                        amount_usd=amount_usd,
                        currency="USD",
                        reference=charge_id or order_ref,
                        status="pending",
                    )
                    await session.flush()

                    return {
                        "success": True,
                        "checkout_url": hosted,
                        "charge_id": charge_id,
                        "amount": amount_usd,
                        "plan_id": plan_id,
                        "processor": processor,
                        "payment_method": "crypto",
                        "currency": "USD",
                        "requested_payment_method": requested_payment_method,
                        "resolved_payment_method": payment_method,
                    }
                else:
                    logger.error(f"❌ [Crypto] Charge creation failed: {(result or {}).get('message')}")
                    return {"success": False, "message": (result or {}).get("message", "Crypto checkout not available")}

            # Paystack payment methods (card, mpesa, bank_transfer, mobile_money, ussd, qr)
            elif payment_method in ["card", "mpesa", "bank_transfer", "mobile_money", "ussd", "qr", "stripe"]:
                paystack_method = "card" if payment_method == "stripe" else payment_method
                logger.info(
                    f"💰 [Paystack] Creating Paystack payment for user {user_id} "
                    f"plan {plan_id} method {paystack_method}"
                )

                supported_currencies = self._paystack_supported_currencies()
                local_currency, _ = await self.get_currency_for_country(country_code)
                fallback_currency = (settings.PAYSTACK_FALLBACK_CURRENCY or "NGN").upper()
                charge_currency = (getattr(settings, "BILLING_CHARGE_CURRENCY", "USD") or "USD").upper()
                strict_usd = bool(getattr(settings, "BILLING_STRICT_USD", True))
                fx_buffer = float(getattr(settings, "BILLING_FX_BUFFER_PERCENT", 0.0) or 0.0)
                preferred_currency = local_currency if prefer_local_currency else charge_currency

                # Try preferred currency first, then fallback, then other configured/common currencies.
                paystack_currency = self._paystack_charge_currency(local_currency)
                if strict_usd:
                    candidate_currencies: List[str] = [paystack_currency]
                    logger.info(
                        f"💵 [Billing] Strict USD base pricing enabled. Paystack checkout currency: {paystack_currency}"
                    )
                else:
                    candidate_currencies = []
                    for cur in [paystack_currency, preferred_currency, fallback_currency]:
                        cur_u = (cur or "").upper()
                        if cur_u and cur_u not in candidate_currencies:
                            candidate_currencies.append(cur_u)
                    for cur in list(supported_currencies) + ["NGN", "KES", "GHS", "ZAR", "USD"]:
                        cur_u = (cur or "").upper()
                        if cur_u and cur_u not in candidate_currencies:
                            candidate_currencies.append(cur_u)

                reference = f"{user_id}-upgrade-{plan_id}-{int(datetime.utcnow().timestamp())}"
                logger.info(f"📝 [Paystack] Payment reference: {reference}")
                channels = None if is_auto_request else self._paystack_channels_for_method(paystack_method)

                result = None
                currency = None
                conversion_rate = 1.0
                amount_minor = 0
                currency_fallback_applied = False
                currency_fallback_reason = None
                attempted_currencies: List[str] = []

                for idx, candidate_currency in enumerate(candidate_currencies):
                    candidate_rate = await self._conversion_rate_for_currency(candidate_currency)
                    buffered_rate = candidate_rate * (1 + (fx_buffer / 100.0))
                    candidate_amount_minor = int(round(amount_usd * buffered_rate * 100))
                    attempted_currencies.append(candidate_currency)
                    logger.info(
                        f"💱 [Paystack] Attempt {idx + 1}/{len(candidate_currencies)} charging {candidate_currency}: "
                        f"${amount_usd} -> {candidate_amount_minor} {candidate_currency} (minor), "
                        f"fx_rate={candidate_rate}, fx_buffer={fx_buffer}%"
                    )

                    attempt = await self.paystack.initialize_payment(
                        email=user_email,
                        amount=candidate_amount_minor,
                        reference=reference,
                        metadata={
                            "user_id": user_id,
                            "plan_id": plan_id,
                            "transaction_type": "subscription_upgrade",
                            "amount_usd": amount_usd,
                            "payment_method": paystack_method,
                            "currency": candidate_currency,
                            "base_currency": charge_currency,
                            "fx_rate": candidate_rate,
                            "fx_buffer_percent": fx_buffer,
                            "prefer_local_currency": prefer_local_currency,
                        },
                        currency=candidate_currency,
                        channels=channels,
                    )
                    logger.info(f"🔄 [Paystack] Response: success={attempt.get('success')}")

                    if attempt.get("success"):
                        result = attempt
                        currency = candidate_currency
                        conversion_rate = buffered_rate
                        amount_minor = candidate_amount_minor
                        currency_fallback_applied = idx > 0
                        if currency_fallback_applied:
                            currency_fallback_reason = (
                                f"Gateway rejected prior currency option(s); successful with {candidate_currency}."
                            )
                        break

                    # Continue trying only for unsupported currency errors.
                    if not self._is_currency_unsupported_error(attempt.get("message", "")):
                        result = attempt
                        break

                if result and result.get("success"):
                    logger.info(f"✅ [Paystack] Authorization URL obtained")
                    # Record pending transaction
                    transaction = PaymentTransaction(
                        user_id=user_id,
                        tenant_id=user_id,
                        amount_usd=amount_usd,
                        currency=currency,
                        payment_method="paystack",
                        payment_reference=reference,
                        charge_type="subscription_upgrade",
                        reference_id=plan_id,
                        status="pending",
                    )
                    transaction.payment_metadata = {
                        "plan_id": plan_id,
                        "reference": reference,
                        "payment_method": paystack_method,
                        "local_currency": currency,
                        "local_amount_minor": amount_minor,
                        "exchange_rate": conversion_rate,
                        "fx_buffer_percent": fx_buffer,
                        "base_currency": charge_currency,
                    }
                    session.add(transaction)
                    await self._create_payment_row(
                        session=session,
                        user_id=user_id,
                        provider="paystack",
                        amount_usd=amount_usd,
                        currency=currency,
                        reference=reference,
                        status="pending",
                    )
                    await session.flush()
                    
                    return {
                        "success": True,
                        "authorization_url": result["authorization_url"],
                        "reference": reference,
                        "amount": amount_usd,
                        "plan_id": plan_id,
                        "processor": "paystack",
                        "payment_method": paystack_method,
                        "currency": currency,
                        "display_amount": amount_usd if currency == "USD" else round(amount_usd * conversion_rate, 2),
                        "display_currency": currency,
                        "currency_fallback_applied": currency_fallback_applied,
                        "currency_fallback_reason": currency_fallback_reason,
                        "requested_payment_method": requested_payment_method,
                        "resolved_payment_method": paystack_method,
                    }
                else:
                    # For auto checkout, try global processor fallback instead of hard-failing.
                    if self._is_paypal_configured() and (is_auto_request or strict_usd):
                        logger.warning(
                            "⚠️ [Paystack] Paystack currency attempt(s) failed. Falling back to PayPal."
                        )
                        paypal_result = await self.paypal.create_order(
                            user_email=user_email,
                            plan_id=plan_id,
                            plan_name=plan_name,
                            amount_usd=amount_usd,
                            user_id=user_id,
                            return_url=frontend_url or settings.FRONTEND_URL
                        )
                        if paypal_result.get("success"):
                            transaction = PaymentTransaction(
                                user_id=user_id,
                                tenant_id=user_id,
                                amount_usd=amount_usd,
                                currency="USD",
                                payment_method="paypal",
                                payment_reference=paypal_result.get("order_id"),
                                charge_type="subscription_upgrade",
                                reference_id=plan_id,
                                status="pending",
                            )
                            transaction.payment_metadata = {
                                "plan_id": plan_id,
                                "order_id": paypal_result.get("order_id"),
                                "payment_method": "paypal",
                                "paystack_attempted_currencies": attempted_currencies,
                            }
                            session.add(transaction)
                            await self._create_payment_row(
                                session=session,
                                user_id=user_id,
                                provider="paypal",
                                amount_usd=amount_usd,
                                currency="USD",
                                reference=paypal_result.get("order_id"),
                                status="pending",
                            )
                            await session.flush()
                            return {
                                "success": True,
                                "approval_url": paypal_result["approval_url"],
                                "order_id": paypal_result["order_id"],
                                "amount": amount_usd,
                                "plan_id": plan_id,
                                "processor": "paypal",
                                "requested_payment_method": requested_payment_method,
                                "resolved_payment_method": "paypal",
                                "currency_fallback_applied": True,
                                "currency_fallback_reason": (
                                    f"Paystack currencies failed ({', '.join(attempted_currencies)}); switched to PayPal."
                                ),
                            }

                    error_message = (result or {}).get("message", "Unknown error")
                    logger.error(f"❌ [Paystack] Initialization failed: {error_message}")
                    return result or {
                        "success": False,
                        "message": "Paystack initialization failed for all attempted currencies",
                    }
            else:
                logger.error(f"❌ [PaymentService] Unsupported payment method: {payment_method}")
                return {"success": False, "message": f"Unsupported payment method: {payment_method}"}
        except Exception as e:
            logger.error(f"❌ [PaymentService] Error creating upgrade session: {str(e)}", exc_info=True)
            return {"success": False, "message": f"Failed to create payment session: {str(e)}"}
    
    async def process_upgrade_payment(
        self,
        transaction_id: str,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Process a completed upgrade payment and update subscription
    
        Args:
            transaction_id: Payment transaction ID
            session: Database session
    
        Returns:
            Result of the subscription update
        """
        try:
            # Get transaction
            result = await session.execute(
                select(PaymentTransaction).where(
                    PaymentTransaction.id == transaction_id
                )
            )
            transaction = result.scalar()
        
            if not transaction:
                return {"success": False, "message": "Transaction not found"}
        
            if transaction.status == "completed":
                return {"success": False, "message": "Transaction already processed"}
        
            # Verify payment with gateway
            verification_success = False
            if transaction.payment_method == "paypal":
                order_id = transaction.payment_metadata.get("order_id") if transaction.payment_metadata else None
                if order_id:
                    verify_result = await self.paypal.capture_order(order_id)
                    verification_success = verify_result.get("success", False)
                else:
                    verify_result = {"success": False, "message": "No order ID found"}
            elif transaction.payment_method == "paystack":
                verify_result = await self.paystack.verify_payment(
                    transaction.payment_reference
                )
                verification_success = verify_result.get("success", False)
            elif transaction.payment_method == "crypto":
                # Coinbase webhooks should mark/confirm settlement; for now
                # treat redirect flow as accepted and complete subscription.
                verify_result = {"success": True, "message": "Crypto payment accepted"}
                verification_success = True
            else:
                verify_result = {"success": False, "message": f"Unknown gateway: {transaction.payment_method}"}
            
            if not verification_success:
                transaction.status = "failed"
                transaction.failure_reason = verify_result.get("message", "Payment verification failed")
                payment_res = await session.execute(
                    select(Payment).where(Payment.reference == transaction.payment_reference)
                )
                payment = payment_res.scalar_one_or_none()
                if payment:
                    payment.status = "failed"
                return {"success": False, "message": "Payment verification failed"}
            
            # Update transaction status
            transaction.status = "completed"
            transaction.completed_at = datetime.utcnow()
            payment_res = await session.execute(
                select(Payment).where(Payment.reference == transaction.payment_reference)
            )
            payment = payment_res.scalar_one_or_none()
            if payment:
                payment.status = "completed"
            
            # Get subscription service
            subscription_service = SubscriptionService()
            plan_id = transaction.payment_metadata.get("plan_id") if transaction.payment_metadata else None
            
            if not plan_id:
                return {"success": False, "message": "Plan ID not found in transaction"}
            
            # Update user subscription
            await subscription_service.upgrade_subscription(
                transaction.user_id,
                plan_id,
                session
            )
            
            logger.info(f"✅ Subscription upgraded successfully for user {transaction.user_id} to plan {plan_id} via {transaction.payment_method}")
            
            return {
                "success": True,
                "message": f"Subscription upgraded to {plan_id}",
                "plan_id": plan_id,
                "amount": transaction.amount_usd,
                "payment_gateway": transaction.payment_method
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to process upgrade payment for transaction {transaction_id}: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to process payment: {str(e)}"
            }
