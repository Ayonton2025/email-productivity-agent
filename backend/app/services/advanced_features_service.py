"""
Utility service for advanced AI features MVP implementations.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List


class AdvancedFeaturesService:
    @staticmethod
    def detect_meeting_intent(subject: str | None, body: str | None) -> Dict[str, Any]:
        text = f"{subject or ''}\n{body or ''}".lower()
        keywords = ["meeting", "schedule", "calendar", "availability", "zoom", "teams"]
        score = sum(1 for kw in keywords if kw in text)
        return {
            "is_meeting": score >= 2,
            "confidence": min(99, 40 + score * 12),
            "signals": [kw for kw in keywords if kw in text],
        }

    @staticmethod
    def propose_slots() -> List[str]:
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        return [
            (now + timedelta(days=1, hours=10)).isoformat(),
            (now + timedelta(days=2, hours=14)).isoformat(),
            (now + timedelta(days=3, hours=16)).isoformat(),
        ]

    @staticmethod
    def build_meeting_agenda(topic: str) -> List[str]:
        return [
            f"Objective alignment for {topic}",
            "Status and blockers review",
            "Decisions required and owners",
            "Next actions and deadlines",
        ]

    @staticmethod
    def score_security(sender: str, subject: str | None, body: str | None) -> Dict[str, Any]:
        text = f"{subject or ''}\n{body or ''}".lower()
        signals = []
        if "urgent" in text:
            signals.append("urgency_language")
        if "password" in text or "verify your account" in text:
            signals.append("credential_request")
        if "bit.ly" in text or "tinyurl" in text:
            signals.append("shortened_link")
        if sender and ("no-reply" in sender.lower() or "support" in sender.lower()):
            signals.append("impersonation_risk")
        score = min(0.99, 0.12 * len(signals))
        verdict = "safe"
        if score >= 0.6:
            verdict = "dangerous"
        elif score >= 0.3:
            verdict = "suspicious"
        return {"scam_score": round(score, 3), "signals": signals, "verdict": verdict}

    @staticmethod
    def legal_extract(text: str) -> Dict[str, Any]:
        lower = text.lower()
        obligations = []
        penalties = []
        deadlines = []
        if "must" in lower or "shall" in lower:
            obligations.append("Contains mandatory obligations language")
        if "penalty" in lower or "liquidated damages" in lower:
            penalties.append("Potential penalty clause detected")
        if "within" in lower or "by " in lower:
            deadlines.append("Timeline/deadline language detected")
        return {
            "obligations": obligations,
            "penalties": penalties,
            "deadlines": deadlines,
            "risk_level": "high" if penalties else ("medium" if obligations else "low"),
        }

    @staticmethod
    def pseudo_embedding(text: str, dims: int = 12) -> List[float]:
        # Lightweight deterministic embedding fallback.
        base = [0.0] * dims
        for i, ch in enumerate(text.encode("utf-8")):
            base[i % dims] += float(ch % 31) / 31.0
        norm = sum(abs(x) for x in base) or 1.0
        return [round(x / norm, 6) for x in base]

    @staticmethod
    def cosine_like(a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        num = sum(x * y for x, y in zip(a, b))
        den = (sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5)
        if den == 0:
            return 0.0
        return float(num / den)

    @staticmethod
    def translate_text(text: str, target_language: str) -> str:
        return f"[{target_language}] {text}"

    @staticmethod
    def predict_priority(sender: str, subject: str | None, body: str | None) -> float:
        text = f"{subject or ''}\n{body or ''}".lower()
        score = 0.25
        if any(k in text for k in ["urgent", "deadline", "contract", "payment", "incident"]):
            score += 0.35
        if sender and any(k in sender.lower() for k in ["ceo", "finance", "legal", "vip"]):
            score += 0.2
        if len(text) > 1000:
            score += 0.05
        return min(0.99, round(score, 3))

    @staticmethod
    def moderate_reply(reply: str) -> Dict[str, Any]:
        text = reply.lower()
        flagged_terms = [t for t in ["idiot", "stupid", "hate", "always you people"] if t in text]
        bias_risk = 0.15 * len(flagged_terms)
        return {
            "approved": len(flagged_terms) == 0,
            "bias_risk": round(min(1.0, bias_risk), 3),
            "flags": flagged_terms,
        }
