"""Optional production error monitoring.

The helpers are deliberately safe when Sentry is disabled, keeping local and
isolated test environments free from external network requirements.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def initialize_monitoring() -> bool:
    """Initialize Sentry once when a DSN is configured."""
    if not settings.SENTRY_DSN:
        logger.info("Sentry monitoring disabled because SENTRY_DSN is not configured")
        return False

    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=settings.APP_VERSION,
        integrations=[
            FastApiIntegration(),
            CeleryIntegration(),
            SqlalchemyIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        send_default_pii=False,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
    )
    logger.info("Sentry monitoring initialized", extra={"environment": settings.ENVIRONMENT})
    return True


def capture_exception(exc: BaseException, **context: Any) -> None:
    """Report a handled failure without coupling services to Sentry."""
    if not settings.SENTRY_DSN:
        return
    import sentry_sdk

    with sentry_sdk.push_scope() as scope:
        for key, value in context.items():
            scope.set_extra(key, value)
        sentry_sdk.capture_exception(exc)


def register_debug_error_endpoint(app) -> None:
    """Register a Sentry smoke-test route that is inaccessible outside debug mode."""
    from fastapi import HTTPException

    @app.get("/debug/error", include_in_schema=False)
    async def trigger_debug_error():
        if not settings.DEBUG:
            raise HTTPException(status_code=404, detail="Not found")
        raise RuntimeError("Intentional Sentry test exception")
