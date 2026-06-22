"""
Auto-reply rules API: CRUD rules, away mode, approval queue.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.models.database import Email, EmailDraft, UserEmailAccount, get_db
from app.models.auto_reply_models import AutoReplyRule, AwayModeSetting
from app.models.user_models import User
from app.services.smtp_service import smtp_service

router = APIRouter(prefix="/auto-reply", tags=["auto-reply"])


# ---------- Request/Response models ----------


class CreateRuleBody(BaseModel):
    name: str
    match_category: Optional[str] = None
    match_sender: Optional[str] = None
    instructions: Optional[str] = None
    priority: int = 0
    confidence_min: float = 0.0
    require_away_mode: bool = True
    use_approval_queue: bool = True
    auto_send: bool = False


class UpdateRuleBody(BaseModel):
    name: Optional[str] = None
    match_category: Optional[str] = None
    match_sender: Optional[str] = None
    instructions: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    confidence_min: Optional[float] = None
    require_away_mode: Optional[bool] = None
    use_approval_queue: Optional[bool] = None
    auto_send: Optional[bool] = None


class AwayModeBody(BaseModel):
    is_active: bool
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    message: Optional[str] = None


# ---------- Rules CRUD ----------


@router.get("/", response_model=List[Dict[str, Any]])
async def get_rules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all auto-reply rules for the current user."""
    result = await db.execute(
        select(AutoReplyRule).where(AutoReplyRule.user_id == current_user.id).order_by(
            AutoReplyRule.priority.asc(), AutoReplyRule.created_at.asc()
        )
    )
    rules = result.scalars().all()
    return [r.to_dict() for r in rules]


@router.post("/", response_model=Dict[str, Any])
async def create_rule(
    body: CreateRuleBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new auto-reply rule."""
    rule = AutoReplyRule(
        user_id=current_user.id,
        name=body.name,
        match_category=body.match_category,
        match_sender=body.match_sender,
        instructions=body.instructions,
        is_active=True,
        priority=body.priority,
        confidence_min=body.confidence_min,
        require_away_mode=body.require_away_mode,
        use_approval_queue=body.use_approval_queue,
        auto_send=body.auto_send,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return {"message": "Rule created", "rule_id": rule.id, "rule": rule.to_dict()}


@router.put("/{rule_id}", response_model=Dict[str, Any])
async def update_rule(
    rule_id: str,
    body: UpdateRuleBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an auto-reply rule."""
    result = await db.execute(
        select(AutoReplyRule).where(
            AutoReplyRule.id == rule_id,
            AutoReplyRule.user_id == current_user.id,
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(rule, k, v)
    await db.commit()
    await db.refresh(rule)
    return {"message": "Rule updated", "rule": rule.to_dict()}


@router.delete("/{rule_id}", response_model=Dict[str, Any])
async def delete_rule(
    rule_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an auto-reply rule."""
    result = await db.execute(
        select(AutoReplyRule).where(
            AutoReplyRule.id == rule_id,
            AutoReplyRule.user_id == current_user.id,
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.delete(rule)
    await db.commit()
    return {"message": "Rule deleted"}


# ---------- Away mode ----------


@router.get("/away", response_model=Dict[str, Any])
async def get_away_mode(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's away mode settings."""
    result = await db.execute(
        select(AwayModeSetting).where(AwayModeSetting.user_id == current_user.id)
    )
    s = result.scalar_one_or_none()
    if not s:
        return {
            "is_active": False,
            "valid_from": None,
            "valid_until": None,
            "message": None,
        }
    return s.to_dict()


@router.put("/away", response_model=Dict[str, Any])
async def set_away_mode(
    body: AwayModeBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update away mode settings."""
    result = await db.execute(
        select(AwayModeSetting).where(AwayModeSetting.user_id == current_user.id)
    )
    s = result.scalar_one_or_none()
    if not s:
        s = AwayModeSetting(user_id=current_user.id)
        db.add(s)
    s.is_active = body.is_active
    s.valid_from = body.valid_from
    s.valid_until = body.valid_until
    s.message = body.message
    await db.commit()
    await db.refresh(s)
    return {"message": "Away mode updated", "away": s.to_dict()}


# ---------- Approval queue ----------


@router.get("/approval-queue", response_model=List[Dict[str, Any]])
async def get_approval_queue(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List drafts with auto_reply=True and approval_status=pending."""
    result = await db.execute(
        select(EmailDraft)
        .where(EmailDraft.user_id == current_user.id)
        .order_by(EmailDraft.created_at.desc())
    )
    drafts = result.scalars().all()
    out = []
    for d in drafts:
        meta = d.draft_metadata or {}
        if meta.get("auto_reply") and meta.get("approval_status") == "pending":
            out.append(d.to_dict())
    return out


@router.post("/approval-queue/{draft_id}/approve", response_model=Dict[str, Any])
async def approve_draft(
    draft_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark draft as approved and send immediately when linked account metadata is available."""
    result = await db.execute(
        select(EmailDraft).where(
            EmailDraft.id == draft_id,
            EmailDraft.user_id == current_user.id,
        )
    )
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    meta = dict(draft.draft_metadata or {})
    meta["approval_status"] = "approved"
    send_outcome = None

    account_id = meta.get("account_id")
    account_provider = (meta.get("account_provider") or "").strip().lower()
    if account_id:
        account_result = await db.execute(
            select(UserEmailAccount).where(
                UserEmailAccount.id == account_id,
                UserEmailAccount.user_id == current_user.id,
            )
        )
        account = account_result.scalar_one_or_none()
        if account and draft.recipient:
            # Try provider-native Gmail API send first for OAuth Gmail accounts,
            # then fall back to SMTP for other providers.
            if account_provider == "gmail" and account.access_token:
                email_message_id = None
                if draft.context_email_id:
                    email_result = await db.execute(
                        select(Email).where(Email.id == draft.context_email_id, Email.user_id == current_user.id)
                    )
                    source_email = email_result.scalar_one_or_none()
                    if source_email:
                        email_message_id = source_email.message_id
                try:
                    from app.services.gmail_send_service import send_via_gmail_api
                    await send_via_gmail_api(
                        db=db,
                        user_id=current_user.id,
                        to=draft.recipient,
                        subject=draft.subject or "",
                        body=draft.body or "",
                        in_reply_to=email_message_id,
                        references=[],
                    )
                    send_outcome = {"sent": True, "provider": "gmail_api"}
                except Exception as e:
                    send_outcome = {"sent": False, "provider": "gmail_api", "error": str(e)}

            if not (send_outcome and send_outcome.get("sent")):
                sent, message = await smtp_service.send_email(
                    account=account,
                    db=db,
                    to=draft.recipient,
                    subject=draft.subject or "",
                    body_text=draft.body or "",
                )
                send_outcome = {
                    "sent": bool(sent),
                    "provider": "smtp",
                    "message": message,
                }

    if send_outcome:
        meta["sent_on_approval"] = bool(send_outcome.get("sent"))
        meta["send_result"] = send_outcome

    draft.draft_metadata = meta
    await db.commit()
    await db.refresh(draft)
    return {"message": "Draft approved", "draft": draft.to_dict(), "send_result": send_outcome}


@router.post("/approval-queue/{draft_id}/reject", response_model=Dict[str, Any])
async def reject_draft(
    draft_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark draft as rejected (or delete it)."""
    result = await db.execute(
        select(EmailDraft).where(
            EmailDraft.id == draft_id,
            EmailDraft.user_id == current_user.id,
        )
    )
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    meta = dict(draft.draft_metadata or {})
    meta["approval_status"] = "rejected"
    draft.draft_metadata = meta
    await db.commit()
    await db.refresh(draft)
    return {"message": "Draft rejected", "draft": draft.to_dict()}
