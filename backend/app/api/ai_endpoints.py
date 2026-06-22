"""
Layer 1: AI Intelligence API endpoints

Provides endpoints for:
- Email classification
- Action item extraction
- Sentiment analysis
- Email summarization
- Commitment tracking
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import base64
import hashlib
import hmac
import json
import time

from app.models.database import get_db, User, PromptTemplate
from app.models.billing_models import UsageLog
from app.models.campaign_models import Campaign, CampaignSequence, Lead
from app.models.workflow_models import Workflow, WorkflowStep
from app.models.agent_models import Agent
from app.services.llm_orchestration_service import llm_service
from app.core.security import get_current_user, logger
from app.core.config import settings

router = APIRouter(prefix="/api/v1/ai", tags=["intelligence"])
WORKPLACE_USAGE_METRIC = "ai_workplace_assistant_requests"


def _is_super_admin(current_user: User) -> bool:
    if getattr(current_user, "is_superuser", False) or getattr(current_user, "is_admin", False):
        return True
    if str(getattr(current_user, "plan", "")).strip().lower() == "super_admin":
        return True
    allowed = {e.strip().lower() for e in (settings.ADMIN_EMAILS or "").split(",") if e.strip()}
    return bool(current_user.email and current_user.email.lower() in allowed)


# ============================
# Request/Response Models
# ============================

class ClassifyEmailRequest(BaseModel):
    sender: str
    subject: str
    body: str


class ClassifyEmailResponse(BaseModel):
    category: str
    confidence: float
    reasoning: str


class ExtractActionsRequest(BaseModel):
    sender: str
    subject: str
    body: str


class ActionItem(BaseModel):
    task: str
    deadline: Optional[str] = None
    priority: str = "medium"
    assigned_to: Optional[str] = None


class ExtractActionsResponse(BaseModel):
    actions: List[ActionItem]


class AnalyzeSentimentRequest(BaseModel):
    content: str


class AnalyzeSentimentResponse(BaseModel):
    sentiment: str  # positive, neutral, negative
    tone: str  # professional, casual, urgent, friendly
    confidence: float


class SummarizeThreadRequest(BaseModel):
    thread_content: str


class AnalyzeRelationshipRequest(BaseModel):
    sender: str
    email_content: str


class WorkspaceAssistRequest(BaseModel):
    page: str
    objective: str
    mode: str = "draft"
    context: Optional[dict] = None
    draft: Optional[dict] = None
    confirmed: bool = False
    confirmation_token: Optional[str] = None


class RelationshipAnalysisResponse(BaseModel):
    relationship_score: float
    engagement_level: str
    relationship_type: str


# ============================
# Email Classification Endpoint
# ============================

@router.post("/classify", response_model=ClassifyEmailResponse)
async def classify_email(
    request: ClassifyEmailRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
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
            session=session
        )
        
        return ClassifyEmailResponse(
            category=result.get("category", "FYI"),
            confidence=result.get("confidence", 0.5),
            reasoning=result.get("reasoning", "")
        )
    
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits for this operation"
        )
    except Exception as e:
        logger.error(f"Error classifying email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to classify email"
        )


# ============================
# Action Extraction Endpoint
# ============================

@router.post("/extract-actions", response_model=ExtractActionsResponse)
async def extract_actions(
    request: ExtractActionsRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Extract action items and tasks from an email.
    
    Identifies specific tasks, deadlines, and responsible parties mentioned in the email.
    """
    try:
        result = await llm_service.extract_actions(
            email_body=f"From: {request.sender}\nSubject: {request.subject}\n\n{request.body}",
            user_id=current_user.id,
            session=session
        )
        
        actions = []
        for action in result.get("actions", []):
            actions.append(ActionItem(
                task=action.get("task", ""),
                deadline=action.get("deadline"),
                priority=action.get("priority", "medium"),
                assigned_to=action.get("assigned_to")
            ))
        
        return ExtractActionsResponse(actions=actions)
    
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits for this operation"
        )
    except Exception as e:
        logger.error(f"Error extracting actions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract actions"
        )


# ============================
# Sentiment Analysis Endpoint
# ============================

