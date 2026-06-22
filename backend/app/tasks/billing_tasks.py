"""
Billing and subscription management background tasks
"""

from app.tasks.celery_app import celery_app as celery
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from app.models.database import AsyncSessionLocal
from app.models.billing_models import Subscription, AICredits, OutboundCredits
from app.core.security import logger
from app.tasks.async_runner import run_async


@celery.task(bind=True)
def reset_monthly_credits(self):
    """Sync wrapper to reset monthly credits for all active subscriptions."""
    return run_async(_reset_monthly_credits(self))


async def _reset_monthly_credits(self):
    """Async implementation that resets monthly credits."""
    try:
        async with AsyncSessionLocal() as session:
            # Reset only paid plans monthly.
            result = await session.execute(
                select(Subscription).where(
                    Subscription.status == "active",
                    Subscription.plan_id != "personal",
                )
            )
            subscriptions = result.scalars().all()

            reset_count = 0

            for subscription in subscriptions:
                try:
                    # Reset AI credits
                    ai_result = await session.execute(
                        select(AICredits).where(
                            AICredits.user_id == subscription.user_id
                        )
                    )
                    ai_credits = ai_result.scalar()

                    if ai_credits:
                        ai_credits.balance = ai_credits.monthly_allocation
                        ai_credits.monthly_used = 0
                        ai_credits.classification_used = 0
                        ai_credits.extraction_used = 0
                        ai_credits.summarization_used = 0
                        ai_credits.sentiment_analysis_used = 0
                        ai_credits.other_used = 0

                    # Reset outbound credits
                    out_result = await session.execute(
                        select(OutboundCredits).where(
                            OutboundCredits.user_id == subscription.user_id
                        )
                    )
                    outbound_credits = out_result.scalar()

                    if outbound_credits:
                        outbound_credits.balance = outbound_credits.monthly_allocation
                        outbound_credits.monthly_used = 0

                    # Reset subscription tracking
                    subscription.ai_credits_monthly_used = 0
                    subscription.outbound_emails_monthly_used = 0

                    reset_count += 1

                except Exception as e:
                    logger.error(f"Error resetting credits for subscription {subscription.id}: {str(e)}")
                    continue

            await session.commit()
            logger.info(f"Reset credits for {reset_count} subscriptions")
            return {"reset": reset_count, "status": "success"}

    except Exception as exc:
        logger.error(f"reset_monthly_credits failed: {str(exc)}")
        raise


@celery.task(bind=True)
def reset_daily_free_credits(self):
    """Sync wrapper to reset daily credits for free plan users."""
    return run_async(_reset_daily_free_credits(self))


async def _reset_daily_free_credits(self):
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Subscription).where(
                    Subscription.status == "active",
                    Subscription.plan_id == "personal",
                )
            )
            subscriptions = result.scalars().all()
            reset_count = 0
            for subscription in subscriptions:
                ai_result = await session.execute(
                    select(AICredits).where(AICredits.user_id == subscription.user_id)
                )
                ai_credits = ai_result.scalar_one_or_none()
                if not ai_credits:
                    continue

                daily_alloc = int(subscription.ai_credits_monthly_allocation or 50)
                ai_credits.balance = daily_alloc
                ai_credits.monthly_allocation = daily_alloc
                ai_credits.monthly_used = 0
                ai_credits.classification_used = 0
                ai_credits.extraction_used = 0
                ai_credits.summarization_used = 0
                ai_credits.sentiment_analysis_used = 0
                ai_credits.other_used = 0

                subscription.ai_credits_monthly_used = 0
                subscription.credits_used = 0
                reset_count += 1

            await session.commit()
            logger.info("Reset daily free credits for %s users", reset_count)
            return {"reset": reset_count, "status": "success"}
    except Exception as exc:
        logger.error("reset_daily_free_credits failed: %s", str(exc))
        raise


@celery.task(bind=True, max_retries=2)
def check_subscription_renewals(self):
    """Sync wrapper to check for subscriptions due for renewal."""
    return run_async(_check_subscription_renewals(self))


async def _check_subscription_renewals(self):
    """Async implementation that checks subscription renewals."""
    try:
        async with AsyncSessionLocal() as session:
            # Get subscriptions with auto-renew enabled that are near renewal date
            tomorrow = datetime.utcnow() + timedelta(days=1)

            result = await session.execute(
                select(Subscription).where(
                    and_(
                        Subscription.auto_renew == True,
                        Subscription.current_period_end <= tomorrow,
                        Subscription.status == "active"
                    )
                )
            )
            subscriptions = result.scalars().all()

            renewed = 0

            for subscription in subscriptions:
                try:
                    # Trigger renewal payment process
                    # This would integrate with Paystack or other payment gateway

                    # For now, just mark as pending renewal
                    subscription.renewal_date = datetime.utcnow() + timedelta(days=subscription.billing_cycle == "monthly" and 30 or 365)
                    renewed += 1

                except Exception as e:
                    logger.error(f"Error processing renewal for subscription {subscription.id}: {str(e)}")
                    continue

            await session.commit()
            logger.info(f"Processed {renewed} subscription renewals")
            return {"renewed": renewed, "status": "success"}

    except Exception as exc:
        logger.error(f"check_subscription_renewals failed: {str(exc)}")
        try:
            self.retry(exc=exc, countdown=300)
        except Exception:
            raise


@celery.task(bind=True, max_retries=1)
def charge_subscription(self, subscription_id: str):
    """Sync wrapper to charge a subscription payment."""
    return run_async(_charge_subscription(self, subscription_id))


async def _charge_subscription(self, subscription_id: str):
    """Async implementation that triggers payment with a gateway."""
    try:
        async with AsyncSessionLocal() as session:
            subscription = await session.get(Subscription, subscription_id)

            if not subscription:
                return {"success": False, "message": "Subscription not found"}

            # Trigger payment with Paystack
            from app.services.billing_service import PaystackService

            paystack = PaystackService()
            result = await paystack.initialize_payment(
                email=subscription.user_id,  # Should be actual email
                amount=int(float(subscription.price_usd) * 100),  # Convert to minor currency unit
                reference=f"{subscription_id}-{datetime.utcnow().timestamp()}",
                metadata={
                    "subscription_id": subscription_id,
                    "plan_id": subscription.plan_id
                }
            )

            if result.get("success"):
                return {"success": True, "authorization_url": result["authorization_url"]}
            else:
                return {"success": False, "message": result.get("message")}

    except Exception as exc:
        logger.error(f"charge_subscription failed: {str(exc)}")
        try:
            self.retry(exc=exc, countdown=60)
        except Exception:
            raise
