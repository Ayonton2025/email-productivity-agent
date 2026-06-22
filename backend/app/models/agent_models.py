"""
Agent Runtime Models for long-lived autonomous agents.

Agents:
- Sales agent
- Support agent
- Recruitment agent
- Executive assistant
- Legal filter agent
- Student assistant
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON, Index

from app.models.database import Base


class Agent(Base):
    """Long-lived autonomous agent definition"""
    __tablename__ = "agents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Agent Identity
    name = Column(String, nullable=False)
    agent_type = Column(String, nullable=False, index=True)  # sales, support, recruitment, executive_assistant, legal_filter, student
    description = Column(Text, nullable=True)
    
    # Agent Configuration
    system_prompt = Column(Text, nullable=False)  # Base system prompt for the agent
    instructions = Column(Text, nullable=True)  # Additional instructions
    capabilities = Column(JSON, default=list)  # List of capabilities (draft_replies, escalate, tag, etc.)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_running = Column(Boolean, default=False)  # Currently running/processing
    
    # Subscription Settings (what emails to process)
    subscribe_to_categories = Column(JSON, default=list)  # Email categories to process
    subscribe_to_senders = Column(JSON, default=list)  # Specific senders to monitor
    subscribe_to_keywords = Column(JSON, default=list)  # Keywords in subject/body
    
    # Behavior Settings
    auto_draft_replies = Column(Boolean, default=False)  # Automatically draft replies
    require_approval = Column(Boolean, default=True)  # Require human approval before sending
    strategy_prompt = Column(Text, nullable=True)  # Negotiation or domain strategy prompt
    approval_threshold = Column(Integer, default=75)  # Confidence threshold (0-100) for auto-send
    escalation_rules = Column(JSON, default=dict)  # When to escalate to human
    
    # Memory & Context
    memory_enabled = Column(Boolean, default=True)
    context_window = Column(Integer, default=10)  # Number of previous emails to consider
    
    # Statistics
    emails_processed = Column(Integer, default=0)
    replies_drafted = Column(Integer, default=0)
    escalations = Column(Integer, default=0)
    last_activity_at = Column(DateTime, nullable=True)
    
    # Metadata
    tags = Column(JSON, default=list)
    extra_data = Column(JSON, default=dict)  # Renamed from metadata to avoid SQLAlchemy conflict
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_user_type', 'user_id', 'agent_type'),
        Index('idx_user_active', 'user_id', 'is_active'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "agent_type": self.agent_type,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "instructions": self.instructions,
            "capabilities": self.capabilities or [],
            "is_active": self.is_active,
            "is_running": self.is_running,
            "subscribe_to_categories": self.subscribe_to_categories or [],
            "subscribe_to_senders": self.subscribe_to_senders or [],
            "subscribe_to_keywords": self.subscribe_to_keywords or [],
            "auto_draft_replies": self.auto_draft_replies,
            "require_approval": self.require_approval,
            "strategy_prompt": self.strategy_prompt,
            "approval_threshold": self.approval_threshold,
            "escalation_rules": self.escalation_rules or {},
            "memory_enabled": self.memory_enabled,
            "context_window": self.context_window,
            "emails_processed": self.emails_processed,
            "replies_drafted": self.replies_drafted,
            "escalations": self.escalations,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "tags": self.tags or [],
            "metadata": self.extra_data or {},  # Keep API field name as 'metadata' for backward compatibility
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class AgentMemory(Base):
    """Agent memory/context for maintaining conversation history"""
    __tablename__ = "agent_memory"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Memory Content
    memory_type = Column(String, nullable=False, index=True)  # conversation, fact, preference, rule
    content = Column(Text, nullable=False)
    
    # Context
    related_email_id = Column(String, nullable=True, index=True)
    related_contact_id = Column(String, nullable=True, index=True)
    
    # Importance & Retention
    importance_score = Column(Integer, default=50)  # 0-100, higher = more important
    expires_at = Column(DateTime, nullable=True)  # When to forget this memory
    
    # Metadata
    extra_data = Column(JSON, default=dict)  # Renamed from metadata to avoid SQLAlchemy conflict
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_agent_type', 'agent_id', 'memory_type'),
        Index('idx_agent_importance', 'agent_id', 'importance_score'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "memory_type": self.memory_type,
            "content": self.content,
            "related_email_id": self.related_email_id,
            "related_contact_id": self.related_contact_id,
            "importance_score": self.importance_score,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.extra_data or {},  # Keep API field name as 'metadata' for backward compatibility
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class AgentActivity(Base):
    """Log of agent activities and actions"""
    __tablename__ = "agent_activities"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Activity Details
    activity_type = Column(String, nullable=False, index=True)  # email_processed, reply_drafted, escalated, tagged, etc.
    email_id = Column(String, nullable=True, index=True)
    
    # Action Details
    action_taken = Column(String, nullable=True)  # What the agent did
    action_result = Column(Text, nullable=True)  # Result of the action
    
    # Decision Context
    decision_reasoning = Column(Text, nullable=True)  # Why the agent made this decision
    
    # Status
    status = Column(String, default="completed")  # completed, pending_approval, failed
    
    # Metadata
    extra_data = Column(JSON, default=dict)  # Renamed from metadata to avoid SQLAlchemy conflict
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_agent_date', 'agent_id', 'created_at'),
        Index('idx_user_date', 'user_id', 'created_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "activity_type": self.activity_type,
            "email_id": self.email_id,
            "action_taken": self.action_taken,
            "action_result": self.action_result,
            "decision_reasoning": self.decision_reasoning,
            "status": self.status,
            "metadata": self.extra_data or {},  # Keep API field name as 'metadata' for backward compatibility
            "created_at": self.created_at.isoformat(),
        }
