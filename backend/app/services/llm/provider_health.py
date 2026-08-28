"""LLM provider health probes and administrative diagnostics."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import logger
from app.models.database import AsyncSessionLocal
from app.services.llm_provider_config_service import LLMProviderConfigService, RuntimeProviderConfig


class ProviderHealthMixin:
    async def provider_health(
        self,
        session: Optional[AsyncSession] = None,
        include_live_checks: bool = False,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        # For health checks, include disabled providers too (user may test them before enabling)
        if session:
            cfgs = await LLMProviderConfigService.get_runtime_configs(session, include_disabled=True)
        else:
            async with AsyncSessionLocal() as s:
                cfgs = await LLMProviderConfigService.get_runtime_configs(s, include_disabled=True)

        providers = []
        configured_providers = []  # Track only providers with keys
        provider_filter = (provider or "").strip().lower()

        for cfg in sorted(cfgs, key=lambda x: (x.priority, x.provider)):
            if provider_filter and cfg.provider != provider_filter:
                continue
            has_auth = bool(cfg.api_keys) or cfg.provider in {"ollama"}

            # Skip providers without keys - don't report them at all
            if not has_auth:
                continue

            status = "configured"
            reason = None
            latency_ms = None

            # If live checks requested, test this provider
            if include_live_checks:
                start = datetime.utcnow()
                try:
                    await self._call_with_retry(cfg, 'Return {"ok":true}', "Health check", cfg.model, 0.0, 16)
                    status = "healthy"
                except Exception as e:
                    status = "unhealthy"
                    reason = str(e)
                latency_ms = int((datetime.utcnow() - start).total_seconds() * 1000)

            providers.append(
                {
                    "provider": cfg.provider,
                    "display_name": cfg.display_name,
                    "configured": has_auth,
                    "status": status,
                    "reason": reason,
                    "model": cfg.model,
                    "endpoint": cfg.endpoint,
                    "priority": cfg.priority,
                    "key_count": len(cfg.api_keys),
                    "max_retries": cfg.max_retries,
                    "backoff_seconds": cfg.backoff_seconds,
                    "latency_ms": latency_ms,
                }
            )
            configured_providers.append(cfg.provider)

        # If no providers have keys configured
        if not providers:
            msg = "No LLM providers configured. Configure at least one provider via Admin LLM settings."
            if provider_filter:
                msg = f"Provider '{provider_filter}' is not configured with a usable key."
            return {"success": True, "overall_status": "unconfigured", "message": msg, "providers": []}

        # Determine overall status: healthy if any configured provider is healthy/works
        if any(p["status"] in {"healthy", "configured"} for p in providers):
            overall = "healthy"
        else:
            overall = "unhealthy"  # All configured providers are unhealthy

        return {
            "success": True,
            "overall_status": overall,
            "message": f"Has {len(configured_providers)} configured provider(s)",
            "providers": providers,
        }

    async def test_providers(
        self,
        session: Optional[AsyncSession] = None,
        sample_prompt: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Perform a stronger diagnostic: run a small test prompt against each provider with keys.

        Returns per-provider success, response snippet, error, and latency_ms.
        Admin-only; may incur usage on providers.
        Only tests providers that have keys configured (includes disabled providers for testing).
        """
        # For testing, include disabled providers too (user may want to test before enabling)
        if session:
            cfgs = await LLMProviderConfigService.get_runtime_configs(session, include_disabled=True)
        else:
            async with AsyncSessionLocal() as s:
                cfgs = await LLMProviderConfigService.get_runtime_configs(s, include_disabled=True)

        results = []
        tested_count = 0
        provider_filter = (provider or "").strip().lower()

        for cfg in sorted(cfgs, key=lambda x: (x.priority, x.provider)):
            if provider_filter and cfg.provider != provider_filter:
                continue
            # Skip providers without keys - don't test them
            if not cfg.api_keys and cfg.provider not in {"ollama"}:
                continue

            tested_count += 1
            prompt = sample_prompt or 'Return JSON {"ok": true, "probe": "health"} and nothing else.'
            start = datetime.utcnow()
            try:
                text, model = await self._call_with_retry(cfg, prompt, None, cfg.model or self.default_model, 0.0, 120)
                latency_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
                snippet = (text or "").strip()[:800]
                results.append(
                    {
                        "provider": cfg.provider,
                        "display_name": cfg.display_name,
                        "configured": True,
                        "success": True if snippet else False,
                        "model": model,
                        "response_snippet": snippet,
                        "latency_ms": latency_ms,
                    }
                )
            except Exception as e:
                latency_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
                results.append(
                    {
                        "provider": cfg.provider,
                        "display_name": cfg.display_name,
                        "configured": True,
                        "success": False,
                        "error": str(e),
                        "latency_ms": latency_ms,
                    }
                )

        # If no providers are configured (have keys)
        if tested_count == 0:
            msg = "No LLM providers configured. Configure at least one provider with API keys to run tests."
            if provider_filter:
                msg = f"Provider '{provider_filter}' is not configured with a usable key to run tests."
            return {"success": False, "message": msg, "results": []}

        return {"success": True, "message": f"Tested {tested_count} configured provider(s)", "results": results}
