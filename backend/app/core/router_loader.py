"""Declarative API router discovery and registration."""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass

from fastapi import APIRouter, FastAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RouterSpec:
    module: str
    attribute: str = "router"
    prefix: str = ""
    tags: tuple[str, ...] = ()

    @property
    def name(self) -> str:
        return f"{self.module}.{self.attribute}"


ROUTERS: tuple[RouterSpec, ...] = (
    RouterSpec("app.api.auth_endpoints", prefix="/api/v1", tags=("authentication",)),
    RouterSpec("app.api.endpoints", prefix="/api/v1", tags=("api",)),
    RouterSpec("app.api.user_email_endpoints", prefix="/api/v1", tags=("email-accounts",)),
    RouterSpec("app.api.oauth_endpoints", prefix="/api/v1", tags=("oauth",)),
    RouterSpec("app.api.auto_reply_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.insights_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.workflow_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.agent_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.campaign_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.billing_endpoints"),
    RouterSpec("app.api.ai_endpoints"),
    RouterSpec("app.api.inbox_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.webhook_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.realtime_endpoints"),
    RouterSpec("app.api.sync_history_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.bulk_email_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.search_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.multi_provider_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.email_provider_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.analytics_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.contact_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.briefing_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.followup_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.hosted_email_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.shared_inbox_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.deliverability_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.executive_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.admin_llm_endpoints"),
    RouterSpec("app.api.admin_usage_endpoints"),
    RouterSpec("app.api.usage_endpoints"),
    RouterSpec("app.api.meeting_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.voice_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.security_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.legal_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.knowledge_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.language_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.persona_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.task_manager_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.priority_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.sales_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.social_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.timeline_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.offline_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.ethics_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.simulator_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.support_endpoints", prefix="/api/v1"),
    RouterSpec("app.api.attachment_endpoints", prefix="/api/v1"),
    RouterSpec(
        "app.api.attachment_endpoints", attribute="email_attachment_router", prefix="/api/v1"
    ),
)


def load_router(spec: RouterSpec) -> APIRouter | None:
    """Load one optional router while keeping startup diagnostics explicit."""
    try:
        module = importlib.import_module(spec.module)
        router = getattr(module, spec.attribute)
    except (ImportError, AttributeError) as exc:
        logger.exception("Unable to load router %s: %s", spec.name, exc)
        return None
    if not isinstance(router, APIRouter):
        logger.error("Router %s has invalid type %s", spec.name, type(router).__name__)
        return None
    return router


def register_routers(app: FastAPI, specs: tuple[RouterSpec, ...] = ROUTERS) -> list[str]:
    """Load and register configured routers, returning their registered names."""
    registered: list[str] = []
    for spec in specs:
        router = load_router(spec)
        if router is None:
            continue
        app.include_router(router, prefix=spec.prefix, tags=list(spec.tags) or None)
        registered.append(spec.name)
        logger.info("Registered router %s", spec.name)
    return registered
