"""Domain exceptions raised by LLM orchestration boundaries."""


class LLMOrchestrationError(RuntimeError):
    """Base error for orchestration failures."""


class ProviderUnavailableError(LLMOrchestrationError):
    """Raised when no configured provider can satisfy a request."""


class UsageLimitExceededError(LLMOrchestrationError):
    """Raised when an account has exhausted an enforced usage limit."""