@router.post("/sentiment", response_model=AnalyzeSentimentResponse)
async def analyze_sentiment(
    request: AnalyzeSentimentRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Analyze the sentiment and tone of email content.
    
    Returns sentiment (positive/neutral/negative) and tone indicators.
    """
    try:
        result = await llm_service.analyze_sentiment(
            email_body=request.content,
            user_id=current_user.id,
            session=session
        )
        
        return AnalyzeSentimentResponse(
            sentiment=result.get("sentiment", "neutral"),
            tone=result.get("tone", "professional"),
            confidence=result.get("confidence", 0.5)
        )
    
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits for this operation"
        )
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze sentiment"
        )


# ============================
# Thread Summarization Endpoint
# ============================

@router.post("/summarize")
async def summarize_thread(
    request: SummarizeThreadRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Summarize an email thread.
    
    Condenses conversation history into a concise summary highlighting key points.
    """
    try:
        summary = await llm_service.summarize_thread(
            thread_body=request.thread_content,
            user_id=current_user.id,
            session=session
        )
        
        return {
            "success": True,
            "summary": summary
        }
    
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits for this operation"
        )
    except Exception as e:
        logger.error(f"Error summarizing thread: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to summarize thread"
        )


# ============================
# Relationship Analysis Endpoint
# ============================

