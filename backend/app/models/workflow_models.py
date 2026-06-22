"""
Workflow models for no-code automation.

Supports:
- Multi-step flows
- AI-conditional branching
- Integration with EmailService, AutoReplyService, AgentService
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON, Index

from app.models.database import Base


class Workflow(Base):
    """Workflow definition - a set of steps that execute when conditions are met"""
    __tablename__ = "workflows"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Workflow Identity
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_system = Column(Boolean, default=False)  # System workflows cannot be deleted
    
    # Trigger Conditions (when to run)
    trigger_type = Column(String, nullable=False, index=True)  # email_received, email_sent, schedule, manual
    trigger_conditions = Column(JSON, default=dict)  # Match criteria (category, sender, subject, etc.)
    
    # Execution Settings
    run_on_match = Column(Boolean, default=True)  # Run automatically when conditions match
    require_approval = Column(Boolean, default=False)  # Require human approval before execution
    
    # Statistics
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)
    last_run_at = Column(DateTime, nullable=True)
    
    # Metadata
    tags = Column(JSON, default=list)
    extra_data = Column(JSON, default=dict)  # Renamed from metadata to avoid SQLAlchemy conflict
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_workflows_user_active', 'user_id', 'is_active'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "is_system": self.is_system,
            "trigger_type": self.trigger_type,
            "trigger_conditions": self.trigger_conditions or {},
            "run_on_match": self.run_on_match,
            "require_approval": self.require_approval,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "tags": self.tags or [],
            "metadata": self.extra_data or {},  # Keep API field name as 'metadata' for backward compatibility
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class WorkflowStep(Base):
    """Individual step in a workflow"""
    __tablename__ = "workflow_steps"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Step Identity
    step_order = Column(Integer, nullable=False)  # Order of execution
    name = Column(String, nullable=False)
    step_type = Column(String, nullable=False, index=True)  # action, condition, delay, integration
    
    # Step Configuration
    action_type = Column(String, nullable=True)  # send_email, create_draft, tag, archive, notify, call_api, etc.
    action_config = Column(JSON, default=dict)  # Configuration for the action
    
    # Conditional Branching
    condition_type = Column(String, nullable=True)  # ai_condition, field_match, custom
    condition_config = Column(JSON, default=dict)  # Condition evaluation config
    
    # Next Steps (for branching)
    next_step_id_on_true = Column(String, nullable=True)  # Step to execute if condition is true
    next_step_id_on_false = Column(String, nullable=True)  # Step to execute if condition is false
    
    # Delay (for delay steps)
    delay_seconds = Column(Integer, nullable=True)
    
    # Error Handling
    on_error = Column(String, default="stop")  # stop, continue, retry
    max_retries = Column(Integer, default=0)
    
    # Metadata
    extra_data = Column(JSON, default=dict)  # Renamed from metadata to avoid SQLAlchemy conflict
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_workflow_order', 'workflow_id', 'step_order'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "step_order": self.step_order,
            "name": self.name,
            "step_type": self.step_type,
            "action_type": self.action_type,
            "action_config": self.action_config or {},
            "condition_type": self.condition_type,
            "condition_config": self.condition_config or {},
            "next_step_id_on_true": self.next_step_id_on_true,
            "next_step_id_on_false": self.next_step_id_on_false,
            "delay_seconds": self.delay_seconds,
            "on_error": self.on_error,
            "max_retries": self.max_retries,
            "metadata": self.extra_data or {},  # Keep API field name as 'metadata' for backward compatibility
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class WorkflowExecution(Base):
    """Execution log for workflow runs"""
    __tablename__ = "workflow_executions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Trigger Context
    trigger_type = Column(String, nullable=False)  # email_received, email_sent, schedule, manual
    trigger_email_id = Column(String, nullable=True, index=True)  # Email that triggered this execution
    trigger_data = Column(JSON, default=dict)  # Additional trigger context
    
    # Execution Status
    status = Column(String, default="running", index=True)  # running, completed, failed, stopped, waiting_approval
    current_step_id = Column(String, nullable=True)
    
    # Results
    steps_completed = Column(Integer, default=0)
    steps_failed = Column(Integer, default=0)
    execution_log = Column(JSON, default=list)  # Log of step executions
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Error Information
    error_message = Column(Text, nullable=True)
    error_step_id = Column(String, nullable=True)
    
    # Metadata
    extra_data = Column(JSON, default=dict)  # Renamed from metadata to avoid SQLAlchemy conflict
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "user_id": self.user_id,
            "trigger_type": self.trigger_type,
            "trigger_email_id": self.trigger_email_id,
            "trigger_data": self.trigger_data or {},
            "status": self.status,
            "current_step_id": self.current_step_id,
            "steps_completed": self.steps_completed,
            "steps_failed": self.steps_failed,
            "execution_log": self.execution_log or [],
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "error_step_id": self.error_step_id,
            "metadata": self.extra_data or {},  # Keep API field name as 'metadata' for backward compatibility
        }


class Reminder(Base):
    """Reminder entries for workflow or task follow-ups"""
    __tablename__ = "reminders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=True, index=True)

    due_at = Column(DateTime, nullable=False, index=True)
    sent = Column(Boolean, default=False, index=True)
    sent_at = Column(DateTime, nullable=True)

    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_reminder_user_due', 'user_id', 'due_at'),
    )
