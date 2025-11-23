from sqlalchemy import Column, String, Text, JSON, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class EmailProviderConfig(Base):
    __tablename__ = "email_provider_configs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String, nullable=False)  # gmail, outlook
    user_id = Column(String, nullable=False)
    config_data = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    last_sync = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "provider": self.provider,
            "user_id": self.user_id,
            "is_active": self.is_active,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

class SyncHistory(Base):
    __tablename__ = "sync_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_config_id = Column(String, nullable=False)
    sync_type = Column(String, nullable=False)  # full, incremental
    emails_processed = Column(JSON, default=list)
    status = Column(String, default="completed")  # completed, failed, partial
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "provider_config_id": self.provider_config_id,
            "sync_type": self.sync_type,
            "emails_processed": self.emails_processed,
            "status": self.status,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }