"""
Attachment and Document API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional, Dict, Any

from app.models.database import get_db, Email
from app.models.user_models import User
from app.models.document_models import EmailAttachment, DocumentAnalysis
from app.services.attachment_service import AttachmentService, DocumentAnalysisService
from app.core.security import get_current_user, logger
from app.tasks.document_analysis_task import task_handler

router = APIRouter(prefix="/attachments", tags=["attachments"])
attachment_service = AttachmentService()
analysis_service = DocumentAnalysisService()


def _resolve_user_plan(current_user: User) -> str:
    """
    Normalize user plan for tiered analysis logic.
    """
    subscription_status = (getattr(current_user, "subscription_status", "free") or "free").lower()
    plan = (getattr(current_user, "plan", "free") or "free").lower()
    if subscription_status == "active" or plan in {"pro", "plus", "professional", "enterprise"}:
        return plan if plan != "free" else "pro"
    return "free"


@router.get("/{attachment_id}/info")
async def get_attachment_info(
    attachment_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get attachment metadata"""
    try:
        # Fetch attachment
        stmt = select(EmailAttachment).where(EmailAttachment.id == attachment_id)
        result = await session.execute(stmt)
        attachment = result.scalars().first()
        
        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")
        
        # Check user owns the email
        email = await session.get(Email, attachment.email_id)
        if not email or email.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        return {
            "success": True,
            "data": {
                "id": attachment.id,
                "filename": attachment.filename,
                "mime_type": attachment.mime_type,
                "file_size": attachment.file_size,
                "extension": attachment.extension,
                "created_at": attachment.created_at.isoformat() if attachment.created_at else None,
                "download_url": attachment_service.get_attachment_url(attachment.id)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching attachment info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{attachment_id}/download")
async def download_attachment(
    attachment_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Download attachment file"""
    try:
        # Fetch attachment
        stmt = select(EmailAttachment).where(EmailAttachment.id == attachment_id)
        result = await session.execute(stmt)
        attachment = result.scalars().first()
        
        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")
        
        # Check user owns the email
        email = await session.get(Email, attachment.email_id)
        if not email or email.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Read file
        file_content = attachment_service.read_file_content(attachment.storage_path)
        if not file_content:
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        from fastapi.responses import FileResponse
        import tempfile
        import os
        
        # Create temporary file for download
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{attachment.extension}")
        temp_file.write(file_content)
        temp_file.close()
        
        return FileResponse(
            path=temp_file.name,
            filename=attachment.filename,
            media_type=attachment.mime_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading attachment: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{attachment_id}/analysis")
async def get_attachment_analysis(
    attachment_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get AI analysis of attachment (with tiering)"""
    try:
        # Fetch attachment
        stmt = select(EmailAttachment).where(EmailAttachment.id == attachment_id)
        result = await session.execute(stmt)
        attachment = result.scalars().first()
        
        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")
        
        # Check user owns the email
        email = await session.get(Email, attachment.email_id)
        if not email or email.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Check if analysis exists
        stmt = select(DocumentAnalysis).where(DocumentAnalysis.attachment_id == attachment_id)
        result = await session.execute(stmt)
        analysis = result.scalars().first()
        
        if not analysis:
            # Return "not analyzed yet" message
            return {
                "success": True,
                "data": {
                    "status": "not_analyzed",
                    "message": "Analysis not yet available. Use POST to trigger analysis.",
                    "file_name": attachment.filename,
                    "file_extension": attachment.extension
                }
            }
        
        # Return with tiering applied
        user_plan = _resolve_user_plan(current_user)
        return {
            "success": True,
            "data": analysis.to_dict(include_full_analysis=(user_plan != "free"))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching analysis: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{attachment_id}/analyze")
async def trigger_attachment_analysis(
    attachment_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Trigger AI analysis on attachment (runs in background)"""
    try:
        # Fetch attachment
        stmt = select(EmailAttachment).where(EmailAttachment.id == attachment_id)
        result = await session.execute(stmt)
        attachment = result.scalars().first()
        
        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")
        
        # Check user owns the email
        email = await session.get(Email, attachment.email_id)
        if not email or email.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Check if analysis already exists
        stmt = select(DocumentAnalysis).where(DocumentAnalysis.attachment_id == attachment_id)
        result = await session.execute(stmt)
        existing_analysis = result.scalars().first()
        
        if existing_analysis and existing_analysis.analysis_status == "completed":
            return {
                "success": True,
                "message": "Analysis already completed",
                "analysis_id": existing_analysis.id
            }
        
        # Schedule background analysis using task handler (Celery or async fallback)
        await task_handler.analyze_attachment(
            attachment_id=attachment_id,
            user_id=current_user.id,
            user_plan=_resolve_user_plan(current_user)
        )
        
        logger.info(f"📊 Analysis scheduled for attachment: {attachment.filename}")
        
        return {
            "success": True,
            "message": "Analysis triggered. Check back in a moment for results.",
            "attachment_id": attachment_id,
            "filename": attachment.filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering analysis: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Email-specific attachment endpoints
email_attachment_router = APIRouter(prefix="/emails", tags=["email-attachments"])


@email_attachment_router.get("/{email_id}/attachments")
async def list_email_attachments(
    email_id: str,
    include_analysis: bool = Query(False, description="Include analysis status for each attachment"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """List all attachments for an email"""
    try:
        # Check user owns the email
        email = await session.get(Email, email_id)
        if not email or email.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Fetch attachments
        stmt = select(EmailAttachment).where(EmailAttachment.email_id == email_id)
        result = await session.execute(stmt)
        attachments = result.scalars().all()
        
        attachment_list = []
        for att in attachments:
            att_data = {
                "id": att.id,
                "filename": att.filename,
                "extension": att.extension,
                "file_size": att.file_size,
                "mime_type": att.mime_type,
                "download_url": attachment_service.get_attachment_url(att.id),
                "created_at": att.created_at.isoformat() if att.created_at else None
            }
            
            # Include analysis status if requested
            if include_analysis:
                stmt = select(DocumentAnalysis).where(DocumentAnalysis.attachment_id == att.id)
                res = await session.execute(stmt)
                analysis = res.scalars().first()
                
                if analysis:
                    att_data["analysis"] = {
                        "status": analysis.analysis_status,
                        "summary": analysis.summary[:100] if analysis.summary else None,
                        "has_full_analysis": analysis.is_full_analysis
                    }
                else:
                    att_data["analysis"] = {
                        "status": "not_analyzed",
                        "summary": None,
                        "has_full_analysis": False
                    }
            
            attachment_list.append(att_data)
        
        return {
            "success": True,
            "data": {
                "count": len(attachments),
                "attachments": attachment_list
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing attachments: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@email_attachment_router.get("/{email_id}/attachments/count")
async def get_attachment_count(
    email_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get attachment count for email (for UI badges)"""
    try:
        # Check user owns the email
        email = await session.get(Email, email_id)
        if not email or email.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Count attachments
        stmt = select(EmailAttachment).where(EmailAttachment.email_id == email_id)
        result = await session.execute(stmt)
        attachments = result.scalars().all()
        
        return {
            "success": True,
            "data": {
                "email_id": email_id,
                "attachment_count": len(attachments)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error counting attachments: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@email_attachment_router.post("/{email_id}/attachments/analyze-all")
async def analyze_all_email_attachments(
    email_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Trigger AI analysis on all attachments in an email"""
    try:
        # Check user owns the email
        email = await session.get(Email, email_id)
        if not email or email.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Get all attachments
        stmt = select(EmailAttachment).where(EmailAttachment.email_id == email_id)
        result = await session.execute(stmt)
        attachments = result.scalars().all()
        
        if not attachments:
            return {
                "success": True,
                "message": "No attachments found",
                "attachments_queued": 0
            }
        
        # Queue analysis for all attachments
        await task_handler.analyze_email_attachments(
            email_id=email_id,
            user_id=current_user.id,
            user_plan=_resolve_user_plan(current_user),
        )
        
        logger.info(f"📊 Analysis queued for {len(attachments)} attachments in email: {email_id}")
        
        return {
            "success": True,
            "message": f"Analysis triggered for {len(attachments)} attachment(s)",
            "attachments_queued": len(attachments),
            "email_id": email_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing email attachments: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
