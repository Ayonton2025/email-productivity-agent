from unittest.mock import AsyncMock

import pytest

from app.core.config import settings
from app.services.llm_orchestration_service import LLMOrchestrationService
from app.services.llm_provider_config_service import RuntimeProviderConfig


def provider(name: str, priority: int) -> RuntimeProviderConfig:
    return RuntimeProviderConfig(
        provider=name,
        display_name=name.title(),
        model=f"{name}-model",
        endpoint=None,
        api_keys=["test-key"],
        additional_headers={},
        extra_config={},
        max_retries=1,
        backoff_seconds=0,
        timeout_seconds=5,
        priority=priority,
    )


@pytest.mark.asyncio
async def test_call_llm_falls_back_to_next_configured_provider(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MOCK_MODE", False)
    monkeypatch.setattr(settings, "LLM_PROVIDER", "google")
    service = LLMOrchestrationService()
    monkeypatch.setattr(
        service, "_runtime_configs", AsyncMock(return_value=[provider("google", 1), provider("openai", 2)])
    )
    monkeypatch.setattr(service, "_cache_get", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_cache_set", AsyncMock())
    calls = []

    async def call(config, *_args):
        calls.append(config.provider)
        if config.provider == "google":
            raise ConnectionError("primary unavailable")
        return "fallback response", "gemini-1.5-flash"

    monkeypatch.setattr(service, "_call_with_retry", call)

    result = await service.call_llm("Summarize this message")

    assert calls == ["google", "openai"]
    assert result["success"] is True
    assert result["provider"] == "openai"
    assert result["response"] == "fallback response"


@pytest.mark.asyncio
async def test_call_llm_returns_explicit_error_when_every_provider_fails(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MOCK_MODE", False)
    service = LLMOrchestrationService()
    monkeypatch.setattr(service, "_runtime_configs", AsyncMock(return_value=[provider("google", 1)]))
    monkeypatch.setattr(service, "_cache_get", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_call_with_retry", AsyncMock(side_effect=TimeoutError("provider timed out")))

    result = await service.call_llm("Classify this message")

    assert result == {"success": False, "error": "provider timed out"}
