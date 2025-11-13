"""WebSocket routes for real-time updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, Depends
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import logging
from datetime import datetime

from ..websocket.manager import manager
from ..websocket.errors import WebSocketErrorCode, handle_ws_error, send_error_message
from ..websocket.rate_limit import rate_limiter
from ..websocket.realtime_metrics import RealtimeMetricsService
from ..middleware.auth import jwt_auth
from ...core.database import get_db

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

    Connection URL: ws://analytics.shadower.ai/api/v1/ws?token=JWT_TOKEN&workspace_id=WORKSPACE_ID
    """
    connection_id = str(uuid.uuid4())
    user_info = None
    workspace = None
    db = None

    try:
        # Verify JWT token
        try:
            user_info = await verify_token_ws(token)
        except HTTPException as e:
            await handle_ws_error(
                websocket,
                WebSocketErrorCode.INVALID_TOKEN,
                details=str(e.detail),
            )
            return

        # Use workspace from token if not provided
        if not workspace_id:
            workspace = user_info.get("workspace_id")
        else:
            workspace = workspace_id

        # Validate workspace access
        user_workspaces = user_info.get("workspaces", [])
        if workspace not in user_workspaces:
            await handle_ws_error(
                websocket,
                WebSocketErrorCode.ACCESS_DENIED,
                details=f"No access to workspace {workspace}",
            )
            logger.warning(
                f"User {user_info.get('user_id')} attempted to access workspace {workspace} without permission"
            )
            return

        # Get database session
        async for session in get_db():
            db = session
            break

        # Connect
        await manager.connect(websocket, connection_id, workspace, user_info)

        # Handle messages
        while True:
            try:
                data = await websocket.receive_json()
                await handle_websocket_message(
                    connection_id, workspace, data, user_info, db
                )
            except ValueError as e:
                # Invalid JSON
                await send_error_message(
                    websocket,
                    "invalid_message",
                    "Invalid message format",
                    {"error": str(e)},
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

    finally:
        # Clean up database session
        if db:
            await db.close()


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
    db: AsyncSession,
):
    """
    Handle incoming WebSocket messages.

    Args:
        connection_id: Unique connection identifier
        workspace_id: Workspace the connection belongs to
        message: Message data from client
        user_info: Authenticated user information
        db: Database session
    """
    msg_type = message.get("type")
    user_id = user_info.get("user_id")

    # Rate limiting
    if not rate_limiter.check_rate_limit(user_id, msg_type):
        await manager.send_personal_message(
            connection_id,
            {
                "type": "error",
                "code": WebSocketErrorCode.RATE_LIMITED[0],
                "message": WebSocketErrorCode.RATE_LIMITED[1],
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        return

    # Handle different message types
    if msg_type == "subscribe":
        # Subscribe to event channels
        channels = message.get("channels", [])
        event_types = message.get("event_types", channels)  # Support both formats
        await manager.subscribe(connection_id, event_types)
        logger.debug(f"Connection {connection_id} subscribed to: {event_types}")

    elif msg_type == "unsubscribe":
        # Unsubscribe from event channels
        channels = message.get("channels", [])
        event_types = message.get("event_types", channels)
        await manager.unsubscribe(connection_id, event_types)
        logger.debug(f"Connection {connection_id} unsubscribed from: {event_types}")

    elif msg_type == "join_room":
        # Join a room
        room_name = message.get("room")
        if room_name:
            await manager.join_room(connection_id, room_name, workspace_id)
        else:
            await manager.send_personal_message(
                connection_id,
                {
                    "type": "error",
                    "message": "Room name required",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

    elif msg_type == "leave_room":
        # Leave a room
        room_name = message.get("room")
        if room_name:
            await manager.leave_room(connection_id, room_name, workspace_id)
        else:
            await manager.send_personal_message(
                connection_id,
                {
                    "type": "error",
                    "message": "Room name required",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

    elif msg_type == "start_stream":
        # Start metrics streaming
        stream_type = message.get("stream_type")
        interval = message.get("interval", 5000)  # Default 5 seconds
        filters = message.get("filters", {})

        if not stream_type:
            await manager.send_personal_message(
                connection_id,
                {
                    "type": "error",
                    "message": "stream_type required",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            return

        # Get the appropriate stream function
        stream_func = get_stream_function(stream_type, db, workspace_id, filters)

        if stream_func:
            await manager.start_stream(
                connection_id, stream_type, stream_func, interval
            )
        else:
            await manager.send_personal_message(
                connection_id,
                {
                    "type": "error",
                    "message": f"Unknown stream type: {stream_type}",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

    elif msg_type == "stop_stream":
        # Stop metrics streaming
        stream_type = message.get("stream_type")
        if stream_type:
            await manager.stop_stream(connection_id, stream_type)
        else:
            await manager.send_personal_message(
                connection_id,
                {
                    "type": "error",
                    "message": "stream_type required",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

    elif msg_type == "get_metrics":
        # Get one-time metrics snapshot
        metrics = message.get("metrics", [])
        timeframe = message.get("timeframe", "1h")
        await send_metrics_snapshot(connection_id, workspace_id, metrics, db)

    elif msg_type == "ping":
        # Heartbeat response
        await manager.send_personal_message(
            connection_id,
            {"type": "pong", "timestamp": datetime.utcnow().isoformat()},
        )

    elif msg_type == "get_connection_info":
        # Send connection info
        await manager.send_personal_message(
            connection_id,
            {
                "type": "connection_info",
                "data": {
                    "connection_id": connection_id,
                    "workspace_id": workspace_id,
                    "user_id": user_id,
                    "subscriptions": list(manager.subscriptions.get(connection_id, set())),
                    "active_streams": list(
                        manager.active_streams.get(connection_id, {}).keys()
                    ),
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    elif msg_type == "update_settings":
        # Update user settings (placeholder for future implementation)
        settings = message.get("settings", {})
        await manager.send_personal_message(
            connection_id,
            {
                "type": "settings_updated",
                "settings": settings,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    else:
        logger.warning(f"Unknown message type: {msg_type}")
        await manager.send_personal_message(
            connection_id,
            {
                "type": "error",
                "code": WebSocketErrorCode.UNKNOWN_MESSAGE_TYPE[0],
                "message": f"Unknown message type: {msg_type}",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


def get_stream_function(
    stream_type: str, db: AsyncSession, workspace_id: str, filters: Dict[str, Any]
):
    """
    Get the appropriate stream function based on stream type.

    Args:
        stream_type: Type of stream to create
        db: Database session
        workspace_id: Workspace ID
        filters: Additional filters

    Returns:
        Async function that fetches stream data
    """
    metrics_service = RealtimeMetricsService()

    # Map stream types to service methods
    stream_map = {
        "active_users": lambda: metrics_service.get_active_users_count(
            db, workspace_id, filters
        ),
        "credits_consumed": lambda: metrics_service.get_credits_consumed(
            db, workspace_id, filters
        ),
        "error_rate": lambda: metrics_service.get_error_rate(
            db, workspace_id, filters
        ),
        "dashboard_summary": lambda: metrics_service.get_dashboard_summary(
            db, workspace_id
        ),
        "queue_status": lambda: metrics_service.get_execution_queue_status(
            db, workspace_id
        ),
    }

    # Agent-specific stream
    if stream_type == "agent_performance" and filters.get("agent_id"):
        return lambda: metrics_service.get_agent_performance(
            db, workspace_id, filters["agent_id"]
        )

    return stream_map.get(stream_type)


async def send_metrics_snapshot(
    connection_id: str, workspace_id: str, metrics: list, db: AsyncSession
):
    """
    Send one-time metrics snapshot.

    Args:
        connection_id: Connection to send to
        workspace_id: Workspace ID
        metrics: List of metrics to fetch
        db: Database session
    """
    try:
        metrics_service = RealtimeMetricsService()
        results = {}

        # Fetch requested metrics
        for metric in metrics:
            if metric == "active_users":
                results[metric] = await metrics_service.get_active_users_count(
                    db, workspace_id
                )
            elif metric == "credits_consumed":
                results[metric] = await metrics_service.get_credits_consumed(
                    db, workspace_id
                )
            elif metric == "error_rate":
                results[metric] = await metrics_service.get_error_rate(db, workspace_id)

        await manager.send_personal_message(
            connection_id,
            {
                "type": "metrics_snapshot",
                "data": results,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    except Exception as e:
        logger.error(f"Error sending metrics snapshot: {e}")
        await manager.send_personal_message(
            connection_id,
            {
                "type": "error",
                "message": "Failed to fetch metrics",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
