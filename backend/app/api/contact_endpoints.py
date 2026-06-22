"""
Public contact-form endpoints for sales/support forms.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.core.security import logger

router = APIRouter(prefix="/contact", tags=["contact"])


class ContactSendEmailRequest(BaseModel):
    name: str
    email: EmailStr
    company: Optional[str] = None
    message: str
    type: Optional[str] = "sales_inquiry"
    recipients: Optional[List[EmailStr]] = None


class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    company: Optional[str] = None
    message: str
    contact_type: Optional[str] = "sales_inquiry"


@router.post("/send-email", response_model=Dict[str, Any])
async def send_contact_email(payload: ContactSendEmailRequest):
    """
    Compatibility endpoint.
    In this version we acknowledge and log the request for processing.
    """
    try:
        logger.info(
            "Contact form submission (send-email): email=%s type=%s recipients=%s",
            payload.email,
            payload.type,
            payload.recipients or [],
        )
        return {
            "success": True,
            "message": "Contact request received",
            "queued": True,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process contact form: {str(exc)}")


@router.post("", response_model=Dict[str, Any])
async def create_contact(payload: ContactRequest):
    """Fallback contact endpoint used by frontend service retry path."""
    try:
        logger.info(
            "Contact form submission: email=%s type=%s",
            payload.email,
            payload.contact_type,
        )
        return {
            "success": True,
            "message": "Contact request received",
            "queued": True,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process contact request: {str(exc)}")
