from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import google.generativeai as genai
import httpx
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import logger
from app.models.billing_models import UsageLog
from app.models.database import AsyncSessionLocal
from app.services.llm_provider_config_service import LLMProviderConfigService, RuntimeProviderConfig


class LLMProviderMixin:
    """Provider adapters, retries, and operational health checks."""

    async def _call_with_retry(
        self,
        cfg: RuntimeProviderConfig,
        full_prompt: str,
        system_prompt: Optional[str],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> Tuple[str, str]:
        keys = cfg.api_keys or [""]
        last_exc = None
        for attempt in range(max(1, int(cfg.max_retries))):
            for offset, key in enumerate(keys):
                try:
                    return await self._call_provider(
                        cfg,
                        key,
                        (attempt + offset) % max(1, len(keys)),
                        full_prompt,
                        system_prompt,
                        model,
                        temperature,
                        max_tokens,
                    )
                except Exception as e:
                    last_exc = e
            if attempt < cfg.max_retries - 1 and cfg.backoff_seconds > 0:
                await asyncio.sleep(cfg.backoff_seconds * (2**attempt))
        raise last_exc or RuntimeError(f"{cfg.provider} failed")

    async def _call_provider(
        self,
        cfg: RuntimeProviderConfig,
        key: str,
        key_index: int,
        full_prompt: str,
        system_prompt: Optional[str],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> Tuple[str, str]:
        m = cfg.model or model or self.default_model
        if cfg.provider == "google":
            return await self._call_google(full_prompt, m, key, temperature, max_tokens)
        if cfg.provider == "anthropic":
            return await self._call_anthropic(full_prompt, system_prompt, m, key, temperature, max_tokens)
        if cfg.provider == "huggingface":
            return await self._call_hf(full_prompt, m, key, cfg.timeout_seconds, temperature, max_tokens)
        if cfg.provider == "ollama":
            return await self._call_ollama(
                full_prompt,
                m,
                cfg.endpoint or settings.OLLAMA_URL or "http://localhost:11434",
                cfg.timeout_seconds,
                temperature,
                max_tokens,
            )
        return await self._call_openai_compatible(
            full_prompt,
            system_prompt,
            m,
            key,
            cfg.provider,
            cfg.endpoint,
            cfg.timeout_seconds,
            cfg.additional_headers or {},
            key_index,
            temperature,
            max_tokens,
        )

    async def _call_google(
        self, full_prompt: str, model: str, api_key: str, temperature: float, max_tokens: int
    ) -> Tuple[str, str]:
        key = api_key or settings.GOOGLE_API_KEY
        if not key:
            raise ValueError("Google API key not configured")

        def _run() -> str:
            genai.configure(api_key=key)
            gm = genai.GenerativeModel(model_name=model, safety_settings=self.safety_settings)
            r = gm.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(max_output_tokens=max_tokens, temperature=temperature),
                safety_settings=self.safety_settings,
            )
            return r.text if r else ""

        text = await asyncio.get_event_loop().run_in_executor(None, _run)
        return text or "", model

    async def _call_anthropic(
        self,
        full_prompt: str,
        system_prompt: Optional[str],
        model: str,
        api_key: str,
        temperature: float,
        max_tokens: int,
    ) -> Tuple[str, str]:
        key = api_key.strip() if api_key else ""
        if not key:
            raise ValueError("Anthropic API key not configured")
        try:
            client = AsyncAnthropic(api_key=key)
            # Ensure client.messages is available (check Anthropic SDK version)
            if not hasattr(client, "messages"):
                raise ValueError("Anthropic SDK not properly initialized. Check your anthropic package version.")
            r = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "You are a helpful AI assistant.",
                messages=[{"role": "user", "content": full_prompt}],
            )
            return (r.content[0].text if r and r.content else "") or "", model
        except AttributeError as e:
            raise ValueError(
                f"Anthropic SDK error: {str(e)}. Please ensure you have the latest anthropic package installed."
            )
        except Exception as e:
            raise ValueError(f"Anthropic API call failed: {str(e)}")

    async def _call_hf(
        self, full_prompt: str, model: str, api_key: str, timeout_seconds: int, temperature: float, max_tokens: int
    ) -> Tuple[str, str]:
        key = api_key.strip() if api_key else ""
        if not key:
            raise ValueError("HuggingFace API key not configured")
        # Use new endpoint: https://router.huggingface.co instead of deprecated https://api-inference.huggingface.co
        async with httpx.AsyncClient(timeout=max(5, int(timeout_seconds))) as client:
            resp = await client.post(
                f"https://router.huggingface.co/models/{model}",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "inputs": full_prompt,
                    "options": {"wait_for_model": True},
                    "parameters": {"max_new_tokens": max_tokens, "temperature": temperature},
                },
            )
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

    async def _call_ollama(
        self, full_prompt: str, model: str, base_url: str, timeout_seconds: int, temperature: float, max_tokens: int
    ) -> Tuple[str, str]:
        async with httpx.AsyncClient(timeout=max(10, int(timeout_seconds))) as client:
            resp = await client.post(
                base_url.rstrip("/") + "/api/generate",
                json={
                    "model": model or self.default_model,
                    "prompt": full_prompt,
                    "temperature": temperature,
                    "options": {"num_predict": max_tokens},
                    "stream": False,
                },
            )
            if resp.status_code != 200:
                raise ValueError(f"Ollama call failed: {resp.status_code} {resp.text}")
            return (resp.json().get("response") or ""), model

    async def _call_openai_compatible(
        self,
        full_prompt: str,
        system_prompt: Optional[str],
        model: str,
        api_key: str,
        provider: str,
        endpoint: Optional[str],
        timeout_seconds: int,
        headers: Dict[str, str],
        key_index: int,
        temperature: float,
        max_tokens: int,
    ) -> Tuple[str, str]:
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

        client = AsyncOpenAI(
            api_key=key, base_url=base.rstrip("/"), timeout=max(5, int(timeout_seconds)), default_headers=headers
        )
        messages = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + [
            {"role": "user", "content": full_prompt}
        ]
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
                    error_msg += (
                        " [Invalid API key or insufficient permissions. Check your key and provider account settings]"
                    )
                elif "429" in error_msg or "quota" in lowered or "rate" in lowered:
                    error_msg += " [API quota exceeded or rate limited. Check billing and usage limits]"
                raise ValueError(error_msg)

        # If all model variants fail, return the most actionable error.
        raise ValueError(f"{provider} call failed for models {candidate_models}: {last_error}")

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
