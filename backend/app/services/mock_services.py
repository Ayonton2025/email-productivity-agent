"""Deterministic, offline responses used by development and tests.

Keep these helpers free of database and network imports.  Service boundaries call
them before initializing third-party clients whenever ENABLE_MOCK_MODE is true.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional


def mock_llm_response(prompt: str, feature: Optional[str], model: str) -> Dict[str, Any]:
    """Return the same useful response for the same prompt and feature."""
    normalized_feature = (feature or "general").lower()
    prompt_excerpt = " ".join((prompt or "").split())[:160]

    if "classif" in normalized_feature:
        response = {"category": "Work", "confidence": 0.99, "reasoning": "Offline mock classification"}
    elif "sentiment" in normalized_feature:
        response = {"sentiment": "neutral", "tone": "professional", "confidence": 0.99}
    elif "summar" in normalized_feature:
        response = {"summary": prompt_excerpt or "Mock email summary", "key_points": ["Generated offline"]}
    elif "action" in normalized_feature or "extract" in normalized_feature:
        response = {
            "actions": [{"action": "Review and respond", "deadline": None, "priority": "Medium", "assigned_to": "You"}]
        }
    elif "reply" in normalized_feature:
        response = {
            "reply": "Thank you for your email. I have received it and will respond shortly.",
            "tone": "professional",
        }
    elif "relationship" in normalized_feature:
        response = {"relationship_score": 0.75, "relationship_type": "professional", "engagement_level": "active"}
    else:
        response = {"message": "Mock AI response", "excerpt": prompt_excerpt}

    text = json.dumps(response)
    input_tokens = max(1, len((prompt or "").split()))
    output_tokens = max(1, len(text.split()))
    return {
        "response": text,
        "tokens": {"input": input_tokens, "output": output_tokens, "total": input_tokens + output_tokens},
        "cost": 0.0,
        "model": f"mock:{model}",
        "provider": "mock",
        "success": True,
        "cached": False,
        "mock": True,
    }


def mock_payment(reference: str, amount: int, currency: str, email: str) -> Dict[str, Any]:
    """Create an offline checkout response without handling real money."""
    stable_id = hashlib.sha256(reference.encode("utf-8")).hexdigest()[:16]
    return {
        "success": True,
        "authorization_url": f"http://localhost:3000/billing/mock-success?reference={reference}",
        "access_code": f"mock_{stable_id}",
        "reference": reference,
        "amount": amount,
        "currency": currency,
        "email": email,
        "payment_status": "completed",
        "mock": True,
    }
