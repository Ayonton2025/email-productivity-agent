"""
API endpoints for workflow management:
- CRUD operations for workflows
- Workflow step management
- Workflow execution
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.models.database import get_db
from app.models.user_models import User
from app.core.security import get_current_user
from app.models.workflow_models import Workflow, WorkflowStep, WorkflowExecution
from app.services.workflow_engine import WorkflowEngine
from app.services.billing_service import FeatureGatingService
from sqlalchemy import select, and_

router = APIRouter(prefix="/workflows", tags=["workflows"])
gating_service = FeatureGatingService()


# Pydantic models for request/response
class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: str
    trigger_conditions: Dict[str, Any] = {}
    run_on_match: bool = True
    require_approval: bool = False
    tags: List[str] = []


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    trigger_conditions: Optional[Dict[str, Any]] = None
    run_on_match: Optional[bool] = None
    require_approval: Optional[bool] = None
    tags: Optional[List[str]] = None


class WorkflowStepCreate(BaseModel):
    workflow_id: str
    step_order: int
    name: str
    step_type: str  # action, condition, delay, integration, negotiate
    action_type: Optional[str] = None
    action_config: Dict[str, Any] = {}
    condition_type: Optional[str] = None
    condition_config: Dict[str, Any] = {}
    next_step_id_on_true: Optional[str] = None
    next_step_id_on_false: Optional[str] = None
    delay_seconds: Optional[int] = None
    on_error: str = "stop"
    max_retries: int = 0


class WorkflowStepUpdate(BaseModel):
    step_order: Optional[int] = None
    name: Optional[str] = None
    action_config: Optional[Dict[str, Any]] = None
    condition_config: Optional[Dict[str, Any]] = None
    next_step_id_on_true: Optional[str] = None
    next_step_id_on_false: Optional[str] = None
    delay_seconds: Optional[int] = None


@router.get("/", response_model=List[Dict[str, Any]])
async def get_workflows(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all workflows for the user"""
    try:
        result = await db.execute(
            select(Workflow).where(Workflow.user_id == current_user.id).order_by(Workflow.created_at.desc())
        )
        workflows = list(result.scalars().all())
        return [w.to_dict() for w in workflows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workflows: {str(e)}")


@router.get("/{workflow_id}", response_model=Dict[str, Any])
async def get_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific workflow with its steps"""
    try:
        result = await db.execute(
            select(Workflow).where(
                and_(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
            )
        )
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Get steps
        steps_result = await db.execute(
            select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id).order_by(WorkflowStep.step_order.asc())
        )
        steps = list(steps_result.scalars().all())
        
        workflow_dict = workflow.to_dict()
        workflow_dict["steps"] = [s.to_dict() for s in steps]
        return workflow_dict
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workflow: {str(e)}")


@router.post("/", response_model=Dict[str, Any])
async def create_workflow(
    workflow_data: WorkflowCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new workflow"""
    try:
        # Check: Does user have access to workflow automation?
        can_access = await gating_service.can_access_feature(
            user_id=current_user.id,
            feature="workflow_automation",
            session=db
        )
        if not can_access:
            raise HTTPException(
                status_code=403,
                detail="Workflow automation is not available on your plan. Upgrade to Plus or Pro."
            )
        
        workflow = Workflow(
            user_id=current_user.id,
            name=workflow_data.name,
            description=workflow_data.description,
            trigger_type=workflow_data.trigger_type,
            trigger_conditions=workflow_data.trigger_conditions,
            run_on_match=workflow_data.run_on_match,
            require_approval=workflow_data.require_approval,
            tags=workflow_data.tags
        )
        db.add(workflow)
        await db.commit()
        await db.refresh(workflow)
        return workflow.to_dict()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create workflow: {str(e)}")


@router.put("/{workflow_id}", response_model=Dict[str, Any])
async def update_workflow(
    workflow_id: str,
    workflow_data: WorkflowUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a workflow"""
    try:
        result = await db.execute(
            select(Workflow).where(
                and_(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
            )
        )
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        if workflow_data.name is not None:
            workflow.name = workflow_data.name
        if workflow_data.description is not None:
            workflow.description = workflow_data.description
        if workflow_data.is_active is not None:
            workflow.is_active = workflow_data.is_active
        if workflow_data.trigger_conditions is not None:
            workflow.trigger_conditions = workflow_data.trigger_conditions
        if workflow_data.run_on_match is not None:
            workflow.run_on_match = workflow_data.run_on_match
        if workflow_data.require_approval is not None:
            workflow.require_approval = workflow_data.require_approval
        if workflow_data.tags is not None:
            workflow.tags = workflow_data.tags
        
        await db.commit()
        await db.refresh(workflow)
        return workflow.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update workflow: {str(e)}")


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a workflow"""
    try:
        result = await db.execute(
            select(Workflow).where(
                and_(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
            )
        )
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        if workflow.is_system:
            raise HTTPException(status_code=400, detail="Cannot delete system workflow")
        
        await db.delete(workflow)
        await db.commit()
        return {"message": "Workflow deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete workflow: {str(e)}")


@router.post("/{workflow_id}/steps", response_model=Dict[str, Any])
async def create_workflow_step(
    workflow_id: str,
    step_data: WorkflowStepCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a workflow step"""
    try:
        # Verify workflow belongs to user
        result = await db.execute(
            select(Workflow).where(
                and_(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
            )
        )
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        step = WorkflowStep(
            workflow_id=workflow_id,
            step_order=step_data.step_order,
            name=step_data.name,
            step_type=step_data.step_type,
            action_type=step_data.action_type,
            action_config=step_data.action_config,
            condition_type=step_data.condition_type,
            condition_config=step_data.condition_config,
            next_step_id_on_true=step_data.next_step_id_on_true,
            next_step_id_on_false=step_data.next_step_id_on_false,
            delay_seconds=step_data.delay_seconds,
            on_error=step_data.on_error,
            max_retries=step_data.max_retries
        )
        db.add(step)
        await db.commit()
        await db.refresh(step)
        return step.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create workflow step: {str(e)}")


@router.put("/steps/{step_id}", response_model=Dict[str, Any])
async def update_workflow_step(
    step_id: str,
    step_data: WorkflowStepUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a workflow step"""
    try:
        result = await db.execute(
            select(WorkflowStep).join(Workflow).where(
                and_(WorkflowStep.id == step_id, Workflow.user_id == current_user.id)
            )
        )
        step = result.scalar_one_or_none()
        if not step:
            raise HTTPException(status_code=404, detail="Workflow step not found")
        
        if step_data.step_order is not None:
            step.step_order = step_data.step_order
        if step_data.name is not None:
            step.name = step_data.name
        if step_data.action_config is not None:
            step.action_config = step_data.action_config
        if step_data.condition_config is not None:
            step.condition_config = step_data.condition_config
        if step_data.next_step_id_on_true is not None:
            step.next_step_id_on_true = step_data.next_step_id_on_true
        if step_data.next_step_id_on_false is not None:
            step.next_step_id_on_false = step_data.next_step_id_on_false
        if step_data.delay_seconds is not None:
            step.delay_seconds = step_data.delay_seconds
        
        await db.commit()
        await db.refresh(step)
        return step.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update workflow step: {str(e)}")


@router.delete("/steps/{step_id}")
async def delete_workflow_step(
    step_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a workflow step"""
    try:
        result = await db.execute(
            select(WorkflowStep).join(Workflow).where(
                and_(WorkflowStep.id == step_id, Workflow.user_id == current_user.id)
            )
        )
        step = result.scalar_one_or_none()
        if not step:
            raise HTTPException(status_code=404, detail="Workflow step not found")
        
        await db.delete(step)
        await db.commit()
        return {"message": "Workflow step deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete workflow step: {str(e)}")


@router.get("/{workflow_id}/executions", response_model=List[Dict[str, Any]])
async def get_workflow_executions(
    workflow_id: str,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get execution history for a workflow"""
    try:
        # Verify workflow belongs to user
        result = await db.execute(
            select(Workflow).where(
                and_(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
            )
        )
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        executions_result = await db.execute(
            select(WorkflowExecution).where(
                WorkflowExecution.workflow_id == workflow_id
            ).order_by(WorkflowExecution.started_at.desc()).limit(limit)
        )
        executions = list(executions_result.scalars().all())
        return [e.to_dict() for e in executions]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workflow executions: {str(e)}")


@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    email_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger a workflow execution"""
    try:
        result = await db.execute(
            select(Workflow).where(
                and_(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
            )
        )
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        email = None
        if email_id:
            from app.models.database import Email
            email_result = await db.execute(
                select(Email).where(
                    and_(Email.id == email_id, Email.user_id == current_user.id)
                )
            )
            email = email_result.scalar_one_or_none()
        
        workflow_engine = WorkflowEngine(db)
        execution = await workflow_engine.execute_workflow(workflow, email, "manual")
        
        return execution.to_dict() if execution else {"message": "Workflow execution started"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute workflow: {str(e)}")
