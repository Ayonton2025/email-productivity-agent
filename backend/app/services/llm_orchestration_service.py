from __future__ import annotations

import asyncio
import hashlib
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import google.generativeai as genai
import httpx
from anthropic import AsyncAnthropic
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from openai import AsyncOpenAI
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import logger
from app.models.billing_models import UsageLog
from app.models.database import AsyncSessionLocal
from app.services.llm_provider_config_service import LLMProviderConfigService, RuntimeProviderConfig

try:
    import redis.asyncio as redis_async
except Exception:  # pragma: no cover
    redis_async = None


if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)


class ModelRegistry:
    MODELS = {
        "gemini-1.5-flash": {"name": "Gemini 1.5 Flash", "provider": "google", "description": "Fast general-purpose Gemini model", "input_cost_per_1k": 0.000075, "output_cost_per_1k": 0.0003},
        "gemini-1.5-pro": {"name": "Gemini 1.5 Pro", "provider": "google", "description": "Higher-quality Gemini model", "input_cost_per_1k": 0.0035, "output_cost_per_1k": 0.0105},
    }

    @classmethod
    def get_model(cls, model_id: str) -> Optional[Dict[str, Any]]:
        return cls.MODELS.get(model_id)

    @classmethod
    def list_models(cls) -> Dict[str, Dict[str, Any]]:
        return cls.MODELS

    @classmethod
    def calculate_cost(cls, model_id: str, input_tokens: int, output_tokens: int) -> float:
        model = cls.get_model(model_id)
        if not model:
            return 0.0
        return (input_tokens / 1000) * model["input_cost_per_1k"] + (output_tokens / 1000) * model["output_cost_per_1k"]


class PromptRegistry:
    PROMPTS = {
        "email_classifier": {"id": "email_classifier", "system_prompt": 'Return JSON {"category":"...","confidence":0.0,"reasoning":"..."}'},
        "action_extractor": {"id": "action_extractor", "system_prompt": 'Return JSON {"actions":[{"action":"...","deadline":"YYYY-MM-DD","priority":"High/Medium/Low","assigned_to":"name"}]}'},
        "sentiment_analyzer": {"id": "sentiment_analyzer", "system_prompt": 'Return JSON {"sentiment":"positive/neutral/negative","tone":"professional/casual/urgent/friendly","confidence":0.0}'},
        "email_summarizer": {"id": "email_summarizer", "system_prompt": 'Return JSON {"summary":"...","key_points":["..."]}'},
        "reply_generator": {"id": "reply_generator", "system_prompt": 'Return JSON {"reply":"...","tone":"professional/casual"}'},
        "relationship_scorer": {"id": "relationship_scorer", "system_prompt": 'Return JSON {"relationship_score":0.0,"relationship_type":"...","engagement_level":"..."}'},
    }

    @classmethod
    def get_prompt(cls, prompt_id: str) -> Dict[str, Any]:
        return cls.PROMPTS.get(prompt_id, {})

    @classmethod
    def list_prompts(cls) -> List[str]:
        return list(cls.PROMPTS.keys())


class UsageTracker:
    @staticmethod
    def log_usage(user_id: str, feature: str, model: str, input_tokens: int, output_tokens: int, cost: float) -> Dict[str, Any]:
        return {"user_id": user_id, "feature": feature, "model": model, "input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": input_tokens + output_tokens, "cost_usd": cost, "timestamp": datetime.utcnow().isoformat()}


