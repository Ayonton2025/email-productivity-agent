"""Workspace assistant orchestration, quota accounting and confirmation."""

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.ai_schemas import WorkspaceAssistRequest
from app.core.config import settings
from app.core.security import logger
from app.models.billing_models import UsageLog
from app.models.user_models import User
from app.services.llm_orchestration_service import llm_service
from app.services.workspace_confirmation import (
    _create_confirmation_token,
    _decode_confirmation_token,
    _validate_confirmation_token,
)
from app.services.workspace_execution import _execute_assistant_draft

WORKPLACE_USAGE_METRIC = "ai_workplace_assistant_requests"


def _is_super_admin(current_user: User) -> bool:
    if getattr(current_user, "is_superuser", False) or getattr(current_user, "is_admin", False):
        return True
    if str(getattr(current_user, "plan", "")).strip().lower() == "super_admin":
        return True
    allowed = {e.strip().lower() for e in (settings.ADMIN_EMAILS or "").split(",") if e.strip()}
    return bool(current_user.email and current_user.email.lower() in allowed)


async def workspace_assist(
    request: WorkspaceAssistRequest,
    current_user: User,
    session: AsyncSession,
):
    """Generate page-aware AI drafts and next-step actions for workspace builders."""
    try:
        execute_mode = request.mode.lower() == "execute"
        if execute_mode and request.confirmed:
            if not request.confirmation_token:
                raise HTTPException(status_code=400, detail="Missing confirmation token")
            if not isinstance(request.draft, dict):
                raise HTTPException(status_code=400, detail="Missing draft for confirmed execute")

            token_payload = _decode_confirmation_token(request.confirmation_token)
            _validate_confirmation_token(
                token_payload=token_payload,
                user_id=str(current_user.id),
                page=request.page,
                objective=request.objective,
                draft=request.draft,
            )
            execution = await _execute_assistant_draft(
                page=request.page,
                draft=request.draft,
                objective=request.objective,
                current_user=current_user,
                session=session,
            )
            return {
                "success": True,
                "page": request.page,
                "assistant_message": "Execution completed after confirmation.",
                "draft": request.draft,
                "execution": execution,
            }

        monthly_limit = max(int(settings.WORKPLACE_ASSIST_MONTHLY_LIMIT or 0), 0)
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        usage_query = select(func.coalesce(func.sum(UsageLog.quantity), 0)).where(
            UsageLog.user_id == current_user.id,
            UsageLog.metric == WORKPLACE_USAGE_METRIC,
            UsageLog.created_at >= month_start,
        )
        usage_result = await session.execute(usage_query)
        used_this_month = int(usage_result.scalar_one() or 0)
        if monthly_limit > 0 and used_this_month >= monthly_limit and not _is_super_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Workplace monthly limit reached ({monthly_limit} requests).",
            )

        result = await llm_service.create_workspace_assist(
            page=request.page,
            objective=request.objective,
            mode=request.mode,
            context=request.context or {},
            user_id=current_user.id,
            session=session,
        )
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail=result.get("error", "Assistant request failed")
            )
        if execute_mode:
            draft_for_confirmation = result.get("draft", {}) or {}
            token = _create_confirmation_token(
                user_id=str(current_user.id),
                page=request.page,
                objective=request.objective,
                draft=draft_for_confirmation,
            )
            result["requires_confirmation"] = True
            result["confirmation_token"] = token
            result["assistant_message"] = (
                result.get("assistant_message") or "Preview ready. Confirm execution to apply changes."
            )

        session.add(
            UsageLog(
                user_id=current_user.id,
                tenant_id=current_user.id,
                metric=WORKPLACE_USAGE_METRIC,
                quantity=1,
                breakdown={"page": request.page, "mode": request.mode},
            )
        )
        result["usage"] = {
            "month_used": used_this_month + 1,
            "month_limit": monthly_limit,
            "month_remaining": max(0, monthly_limit - (used_this_month + 1)) if monthly_limit > 0 else None,
        }
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Workspace assist error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate assistant response"
        )
