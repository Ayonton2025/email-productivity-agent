"""Reply endpoints."""

from datetime import datetime

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


@router.post("/emails/{email_id}/generate-reply")
async def generate_email_reply(
    email_id: str,
    request: dict = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate AI-powered email reply"""
    try:
        # Be defensive: some User records may not have a `plan` attribute yet
        user_plan = getattr(current_user, "plan", "free")
        logger.info(
            f"🤖 [generate_email_reply] Generating reply for email: {email_id}, user: {current_user.id}, plan: {user_plan}"
        )

        email_service = EmailService(db)

        # ✅ REMOVED: Don't automatically ensure user has emails here
        # await email_service.ensure_user_has_emails(current_user.id)

        # Get the email with user_id filter for security
        email = await email_service.get_email_by_id(email_id, current_user.id)
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")

        logger.info(f"📧 [generate_email_reply] Generating reply for email from: {email.get('sender')}")

        # ✅ Generate reply with user plan information
        reply_data = await email_service.generate_reply_draft(
            email_id,
            current_user.id,
            user_plan=user_plan,
            user_name=(getattr(current_user, "full_name", None) or current_user.email.split("@")[0]),
        )

        reply_body = reply_data.get("body", "")

        # Create draft with the generated reply
        draft_data = {
            "subject": reply_data.get("subject", f"Re: {email.get('subject', 'Your email')}"),
            "body": reply_body,
            "recipient": email.get("sender"),
            "context_email_id": email_id,
            "metadata": {
                "ai_generated": reply_data.get("ai_generated", False),
                "mock": reply_data.get("mock", False),
                "original_subject": email.get("subject"),
                "generated_at": datetime.utcnow().isoformat(),
            },
        }

        draft = await email_service.create_draft(draft_data, user_id=current_user.id)

        logger.info(f"✅ [generate_email_reply] Reply generated and saved as draft: {draft['id']}")

        response = {
            "message": "Reply generated successfully",
            "reply": reply_body,  # ✅ Return the reply directly for frontend display
            "draft": draft,
            "ai_generated": reply_data.get("ai_generated", False),
            "mock": reply_data.get("mock", False),
        }

        # Include mock warning if fallback to mock
        if reply_data.get("mock_warning"):
            response["mock_warning"] = reply_data.get("mock_warning")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [generate_email_reply] Error generating reply: {e}")
        import traceback

        logger.info(f"❌ [generate_email_reply] Stack trace: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to generate reply: {str(e)}")
