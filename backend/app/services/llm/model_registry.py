"""Model metadata and deterministic cost calculation."""

from typing import Any, Dict, Optional


class ModelRegistry:
    MODELS = {
        "gemini-1.5-flash": {
            "name": "Gemini 1.5 Flash",
            "provider": "google",
            "description": "Fast general-purpose Gemini model",
            "input_cost_per_1k": 0.000075,
            "output_cost_per_1k": 0.0003,
        },
        "gemini-1.5-pro": {
            "name": "Gemini 1.5 Pro",
            "provider": "google",
            "description": "Higher-quality Gemini model",
            "input_cost_per_1k": 0.0035,
            "output_cost_per_1k": 0.0105,
        },
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
        return (input_tokens / 1000) * model["input_cost_per_1k"] + (output_tokens / 1000) * model[
            "output_cost_per_1k"
        ]