class LLMOrchestrationService:
    def __init__(self, default_model: Optional[str] = None):
        self.default_model = default_model or getattr(settings, "LLM_MODEL", "qwen2.5-7b-instruct-q4_k_m-00001-of-00002")
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
            self._redis = redis_async.from_url(getattr(settings, "CELERY_BROKER_URL", "redis://redis:6379/0"), decode_responses=True)
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
    def _sort_chain(configs: List[RuntimeProviderConfig], requested_provider: str, profile: str) -> List[RuntimeProviderConfig]:
        pref = {p: i for i, p in enumerate(LLMOrchestrationService._preference(profile))}
        return sorted(configs, key=lambda c: (0 if c.provider == requested_provider else 1, pref.get(c.provider, 99), c.priority, c.provider))

    async def call_llm(self, prompt: str, model: Optional[str] = None, system_prompt: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1024, user_id: Optional[str] = None, feature: Optional[str] = None, session: Optional[AsyncSession] = None) -> Dict[str, Any]:
        model = model or self.default_model
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
                return {"success": False, "error": "No LLM providers configured. Configure at least one provider via the Admin LLM settings."}

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
                    response_text, resolved_model = await self._call_with_retry(cfg, full_prompt, system_prompt, model, temperature, max_tokens)
                    if response_text:
                        resolved_provider = cfg.provider
                        break
                except Exception as e:
                    last_error = e
                    logger.warning(f"LLM provider {cfg.provider} failed: {e}")

            if not response_text:
                return {"success": False, "error": str(last_error) if last_error else "All configured providers failed."}

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

            payload = {"response": response_text, "tokens": {"input": input_tokens, "output": output_tokens, "total": input_tokens + output_tokens}, "cost": cost, "model": resolved_model, "provider": resolved_provider, "success": True, "cached": False}
            await self._cache_set(cache_key, payload)
            logger.info(f"LLM usage: {json.dumps(UsageTracker.log_usage(user_id or 'unknown', feature or 'general', resolved_model, input_tokens, output_tokens, cost))}")
            return payload
        except ValueError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected LLM error: {e}")
            return {"success": False, "error": f"LLM service error: {str(e)}"}

    async def _call_with_retry(self, cfg: RuntimeProviderConfig, full_prompt: str, system_prompt: Optional[str], model: str, temperature: float, max_tokens: int) -> Tuple[str, str]:
        keys = cfg.api_keys or [""]
        last_exc = None
        for attempt in range(max(1, int(cfg.max_retries))):
            for offset, key in enumerate(keys):
                try:
                    return await self._call_provider(cfg, key, (attempt + offset) % max(1, len(keys)), full_prompt, system_prompt, model, temperature, max_tokens)
                except Exception as e:
                    last_exc = e
            if attempt < cfg.max_retries - 1 and cfg.backoff_seconds > 0:
                await asyncio.sleep(cfg.backoff_seconds * (2 ** attempt))
        raise last_exc or RuntimeError(f"{cfg.provider} failed")

    async def _call_provider(self, cfg: RuntimeProviderConfig, key: str, key_index: int, full_prompt: str, system_prompt: Optional[str], model: str, temperature: float, max_tokens: int) -> Tuple[str, str]:
        m = cfg.model or model or self.default_model
        if cfg.provider == "google":
            return await self._call_google(full_prompt, m, key, temperature, max_tokens)
        if cfg.provider == "anthropic":
            return await self._call_anthropic(full_prompt, system_prompt, m, key, temperature, max_tokens)
        if cfg.provider == "huggingface":
            return await self._call_hf(full_prompt, m, key, cfg.timeout_seconds, temperature, max_tokens)
        if cfg.provider == "ollama":
            return await self._call_ollama(full_prompt, m, cfg.endpoint or settings.OLLAMA_URL or "http://localhost:11434", cfg.timeout_seconds, temperature, max_tokens)
        return await self._call_openai_compatible(full_prompt, system_prompt, m, key, cfg.provider, cfg.endpoint, cfg.timeout_seconds, cfg.additional_headers or {}, key_index, temperature, max_tokens)

    async def _call_google(self, full_prompt: str, model: str, api_key: str, temperature: float, max_tokens: int) -> Tuple[str, str]:
        key = api_key or settings.GOOGLE_API_KEY
        if not key:
            raise ValueError("Google API key not configured")

        def _run() -> str:
            genai.configure(api_key=key)
            gm = genai.GenerativeModel(model_name=model, safety_settings=self.safety_settings)
            r = gm.generate_content(full_prompt, generation_config=genai.types.GenerationConfig(max_output_tokens=max_tokens, temperature=temperature), safety_settings=self.safety_settings)
            return r.text if r else ""

        text = await asyncio.get_event_loop().run_in_executor(None, _run)
        return text or "", model

    async def _call_anthropic(self, full_prompt: str, system_prompt: Optional[str], model: str, api_key: str, temperature: float, max_tokens: int) -> Tuple[str, str]:
        key = api_key.strip() if api_key else ""
        if not key:
            raise ValueError("Anthropic API key not configured")
        try:
            client = AsyncAnthropic(api_key=key)
            # Ensure client.messages is available (check Anthropic SDK version)
            if not hasattr(client, 'messages'):
                raise ValueError("Anthropic SDK not properly initialized. Check your anthropic package version.")
            r = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "You are a helpful AI assistant.",
                messages=[{"role": "user", "content": full_prompt}]
            )
            return (r.content[0].text if r and r.content else "") or "", model
        except AttributeError as e:
            raise ValueError(f"Anthropic SDK error: {str(e)}. Please ensure you have the latest anthropic package installed.")
        except Exception as e:
            raise ValueError(f"Anthropic API call failed: {str(e)}")

    async def _call_hf(self, full_prompt: str, model: str, api_key: str, timeout_seconds: int, temperature: float, max_tokens: int) -> Tuple[str, str]:
        key = api_key.strip() if api_key else ""
        if not key:
            raise ValueError("HuggingFace API key not configured")
        # Use new endpoint: https://router.huggingface.co instead of deprecated https://api-inference.huggingface.co
        async with httpx.AsyncClient(timeout=max(5, int(timeout_seconds))) as client:
            resp = await client.post(f"https://router.huggingface.co/models/{model}", headers={"Authorization": f"Bearer {key}"}, json={"inputs": full_prompt, "options": {"wait_for_model": True}, "parameters": {"max_new_tokens": max_tokens, "temperature": temperature}})
            if resp.status_code != 200:
                raise ValueError(f"HuggingFace call failed: {resp.status_code} {resp.text}")
            data = resp.json()
            if isinstance(data, list) and data:
                text = data[0].get("generated_text") or ""
            elif isinstance(data, dict):
                text = data.get("generated_text") or data.get("output") or ""
            else:
                text = ""
            return text or "", model

    async def _call_ollama(self, full_prompt: str, model: str, base_url: str, timeout_seconds: int, temperature: float, max_tokens: int) -> Tuple[str, str]:
        async with httpx.AsyncClient(timeout=max(10, int(timeout_seconds))) as client:
            resp = await client.post(base_url.rstrip("/") + "/api/generate", json={"model": model or self.default_model, "prompt": full_prompt, "temperature": temperature, "options": {"num_predict": max_tokens}, "stream": False})
            if resp.status_code != 200:
                raise ValueError(f"Ollama call failed: {resp.status_code} {resp.text}")
            return (resp.json().get("response") or ""), model

    async def _call_openai_compatible(self, full_prompt: str, system_prompt: Optional[str], model: str, api_key: str, provider: str, endpoint: Optional[str], timeout_seconds: int, headers: Dict[str, str], key_index: int, temperature: float, max_tokens: int) -> Tuple[str, str]:
        key = api_key.strip() if api_key else ""
        if not key:
            raise ValueError(f"{provider} API key not configured")
        
        # Provider endpoint map
        base = endpoint or {
            "openai": "https://api.openai.com/v1",
            "groq": "https://api.groq.com/openai/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "together": "https://api.together.xyz/v1",
            "fireworks": "https://api.fireworks.ai/inference/v1",
            "mistral": "https://api.mistral.ai/v1",
            "cerebras": "https://api.cerebras.ai/v1",
            "nebius": "https://api.studio.nebius.ai/v1",
            "alibaba": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "nvidia_nim": "https://integrate.api.nvidia.com/v1",
            "github_models": "https://models.inference.ai.azure.com",
        }.get(provider, "https://api.openai.com/v1")
        
        client = AsyncOpenAI(api_key=key, base_url=base.rstrip("/"), timeout=max(5, int(timeout_seconds)), default_headers=headers)
        messages = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + [{"role": "user", "content": full_prompt}]
        candidate_models = [model]
        # Preserve order while de-duplicating.
        candidate_models = list(dict.fromkeys(candidate_models))

        last_error = None
        for candidate_model in candidate_models:
            try:
                resp = await client.chat.completions.create(
                    model=candidate_model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return (resp.choices[0].message.content if resp and resp.choices else "") or "", candidate_model
            except Exception as e:
                last_error = e
                error_msg = str(e)
                lowered = error_msg.lower()
                # Provide helpful diagnostics for common errors
                if "404" in error_msg and "not found" in lowered:
                    error_msg += f" [Model '{candidate_model}' not available. Check provider's available models or use a different model version]"
                elif "401" in error_msg or "unauthorized" in lowered:
                    error_msg += " [Invalid API key or insufficient permissions. Check your key and provider account settings]"
                elif "429" in error_msg or "quota" in lowered or "rate" in lowered:
                    error_msg += " [API quota exceeded or rate limited. Check billing and usage limits]"
                raise ValueError(error_msg)

        # If all model variants fail, return the most actionable error.
        raise ValueError(
            f"{provider} call failed for models {candidate_models}: {last_error}"
        )

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
            
            providers.append({"provider": cfg.provider, "display_name": cfg.display_name, "configured": has_auth, "status": status, "reason": reason, "model": cfg.model, "endpoint": cfg.endpoint, "priority": cfg.priority, "key_count": len(cfg.api_keys), "max_retries": cfg.max_retries, "backoff_seconds": cfg.backoff_seconds, "latency_ms": latency_ms})
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
        
        return {"success": True, "overall_status": overall, "message": f"Has {len(configured_providers)} configured provider(s)", "providers": providers}

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
                results.append({
                    "provider": cfg.provider,
                    "display_name": cfg.display_name,
                    "configured": True,
                    "success": True if snippet else False,
                    "model": model,
                    "response_snippet": snippet,
                    "latency_ms": latency_ms,
                })
            except Exception as e:
                latency_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
                results.append({
                    "provider": cfg.provider,
                    "display_name": cfg.display_name,
                    "configured": True,
                    "success": False,
                    "error": str(e),
                    "latency_ms": latency_ms,
                })
        
        # If no providers are configured (have keys)
        if tested_count == 0:
            msg = "No LLM providers configured. Configure at least one provider with API keys to run tests."
            if provider_filter:
                msg = f"Provider '{provider_filter}' is not configured with a usable key to run tests."
            return {
                "success": False,
                "message": msg,
                "results": []
            }
        
        return {
            "success": True,
            "message": f"Tested {tested_count} configured provider(s)",
            "results": results
        }

    def _extract_json(self, raw_text: str) -> Optional[Dict[str, Any]]:
        if not raw_text:
            return None
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            pass
        m = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None

    async def create_workspace_assist(self, page: str, objective: str, mode: str = "draft", context: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None, session: Optional[AsyncSession] = None) -> Dict[str, Any]:
        schema = self._assist_schema_for_page(page)
        prompt = f"Page:{page}\nMode:{mode}\nObjective:{objective}\nContext:{json.dumps(context or {}, ensure_ascii=True)}\nReturn JSON:\n{schema}"
        result = await self.call_llm(prompt=prompt, system_prompt="Generate structured JSON only.", model=self.default_model, user_id=user_id, feature=f"workspace_assist_{page}", session=session, temperature=0.4, max_tokens=1200)
        if not result.get("success"):
            return {"success": False, "error": result.get("error", "Unknown LLM error")}
        parsed = self._extract_json(result.get("response", ""))
        if not parsed:
            return {"success": True, "page": page, "assistant_message": "I could not format a structured plan. Please refine your objective.", "suggested_actions": [], "draft": {}, "raw_response": result.get("response", ""), "provider": result.get("provider"), "model": result.get("model")}
        parsed["success"] = True
        parsed["provider"] = result.get("provider")
        parsed["model"] = result.get("model")
        return parsed

    def _assist_schema_for_page(self, page: str) -> str:
        p = (page or "").lower()
        if p == "campaigns":
            return json.dumps({"page": "campaigns", "assistant_message": "string", "suggested_actions": ["string"], "draft": {"campaign": {"name": "string"}, "sequences": [{"name": "string", "subject_template": "string", "body_template": "string"}], "leads": [{"email": "string"}]}})
        if p == "workflows":
            return json.dumps({"page": "workflows", "assistant_message": "string", "suggested_actions": ["string"], "draft": {"workflow": {"name": "string", "trigger_type": "email_received"}, "steps": [{"name": "string", "step_type": "action"}]}})
        if p == "agents":
            return json.dumps({"page": "agents", "assistant_message": "string", "suggested_actions": ["string"], "draft": {"agent": {"name": "string", "agent_type": "support", "system_prompt": "string"}}})
        if p in {"prompts", "prompt_brain"}:
            return json.dumps({"page": "prompts", "assistant_message": "string", "suggested_actions": ["string"], "draft": {"prompt": {"name": "string", "template": "string", "category": "analysis"}}})
        return json.dumps({"page": p or "general", "assistant_message": "string", "suggested_actions": ["string"], "draft": {}})

    async def classify_email(self, sender: str, subject: str, body: str, tenant_id: str, user_id: Optional[str] = None, session: Optional[AsyncSession] = None) -> Dict[str, Any]:
        r = await self.call_llm(prompt=f"From:{sender}\nSubject:{subject}\nBody:{body[:2000]}", system_prompt=PromptRegistry.get_prompt("email_classifier").get("system_prompt"), model=self.default_model, user_id=user_id, feature="categorization", session=session)
        if not r.get("success"):
            return {"error": r.get("error")}
        try:
            c = json.loads(r["response"])
            return {"category": c.get("category"), "confidence": c.get("confidence"), "reasoning": c.get("reasoning"), "cost": r["cost"]}
        except json.JSONDecodeError:
            return {"error": "Failed to parse classification", "raw_response": r.get("response")}

    async def extract_actions(self, email_body: str, user_id: Optional[str] = None, session: Optional[AsyncSession] = None) -> Dict[str, Any]:
        r = await self.call_llm(prompt=f"Extract action items:\n{email_body[:3000]}", system_prompt=PromptRegistry.get_prompt("action_extractor").get("system_prompt"), model=self.default_model, user_id=user_id, feature="action_extraction", session=session)
        if not r.get("success"):
            return {"error": r.get("error")}
        try:
            a = json.loads(r["response"])
            return {"actions": a.get("actions", []), "cost": r["cost"]}
        except json.JSONDecodeError:
            return {"error": "Failed to parse actions"}

    async def analyze_sentiment(self, email_body: str, user_id: Optional[str] = None, session: Optional[AsyncSession] = None) -> Dict[str, Any]:
        r = await self.call_llm(prompt=f"Analyze sentiment:\n{email_body[:2000]}", system_prompt=PromptRegistry.get_prompt("sentiment_analyzer").get("system_prompt"), model=self.default_model, user_id=user_id, feature="sentiment_analysis", session=session)
        if not r.get("success"):
            return {"error": r.get("error")}
        try:
            s = json.loads(r["response"])
            return {"sentiment": s.get("sentiment"), "tone": s.get("tone"), "confidence": s.get("confidence"), "cost": r["cost"]}
        except json.JSONDecodeError:
            return {"error": "Failed to parse sentiment"}

    async def summarize_thread(self, thread_body: str, user_id: Optional[str] = None, session: Optional[AsyncSession] = None) -> Dict[str, Any]:
        r = await self.call_llm(prompt=f"Summarize thread:\n{thread_body[:4000]}", system_prompt=PromptRegistry.get_prompt("email_summarizer").get("system_prompt"), model=self.default_model, user_id=user_id, feature="summarization", session=session)
        if not r.get("success"):
            return {"error": r.get("error")}
        try:
            s = json.loads(r["response"])
            return {"summary": s.get("summary"), "key_points": s.get("key_points", []), "cost": r["cost"]}
        except json.JSONDecodeError:
            return {"error": "Failed to parse summary"}

    async def generate_reply(self, email_body: str, user_id: Optional[str] = None, session: Optional[AsyncSession] = None) -> Dict[str, Any]:
        r = await self.call_llm(prompt=f"Generate reply:\n{email_body[:2000]}", system_prompt=PromptRegistry.get_prompt("reply_generator").get("system_prompt"), model=self.default_model, user_id=user_id, feature="reply_drafting", session=session, temperature=0.7)
        if not r.get("success"):
            return {"error": r.get("error")}
        try:
            d = json.loads(r["response"])
            return {"reply": d.get("reply"), "tone": d.get("tone"), "cost": r["cost"]}
        except json.JSONDecodeError:
            return {"error": "Failed to parse reply"}

    async def score_relationship(self, email_history: str, user_id: Optional[str] = None, session: Optional[AsyncSession] = None) -> Dict[str, Any]:
        r = await self.call_llm(prompt=f"Score relationship:\n{email_history[:3000]}", system_prompt=PromptRegistry.get_prompt("relationship_scorer").get("system_prompt"), model=self.default_model, user_id=user_id, feature="relationship_scoring", session=session)
        if not r.get("success"):
            return {"error": r.get("error")}
        try:
            d = json.loads(r["response"])
            return {"relationship_score": d.get("relationship_score"), "relationship_type": d.get("relationship_type"), "engagement_level": d.get("engagement_level"), "cost": r["cost"]}
        except json.JSONDecodeError:
            return {"error": "Failed to parse relationship score"}


llm_service = LLMOrchestrationService()
