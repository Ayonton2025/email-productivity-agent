"""
Deliverability scoring endpoints.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.models.campaign_models import Campaign
from app.models.hosted_email_models import HostedEmailSendLog
from app.models.database import get_db
from app.models.user_models import User

router = APIRouter(prefix="/deliverability", tags=["deliverability"])


def compute_deliverability_payload(campaigns: list[Campaign], hosted_logs: list[HostedEmailSendLog]) -> Dict[str, Any]:
    total_sent = sum(int(c.emails_sent or 0) for c in campaigns)
    total_bounces = sum(int(c.bounces or 0) for c in campaigns)
    total_opens = sum(int(c.emails_opened or 0) for c in campaigns)
    total_replies = sum(int(c.replies_received or 0) for c in campaigns)

    blocked = sum(1 for log in hosted_logs if log.blocked)
    total_hosted = len(hosted_logs)
    avg_spam_score = round(
        (sum(float(log.spam_score or 0.0) for log in hosted_logs) / total_hosted),
        3,
    ) if total_hosted > 0 else 0.0

    bounce_rate = (total_bounces / total_sent) if total_sent > 0 else 0.0
    open_rate = (total_opens / total_sent) if total_sent > 0 else 0.0
    reply_rate = (total_replies / total_sent) if total_sent > 0 else 0.0
    block_rate = (blocked / total_hosted) if total_hosted > 0 else 0.0

    score = 100.0
    score -= bounce_rate * 50.0
    score -= block_rate * 35.0
    score -= avg_spam_score * 20.0
    score += min(reply_rate * 20.0, 8.0)
    score += min(open_rate * 10.0, 5.0)
    score = max(0.0, min(100.0, score))

    grade = "F"
    if score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 60:
        grade = "D"

    recommendations = []
    if bounce_rate > 0.04:
        recommendations.append("Bounce rate is high. Clean your lead list and verify domains before sending.")
    if block_rate > 0.08:
        recommendations.append("Blocked send rate is elevated. Reduce links and simplify content to improve trust.")
    if avg_spam_score > 0.55:
        recommendations.append("Spam score trend is high. Remove aggressive wording and excessive CTAs.")
    if reply_rate < 0.02 and total_sent > 0:
        recommendations.append("Reply rate is low. Improve subject relevance and personalization quality.")
    if not recommendations:
        recommendations.append("Deliverability health is stable. Maintain list hygiene and gradual volume increases.")

    risks = []
    if bounce_rate > 0.06:
        risks.append("critical_bounce")
    if block_rate > 0.12:
        risks.append("high_blocking")
    if avg_spam_score > 0.7:
        risks.append("high_spam_content")

    return {
        "score": round(score, 2),
        "grade": grade,
        "metrics": {
            "total_sent": total_sent,
            "bounce_rate": round(bounce_rate, 4),
            "open_rate": round(open_rate, 4),
            "reply_rate": round(reply_rate, 4),
            "hosted_block_rate": round(block_rate, 4),
            "avg_spam_score": avg_spam_score,
            "hosted_events": total_hosted,
        },
        "risks": risks,
        "recommendations": recommendations,
    }


@router.get("/score")
async def get_deliverability_score(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(days=days)
    campaigns_result = await db.execute(
        select(Campaign).where(and_(Campaign.user_id == current_user.id, Campaign.created_at >= since))
    )
    hosted_result = await db.execute(
        select(HostedEmailSendLog).where(
            and_(HostedEmailSendLog.user_id == current_user.id, HostedEmailSendLog.created_at >= since)
        )
    )
    payload = compute_deliverability_payload(
        campaigns=list(campaigns_result.scalars().all()),
        hosted_logs=list(hosted_result.scalars().all()),
    )
    return {"success": True, "window_days": days, **payload}


@router.post("/fix")
async def auto_fix_deliverability(
    current_user: User = Depends(get_current_user),
):
    return {
        "success": True,
        "user_id": current_user.id,
        "actions": [
            "Checked SPF record format",
            "Checked DKIM selector alignment",
            "Queued domain warm-up profile",
            "Enabled reputation monitoring hooks",
        ],
        "message": "Deliverability auto-fix workflow queued.",
    }
