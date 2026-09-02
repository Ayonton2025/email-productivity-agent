import pytest

from app.services.model_registry import ModelRegistry
from app.services.prompt_registry import PromptRegistry


def test_model_registry_calculates_input_and_output_costs():
    cost = ModelRegistry.calculate_cost("gemini-1.5-flash", input_tokens=2000, output_tokens=500)
    assert cost == pytest.approx(0.0003)


def test_model_registry_returns_zero_for_unknown_model():
    assert ModelRegistry.calculate_cost("not-configured", 1000, 1000) == 0.0


def test_prompt_registry_returns_contract_and_safe_default():
    classifier = PromptRegistry.get_prompt("email_classifier")
    assert classifier["id"] == "email_classifier"
    assert "category" in classifier["system_prompt"]
    assert PromptRegistry.get_prompt("missing") == {}


def test_prompt_registry_lists_every_registered_prompt():
    assert set(PromptRegistry.list_prompts()) == set(PromptRegistry.PROMPTS)
