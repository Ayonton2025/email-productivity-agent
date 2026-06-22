"""
WebSocket Manager for Real-Time Email Updates

Handles WebSocket connections, broadcasting email updates to connected clients,
and managing subscription to specific user channels.
"""

import json
import logging
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect, Query
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections grouped by user ID.
    
    Each user can have multiple connections (different tabs/devices).
    Broadcasts email updates to all connected clients for that user.
    """
    
    def __init__(self):
        # user_id -> Set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Track connection metadata (user_id, connected_at)
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """
        Register a new WebSocket connection.
        
        Args:
            websocket: FastAPI WebSocket connection
            user_id: User ID associated with this connection
        """
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow().isoformat(),
        }
        
        logger.info(f"✅ WebSocket connected: {user_id} ({len(self.active_connections[user_id])} connections)")
    
    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """
        Unregister a WebSocket connection.
        
        Args:
            websocket: FastAPI WebSocket connection
            user_id: User ID associated with this connection
        """
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            
            # Clean up empty user sets
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        self.connection_metadata.pop(websocket, None)
        
        logger.info(f"✅ WebSocket disconnected: {user_id}")
    
    async def broadcast_email_received(
        self,
        user_id: str,
        email_id: int,
        email_data: Dict[str, Any],
        source: str = "gmail"
    ) -> None:
        """
        Broadcast a new email received event to all connections for a user.
        
        Args:
            user_id: User ID to broadcast to
            email_id: Email ID in database
            email_data: Email data to send (subject, sender, etc.)
            source: Email source (gmail, outlook, yahoo)
        """
        if user_id not in self.active_connections:
            logger.debug(f"No active connections for user {user_id}")
            return
        
        message = {
            "type": "email_received",
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
            "email": {
                "id": email_id,
                "subject": email_data.get("subject", "(No Subject)"),
                "sender": email_data.get("sender", "Unknown"),
                "preview": email_data.get("body_text", "")[:100],
                "thread_id": email_data.get("thread_id"),
                "has_attachments": bool(email_data.get("attachments")),
            }
        }
        
        await self.broadcast_to_user(user_id, message)
    
    async def broadcast_email_read(
        self,
        user_id: str,
        email_id: int,
        is_read: bool
    ) -> None:
        """
        Broadcast an email read status change.
        
        Args:
            user_id: User ID to broadcast to
            email_id: Email ID
            is_read: New read status
        """
        message = {
            "type": "email_read",
            "timestamp": datetime.utcnow().isoformat(),
            "email_id": email_id,
            "is_read": is_read,
        }
        
        await self.broadcast_to_user(user_id, message)
    
    async def broadcast_email_flagged(
        self,
        user_id: str,
        email_id: int,
        is_flagged: bool
    ) -> None:
        """
        Broadcast an email flag status change.
        
        Args:
            user_id: User ID to broadcast to
            email_id: Email ID
            is_flagged: New flag status
        """
        message = {
            "type": "email_flagged",
            "timestamp": datetime.utcnow().isoformat(),
            "email_id": email_id,
            "is_flagged": is_flagged,
        }
        
        await self.broadcast_to_user(user_id, message)
    
    async def broadcast_sync_started(
        self,
        user_id: str,
        account_email: str,
        provider: str = "gmail"
    ) -> None:
        """
        Broadcast email sync started event.
        
        Args:
            user_id: User ID
            account_email: Email account being synced
            provider: Email provider (gmail, outlook, yahoo)
        """
        message = {
            "type": "sync_started",
            "timestamp": datetime.utcnow().isoformat(),
            "account_email": account_email,
            "provider": provider,
        }
        
        await self.broadcast_to_user(user_id, message)
    
    async def broadcast_sync_completed(
        self,
        user_id: str,
        account_email: str,
        emails_fetched: int,
        provider: str = "gmail"
    ) -> None:
        """
        Broadcast email sync completed event.
        
        Args:
            user_id: User ID
            account_email: Email account being synced
            emails_fetched: Number of emails fetched
            provider: Email provider (gmail, outlook, yahoo)
        """
        message = {
            "type": "sync_completed",
            "timestamp": datetime.utcnow().isoformat(),
            "account_email": account_email,
            "provider": provider,
            "emails_fetched": emails_fetched,
        }
        
        await self.broadcast_to_user(user_id, message)
    
    async def broadcast_sync_error(
        self,
        user_id: str,
        account_email: str,
        error_message: str,
        provider: str = "gmail"
    ) -> None:
        """
        Broadcast sync error event.
        
        Args:
            user_id: User ID
            account_email: Email account
            error_message: Error description
            provider: Email provider
        """
        message = {
            "type": "sync_error",
            "timestamp": datetime.utcnow().isoformat(),
            "account_email": account_email,
            "provider": provider,
            "error": error_message,
        }
        
        await self.broadcast_to_user(user_id, message)
    
    async def send_personal_message(
        self,
        websocket: WebSocket,
        message: Dict[str, Any]
    ) -> None:
        """
        Send a message to a specific connection.
        
        Args:
            websocket: WebSocket connection
            message: Message dict to send
        """
        try:
            await websocket.send_json(message)
        except RuntimeError as e:
            logger.error(f"Failed to send message: {e}")
    
    async def broadcast_to_user(
        self,
        user_id: str,
        message: Dict[str, Any]
    ) -> None:
        """
        Broadcast a message to all connections for a user.
        
        Args:
            user_id: User ID to broadcast to
            message: Message dict to broadcast
        """
        if user_id not in self.active_connections:
            return
        
        # Send to all connections for this user
        disconnected = []
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_json(message)
            except RuntimeError as e:
                logger.warning(f"Error sending message to connection: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected sockets
        for conn in disconnected:
            self.active_connections[user_id].discard(conn)
            self.connection_metadata.pop(conn, None)


# Global connection manager instance
connection_manager = ConnectionManager()
