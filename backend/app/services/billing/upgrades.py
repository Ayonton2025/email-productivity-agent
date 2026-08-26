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


class UpgradeSessionMixin:
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
                "paypal",
                "apple_pay",
                "google_pay",
                "card_international",
                "sepa_debit",
                "ideal",
                "sofort",
                "bancontact",
                "eps",
                "p24",
                "blik",
                "multibanco",
                "pix",
                "boleto",
                "alipay",
                "wechat_pay",
                "upi",
                "net_banking",
                "paytm",
                "grabpay",
                "gcash",
                "paynow",
                "fpx",
                "klarna",
                "afterpay",
            }
            if payment_method in paypal_family_methods:
                logger.info(f"Creating PayPal order for user {user_id} plan {plan_id}")
                result = await self.paypal.create_order(
                    user_email=user_email,
                    plan_id=plan_id,
                    plan_name=plan_name,
                    amount_usd=amount_usd,
                    user_id=user_id,
                    return_url=frontend_url or settings.FRONTEND_URL,
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
                        "payment_method": payment_method,
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
                        logger.warning(
                            f"⚠️ [Crypto] Bybit unavailable, trying Coinbase fallback: {bybit_res.get('message')}"
                        )
                if result is None and self._is_coinbase_configured():
                    logger.info(f"🔗 [Crypto] Creating Coinbase Commerce charge for user {user_id} plan {plan_id}")
                    coinbase_res = await self.coinbase.create_charge(
                        name=f"{plan_name} subscription",
                        description=f"Upgrade to {plan_name} ({plan_id})",
                        amount_usd=amount_usd,
                        metadata={"user_id": user_id, "plan_id": plan_id},
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
                    candidate_currencies: List[str] = [preferred_currency]
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
                    logger.info("✅ [Paystack] Authorization URL obtained")
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
                        logger.warning("⚠️ [Paystack] Paystack currency attempt(s) failed. Falling back to PayPal.")
                        paypal_result = await self.paypal.create_order(
                            user_email=user_email,
                            plan_id=plan_id,
                            plan_name=plan_name,
                            amount_usd=amount_usd,
                            user_id=user_id,
                            return_url=frontend_url or settings.FRONTEND_URL,
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
