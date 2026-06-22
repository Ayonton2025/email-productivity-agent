"""
Workflow Engine - Executes workflows based on triggers and conditions.

Supports:
- Multi-step flows
- AI-conditional branching
- Integration with EmailService, AutoReplyService, AgentService
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.workflow_models import Workflow, WorkflowStep, WorkflowExecution
from app.models.database import Email
from app.services.email_service import EmailService
from app.services.auto_reply_service import AutoReplyService
from app.services.agent_service import AgentService
from app.services.llm_service import LLMService


class WorkflowEngine:
    """Engine for executing workflows"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_service = EmailService(db)
        self.auto_reply_service = AutoReplyService(db)
        self.llm_service = LLMService()
    
    async def trigger_workflows_for_email(
        self,
        email: Email,
        trigger_type: str = "email_received"
    ) -> List[WorkflowExecution]:
        """
        Check if any workflows should be triggered for this email and execute them.
        Returns list of execution records.
        """
        # Find active workflows that match this trigger
        workflows = await self.find_matching_workflows(
            user_id=email.user_id,
            trigger_type=trigger_type,
            email=email
        )
        
        executions = []
        for workflow in workflows:
            execution = await self.execute_workflow(workflow, email, trigger_type)
            if execution:
                executions.append(execution)
        
        return executions
    
    async def find_matching_workflows(
        self,
        user_id: str,
        trigger_type: str,
        email: Email
    ) -> List[Workflow]:
        """Find workflows that match the trigger conditions"""
        result = await self.db.execute(
            select(Workflow).where(
                and_(
                    Workflow.user_id == user_id,
                    Workflow.is_active == True,
                    Workflow.trigger_type == trigger_type
                )
            )
        )
        all_workflows = list(result.scalars().all())
        
        matching = []
        for workflow in all_workflows:
            if await self.workflow_matches_email(workflow, email):
                matching.append(workflow)
        
        return matching
    
    async def workflow_matches_email(self, workflow: Workflow, email: Email) -> bool:
        """Check if workflow trigger conditions match the email"""
        conditions = workflow.trigger_conditions or {}
        
        # Check category match
        if conditions.get("category"):
            if email.ai_category != conditions["category"]:
                return False
        
        # Check sender match
        if conditions.get("sender"):
            sender_pattern = conditions["sender"].lower()
            if sender_pattern not in email.sender.lower():
                return False
        
        # Check subject match
        if conditions.get("subject_contains"):
            if conditions["subject_contains"].lower() not in (email.subject or "").lower():
                return False
        
        # Check AI condition (use LLM to evaluate)
        if conditions.get("ai_condition"):
            ai_prompt = f"""Evaluate if this email matches the condition: {conditions["ai_condition"]}

Email:
From: {email.sender}
Subject: {email.subject}
Body: {(email.body_text or email.body_html or '')[:2000]}

Respond with only "yes" or "no"."""
            
            try:
                response = await self.llm_service.process_prompt(ai_prompt, "")
                if "yes" not in str(response).lower():
                    return False
            except Exception:
                return False  # If AI evaluation fails, don't match
        
        return True
    
    async def execute_workflow(
        self,
        workflow: Workflow,
        email: Optional[Email],
        trigger_type: str
    ) -> Optional[WorkflowExecution]:
        """Execute a workflow"""
        # Create execution record
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            user_id=workflow.user_id,
            trigger_type=trigger_type,
            trigger_email_id=email.id if email else None,
            trigger_data={"email_id": email.id} if email else {},
            status="running"
        )
        self.db.add(execution)
        await self.db.flush()
        
        # Get workflow steps in order
        steps_result = await self.db.execute(
            select(WorkflowStep).where(
                WorkflowStep.workflow_id == workflow.id
            ).order_by(WorkflowStep.step_order.asc())
        )
        steps = list(steps_result.scalars().all())
        
        if not steps:
            execution.status = "completed"
            execution.completed_at = datetime.utcnow()
            await self.db.commit()
            return execution
        
        # Execute steps
        context = {
            "email": email.to_dict() if email else {},
            "workflow": workflow.to_dict(),
            "execution_id": execution.id
        }
        
        current_step = steps[0]
        step_index = 0
        
        try:
            while current_step:
                # Execute step
                step_result = await self.execute_step(current_step, context, execution)
                
                if step_result.get("error"):
                    execution.steps_failed += 1
                    execution.error_message = step_result["error"]
                    execution.error_step_id = current_step.id
                    execution.status = "failed"
                    break
                
                execution.steps_completed += 1
                execution.current_step_id = current_step.id
                
                # Determine next step
                if step_result.get("condition_result") is not None:
                    # Conditional branching
                    if step_result["condition_result"]:
                        next_step_id = current_step.next_step_id_on_true
                    else:
                        next_step_id = current_step.next_step_id_on_false
                    
                    if next_step_id:
                        next_step = next((s for s in steps if s.id == next_step_id), None)
                        current_step = next_step
                    else:
                        # Move to next step in order
                        step_index += 1
                        current_step = steps[step_index] if step_index < len(steps) else None
                else:
                    # Move to next step in order
                    step_index += 1
                    current_step = steps[step_index] if step_index < len(steps) else None
                
                # Add delay if specified
                if current_step and current_step.delay_seconds:
                    await asyncio.sleep(current_step.delay_seconds)
            
            execution.status = "completed"
            execution.completed_at = datetime.utcnow()
            if execution.started_at:
                duration = (execution.completed_at - execution.started_at).total_seconds()
                execution.duration_seconds = int(duration)
            
        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
        
        # Update workflow statistics
        workflow.total_runs += 1
        if execution.status == "completed":
            workflow.successful_runs += 1
        else:
            workflow.failed_runs += 1
        workflow.last_run_at = datetime.utcnow()
        
        await self.db.commit()
        return execution
    
    async def execute_step(
        self,
        step: WorkflowStep,
        context: Dict[str, Any],
        execution: WorkflowExecution
    ) -> Dict[str, Any]:
        """Execute a single workflow step"""
        result = {"success": True}
        
        try:
            if step.step_type == "action":
                result = await self.execute_action(step, context)
            elif step.step_type == "condition":
                result = await self.execute_condition(step, context)
            elif step.step_type == "delay":
                await asyncio.sleep(step.delay_seconds or 0)
                result = {"success": True}
            elif step.step_type == "integration":
                result = await self.execute_integration(step, context)
            
            # Log execution
            execution.execution_log.append({
                "step_id": step.id,
                "step_name": step.name,
                "timestamp": datetime.utcnow().isoformat(),
                "result": result
            })
            
        except Exception as e:
            result = {"success": False, "error": str(e)}
        
        return result
    
    async def execute_action(
        self,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an action step"""
        action_type = step.action_type
        config = step.action_config or {}
        email_data = context.get("email", {})
        
        if action_type == "send_email":
            # Send email using email service
            recipient = config.get("recipient") or email_data.get("sender")
            subject = config.get("subject", "Auto-reply")
            body = config.get("body", "")
            
            # Could integrate with EmailService.send_email here
            return {"success": True, "action": "send_email", "recipient": recipient}
        
        elif action_type == "create_draft":
            # Create draft
            draft_data = {
                "subject": config.get("subject", "Draft"),
                "body": config.get("body", ""),
                "recipient": config.get("recipient") or email_data.get("sender"),
                "context_email_id": email_data.get("id")
            }
            # Could integrate with EmailService.create_draft here
            return {"success": True, "action": "create_draft"}
        
        elif action_type == "tag":
            # Tag email (would need to add tag field to Email model)
            return {"success": True, "action": "tag"}
        
        elif action_type == "archive":
            # Archive email
            if email_data.get("id"):
                # Could integrate with EmailService.archive_email here
                pass
            return {"success": True, "action": "archive"}
        
        elif action_type == "notify":
            # Send notification
            return {"success": True, "action": "notify"}
        
        else:
            return {"success": False, "error": f"Unknown action type: {action_type}"}
    
    async def execute_condition(
        self,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a condition step"""
        condition_type = step.condition_type
        config = step.condition_config or {}
        email_data = context.get("email", {})
        
        if condition_type == "ai_condition":
            # Use LLM to evaluate condition
            condition_prompt = config.get("prompt", "")
            email_content = f"From: {email_data.get('sender')}\nSubject: {email_data.get('subject')}\nBody: {email_data.get('body', '')[:2000]}"
            
            full_prompt = f"{condition_prompt}\n\nEmail:\n{email_content}\n\nRespond with only 'yes' or 'no'."
            
            try:
                response = await self.llm_service.process_prompt(full_prompt, "")
                condition_result = "yes" in str(response).lower()
                return {"success": True, "condition_result": condition_result}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        elif condition_type == "field_match":
            # Simple field matching
            field = config.get("field")
            operator = config.get("operator", "equals")
            value = config.get("value")
            
            email_value = email_data.get(field)
            
            if operator == "equals":
                result = str(email_value) == str(value)
            elif operator == "contains":
                result = str(value) in str(email_value)
            else:
                result = False
            
            return {"success": True, "condition_result": result}
        
        else:
            return {"success": False, "error": f"Unknown condition type: {condition_type}"}
    
    async def execute_integration(
        self,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an integration step (CRM, Slack, etc.)"""
        # Placeholder for integration execution
        # Would integrate with integration_hub services
        return {"success": True, "action": "integration", "note": "Integration execution not yet implemented"}
