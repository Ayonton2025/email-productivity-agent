from datetime import datetime
from typing import Any, Dict


class UsageTracker:
    """Build the normalized usage record returned by LLM calls."""

    @staticmethod
    def log_usage(
        user_id: str, feature: str, model: str, input_tokens: int, output_tokens: int, cost: float
    ) -> Dict[str, Any]:
        return {
            "user_id": user_id,
            "feature": feature,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": cost,
            "timestamp": datetime.utcnow().isoformat(),
        }
