"""Compatibility aggregator for billing API routes."""

from fastapi import APIRouter

from app.api.billing.credits import router as credits_router
from app.api.billing.features import router as features_router
from app.api.billing.payments import router as payments_router
from app.api.billing.subscriptions import router as subscriptions_router
from app.api.billing.webhooks import router as webhooks_router

router = APIRouter()
for child_router in (
    subscriptions_router,
    payments_router,
    credits_router,
    webhooks_router,
    features_router,
):
    router.include_router(child_router)