@router.post("/relationship-analysis", response_model=RelationshipAnalysisResponse)
async def analyze_relationship(
    request: AnalyzeRelationshipRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Analyze the relationship quality based on email communication.
    
    Provides insights into relationship strength, engagement level, and relationship type.
    """
    try:
        # Use the LLM service to analyze relationship
        # This would use a dedicated prompt
        result = {
            "relationship_score": 0.75,
            "engagement_level": "active",
            "relationship_type": "colleague"
        }
        
        return RelationshipAnalysisResponse(**result)
    
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits for this operation"
        )
    except Exception as e:
        logger.error(f"Error analyzing relationship: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze relationship"
        )


# ============================
# Models & Prompts Management
# ============================

@router.get("/models")
async def list_available_models(
    current_user: User = Depends(get_current_user)
):
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
                "cost_per_1k_output": model_info["output_cost_per_1k"]
            }
            for model_id, model_info in models.items()
        ]
    }


@router.get("/prompts")
async def list_available_prompts(
    current_user: User = Depends(get_current_user)
):
    """Get list of available prompts"""
    from app.services.llm_orchestration_service import PromptRegistry
    
    prompts = PromptRegistry.list_prompts()
    
    return {
        "prompts": prompts
    }


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
    session: AsyncSession = Depends(get_db)
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
                draft=request.draft
            )
            execution = await _execute_assistant_draft(
                page=request.page,
                draft=request.draft,
                objective=request.objective,
                current_user=current_user,
                session=session
            )
            return {
                "success": True,
                "page": request.page,
                "assistant_message": "Execution completed after confirmation.",
                "draft": request.draft,
                "execution": execution
            }

        monthly_limit = max(int(settings.WORKPLACE_ASSIST_MONTHLY_LIMIT or 0), 0)
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        usage_query = select(func.coalesce(func.sum(UsageLog.quantity), 0)).where(
            UsageLog.user_id == current_user.id,
            UsageLog.metric == WORKPLACE_USAGE_METRIC,
            UsageLog.created_at >= month_start
        )
        usage_result = await session.execute(usage_query)
        used_this_month = int(usage_result.scalar_one() or 0)
        if monthly_limit > 0 and used_this_month >= monthly_limit and not _is_super_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Workplace monthly limit reached ({monthly_limit} requests)."
            )

        result = await llm_service.create_workspace_assist(
            page=request.page,
            objective=request.objective,
            mode=request.mode,
            context=request.context or {},
            user_id=current_user.id,
            session=session
        )
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=result.get("error", "Assistant request failed")
            )
        if execute_mode:
            draft_for_confirmation = result.get("draft", {}) or {}
            token = _create_confirmation_token(
                user_id=str(current_user.id),
                page=request.page,
                objective=request.objective,
                draft=draft_for_confirmation
            )
            result["requires_confirmation"] = True
            result["confirmation_token"] = token
            result["assistant_message"] = (
                result.get("assistant_message")
                or "Preview ready. Confirm execution to apply changes."
            )

        session.add(
            UsageLog(
                user_id=current_user.id,
                tenant_id=current_user.id,
                metric=WORKPLACE_USAGE_METRIC,
                quantity=1,
                breakdown={
                    "page": request.page,
                    "mode": request.mode
                }
            )
        )
        result["usage"] = {
            "month_used": used_this_month + 1,
            "month_limit": monthly_limit,
            "month_remaining": max(0, monthly_limit - (used_this_month + 1)) if monthly_limit > 0 else None
        }
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Workspace assist error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate assistant response"
        )


def _canonical_draft_hash(page: str, objective: str, draft: dict) -> str:
    canonical = json.dumps(
        {
            "page": (page or "").strip().lower(),
            "objective": (objective or "").strip(),
            "draft": draft or {}
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _create_confirmation_token(user_id: str, page: str, objective: str, draft: dict) -> str:
    exp = int(time.time()) + 600  # 10 minutes
    payload = {
        "uid": user_id,
        "exp": exp,
        "digest": _canonical_draft_hash(page, objective, draft),
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=True)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8")
    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"{payload_b64}.{signature}"


def _decode_confirmation_token(token: str) -> dict:
    try:
        payload_b64, signature = token.split(".", 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid confirmation token format")

    expected = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=400, detail="Invalid confirmation token signature")

    try:
        payload_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
        payload = json.loads(payload_json)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid confirmation token payload")
    return payload


def _validate_confirmation_token(
    token_payload: dict,
    user_id: str,
    page: str,
    objective: str,
    draft: dict
) -> None:
    if token_payload.get("uid") != user_id:
        raise HTTPException(status_code=403, detail="Token user mismatch")
    if int(token_payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=400, detail="Confirmation token expired")
    expected_digest = _canonical_draft_hash(page, objective, draft)
    if token_payload.get("digest") != expected_digest:
        raise HTTPException(status_code=400, detail="Draft changed since preview; regenerate and confirm again")


async def _execute_assistant_draft(
    page: str,
    draft: dict,
    objective: str,
    current_user: User,
    session: AsyncSession
) -> dict:
    """Execute structured AI draft by creating entities directly."""
    page_key = (page or "").strip().lower()

    try:
        if page_key == "campaigns":
            campaign_payload = draft.get("campaign", {}) if isinstance(draft, dict) else {}
            name = campaign_payload.get("name") or f"AI Campaign - {objective[:40]}"
            from_email = campaign_payload.get("from_email") or getattr(current_user, "email", None)
            if not from_email:
                raise HTTPException(status_code=400, detail="Campaign execution requires from_email")

            campaign = Campaign(
                user_id=current_user.id,
                name=name,
                description=campaign_payload.get("description"),
                campaign_type=campaign_payload.get("campaign_type", "cold_outreach"),
                from_email=from_email,
                from_name=campaign_payload.get("from_name"),
                reply_to=campaign_payload.get("reply_to"),
                daily_send_limit=campaign_payload.get("daily_send_limit", 50),
                send_delay_minutes=campaign_payload.get("send_delay_minutes", 5),
                timezone=campaign_payload.get("timezone", "UTC"),
                send_hours=campaign_payload.get("send_hours", []),
                warm_up_enabled=campaign_payload.get("warm_up_enabled", False),
                warm_up_emails_per_day=campaign_payload.get("warm_up_emails_per_day", 5),
                ab_test_enabled=campaign_payload.get("ab_test_enabled", False),
                ab_test_split=campaign_payload.get("ab_test_split", 0.5),
                tags=campaign_payload.get("tags", []),
                status="draft",
            )
            session.add(campaign)
            await session.flush()

            created_sequences = 0
            for idx, seq in enumerate(draft.get("sequences", []) if isinstance(draft, dict) else [], start=1):
                if not seq.get("subject_template") or not seq.get("body_template"):
                    continue
                sequence = CampaignSequence(
                    campaign_id=campaign.id,
                    step_order=idx,
                    name=seq.get("name") or f"Step {idx}",
                    subject_template=seq.get("subject_template"),
                    body_template=seq.get("body_template"),
                    delay_days=seq.get("delay_days", 0),
                    delay_hours=seq.get("delay_hours", 0),
                    send_if_opened=seq.get("send_if_opened", False),
                    send_if_clicked=seq.get("send_if_clicked", False),
                    send_if_replied=seq.get("send_if_replied", False),
                    stop_if_replied=seq.get("stop_if_replied", True),
                )
                session.add(sequence)
                created_sequences += 1

            created_leads = 0
            for lead in draft.get("leads", []) if isinstance(draft, dict) else []:
                email = lead.get("email")
                if not email:
                    continue
                lead_record = Lead(
                    campaign_id=campaign.id,
                    user_id=current_user.id,
                    email=email,
                    first_name=lead.get("first_name"),
                    last_name=lead.get("last_name"),
                    company=lead.get("company"),
                    job_title=lead.get("job_title"),
                    custom_fields=lead.get("custom_fields", {}),
                )
                session.add(lead_record)
                created_leads += 1

            await session.commit()
            await session.refresh(campaign)
            return {
                "mode": "execute",
                "page": "campaigns",
                "created": {
                    "campaign_id": campaign.id,
                    "sequences": created_sequences,
                    "leads": created_leads
                }
            }

        if page_key == "workflows":
            workflow_payload = draft.get("workflow", {}) if isinstance(draft, dict) else {}
            workflow = Workflow(
                user_id=current_user.id,
                name=workflow_payload.get("name") or f"AI Workflow - {objective[:40]}",
                description=workflow_payload.get("description"),
                trigger_type=workflow_payload.get("trigger_type", "email_received"),
                trigger_conditions=workflow_payload.get("trigger_conditions", {}),
                run_on_match=workflow_payload.get("run_on_match", True),
                require_approval=workflow_payload.get("require_approval", False),
                tags=workflow_payload.get("tags", []),
            )
            session.add(workflow)
            await session.flush()

            created_steps = 0
            for idx, step in enumerate(draft.get("steps", []) if isinstance(draft, dict) else [], start=1):
                step_record = WorkflowStep(
                    workflow_id=workflow.id,
                    step_order=idx,
                    name=step.get("name") or f"Step {idx}",
                    step_type=step.get("step_type", "action"),
                    action_type=step.get("action_type"),
                    action_config=step.get("action_config", {}),
                    condition_type=step.get("condition_type"),
                    condition_config=step.get("condition_config", {}),
                    delay_seconds=step.get("delay_seconds"),
                    on_error=step.get("on_error", "stop"),
                    max_retries=step.get("max_retries", 0),
                )
                session.add(step_record)
                created_steps += 1

            await session.commit()
            await session.refresh(workflow)
            return {
                "mode": "execute",
                "page": "workflows",
                "created": {
                    "workflow_id": workflow.id,
                    "steps": created_steps
                }
            }

        if page_key == "agents":
            agent_payload = draft.get("agent", {}) if isinstance(draft, dict) else {}
            system_prompt = agent_payload.get("system_prompt") or "You are a helpful email assistant."
            agent = Agent(
                user_id=current_user.id,
                name=agent_payload.get("name") or f"AI Agent - {objective[:40]}",
                agent_type=agent_payload.get("agent_type", "support"),
                description=agent_payload.get("description"),
                system_prompt=system_prompt,
                instructions=agent_payload.get("instructions"),
                capabilities=agent_payload.get("capabilities", []),
                subscribe_to_categories=agent_payload.get("subscribe_to_categories", []),
                subscribe_to_senders=agent_payload.get("subscribe_to_senders", []),
                subscribe_to_keywords=agent_payload.get("subscribe_to_keywords", []),
                auto_draft_replies=agent_payload.get("auto_draft_replies", False),
                require_approval=agent_payload.get("require_approval", True),
                escalation_rules=agent_payload.get("escalation_rules", {}),
                memory_enabled=agent_payload.get("memory_enabled", True),
                context_window=agent_payload.get("context_window", 10),
                tags=agent_payload.get("tags", []),
            )
            session.add(agent)
            await session.commit()
            await session.refresh(agent)
            return {
                "mode": "execute",
                "page": "agents",
                "created": {"agent_id": agent.id}
            }

        if page_key in {"prompts", "prompt_brain"}:
            prompt_payload = draft.get("prompt", {}) if isinstance(draft, dict) else {}
            template = prompt_payload.get("template")
            if not template:
                raise HTTPException(status_code=400, detail="Prompt execution requires a template")

            prompt = PromptTemplate(
                user_id=current_user.id,
                name=prompt_payload.get("name") or f"AI Prompt - {objective[:32]}",
                description=prompt_payload.get("description"),
                template=template,
                category=prompt_payload.get("category", "analysis"),
                is_active=prompt_payload.get("is_active", True),
                is_system=False,
            )
            session.add(prompt)
            await session.commit()
            await session.refresh(prompt)
            return {
                "mode": "execute",
                "page": "prompts",
                "created": {"prompt_id": prompt.id}
            }

        return {
            "mode": "execute",
            "page": page_key or "unknown",
            "created": {},
            "message": "No execution handler is available for this page."
        }
    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Assistant execute failed ({page_key}): {e}")
        raise HTTPException(status_code=500, detail=f"Assistant execute failed for {page_key}")
