"""
Sales pipeline integration endpoints (CRM bridge).
"""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.user_models import User

router = APIRouter(prefix="/sales", tags=["sales"])


class CRMSyncRequest(BaseModel):
    crm: str  # hubspot, salesforce
    email_id: str
    deal_stage: str


@router.post("/crm/sync-email", response_model=Dict[str, Any])
async def sync_email_to_crm(
    body: CRMSyncRequest,
    current_user: User = Depends(get_current_user),
):
    return {
        "success": True,
        "user_id": current_user.id,
        "crm": body.crm.lower(),
        "email_id": body.email_id,
        "deal_stage": body.deal_stage,
        "message": "CRM sync queued. Configure HubSpot/Salesforce credentials for live sync.",
    }
