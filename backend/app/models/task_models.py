"""
Task manager models generated from emails.
"""

from __future__ import annotations

from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, Index

from app.models.database import Base


class EmailTask(Base):
    __tablename__ = "email_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    email_id = Column(String, ForeignKey("emails.id"), nullable=True, index=True)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="todo", index=True)  # todo, in_progress, done
    priority = Column(String, default="medium", index=True)  # low, medium, high
    lane = Column(String, default="backlog", index=True)  # kanban lane
    due_at = Column(DateTime, nullable=True, index=True)
    slack_notified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_email_tasks_user_status", "user_id", "status"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "email_id": self.email_id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "lane": self.lane,
            "due_at": self.due_at.isoformat() if self.due_at else None,
            "slack_notified": self.slack_notified,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
