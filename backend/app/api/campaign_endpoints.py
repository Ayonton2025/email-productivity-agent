"""
API endpoints for campaign management:
- CRUD operations for campaigns
- Campaign sequence management
- Lead management
- Campaign execution
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from app.models.database import get_db, UserEmailAccount
from app.models.user_models import User
from app.core.security import get_current_user
from app.models.campaign_models import Campaign, CampaignSequence, Lead
from app.services.billing_service import FeatureGatingService
from sqlalchemy import select, and_, desc

router = APIRouter(prefix="/campaigns", tags=["campaigns"])
gating_service = FeatureGatingService()


def _score_sender_account(account: UserEmailAccount) -> int:
    """Higher score means better default sender for campaigns."""
    score = 0
    if account.is_primary:
        score += 50
    if account.sync_enabled:
        score += 20
    if account.last_sync_status == "success":
        score += 10
    if account.provider == "gmail":
        score += 5
    # Prefer accounts with room in daily cap when cap is set
    limit = int(account.send_limit_daily or 0)
    used = int(account.send_count_daily or 0)
    if limit <= 0 or used < limit:
        score += 10
    return score


# Pydantic models
class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    campaign_type: str
    from_email: str
    from_name: Optional[str] = None
    reply_to: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    daily_send_limit: int = 50
    send_delay_minutes: int = 5
    timezone: str = "UTC"
    send_hours: List[int] = []
    warm_up_enabled: bool = False
    warm_up_emails_per_day: int = 5
    ab_test_enabled: bool = False
    ab_test_split: float = 0.5
    tags: List[str] = []


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    reply_to: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    daily_send_limit: Optional[int] = None
    send_delay_minutes: Optional[int] = None
    timezone: Optional[str] = None
    send_hours: Optional[List[int]] = None
    warm_up_enabled: Optional[bool] = None
    warm_up_emails_per_day: Optional[int] = None
    ab_test_enabled: Optional[bool] = None
    ab_test_split: Optional[float] = None
    tags: Optional[List[str]] = None


class CampaignSequenceCreate(BaseModel):
    campaign_id: str
    step_order: int
    name: str
    subject_template: str
    body_template: str
    delay_days: int = 0
    delay_hours: int = 0
    send_if_opened: bool = False
    send_if_clicked: bool = False
    send_if_replied: bool = False
    stop_if_replied: bool = True
    variant_a_subject: Optional[str] = None
    variant_a_body: Optional[str] = None
    variant_b_subject: Optional[str] = None
    variant_b_body: Optional[str] = None


class LeadCreate(BaseModel):
    campaign_id: Optional[str] = None
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    custom_fields: Dict[str, Any] = {}


class LeadsBulkCreate(BaseModel):
    campaign_id: Optional[str] = None
    leads: List[LeadCreate]


@router.get("/recommended-sender", response_model=Dict[str, Any])
async def get_recommended_sender_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Return best available sender account for campaign defaults."""
    try:
        result = await db.execute(
            select(UserEmailAccount).where(
                and_(
                    UserEmailAccount.user_id == current_user.id,
                    UserEmailAccount.is_active == True,
                )
            )
        )
        accounts = list(result.scalars().all())
        if not accounts:
            return {
                "success": True,
                "recommended": None,
                "message": "No active email accounts found. Connect an account first.",
            }

        ranked = sorted(
            accounts,
            key=lambda a: (
                _score_sender_account(a),
                a.created_at or datetime.min,
            ),
            reverse=True,
        )
        best = ranked[0]
        at_name = (best.display_name or "").strip()
        fallback_name = (current_user.full_name or "").strip() or (best.email.split("@")[0] if best.email else "")
        from_name = at_name or fallback_name

        limit = int(best.send_limit_daily or 0)
        used = int(best.send_count_daily or 0)
        send_cap_ok = limit <= 0 or used < limit

        return {
            "success": True,
            "recommended": {
                "account_id": best.id,
                "email": best.email,
                "provider": best.provider,
                "from_name": from_name,
                "reply_to": best.email,
                "is_primary": bool(best.is_primary),
                "sync_enabled": bool(best.sync_enabled),
                "last_sync_status": best.last_sync_status,
                "send_limit_daily": limit,
                "send_count_daily": used,
                "send_cap_ok": send_cap_ok,
            },
            "message": "Recommended sender account loaded",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recommended sender account: {str(e)}")


@router.get("/", response_model=List[Dict[str, Any]])
async def get_campaigns(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all campaigns for the user"""
    try:
        query = select(Campaign).where(Campaign.user_id == current_user.id)
        if status:
            query = query.where(Campaign.status == status)
        query = query.order_by(desc(Campaign.created_at))
        
        result = await db.execute(query)
        campaigns = list(result.scalars().all())
        return [c.to_dict() for c in campaigns]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get campaigns: {str(e)}")


@router.get("/{campaign_id}", response_model=Dict[str, Any])
async def get_campaign(
    campaign_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific campaign with sequences and stats"""
    try:
        result = await db.execute(
            select(Campaign).where(
                and_(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get sequences
        sequences_result = await db.execute(
            select(CampaignSequence).where(
                CampaignSequence.campaign_id == campaign_id
            ).order_by(CampaignSequence.step_order.asc())
        )
        sequences = list(sequences_result.scalars().all())
        
        # Get lead count
        leads_count = await db.execute(
            select(Lead).where(Lead.campaign_id == campaign_id)
        )
        total_leads = len(list(leads_count.scalars().all()))
        
        campaign_dict = campaign.to_dict()
        campaign_dict["sequences"] = [s.to_dict() for s in sequences]
        campaign_dict["total_leads"] = total_leads
        return campaign_dict
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get campaign: {str(e)}")


@router.post("/", response_model=Dict[str, Any])
async def create_campaign(
    campaign_data: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new campaign"""
    try:
        # Check: Does user have access to outbound campaigns?
        can_access = await gating_service.can_access_feature(
            user_id=current_user.id,
            feature="outbound_campaigns",
            session=db
        )
        if not can_access:
            raise HTTPException(
                status_code=403,
                detail="Outbound campaigns are not available on your plan. Upgrade to Enterprise."
            )
        
        campaign = Campaign(
            user_id=current_user.id,
            name=campaign_data.name,
            description=campaign_data.description,
            campaign_type=campaign_data.campaign_type,
            from_email=campaign_data.from_email,
            from_name=campaign_data.from_name,
            reply_to=campaign_data.reply_to,
            start_date=campaign_data.start_date,
            end_date=campaign_data.end_date,
            daily_send_limit=campaign_data.daily_send_limit,
            send_delay_minutes=campaign_data.send_delay_minutes,
            timezone=campaign_data.timezone,
            send_hours=campaign_data.send_hours,
            warm_up_enabled=campaign_data.warm_up_enabled,
            warm_up_emails_per_day=campaign_data.warm_up_emails_per_day,
            ab_test_enabled=campaign_data.ab_test_enabled,
            ab_test_split=campaign_data.ab_test_split,
            tags=campaign_data.tags,
            status="draft"
        )
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)
        return campaign.to_dict()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create campaign: {str(e)}")


@router.put("/{campaign_id}", response_model=Dict[str, Any])
async def update_campaign(
    campaign_id: str,
    campaign_data: CampaignUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a campaign"""
    try:
        result = await db.execute(
            select(Campaign).where(
                and_(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Update fields
        for field, value in campaign_data.dict(exclude_unset=True).items():
            setattr(campaign, field, value)
        
        await db.commit()
        await db.refresh(campaign)
        return campaign.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update campaign: {str(e)}")


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a campaign"""
    try:
        result = await db.execute(
            select(Campaign).where(
                and_(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        await db.delete(campaign)
        await db.commit()
        return {"message": "Campaign deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete campaign: {str(e)}")


@router.post("/{campaign_id}/sequences", response_model=Dict[str, Any])
async def create_campaign_sequence(
    campaign_id: str,
    sequence_data: CampaignSequenceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a campaign sequence step"""
    try:
        # Verify campaign belongs to user
        result = await db.execute(
            select(Campaign).where(
                and_(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        sequence = CampaignSequence(
            campaign_id=campaign_id,
            step_order=sequence_data.step_order,
            name=sequence_data.name,
            subject_template=sequence_data.subject_template,
            body_template=sequence_data.body_template,
            delay_days=sequence_data.delay_days,
            delay_hours=sequence_data.delay_hours,
            send_if_opened=sequence_data.send_if_opened,
            send_if_clicked=sequence_data.send_if_clicked,
            send_if_replied=sequence_data.send_if_replied,
            stop_if_replied=sequence_data.stop_if_replied,
            variant_a_subject=sequence_data.variant_a_subject,
            variant_a_body=sequence_data.variant_a_body,
            variant_b_subject=sequence_data.variant_b_subject,
            variant_b_body=sequence_data.variant_b_body
        )
        db.add(sequence)
        await db.commit()
        await db.refresh(sequence)
        return sequence.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create campaign sequence: {str(e)}")


@router.post("/{campaign_id}/leads/bulk", response_model=Dict[str, Any])
async def bulk_create_leads(
    campaign_id: str,
    leads_data: LeadsBulkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Bulk create leads for a campaign"""
    try:
        # Verify campaign belongs to user
        result = await db.execute(
            select(Campaign).where(
                and_(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        created_leads = []
        for lead_data in leads_data.leads:
            lead = Lead(
                campaign_id=campaign_id,
                user_id=current_user.id,
                email=lead_data.email,
                first_name=lead_data.first_name,
                last_name=lead_data.last_name,
                company=lead_data.company,
                job_title=lead_data.job_title,
                custom_fields=lead_data.custom_fields,
                status="pending"
            )
            db.add(lead)
            created_leads.append(lead)
        
        campaign.total_leads = (campaign.total_leads or 0) + len(created_leads)
        await db.commit()
        
        return {
            "message": f"Created {len(created_leads)} leads",
            "leads_created": len(created_leads)
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create leads: {str(e)}")


@router.get("/{campaign_id}/leads", response_model=List[Dict[str, Any]])
async def get_campaign_leads(
    campaign_id: str,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get leads for a campaign"""
    try:
        # Verify campaign belongs to user
        result = await db.execute(
            select(Campaign).where(
                and_(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        query = select(Lead).where(Lead.campaign_id == campaign_id)
        if status:
            query = query.where(Lead.status == status)
        query = query.order_by(desc(Lead.created_at)).limit(limit).offset(offset)
        
        leads_result = await db.execute(query)
        leads = list(leads_result.scalars().all())
        return [l.to_dict() for l in leads]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get campaign leads: {str(e)}")


@router.post("/{campaign_id}/start")
async def start_campaign(
    campaign_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start a campaign"""
    try:
        result = await db.execute(
            select(Campaign).where(
                and_(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        campaign.status = "running"
        await db.commit()
        # Kick off send cycle immediately; periodic beat task will continue processing.
        try:
            from app.tasks.campaign_tasks import send_campaign_emails
            send_campaign_emails.delay()
        except Exception:
            # Keep campaign start non-blocking even if broker enqueue fails.
            pass
        return {"message": "Campaign started", "status": "running", "send_cycle_queued": True}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to start campaign: {str(e)}")


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Pause a campaign"""
    try:
        result = await db.execute(
            select(Campaign).where(
                and_(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        campaign.status = "paused"
        await db.commit()
        return {"message": "Campaign paused", "status": "paused"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to pause campaign: {str(e)}")
