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
from app.services.billing.subscriptions import SubscriptionService


class CreditPurchaseMixin:
    async def initialize_credit_purchase(
        self,
        user_id: str,
        email: str,
        credits: int,
        amount_minor: int,
        currency: str,
        amount_usd: float,
        session: AsyncSession,
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
            status="pending",
        )
        transaction.payment_metadata = {
            "credits": credits,
            "local_amount_minor": amount_minor,
            "local_currency": currency,
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
            metadata={"user_id": user_id, "credits": credits, "transaction_id": transaction.id},
        )
        if result.get("success"):
            return {
                "success": True,
                "authorization_url": result["authorization_url"],
                "transaction_id": transaction.id,
                "reference": result["reference"],
            }
        else:
            transaction.status = "failed"
            transaction.failure_reason = result.get("message")
            payment_row = await session.execute(select(Payment).where(Payment.reference == reference))
            payment = payment_row.scalar_one_or_none()
            if payment:
                payment.status = "failed"
            return {"success": False, "message": result.get("message")}

    async def handle_payment_callback(self, reference: str, session: AsyncSession) -> Dict[str, Any]:
        """Handle Paystack payment callback"""
        # Verify payment
        verification = await self.paystack.verify_payment(reference)
        if not verification.get("success"):
            return {"success": False, "message": "Payment verification failed"}
        # Update transaction
        result = await session.execute(
            select(PaymentTransaction).where(
                PaymentTransaction.payment_reference == reference, PaymentTransaction.charge_type == "credit_topup"
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
        success = await self.credit_service.add_credits(transaction.user_id, credits, "credit_purchase", session)
        if success:
            return {
                "success": True,
                "message": "Credits added successfully",
                "transaction_id": transaction.id,
                "credits_added": credits,
            }
        else:
            transaction.status = "failed"
            transaction.failure_reason = "Failed to add credits"
            if payment:
                payment.status = "failed"
            return {"success": False, "message": "Failed to add credits"}


class PaymentFinalizeMixin:
    async def process_upgrade_payment(self, transaction_id: str, session: AsyncSession) -> Dict[str, Any]:
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
            result = await session.execute(select(PaymentTransaction).where(PaymentTransaction.id == transaction_id))
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
                verify_result = await self.paystack.verify_payment(transaction.payment_reference)
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
            await subscription_service.upgrade_subscription(transaction.user_id, plan_id, session)
            logger.info(
                f"✅ Subscription upgraded successfully for user {transaction.user_id} to plan {plan_id} via {transaction.payment_method}"
            )
            return {
                "success": True,
                "message": f"Subscription upgraded to {plan_id}",
                "plan_id": plan_id,
                "amount": transaction.amount_usd,
                "payment_gateway": transaction.payment_method,
            }
        except Exception as e:
            logger.error(f"❌ Failed to process upgrade payment for transaction {transaction_id}: {str(e)}")
            return {"success": False, "message": f"Failed to process payment: {str(e)}"}
