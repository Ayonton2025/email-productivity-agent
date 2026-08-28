import logging
from typing import Any, Dict

from fastapi import Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.agent_service import AgentService

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.agent_services: Dict[str, AgentService] = {}

    async def connect(self, websocket: WebSocket, client_id: str, db: AsyncSession):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.agent_services[client_id] = AgentService(db, websocket)
        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.agent_services:
            del self.agent_services[client_id]
        logger.info(f"Client {client_id} disconnected")

    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

    async def handle_websocket_message(self, client_id: str, data: Dict[str, Any]):
        if client_id in self.agent_services:
            await self.agent_services[client_id].handle_message(data)


manager = ConnectionManager()


async def websocket_endpoint(
    websocket: WebSocket, client_id: str = "default", db: AsyncSession = Depends(get_db)
):
    await manager.connect(websocket, client_id, db)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.handle_websocket_message(client_id, data)
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(client_id)
