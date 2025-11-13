"""WebSocket connection manager for real-time updates."""

from typing import Dict, Set, List, Optional, Any
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

        # Active streams: {connection_id: {stream_type: task}}
        self.active_streams: Dict[str, Dict[str, asyncio.Task]] = {}

        # Heartbeat tasks: {connection_id: task}
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}

        # Room subscriptions: {room_key: set(connection_ids)}
        self.room_subscriptions: Dict[str, Set[str]] = {}

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
        self.active_streams[connection_id] = {}

        # Start heartbeat
        self.heartbeat_tasks[connection_id] = asyncio.create_task(
            self._heartbeat(connection_id, websocket)
        )

        # Send connection confirmation
        await self.send_personal_message(
            connection_id,
            {
                "type": "connection_established",
                "connection_id": connection_id,
                "workspace_id": workspace_id,
                "user_id": user_info.get("user_id"),
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

        # Stop all active streams
        if connection_id in self.active_streams:
            for stream_task in self.active_streams[connection_id].values():
                if not stream_task.done():
                    stream_task.cancel()
            del self.active_streams[connection_id]

        # Stop heartbeat
        if connection_id in self.heartbeat_tasks:
            if not self.heartbeat_tasks[connection_id].done():
                self.heartbeat_tasks[connection_id].cancel()
            del self.heartbeat_tasks[connection_id]

        # Remove from rooms
        for room_key, connections in list(self.room_subscriptions.items()):
            connections.discard(connection_id)
            if not connections:
                del self.room_subscriptions[room_key]

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

    async def join_room(
        self, connection_id: str, room_name: str, workspace_id: str
    ):
        """Add connection to a specific room."""
        room_key = f"{workspace_id}:{room_name}"
        if room_key not in self.room_subscriptions:
            self.room_subscriptions[room_key] = set()
        self.room_subscriptions[room_key].add(connection_id)

        await self.send_personal_message(
            connection_id,
            {
                "type": "room_joined",
                "room": room_name,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        logger.debug(f"Connection {connection_id} joined room {room_key}")

    async def leave_room(
        self, connection_id: str, room_name: str, workspace_id: str
    ):
        """Remove connection from a room."""
        room_key = f"{workspace_id}:{room_name}"
        if room_key in self.room_subscriptions:
            self.room_subscriptions[room_key].discard(connection_id)
            if not self.room_subscriptions[room_key]:
                del self.room_subscriptions[room_key]

        await self.send_personal_message(
            connection_id,
            {
                "type": "room_left",
                "room": room_name,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        logger.debug(f"Connection {connection_id} left room {room_key}")

    async def broadcast_to_room(
        self, room_key: str, message: Dict, exclude_connection: Optional[str] = None
    ):
        """Broadcast message to all connections in a room."""
        if room_key not in self.room_subscriptions:
            return

        disconnected = []

        for conn_id in self.room_subscriptions[room_key]:
            if conn_id == exclude_connection:
                continue

            try:
                await self.send_personal_message(conn_id, message)
            except Exception as e:
                logger.error(f"Error broadcasting to {conn_id} in room {room_key}: {e}")
                disconnected.append(conn_id)

        # Clean up disconnected clients
        for conn_id in disconnected:
            self.room_subscriptions[room_key].discard(conn_id)

    async def send_to_user(self, user_id: str, message: Dict):
        """Send message to specific user by user_id."""
        for conn_id, user_info in self.connection_users.items():
            if user_info.get("user_id") == user_id:
                await self.send_personal_message(conn_id, message)
                return True
        return False

    async def start_stream(
        self,
        connection_id: str,
        stream_type: str,
        stream_func,
        interval: int = 1000,
        **kwargs,
    ):
        """Start a data stream for a connection."""
        # Stop existing stream of same type
        if connection_id in self.active_streams:
            if stream_type in self.active_streams[connection_id]:
                await self.stop_stream(connection_id, stream_type)

        # Get websocket
        websocket = None
        for workspace_connections in self.active_connections.values():
            if connection_id in workspace_connections:
                websocket = workspace_connections[connection_id]
                break

        if not websocket:
            logger.error(f"WebSocket not found for connection {connection_id}")
            return

        # Create and start stream task
        stream_task = asyncio.create_task(
            self._stream_data(
                connection_id, websocket, stream_type, stream_func, interval, **kwargs
            )
        )

        if connection_id not in self.active_streams:
            self.active_streams[connection_id] = {}

        self.active_streams[connection_id][stream_type] = stream_task

        await self.send_personal_message(
            connection_id,
            {
                "type": "stream_started",
                "stream_type": stream_type,
                "interval": interval,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        logger.info(
            f"Started stream {stream_type} for connection {connection_id} with interval {interval}ms"
        )

    async def stop_stream(self, connection_id: str, stream_type: str):
        """Stop a data stream for a connection."""
        if (
            connection_id in self.active_streams
            and stream_type in self.active_streams[connection_id]
        ):
            stream_task = self.active_streams[connection_id][stream_type]
            if not stream_task.done():
                stream_task.cancel()
                try:
                    await stream_task
                except asyncio.CancelledError:
                    pass

            del self.active_streams[connection_id][stream_type]

            await self.send_personal_message(
                connection_id,
                {
                    "type": "stream_stopped",
                    "stream_type": stream_type,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            logger.info(f"Stopped stream {stream_type} for connection {connection_id}")

    async def _stream_data(
        self,
        connection_id: str,
        websocket: WebSocket,
        stream_type: str,
        stream_func,
        interval: int,
        **kwargs,
    ):
        """Stream data at specified interval."""
        try:
            while True:
                try:
                    # Call the stream function to get data
                    data = await stream_func(**kwargs)

                    await websocket.send_json(
                        {
                            "type": "metrics_update",
                            "stream_type": stream_type,
                            "data": data,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

                    await asyncio.sleep(interval / 1000)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in stream {stream_type}: {e}")
                    await websocket.send_json(
                        {
                            "type": "stream_error",
                            "stream_type": stream_type,
                            "error": str(e),
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                    break

        except Exception as e:
            logger.error(f"Fatal error in stream {stream_type}: {e}")

    async def _heartbeat(self, connection_id: str, websocket: WebSocket):
        """Send periodic heartbeat to keep connection alive."""
        try:
            while True:
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                try:
                    await websocket.send_json(
                        {
                            "type": "heartbeat",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                except Exception as e:
                    logger.error(f"Heartbeat failed for {connection_id}: {e}")
                    break
        except asyncio.CancelledError:
            logger.debug(f"Heartbeat cancelled for {connection_id}")
        except Exception as e:
            logger.error(f"Heartbeat error for {connection_id}: {e}")


# Global instance
manager = ConnectionManager()
