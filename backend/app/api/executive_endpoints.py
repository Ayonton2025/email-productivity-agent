"""
AI executive layer endpoints.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deliverability_endpoints import compute_deliverability_payload
from app.core.security import get_current_user
from app.models.campaign_models import Campaign
from app.models.collaboration_models import SharedInbox, SharedInboxEmail, SharedInboxMember
from app.models.hosted_email_models import HostedEmailSendLog
from app.models.database import get_db
from app.models.user_models import User
from app.services.daily_briefing_service import DailyBriefingService
from app.services.llm_orchestration_service import llm_service

router = APIRouter(prefix="/executive", tags=["executive"])


class ExecutiveCommandRequest(BaseModel):
    objective: str
    context: Optional[dict] = None


@router.get("/summary")
async def executive_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    briefing_service = DailyBriefingService()
    briefing = await briefing_service.get_today_briefing(current_user.id, db)
    if not briefing:
        briefing = await briefing_service.generate_daily_briefing(current_user.id, db)

    since = datetime.utcnow() - timedelta(days=30)
    campaigns_result = await db.execute(
        select(Campaign).where(and_(Campaign.user_id == current_user.id, Campaign.created_at >= since))
    )
    hosted_result = await db.execute(
        select(HostedEmailSendLog).where(
            and_(HostedEmailSendLog.user_id == current_user.id, HostedEmailSendLog.created_at >= since)
        )
    )
    deliverability = compute_deliverability_payload(
        campaigns=list(campaigns_result.scalars().all()),
        hosted_logs=list(hosted_result.scalars().all()),
    )

    member_rows = await db.execute(
        select(SharedInboxMember).where(SharedInboxMember.user_id == current_user.id)
    )
    inbox_memberships = list(member_rows.scalars().all())
    inbox_ids = [row.inbox_id for row in inbox_memberships]
    open_items = 0
    if inbox_ids:
        open_rows = await db.execute(
            select(SharedInboxEmail).where(
                and_(
                    SharedInboxEmail.inbox_id.in_(inbox_ids),
                    SharedInboxEmail.status != "resolved",
                )
            )
        )
        open_items = len(list(open_rows.scalars().all()))

    return {
        "success": True,
        "briefing": briefing.to_dict() if briefing else None,
        "deliverability": deliverability,
        "shared_inbox": {
            "inboxes": len(inbox_ids),
            "open_items": open_items,
        },
    }


@router.post("/command")
async def executive_command(
    request: ExecutiveCommandRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    summary = await executive_summary(current_user=current_user, db=db)
    if not summary.get("success"):
        raise HTTPException(status_code=500, detail="Could not load executive context")

    context = {
        "summary": summary,
        "user_context": request.context or {},
    }
    result = await llm_service.create_workspace_assist(
        page="executive",
        objective=request.objective,
        mode="draft",
        context=context,
        user_id=current_user.id,
        session=db,
    )
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Executive AI command failed"))
    return result
