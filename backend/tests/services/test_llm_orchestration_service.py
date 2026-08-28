import json

import pytest

from app.core.config import settings
from app.services.llm_orchestration_service import LLMOrchestrationService, ModelRegistry, UsageTracker
from app.services.llm_provider_config_service import RuntimeProviderConfig


def provider(name: str, model: str) -> RuntimeProviderConfig:
    return RuntimeProviderConfig(
        provider=name,
        display_name=name.title(),
        model=model,
        endpoint=None,
        api_keys=[f"{name}-key"],
        additional_headers={},
        extra_config={},
        max_retries=1,
        backoff_seconds=0,
        timeout_seconds=5,
        priority=1,
    )


@pytest.fixture
def live_service(monkeypatch, mocker):
    monkeypatch.setattr(settings, "ENABLE_MOCK_MODE", False)
    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    service = LLMOrchestrationService(default_model="gemini-1.5-flash")
    mocker.patch.object(service, "_cache_get", new=mocker.AsyncMock(return_value=None))
    mocker.patch.object(service, "_cache_set", new=mocker.AsyncMock())
    return service


@pytest.mark.asyncio
async def test_provider_switches_from_openai_to_anthropic(live_service, mocker):
    configs = [provider("openai", "gpt-4o-mini"), provider("anthropic", "claude-3-5-haiku-20241022")]
    mocker.patch.object(live_service, "_runtime_configs", new=mocker.AsyncMock(return_value=configs))

    async def call(config, *_args):
        if config.provider == "openai":
            raise ConnectionError("OpenAI unavailable")
        return '{"reply":"Happy to help","tone":"professional"}', config.model

    call_mock = mocker.patch.object(live_service, "_call_with_retry", side_effect=call)
    result = await live_service.call_llm("Reply to this customer email", feature="reply_generator")

    assert result["success"] is True
    assert result["provider"] == "anthropic"
    assert json.loads(result["response"])["reply"] == "Happy to help"
    assert [item.args[0].provider for item in call_mock.await_args_list] == ["openai", "anthropic"]


@pytest.mark.asyncio
async def test_prompt_generation_returns_structured_response(live_service, mocker):
    config = provider("google", "gemini-1.5-flash")
    mocker.patch.object(live_service, "_runtime_configs", new=mocker.AsyncMock(return_value=[config]))
    structured = {"category": "support", "confidence": 0.96, "reasoning": "Customer requests assistance"}
    mocker.patch.object(
        live_service,
        "_call_with_retry",
        new=mocker.AsyncMock(return_value=(json.dumps(structured), "gemini-1.5-flash")),
    )

    result = await live_service.call_llm(
        "Customer email: I cannot access my account",
        system_prompt='Return JSON with category, confidence, and reasoning',
        feature="email_classifier",
    )

    assert result["success"] is True
    assert json.loads(result["response"]) == structured


@pytest.mark.asyncio
async def test_token_accounting_and_cost_are_consistent(live_service, mocker):
    config = provider("google", "gemini-1.5-flash")
    mocker.patch.object(live_service, "_runtime_configs", new=mocker.AsyncMock(return_value=[config]))
    mocker.patch.object(
        live_service,
        "_call_with_retry",
        new=mocker.AsyncMock(return_value=("one two three four", "gemini-1.5-flash")),
    )

    result = await live_service.call_llm("one two three four five", feature="email_summarizer")

    assert result["tokens"] == {"input": 6, "output": 5, "total": 11}
    assert result["cost"] == pytest.approx(ModelRegistry.calculate_cost("gemini-1.5-flash", 6, 5))
    usage = UsageTracker.log_usage("user-1", "email_summarizer", result["model"], 6, 5, result["cost"])
    assert usage["total_tokens"] == 11
    assert usage["cost_usd"] == result["cost"]
