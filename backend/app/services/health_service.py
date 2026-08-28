"""Dependency checks used by liveness and operational health endpoints."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import text

from app.core.config import settings
from app.models.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def check_database() -> dict[str, str]:
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "connected"}
    except Exception:
        logger.exception("Database health check failed")
        return {"status": "unavailable"}


async def check_redis() -> dict[str, str]:
    if settings.ENABLE_MOCK_MODE:
        return {"status": "available", "mode": "mock"}
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2)
        try:
            await client.ping()
        finally:
            await client.aclose()
        return {"status": "connected"}
    except Exception:
        logger.exception("Redis health check failed")
        return {"status": "unavailable"}


def check_external_services() -> dict[str, dict[str, str]]:
    """Report configuration readiness without exposing credentials or making costly calls."""
    if settings.ENABLE_MOCK_MODE:
        return {
            "ai": {"status": "available", "mode": "mock"},
            "payments": {"status": "available", "mode": "mock"},
            "email": {"status": "available", "mode": "mock"},
        }

    return {
        "ai": {"status": "available" if settings.is_llm_configured() else "unavailable"},
        "payments": {
            "status": "available"
            if any(
                (settings.PAYSTACK_SECRET_KEY, settings.PAYPAL_CLIENT_ID, settings.STRIPE_API_KEY)
            )
            else "unavailable"
        },
        "email": {
            "status": "available"
            if any((settings.SMTP_HOST, settings.GOOGLE_CLIENT_ID, settings.OUTLOOK_CLIENT_ID))
            else "unavailable"
        },
    }


async def check_dependencies() -> tuple[str, dict[str, Any]]:
    database, redis = await asyncio.gather(check_database(), check_redis())
    dependencies: dict[str, Any] = {
        "database": database,
        "redis": redis,
        "external_services": check_external_services(),
    }
    critical_available = database["status"] == "connected"
    return ("healthy" if critical_available else "degraded"), dependencies
