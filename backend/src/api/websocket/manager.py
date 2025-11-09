"""WebSocket connection manager for real-time updates."""

from typing import Dict, Set, List, Optional
from fastapi import WebSocket
import json
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections with workspace isolation and subscriptions."""

    def __init__(self):
        # Active connections: {workspace_id: {connection_id: WebSocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}

        # User mapping: {connection_id: user_info}
        self.connection_users: Dict[str, Dict] = {}

        # Subscription mapping: {connection_id: set(event_types)}
        self.subscriptions: Dict[str, Set[str]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        workspace_id: str,
        user_info: Dict,
    ):
        """Accept new WebSocket connection."""
        await websocket.accept()

        # Initialize workspace group if needed
        if workspace_id not in self.active_connections:
            self.active_connections[workspace_id] = {}

        # Store connection
        self.active_connections[workspace_id][connection_id] = websocket
        self.connection_users[connection_id] = user_info
        self.subscriptions[connection_id] = set()

        # Send connection confirmation
        await self.send_personal_message(
            connection_id,
            {
                "event": "connected",
                "connection_id": connection_id,
                "workspace_id": workspace_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        logger.info(
            f"WebSocket connected: {connection_id} to workspace {workspace_id}"
        )

    def disconnect(self, connection_id: str, workspace_id: str):
        """Remove WebSocket connection."""
        if workspace_id in self.active_connections:
            self.active_connections[workspace_id].pop(connection_id, None)

            # Clean up empty workspace
            if not self.active_connections[workspace_id]:
                del self.active_connections[workspace_id]

        # Clean up user info and subscriptions
        self.connection_users.pop(connection_id, None)
        self.subscriptions.pop(connection_id, None)

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def send_personal_message(self, connection_id: str, message: Dict):
        """Send message to specific connection."""
        for workspace_connections in self.active_connections.values():
            if connection_id in workspace_connections:
                websocket = workspace_connections[connection_id]

                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to {connection_id}: {e}")
                break

    async def broadcast_to_workspace(
        self,
        workspace_id: str,
        message: Dict,
        exclude_connection: Optional[str] = None,
    ):
        """Broadcast message to all connections in workspace."""
        if workspace_id not in self.active_connections:
            return

        disconnected = []

        for conn_id, websocket in self.active_connections[workspace_id].items():
            if conn_id == exclude_connection:
                continue

            try:
                # Check subscription
                event_type = message.get("event")
                if event_type and event_type not in self.subscriptions.get(
                    conn_id, set()
                ):
                    continue

                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {conn_id}: {e}")
                disconnected.append(conn_id)

        # Clean up disconnected clients
        for conn_id in disconnected:
            self.disconnect(conn_id, workspace_id)

    async def subscribe(self, connection_id: str, event_types: List[str]):
        """Subscribe connection to event types."""
        if connection_id in self.subscriptions:
            self.subscriptions[connection_id].update(event_types)

            await self.send_personal_message(
                connection_id,
                {
                    "event": "subscribed",
                    "event_types": list(self.subscriptions[connection_id]),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

    async def unsubscribe(self, connection_id: str, event_types: List[str]):
        """Unsubscribe connection from event types."""
        if connection_id in self.subscriptions:
            for event_type in event_types:
                self.subscriptions[connection_id].discard(event_type)

            await self.send_personal_message(
                connection_id,
                {
                    "event": "unsubscribed",
                    "event_types": event_types,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

    def get_workspace_connections(self, workspace_id: str) -> List[str]:
        """Get all connection IDs for a workspace."""
        return list(self.active_connections.get(workspace_id, {}).keys())

    def get_connection_count(self, workspace_id: Optional[str] = None) -> int:
        """Get count of active connections."""
        if workspace_id:
            return len(self.active_connections.get(workspace_id, {}))

        total = 0
        for connections in self.active_connections.values():
            total += len(connections)
        return total


# Global instance
manager = ConnectionManager()
