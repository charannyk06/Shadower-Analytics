"""WebSocket routes for real-time updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from typing import Optional, Dict, Any
import uuid
import logging
from datetime import datetime

from ..websocket.manager import manager
from ..middleware.auth import jwt_auth

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token"),
    workspace_id: Optional[str] = Query(
        None, description="Workspace ID to connect to"
    ),
):
    """
    Main WebSocket endpoint for real-time updates.

    Requires JWT token for authentication and supports workspace-based subscriptions.
    Clients can subscribe to specific event types and receive real-time updates.
    """

    connection_id = str(uuid.uuid4())
    user_info = None
    workspace = None

    try:
        # Verify JWT token
        user_info = await verify_token_ws(token)

        # Use workspace from token if not provided
        if not workspace_id:
            workspace = user_info.get("workspace_id")
        else:
            workspace = workspace_id

        # Validate workspace access
        user_workspaces = user_info.get("workspaces", [])
        if workspace not in user_workspaces:
            await websocket.close(code=4003, reason="No workspace access")
            logger.warning(
                f"User {user_info.get('user_id')} attempted to access workspace {workspace} without permission"
            )
            return

        # Connect
        await manager.connect(websocket, connection_id, workspace, user_info)

        # Handle messages
        while True:
            data = await websocket.receive_json()
            await handle_websocket_message(
                connection_id, workspace, data, user_info
            )

    except WebSocketDisconnect:
        if workspace:
            manager.disconnect(connection_id, workspace)
        logger.info(f"Client {connection_id} disconnected normally")

    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")
        if workspace:
            manager.disconnect(connection_id, workspace)

        try:
            await websocket.close(code=4000, reason=str(e))
        except:
            pass


async def verify_token_ws(token: str) -> Dict[str, Any]:
    """
    Verify JWT token for WebSocket connections.

    Args:
        token: JWT token string

    Returns:
        User information dictionary

    Raises:
        HTTPException: If token is invalid
    """
    try:
        from jose import jwt
        from ...core.config import settings

        # Decode token
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )

        # Check expiration
        import time

        if payload.get("exp", 0) < time.time():
            raise HTTPException(status_code=401, detail="Token has expired")

        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "workspace_id": payload.get("workspaceId"),
            "workspaces": payload.get("workspaces", []),
            "role": payload.get("role"),
            "permissions": payload.get("permissions", []),
        }

    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")


async def handle_websocket_message(
    connection_id: str,
    workspace_id: str,
    message: Dict[str, Any],
    user_info: Dict[str, Any],
):
    """
    Handle incoming WebSocket messages.

    Args:
        connection_id: Unique connection identifier
        workspace_id: Workspace the connection belongs to
        message: Message data from client
        user_info: Authenticated user information
    """

    msg_type = message.get("type")

    if msg_type == "subscribe":
        # Subscribe to events
        event_types = message.get("event_types", [])
        await manager.subscribe(connection_id, event_types)
        logger.debug(
            f"Connection {connection_id} subscribed to: {event_types}"
        )

    elif msg_type == "unsubscribe":
        # Unsubscribe from events
        event_types = message.get("event_types", [])
        await manager.unsubscribe(connection_id, event_types)
        logger.debug(
            f"Connection {connection_id} unsubscribed from: {event_types}"
        )

    elif msg_type == "ping":
        # Heartbeat
        await manager.send_personal_message(
            connection_id,
            {"event": "pong", "timestamp": datetime.utcnow().isoformat()},
        )

    elif msg_type == "request_metrics":
        # Request specific metrics update
        metric_type = message.get("metric_type")
        await send_metrics_update(connection_id, workspace_id, metric_type)

    elif msg_type == "get_connection_info":
        # Send connection info
        await manager.send_personal_message(
            connection_id,
            {
                "event": "connection_info",
                "data": {
                    "connection_id": connection_id,
                    "workspace_id": workspace_id,
                    "user_id": user_info.get("user_id"),
                    "subscriptions": list(
                        manager.subscriptions.get(connection_id, set())
                    ),
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    else:
        logger.warning(f"Unknown message type: {msg_type}")
        await manager.send_personal_message(
            connection_id,
            {
                "event": "error",
                "error": f"Unknown message type: {msg_type}",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


async def send_metrics_update(
    connection_id: str, workspace_id: str, metric_type: Optional[str] = None
):
    """
    Send metrics update to a specific connection.

    Args:
        connection_id: Connection to send update to
        workspace_id: Workspace to fetch metrics for
        metric_type: Specific metric type to fetch (optional)
    """
    try:
        # TODO: Fetch actual metrics from database
        # For now, send placeholder data
        metrics_data = {
            "total_executions": 0,
            "active_agents": 0,
            "credits_consumed": 0.0,
            "avg_runtime": 0.0,
        }

        await manager.send_personal_message(
            connection_id,
            {
                "event": "metrics_update",
                "data": metrics_data,
                "metric_type": metric_type,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    except Exception as e:
        logger.error(f"Error sending metrics update: {e}")
        await manager.send_personal_message(
            connection_id,
            {
                "event": "error",
                "error": "Failed to fetch metrics",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
