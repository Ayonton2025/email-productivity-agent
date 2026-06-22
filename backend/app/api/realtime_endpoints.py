"""
WebSocket Endpoints for Real-Time Email Updates

Handles WebSocket connections and message routing for real-time email notifications.
"""

import json
import logging
from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Query,
    Depends,
    HTTPException,
    status
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.api.websocket_manager import connection_manager
from app.models.database import User, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/email-updates/{token}")
async def websocket_email_updates(
    websocket: WebSocket,
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for real-time email updates.
    
    Clients connect with their JWT token to receive:
    - New email notifications
    - Read status changes
    - Flag status changes
    - Sync started/completed events
    - Sync errors
    
    URL: ws://localhost:8000/ws/email-updates/<jwt_token>
    
    Message Types (Received from Server):
    - email_received: New email arrived
    - email_read: Email read status changed
    - email_flagged: Email flag status changed
    - sync_started: Email sync started
    - sync_completed: Email sync completed
    - sync_error: Email sync encountered error
    - ping: Keep-alive ping
    
    Example Message:
    {
        "type": "email_received",
        "timestamp": "2024-01-15T10:30:00",
        "source": "gmail",
        "email": {
            "id": 123,
            "subject": "Meeting Tomorrow",
            "sender": "boss@company.com",
            "preview": "This is a meeting request...",
            "thread_id": "abc123",
            "has_attachments": true
        }
    }
    """
    try:
        # Verify and decode JWT token
        try:
            from app.core.security import decode_token
            payload = decode_token(token)
            user_id = payload.get("sub") if isinstance(payload, dict) else str(payload)
        except Exception as e:
            logger.warning(f"WebSocket auth failed: {e}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
            return
        
        # Register connection
        await connection_manager.connect(websocket, str(user_id))
        
        # Send welcome message
        await connection_manager.send_personal_message(
            websocket,
            {
                "type": "connection_established",
                "user_id": str(user_id),
                "message": "Connected to real-time email updates"
            }
        )
        
        # Listen for messages (keep connection alive)
        while True:
            try:
                data = await websocket.receive_text()
                
                # Parse incoming message
                try:
                    message = json.loads(data)
                    message_type = message.get("type")
                    
                    if message_type == "ping":
                        # Respond to keep-alive ping
                        await connection_manager.send_personal_message(
                            websocket,
                            {"type": "pong", "timestamp": __import__('datetime').datetime.utcnow().isoformat()}
                        )
                    elif message_type == "subscribe_account":
                        # Client subscribing to updates for specific account
                        account_id = message.get("account_id")
                        logger.debug(f"User {user_id} subscribed to account {account_id}")
                    else:
                        logger.debug(f"Unknown message type: {message_type}")
                
                except json.JSONDecodeError:
                    logger.warning("Received invalid JSON on WebSocket")
                    await connection_manager.send_personal_message(
                        websocket,
                        {"type": "error", "message": "Invalid JSON format"}
                    )
            
            except WebSocketDisconnect:
                connection_manager.disconnect(websocket, str(user_id))
                logger.info(f"Client {user_id} disconnected from WebSocket")
                break
            
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                connection_manager.disconnect(websocket, str(user_id))
                break
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.close(code=status.WS_1011_SERVER_ERROR, reason="Internal error")
        except Exception:
            pass
