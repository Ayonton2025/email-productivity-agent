"""Compatibility facade for the decomposed LLM service.

New code should import from :mod:`app.services.llm`.
"""

from app.services.llm import LLMOrchestrationService, ModelRegistry, PromptRegistry, UsageTracker, llm_service

__all__ = ["LLMOrchestrationService", "ModelRegistry", "PromptRegistry", "UsageTracker", "llm_service"]
