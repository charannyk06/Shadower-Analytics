"""WebSocket routes for real-time updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import List
import json
import asyncio

from ...core.database import get_db

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and store WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific client."""
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@router.websocket("/ws/metrics")
async def metrics_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time metrics updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Wait for client messages or send updates
            data = await websocket.receive_text()

            # Process subscription requests
            subscription = json.loads(data)

            # Send real-time updates based on subscription
            await manager.send_personal_message(
                json.dumps({"type": "metric_update", "data": {}}), websocket
            )

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/ws/executions")
async def executions_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time execution updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Send real-time execution updates
            await asyncio.sleep(1)
            await manager.send_personal_message(
                json.dumps({"type": "execution_update", "data": {}}), websocket
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
