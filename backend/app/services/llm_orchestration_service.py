from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import logger
from app.models.billing_models import UsageLog
from app.models.database import AsyncSessionLocal
from app.services.llm_feature_mixin import LLMFeatureMixin
from app.services.llm_provider_config_service import LLMProviderConfigService, RuntimeProviderConfig
from app.services.llm_provider_mixin import LLMProviderMixin
from app.services.model_registry import ModelRegistry
from app.services.prompt_registry import PromptRegistry
from app.services.usage_tracker import UsageTracker

try:
    import redis.asyncio as redis_async
except Exception:  # pragma: no cover
    redis_async = None


if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)


class LLMOrchestrationService(LLMProviderMixin, LLMFeatureMixin):
    def __init__(self, default_model: Optional[str] = None):
        self.default_model = default_model or getattr(
            settings, "LLM_MODEL", "qwen2.5-7b-instruct-q4_k_m-00001-of-00002"
        )
        # Use more flexible defaults that most accounts have access to
        self.openai_model = getattr(settings, "OPENAI_MODEL", "gpt-3.5-turbo")  # More widely available
        self.anthropic_model = getattr(settings, "ANTHROPIC_MODEL", "claude-3-sonnet-20240229")  # Stable model
        self.safety_settings = [
            {"category": HarmCategory.HARM_CATEGORY_HARASSMENT, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
            {"category": HarmCategory.HARM_CATEGORY_HATE_SPEECH, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
        ]
        self._redis = None
        self._redis_init_done = False

    @staticmethod
    def _is_free_workplace_feature(feature: Optional[str]) -> bool:
        return bool(feature and feature.startswith("workspace_assist_"))

    @staticmethod
    def _profile(feature: Optional[str]) -> str:
        f = (feature or "").lower()
        if any(x in f for x in ["spam", "summar", "classif", "action_extract", "sentiment"]):
            return "cheap_fast"
        if "legal" in f:
            return "strong_quality"
        if any(x in f for x in ["reply", "workspace_assist", "relationship"]):
            return "strong_quality"
        return "balanced"

    @staticmethod
    def _preference(profile: str) -> List[str]:
        if profile == "cheap_fast":
            return ["groq", "google", "openrouter", "huggingface", "ollama", "openai", "anthropic"]
        if profile == "strong_quality":
            return ["openai", "anthropic", "google", "groq", "openrouter", "ollama", "huggingface"]
        return ["google", "groq", "openrouter", "openai", "anthropic", "huggingface", "ollama"]

    async def _redis_client(self):
        if self._redis_init_done:
            return self._redis
        self._redis_init_done = True
        if redis_async is None:
            return None
        try:
            self._redis = redis_async.from_url(
                getattr(settings, "CELERY_BROKER_URL", "redis://redis:6379/0"), decode_responses=True
            )
            await self._redis.ping()
        except Exception as e:
            logger.warning(f"Semantic cache disabled: {e}")
            self._redis = None
        return self._redis

    async def _cache_get(self, key: str) -> Optional[Dict[str, Any]]:
        client = await self._redis_client()
        if not client:
            return None
        try:
            raw = await client.get(key)
            return json.loads(raw) if raw else None
        except Exception:
            return None

    async def _cache_set(self, key: str, val: Dict[str, Any], ttl: int = 900) -> None:
        client = await self._redis_client()
        if not client:
            return
        try:
            await client.set(key, json.dumps(val, ensure_ascii=True), ex=max(60, int(ttl)))
        except Exception:
            return

    @staticmethod
    def _cache_key(prompt: str, system_prompt: Optional[str], feature: Optional[str], model: str) -> str:
        norm = " ".join((prompt or "").split()).lower()[:5000]
        sys = " ".join((system_prompt or "").split()).lower()[:1000]
        digest = hashlib.sha256(f"{feature}|{model}|{sys}|{norm}".encode("utf-8")).hexdigest()
        return f"semantic:llm:{digest}"

    async def _runtime_configs(self, session: Optional[AsyncSession]) -> List[RuntimeProviderConfig]:
        if session:
            cfgs = await LLMProviderConfigService.get_runtime_configs(session)
        else:
            async with AsyncSessionLocal() as s:
                cfgs = await LLMProviderConfigService.get_runtime_configs(s)
        if cfgs:
            return cfgs
        # Fallback when DB providers are not configured yet.
        return cfgs

    @staticmethod
    def _sort_chain(
        configs: List[RuntimeProviderConfig], requested_provider: str, profile: str
    ) -> List[RuntimeProviderConfig]:
        pref = {p: i for i, p in enumerate(LLMOrchestrationService._preference(profile))}
        return sorted(
            configs,
            key=lambda c: (
                0 if c.provider == requested_provider else 1,
                pref.get(c.provider, 99),
                c.priority,
                c.provider,
            ),
        )

    async def call_llm(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        user_id: Optional[str] = None,
        feature: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        model = model or self.default_model
        if settings.ENABLE_MOCK_MODE:
            from app.services.mock_services import mock_llm_response

            return mock_llm_response(prompt=prompt, feature=feature, model=model)
        requested_provider = (getattr(settings, "LLM_PROVIDER", "auto") or "auto").lower()
        should_bill = bool(user_id and feature and session and not self._is_free_workplace_feature(feature))
        try:
            if should_bill:
                from app.services.billing_service import CreditService

                credit_service = CreditService()
                if await credit_service._is_user_blocked(user_id=user_id, session=session):
                    raise ValueError("User access is blocked by admin policy.")
                bypass_billing = await credit_service._has_payment_bypass(user_id=user_id, session=session)
                # Hard anti-abuse cap for AI actions.
                daily_used_query = await session.execute(
                    select(func.coalesce(func.sum(UsageLog.credits_used), 0)).where(
                        UsageLog.user_id == user_id,
                        UsageLog.timestamp >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
                    )
                )
                daily_used = int(daily_used_query.scalar() or 0)
                if (not bypass_billing) and daily_used >= 200:
                    raise ValueError("Daily AI usage cap reached (200 emails/day).")

                if not bypass_billing:
                    await credit_service.check_credits_for_ai_action(
                        user_id=user_id,
                        action=feature or "categorization",
                        session=session,
                    )

            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            cfgs = await self._runtime_configs(session)
            enabled = [c for c in cfgs if c.provider in {"ollama"} or len(c.api_keys) > 0]
            if not enabled:
                return {
                    "success": False,
                    "error": "No LLM providers configured. Configure at least one provider via the Admin LLM settings.",
                }

            cache_key = self._cache_key(full_prompt, system_prompt, feature, model)
            cached = await self._cache_get(cache_key)
            if cached:
                cached["cached"] = True
                return cached

            chain = self._sort_chain(enabled, requested_provider, self._profile(feature))
            response_text = ""
            resolved_model = model
            resolved_provider = ""
            last_error: Optional[Exception] = None
            for cfg in chain:
                try:
                    response_text, resolved_model = await self._call_with_retry(
                        cfg, full_prompt, system_prompt, model, temperature, max_tokens
                    )
                    if response_text:
                        resolved_provider = cfg.provider
                        break
                except Exception as e:
                    last_error = e
                    logger.warning(f"LLM provider {cfg.provider} failed: {e}")

            if not response_text:
                return {
                    "success": False,
                    "error": str(last_error) if last_error else "All configured providers failed.",
                }

            input_tokens = int(len(full_prompt.split()) * 1.3)
            output_tokens = int(len(response_text.split()) * 1.3)
            cost = ModelRegistry.calculate_cost(resolved_model, input_tokens, output_tokens)
            if should_bill:
                from app.services.billing_service import CreditService

                credit_service = CreditService()
                bypass_billing = await credit_service._has_payment_bypass(user_id=user_id, session=session)
                if not bypass_billing:
                    await credit_service.deduct_credits_for_ai_action(
                        user_id=user_id,
                        action=feature or "categorization",
                        session=session,
                        tokens_used=input_tokens + output_tokens,
                    )

            payload = {
                "response": response_text,
                "tokens": {"input": input_tokens, "output": output_tokens, "total": input_tokens + output_tokens},
                "cost": cost,
                "model": resolved_model,
                "provider": resolved_provider,
                "success": True,
                "cached": False,
            }
            await self._cache_set(cache_key, payload)
            logger.info(
                f"LLM usage: {json.dumps(UsageTracker.log_usage(user_id or 'unknown', feature or 'general', resolved_model, input_tokens, output_tokens, cost))}"
            )
            return payload
        except ValueError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected LLM error: {e}")
            return {"success": False, "error": f"LLM service error: {str(e)}"}


llm_service = LLMOrchestrationService()
