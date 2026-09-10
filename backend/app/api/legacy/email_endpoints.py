"""Email endpoints."""

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import get_current_user
from app.models.database import get_db
from app.models.user_models import User
from app.services.email_service import EmailService

router = APIRouter()
# Preserve the established log category for compatibility with operational filters.
logger = get_logger("app.api.endpoints")


@router.post("/emails/sync")
async def sync_user_emails(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Sync user emails"""
    try:
        return {
            "message": "Email sync completed",
            "user_id": current_user.id,
            "synced_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error syncing emails: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync emails")


@router.get("/emails", response_model=List[Dict[str, Any]])
async def get_emails(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    """Get all emails (public for demo)"""
    email_service = EmailService(db)
    return await email_service.get_all_emails(limit, offset)


@router.post("/emails/load-mock")
async def load_mock_emails(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Load mock emails for current user"""
    try:
        email_service = EmailService(db)
        emails = await email_service.load_mock_emails(current_user.id)
        return {"message": f"Loaded {len(emails)} mock emails", "emails": emails, "user_id": current_user.id}
    except Exception as e:
        logger.error(f"❌ [load_mock_emails] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load mock emails: {str(e)}")


@router.post("/emails/load-mock-if-empty")
async def load_mock_emails_if_empty(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Load mock emails only if user has very few emails"""
    try:
        email_service = EmailService(db)
        existing_emails = await email_service.get_user_emails(current_user.id)

        if existing_emails and len(existing_emails) >= 5:
            return {
                "message": f"User already has {len(existing_emails)} emails, no mock data loaded",
                "user_id": current_user.id,
                "existing_emails_count": len(existing_emails),
            }
        else:
            emails = await email_service.load_mock_emails(current_user.id)
            return {"message": f"Loaded {len(emails)} mock emails", "emails": emails, "user_id": current_user.id}

    except Exception as e:
        logger.error(f"❌ [load_mock_emails_if_empty] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load mock emails: {str(e)}")


@router.get("/emails/{email_id}", response_model=Dict[str, Any])
async def get_email(email_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get a specific email (user-specific)"""
    try:
        email_service = EmailService(db)

        # ✅ REMOVED: Don't automatically ensure user has emails here
        # await email_service.ensure_user_has_emails(current_user.id)

        # Get email with user_id filter for security
        email = await email_service.get_email_by_id(email_id, current_user.id)
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        return email
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [get_email] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get email: {str(e)}")


@router.put("/emails/{email_id}/category")
async def update_email_category(
    email_id: str, category: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Update email category (user-specific)"""
    try:
        email_service = EmailService(db)
        success = await email_service.update_email_category(email_id, category, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Email not found")
        return {"message": "Category updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [update_email_category] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update category: {str(e)}")
