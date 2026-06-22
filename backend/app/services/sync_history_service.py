"""
Email Sync History Service

Tracks email synchronization operations for audit trail and analytics.
Records sync start, completion, and error events.
"""

import logging
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import SyncHistory, EmailProviderConfig
import uuid

logger = logging.getLogger(__name__)


class SyncHistoryService:
    """Service for tracking email sync operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def start_sync(
        self,
        user_id: str,
        provider_config_id: str,
        sync_type: str = "incremental"
    ) -> SyncHistory:
        """
        Record the start of an email sync operation.
        
        Args:
            user_id: User ID
            provider_config_id: Email provider config ID
            sync_type: Type of sync (incremental or full)
        
        Returns:
            SyncHistory record
        """
        try:
            sync_record = SyncHistory(
                id=str(uuid.uuid4()),
                user_id=user_id,
                provider_config_id=provider_config_id,
                sync_type=sync_type,
                status="in_progress",
                started_at=datetime.utcnow()
            )
            
            self.db.add(sync_record)
            await self.db.commit()
            await self.db.refresh(sync_record)
            
            logger.info(f"✅ Sync started: {sync_record.id} ({sync_type})")
            return sync_record
        
        except Exception as e:
            logger.error(f"❌ Failed to create sync record: {e}")
            raise
    
    async def complete_sync(
        self,
        sync_id: str,
        emails_processed: List[str],
        sync_status: str = "completed"
    ) -> Optional[SyncHistory]:
        """
        Mark a sync operation as completed.
        
        Args:
            sync_id: Sync history ID
            emails_processed: List of email IDs that were synced
            sync_status: Status (completed, partial, failed)
        
        Returns:
            Updated SyncHistory record
        """
        try:
            # Fetch the sync record
            result = await self.db.execute(
                select(SyncHistory).where(SyncHistory.id == sync_id)
            )
            sync_record = result.scalars().first()
            
            if not sync_record:
                logger.warning(f"⚠️ Sync record not found: {sync_id}")
                return None
            
            # Update sync record
            sync_record.status = sync_status
            sync_record.emails_processed = emails_processed
            sync_record.completed_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(sync_record)
            
            duration = (sync_record.completed_at - sync_record.started_at).total_seconds()
            logger.info(f"✅ Sync completed: {sync_id} ({len(emails_processed)} emails in {duration:.1f}s)")
            
            return sync_record
        
        except Exception as e:
            logger.error(f"❌ Failed to complete sync: {e}")
            raise
    
    async def record_sync_error(
        self,
        sync_id: str,
        error_message: str
    ) -> Optional[SyncHistory]:
        """
        Record a sync error.
        
        Args:
            sync_id: Sync history ID
            error_message: Error description
        
        Returns:
            Updated SyncHistory record
        """
        try:
            # Fetch the sync record
            result = await self.db.execute(
                select(SyncHistory).where(SyncHistory.id == sync_id)
            )
            sync_record = result.scalars().first()
            
            if not sync_record:
                logger.warning(f"⚠️ Sync record not found: {sync_id}")
                return None
            
            # Update sync record with error
            sync_record.status = "failed"
            sync_record.error_message = error_message
            sync_record.completed_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(sync_record)
            
            logger.error(f"❌ Sync failed: {sync_id}")
            logger.error(f"   Error: {error_message}")
            
            return sync_record
        
        except Exception as e:
            logger.error(f"❌ Failed to record sync error: {e}")
            raise
    
    async def get_sync_history(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[SyncHistory]:
        """
        Get recent sync history for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of records to return
        
        Returns:
            List of SyncHistory records sorted by most recent first
        """
        try:
            result = await self.db.execute(
                select(SyncHistory)
                .where(SyncHistory.user_id == user_id)
                .order_by(SyncHistory.started_at.desc())
                .limit(limit)
            )
            
            return result.scalars().all()
        
        except Exception as e:
            logger.error(f"❌ Failed to get sync history: {e}")
            return []
    
    async def get_provider_sync_history(
        self,
        provider_config_id: str,
        limit: int = 50
    ) -> List[SyncHistory]:
        """
        Get sync history for a specific email provider config.
        
        Args:
            provider_config_id: Email provider config ID
            limit: Maximum number of records to return
        
        Returns:
            List of SyncHistory records
        """
        try:
            result = await self.db.execute(
                select(SyncHistory)
                .where(SyncHistory.provider_config_id == provider_config_id)
                .order_by(SyncHistory.started_at.desc())
                .limit(limit)
            )
            
            return result.scalars().all()
        
        except Exception as e:
            logger.error(f"❌ Failed to get provider sync history: {e}")
            return []
    
    async def get_sync_stats(self, user_id: str) -> dict:
        """
        Get sync statistics for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Dictionary with sync statistics
        """
        try:
            result = await self.db.execute(
                select(SyncHistory)
                .where(SyncHistory.user_id == user_id)
                .order_by(SyncHistory.started_at.desc())
                .limit(100)  # Check last 100 syncs for stats
            )
            
            syncs = result.scalars().all()
            
            total_syncs = len(syncs)
            completed_syncs = sum(1 for s in syncs if s.status == "completed")
            failed_syncs = sum(1 for s in syncs if s.status == "failed")
            total_emails = sum(len(s.emails_processed or []) for s in syncs)
            
            # Calculate average emails per sync
            avg_emails_per_sync = total_emails / max(completed_syncs, 1)
            
            # Get last sync time
            last_sync = syncs[0] if syncs else None
            last_sync_time = last_sync.started_at.isoformat() if last_sync else None
            last_sync_status = last_sync.status if last_sync else None
            
            return {
                "total_syncs": total_syncs,
                "completed_syncs": completed_syncs,
                "failed_syncs": failed_syncs,
                "success_rate": (completed_syncs / max(total_syncs, 1)) * 100,
                "total_emails_synced": total_emails,
                "avg_emails_per_sync": round(avg_emails_per_sync, 2),
                "last_sync_time": last_sync_time,
                "last_sync_status": last_sync_status,
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to get sync stats: {e}")
            return {}
