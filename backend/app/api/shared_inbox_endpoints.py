"""
Shared inbox endpoints for collaborative email operations.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.core.config import settings
from app.models.billing_models import SUBSCRIPTION_PLANS, Subscription
from app.models.collaboration_models import SharedInbox, SharedInboxEmail, SharedInboxMember
from app.models.database import Email, get_db
from app.models.user_models import User
from app.services.billing_service import FeatureGatingService

router = APIRouter(prefix="/shared-inboxes", tags=["shared-inboxes"])


class SharedInboxCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = None


class AddMemberRequest(BaseModel):
    user_email: str
    role: str = "member"


class SharedInboxEmailUpdateRequest(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    assigned_to_user_email: Optional[str] = None


ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"
VALID_MEMBER_ROLES = {ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER}

ACTION_VIEW = "view"
ACTION_ADD_MEMBER = "add_member"
ACTION_UPDATE_EMAIL = "update_email"
ACTION_ASSIGN = "assign"
ACTION_ADD_EMAIL = "add_email"

ROLE_PERMISSIONS = {
    ACTION_VIEW: {ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER},
    ACTION_ADD_MEMBER: {ROLE_OWNER, ROLE_ADMIN},
    ACTION_UPDATE_EMAIL: {ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER},
    ACTION_ASSIGN: {ROLE_OWNER, ROLE_ADMIN},
    ACTION_ADD_EMAIL: {ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER},
}

DEFAULT_SHARED_INBOX_LIMITS = {
    "team": 5,
    "enterprise": 100,
}


def _is_super_admin(user: User) -> bool:
    allowed = {e.strip().lower() for e in (settings.ADMIN_EMAILS or "").split(",") if e.strip()}
    return bool(user.email and user.email.lower() in allowed)


async def _get_subscription_for_user(user_id: str, db: AsyncSession) -> Optional[Subscription]:
    sub_row = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
    return sub_row.scalar_one_or_none()


def _plan_features(subscription: Optional[Subscription]) -> dict:
    if not subscription or subscription.status != "active":
        return {}
    if isinstance(subscription.features, dict) and subscription.features:
        return subscription.features
    return SUBSCRIPTION_PLANS.get(subscription.plan_id, {}).get("features", {})


def _shared_inbox_limit_for_plan(subscription: Optional[Subscription]) -> int:
    if not subscription or subscription.status != "active":
        return 0

    metadata = subscription.plan_metadata if isinstance(subscription.plan_metadata, dict) else {}
    if "shared_inboxes_limit" in metadata:
        try:
            return int(metadata["shared_inboxes_limit"])
        except (TypeError, ValueError):
            return 0

    default_limit = DEFAULT_SHARED_INBOX_LIMITS.get(subscription.plan_id, 0)
    return default_limit if default_limit >= 0 else 0


def _seat_limit(subscription: Optional[Subscription]) -> int:
    if not subscription or subscription.status != "active":
        return 0
    if subscription.seats_max is not None:
        return max(int(subscription.seats_max), 0)
    if subscription.seats_included is not None:
        return max(int(subscription.seats_included), 0)
    return 0


def _ensure_shared_inbox_feature(subscription: Optional[Subscription]) -> None:
    features = _plan_features(subscription)
    has_feature = bool(features.get("shared_inboxes") or features.get("team_shared_inbox"))
    if not has_feature:
        raise HTTPException(
            status_code=403,
            detail="Your billing plan does not include shared inbox access",
        )


async def _require_member(inbox_id: str, user_id: str, db: AsyncSession) -> tuple[SharedInbox, SharedInboxMember]:
    inbox_result = await db.execute(select(SharedInbox).where(SharedInbox.id == inbox_id))
    inbox = inbox_result.scalar_one_or_none()
    if not inbox or not inbox.is_active:
        raise HTTPException(status_code=404, detail="Shared inbox not found")

    member_result = await db.execute(
        select(SharedInboxMember).where(
            and_(SharedInboxMember.inbox_id == inbox_id, SharedInboxMember.user_id == user_id)
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="You are not a member of this shared inbox")
    return inbox, member


def _require_role(member: SharedInboxMember, action: str) -> None:
    role = member.role if member.role in VALID_MEMBER_ROLES else ROLE_MEMBER
    allowed_roles = ROLE_PERMISSIONS.get(action, {ROLE_OWNER})
    if role not in allowed_roles:
        raise HTTPException(status_code=403, detail=f"Role '{role}' cannot perform action '{action}'")


@router.get("/")
async def list_shared_inboxes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    membership_rows = await db.execute(
        select(SharedInboxMember, SharedInbox)
        .join(SharedInbox, SharedInbox.id == SharedInboxMember.inbox_id)
        .where(
            and_(
                SharedInboxMember.user_id == current_user.id,
                SharedInbox.is_active == True,
            )
        )
    )

    data = []
    for member, inbox in membership_rows.all():
        count_result = await db.execute(
            select(SharedInboxEmail).where(SharedInboxEmail.inbox_id == inbox.id)
        )
        count = len(list(count_result.scalars().all()))
        inbox_data = inbox.to_dict()
        inbox_data["member_role"] = member.role
        inbox_data["email_count"] = count
        data.append(inbox_data)
    return {"success": True, "items": data}


@router.post("/")
async def create_shared_inbox(
    request: SharedInboxCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subscription = await _get_subscription_for_user(current_user.id, db)
    gating_service = FeatureGatingService()
    if not _is_super_admin(current_user):
        can_access = await gating_service.can_access_feature(
            user_id=current_user.id,
            feature="shared_inbox",
            session=db,
        )
        if not can_access:
            _ensure_shared_inbox_feature(subscription)

    shared_inbox_limit = _shared_inbox_limit_for_plan(subscription)
    if shared_inbox_limit <= 0:
        can_access_override = await gating_service.can_access_feature(
            user_id=current_user.id,
            feature="shared_inbox",
            session=db,
        )
        if can_access_override:
            # User has explicit access via admin override; do not enforce plan default cap.
            shared_inbox_limit = 1000
    if _is_super_admin(current_user):
        shared_inbox_limit = max(shared_inbox_limit, 1000)
    owned_count_row = await db.execute(
        select(func.count(SharedInbox.id)).where(
            and_(SharedInbox.owner_user_id == current_user.id, SharedInbox.is_active == True)
        )
    )
    owned_count = int(owned_count_row.scalar_one() or 0)
    if owned_count >= shared_inbox_limit:
        raise HTTPException(
            status_code=403,
            detail=f"Plan limit reached: {shared_inbox_limit} shared inbox(es) allowed",
        )

    inbox = SharedInbox(
        owner_user_id=current_user.id,
        name=request.name.strip(),
        description=request.description,
    )
    db.add(inbox)
    await db.flush()

    db.add(SharedInboxMember(inbox_id=inbox.id, user_id=current_user.id, role="owner"))
    await db.commit()
    await db.refresh(inbox)
    return {"success": True, "inbox": inbox.to_dict()}


@router.get("/{inbox_id}/members")
async def list_shared_inbox_members(
    inbox_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _, member = await _require_member(inbox_id=inbox_id, user_id=current_user.id, db=db)
    _require_role(member, ACTION_VIEW)
    rows = await db.execute(
        select(SharedInboxMember, User)
        .join(User, User.id == SharedInboxMember.user_id)
        .where(SharedInboxMember.inbox_id == inbox_id)
    )
    members = []
    for member, user in rows.all():
        members.append(
            {
                "id": member.id,
                "user_id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": member.role,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            }
        )
    return {"success": True, "members": members}


@router.post("/{inbox_id}/members")
async def add_shared_inbox_member(
    inbox_id: str,
    request: AddMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inbox, member = await _require_member(inbox_id=inbox_id, user_id=current_user.id, db=db)
    _require_role(member, ACTION_ADD_MEMBER)

    owner_subscription = await _get_subscription_for_user(inbox.owner_user_id, db)
    if not _is_super_admin(current_user):
        _ensure_shared_inbox_feature(owner_subscription)

    member_count_row = await db.execute(
        select(func.count(SharedInboxMember.id)).where(SharedInboxMember.inbox_id == inbox_id)
    )
    member_count = int(member_count_row.scalar_one() or 0)
    max_members = _seat_limit(owner_subscription)
    if _is_super_admin(current_user):
        max_members = max(max_members, 500)
    if max_members <= 0:
        raise HTTPException(status_code=403, detail="No team seats available for this shared inbox")
    if member_count >= max_members:
        raise HTTPException(
            status_code=403,
            detail=f"Team seat limit reached: {max_members} member(s) allowed for this plan",
        )

    target_user_result = await db.execute(select(User).where(User.email == request.user_email))
    target_user = target_user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    existing = await db.execute(
        select(SharedInboxMember).where(
            and_(SharedInboxMember.inbox_id == inbox_id, SharedInboxMember.user_id == target_user.id)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User is already a member")

    requested_role = request.role if request.role in VALID_MEMBER_ROLES else ROLE_MEMBER
    # Prevent non-owners from creating/upgrading owner role.
    if requested_role == ROLE_OWNER and current_user.id != inbox.owner_user_id:
        raise HTTPException(status_code=403, detail="Only inbox owner can assign owner role")
    # Keep a single owner model at the inbox level.
    if requested_role == ROLE_OWNER and target_user.id != inbox.owner_user_id:
        raise HTTPException(status_code=400, detail="Owner role must match inbox owner")

    member = SharedInboxMember(
        inbox_id=inbox_id,
        user_id=target_user.id,
        role=requested_role,
    )
    db.add(member)
    await db.commit()
    return {"success": True, "member": member.to_dict()}


@router.post("/{inbox_id}/emails/{email_id}")
async def add_email_to_shared_inbox(
    inbox_id: str,
    email_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _, member = await _require_member(inbox_id=inbox_id, user_id=current_user.id, db=db)
    _require_role(member, ACTION_ADD_EMAIL)

    email_result = await db.execute(
        select(Email).where(and_(Email.id == email_id, Email.user_id == current_user.id))
    )
    email = email_result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found in your mailbox")

    existing = await db.execute(
        select(SharedInboxEmail).where(
            and_(SharedInboxEmail.inbox_id == inbox_id, SharedInboxEmail.email_id == email_id)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already added to this shared inbox")

    record = SharedInboxEmail(
        inbox_id=inbox_id,
        email_id=email_id,
        added_by_user_id=current_user.id,
        status="open",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return {"success": True, "item": record.to_dict()}


@router.get("/{inbox_id}/emails")
async def list_shared_inbox_emails(
    inbox_id: str,
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _, member = await _require_member(inbox_id=inbox_id, user_id=current_user.id, db=db)
    _require_role(member, ACTION_VIEW)

    query = (
        select(SharedInboxEmail, Email)
        .join(Email, Email.id == SharedInboxEmail.email_id)
        .where(SharedInboxEmail.inbox_id == inbox_id)
        .order_by(SharedInboxEmail.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status:
        query = query.where(SharedInboxEmail.status == status)

    rows = await db.execute(query)
    items = []
    for shared_item, email in rows.all():
        items.append(
            {
                "shared": shared_item.to_dict(),
                "email": {
                    "id": email.id,
                    "sender": email.sender,
                    "subject": email.subject,
                    "received_at": email.received_at.isoformat() if email.received_at else None,
                    "ai_category": email.ai_category,
                    "ai_summary": email.ai_summary,
                    "body_preview": (email.body_text or email.body_html or "")[:300],
                },
            }
        )

    return {"success": True, "items": items}


@router.patch("/{inbox_id}/emails/{email_id}")
async def update_shared_inbox_email(
    inbox_id: str,
    email_id: str,
    request: SharedInboxEmailUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _, member = await _require_member(inbox_id=inbox_id, user_id=current_user.id, db=db)
    _require_role(member, ACTION_UPDATE_EMAIL)

    row = await db.execute(
        select(SharedInboxEmail).where(
            and_(SharedInboxEmail.inbox_id == inbox_id, SharedInboxEmail.email_id == email_id)
        )
    )
    item = row.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Shared inbox email not found")

    if request.status is not None:
        allowed = {"open", "in_progress", "resolved"}
        if request.status not in allowed:
            raise HTTPException(status_code=400, detail=f"Invalid status; expected one of {sorted(allowed)}")
        item.status = request.status

    if request.notes is not None:
        item.notes = request.notes

    if request.assigned_to_user_email is not None:
        _require_role(member, ACTION_ASSIGN)
        if request.assigned_to_user_email == "":
            item.assigned_to_user_id = None
        else:
            user_result = await db.execute(select(User).where(User.email == request.assigned_to_user_email))
            target_user = user_result.scalar_one_or_none()
            if not target_user:
                raise HTTPException(status_code=404, detail="Assigned user not found")

            member_result = await db.execute(
                select(SharedInboxMember).where(
                    and_(SharedInboxMember.inbox_id == inbox_id, SharedInboxMember.user_id == target_user.id)
                )
            )
            if not member_result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Assigned user must be a member of the shared inbox")
            item.assigned_to_user_id = target_user.id

    await db.commit()
    await db.refresh(item)
    return {"success": True, "item": item.to_dict()}
