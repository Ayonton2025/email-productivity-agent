"""Operational, health, and local diagnostic endpoints."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.services.health_service import check_dependencies

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeContext:
    allowed_origins: list[str]
    debug: bool
    port: int
    registered_routers: set[str]
    is_ready: Callable[[], bool]

    def router_loaded(self, module: str) -> bool:
        return f"{module}.router" in self.registered_routers


def create_system_router(runtime: RuntimeContext) -> APIRouter:
    router = APIRouter()

    @router.post("/api/v1/test-register")
    async def test_register():
        return {
            "message": "Test endpoint working",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
        }

    @router.get("/api/v1/test-auth")
    async def test_auth():
        return {
            "message": "Auth test endpoint working",
            "endpoints": {
                "register": "POST /api/v1/auth/register",
                "login": "POST /api/v1/auth/login",
                "me": "GET /api/v1/auth/me",
            },
        }

    @router.get("/api/v1/test-cors")
    async def test_cors():
        return {
            "message": "CORS test endpoint",
            "cors_configured": True,
            "allowed_origins_count": len(runtime.allowed_origins),
            "timestamp": datetime.utcnow().isoformat(),
        }

    @router.get("/health")
    async def health_check():
        status, dependencies = await check_dependencies()
        health_status = {
            "status": status,
            "service": settings.SERVICE_NAME,
            "version": settings.APP_VERSION,
            "timestamp": datetime.utcnow().isoformat(),
            "dependencies": dependencies,
        }

        health_status["routers"] = {
            name: runtime.router_loaded(module)
            for name, module in {
                "auth": "app.api.auth_endpoints",
                "api": "app.api.endpoints",
                "email_accounts": "app.api.user_email_endpoints",
                "inbox": "app.api.inbox_endpoints",
                "webhook": "app.api.webhook_endpoints",
                "realtime": "app.api.realtime_endpoints",
                "sync_history": "app.api.sync_history_endpoints",
                "search": "app.api.search_endpoints",
                "multi_provider": "app.api.multi_provider_endpoints",
            }.items()
        }
        health_status["startup_ready"] = runtime.is_ready()
        health_status["cors"] = {
            "enabled": True,
            "allowed_origins_count": len(runtime.allowed_origins),
        }
        return health_status

    @router.get("/api/v1/health")
    async def health_check_api():
        return await health_check()

    @router.get("/ready")
    async def ready():
        if runtime.is_ready():
            return {"status": "ready", "service": "bylix-email-platform"}
        return JSONResponse(
            status_code=503, content={"status": "starting", "service": "bylix-email-platform"}
        )

    @router.get("/")
    async def root():
        return {
            "message": "Bylix Email API",
            "status": "running",
            "version": "2.0.0",
            "docs": "/docs",
            "api_base": "/api/v1",
            "environment": "development" if runtime.debug else "production",
            "timestamp": datetime.utcnow().isoformat(),
        }

    @router.get("/info")
    async def info():
        return {
            "service": "Bylix Email Backend",
            "version": "2.0.0",
            "environment": "development" if runtime.debug else "production",
            "debug_mode": runtime.debug,
            "port": runtime.port,
            "cors": {"allowed_origins": runtime.allowed_origins, "allow_credentials": True},
            "timestamp": datetime.utcnow().isoformat(),
        }

    return router
