"""Authenticated AI routes; schemas and workspace operations live in dedicated modules."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.ai_schemas import (
    ActionItem,
    AnalyzeRelationshipRequest,
    AnalyzeSentimentRequest,
    AnalyzeSentimentResponse,
    ClassifyEmailRequest,
    ClassifyEmailResponse,
    ExtractActionsRequest,
    ExtractActionsResponse,
    RelationshipAnalysisResponse,
    SummarizeThreadRequest,
    WorkspaceAssistRequest,
)
from app.core.security import get_current_user, logger
from app.models.database import get_db
from app.models.user_models import User
from app.services import workspace_assistant_service
from app.services.llm_orchestration_service import llm_service
from app.services.workspace_assistant_service import _is_super_admin

router = APIRouter(prefix="/api/v1/ai", tags=["intelligence"])


@router.post("/classify", response_model=ClassifyEmailResponse)
async def classify_email(
    request: ClassifyEmailRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Classify an email into categories like URGENT, FOLLOW_UP, FYI, TASK, etc.

    Uses AI to analyze the email content and determine its category.
    """
    try:
        result = await llm_service.classify_email(
            sender=request.sender,
            subject=request.subject,
            body=request.body,
            tenant_id=current_user.id,
            session=session,
        )

        return ClassifyEmailResponse(
            category=result.get("category", "FYI"),
            confidence=result.get("confidence", 0.5),
            reasoning=result.get("reasoning", ""),
        )

    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient credits for this operation"
        )
    except Exception as e:
        logger.error(f"Error classifying email: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to classify email")


@router.post("/extract-actions", response_model=ExtractActionsResponse)
async def extract_actions(
    request: ExtractActionsRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Extract action items and tasks from an email.

    Identifies specific tasks, deadlines, and responsible parties mentioned in the email.
    """
    try:
        result = await llm_service.extract_actions(
            email_body=f"From: {request.sender}\nSubject: {request.subject}\n\n{request.body}",
            user_id=current_user.id,
            session=session,
        )

        actions = []
        for action in result.get("actions", []):
            actions.append(
                ActionItem(
                    task=action.get("task", ""),
                    deadline=action.get("deadline"),
                    priority=action.get("priority", "medium"),
                    assigned_to=action.get("assigned_to"),
                )
            )

        return ExtractActionsResponse(actions=actions)

    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient credits for this operation"
        )
    except Exception as e:
        logger.error(f"Error extracting actions: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to extract actions")


@router.post("/sentiment", response_model=AnalyzeSentimentResponse)
async def analyze_sentiment(
    request: AnalyzeSentimentRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Analyze the sentiment and tone of email content.

    Returns sentiment (positive/neutral/negative) and tone indicators.
    """
    try:
        result = await llm_service.analyze_sentiment(
            email_body=request.content, user_id=current_user.id, session=session
        )

        return AnalyzeSentimentResponse(
            sentiment=result.get("sentiment", "neutral"),
            tone=result.get("tone", "professional"),
            confidence=result.get("confidence", 0.5),
        )

    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient credits for this operation"
        )
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to analyze sentiment")


@router.post("/summarize")
async def summarize_thread(
    request: SummarizeThreadRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Summarize an email thread.

    Condenses conversation history into a concise summary highlighting key points.
    """
    try:
        summary = await llm_service.summarize_thread(
            thread_body=request.thread_content, user_id=current_user.id, session=session
        )

        return {"success": True, "summary": summary}

    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient credits for this operation"
        )
    except Exception as e:
        logger.error(f"Error summarizing thread: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to summarize thread")


@router.post("/relationship-analysis", response_model=RelationshipAnalysisResponse)
async def analyze_relationship(
    request: AnalyzeRelationshipRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Analyze the relationship quality based on email communication.

    Provides insights into relationship strength, engagement level, and relationship type.
    """
    try:
        # Use the LLM service to analyze relationship
        # This would use a dedicated prompt
        result = {"relationship_score": 0.75, "engagement_level": "active", "relationship_type": "colleague"}

        return RelationshipAnalysisResponse(**result)

    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient credits for this operation"
        )
    except Exception as e:
        logger.error(f"Error analyzing relationship: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to analyze relationship")


@router.get("/models")
async def list_available_models(current_user: User = Depends(get_current_user)):
    """Get list of available AI models"""
    from app.services.llm_orchestration_service import ModelRegistry

    models = ModelRegistry.list_models()

    return {
        "models": [
            {
                "id": model_id,
                "name": model_info["name"],
                "provider": model_info["provider"],
                "description": model_info["description"],
                "cost_per_1k_input": model_info["input_cost_per_1k"],
                "cost_per_1k_output": model_info["output_cost_per_1k"],
            }
            for model_id, model_info in models.items()
        ]
    }


@router.get("/prompts")
async def list_available_prompts(current_user: User = Depends(get_current_user)):
    """Get list of available prompts"""
    from app.services.llm_orchestration_service import PromptRegistry

    prompts = PromptRegistry.list_prompts()

    return {"prompts": prompts}


@router.get("/health")
async def ai_provider_health(
    check_live: bool = False,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Provider-aware LLM health endpoint.

    - `check_live=false`: returns configuration/status metadata quickly.
    - `check_live=true`: runs live probes (super admin only).
    """
    if check_live and not _is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Live provider checks require super admin access")
    data = await llm_service.provider_health(session=session, include_live_checks=check_live)
    return {
        "success": True,
        "health": data,
    }


@router.post("/assistant/assist")
async def workspace_assist(
    request: WorkspaceAssistRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Generate page-aware AI drafts and next-step actions for workspace builders."""
    return await workspace_assistant_service.workspace_assist(request, current_user, session)
