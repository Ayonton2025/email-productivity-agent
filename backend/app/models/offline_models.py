"""
Offline sync queue models.
"""

from __future__ import annotations

from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Index

from app.models.database import Base


class OfflineSyncQueueItem(Base):
    __tablename__ = "offline_sync_queue_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String, nullable=False, index=True)
    payload = Column(JSON, default=dict)
    status = Column(String, default="queued", index=True)  # queued, synced, failed
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    synced_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_offline_user_status", "user_id", "status"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "payload": self.payload or {},
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
        }
