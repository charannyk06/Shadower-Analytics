# Specification: WebSocket API Endpoints

## Overview
Define WebSocket endpoints for real-time data streaming, live updates, and bidirectional communication.

## Technical Requirements

### WebSocket Connection Management

#### WebSocket Gateway
```python
from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
import json

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_connections: Dict[str, WebSocket] = {}
        self.room_subscriptions: Dict[str, Set[str]] = {}
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        workspace_id: str
    ):
        """Accept and register WebSocket connection"""
        await websocket.accept()
        
        # Add to workspace room
        room_key = f"workspace:{workspace_id}"
        if room_key not in self.active_connections:
            self.active_connections[room_key] = set()
        self.active_connections[room_key].add(websocket)
        
        # Track user connection
        self.user_connections[user_id] = websocket
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "user_id": user_id,
            "workspace_id": workspace_id,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove WebSocket connection"""
        # Remove from all rooms
        for room_key, connections in self.active_connections.items():
            connections.discard(websocket)
        
        # Remove user tracking
        self.user_connections.pop(user_id, None)
    
    async def broadcast_to_room(
        self,
        room_key: str,
        message: dict
    ):
        """Broadcast message to all connections in a room"""
        if room_key in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[room_key]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.add(connection)
            
            # Clean up disconnected clients
            for conn in disconnected:
                self.active_connections[room_key].discard(conn)

manager = WebSocketManager()
```

### Main WebSocket Endpoint

#### WS `/api/v1/ws`
```python
@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    workspace_id: str
):
    """
    Main WebSocket endpoint for real-time communication
    
    Connection URL:
    ws://analytics.shadower.ai/api/v1/ws?token=JWT_TOKEN&workspace_id=WORKSPACE_ID
    """
    # Validate JWT token
    user = await validate_ws_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    # Check workspace access
    if not has_workspace_access(user.id, workspace_id):
        await websocket.close(code=4003, reason="Access denied")
        return
    
    await manager.connect(websocket, user.id, workspace_id)
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()
            await handle_ws_message(websocket, user.id, workspace_id, data)
    
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user.id)
    except Exception as e:
        await websocket.close(code=4000, reason=str(e))
        await manager.disconnect(websocket, user.id)
```

### WebSocket Message Handlers

```python
async def handle_ws_message(
    websocket: WebSocket,
    user_id: str,
    workspace_id: str,
    data: dict
):
    """Route WebSocket messages to appropriate handlers"""
    
    message_type = data.get("type")
    
    handlers = {
        "subscribe": handle_subscribe,
        "unsubscribe": handle_unsubscribe,
        "get_metrics": handle_get_metrics,
        "start_stream": handle_start_stream,
        "stop_stream": handle_stop_stream,
        "ping": handle_ping
    }
    
    handler = handlers.get(message_type)
    if handler:
        await handler(websocket, user_id, workspace_id, data)
    else:
        await websocket.send_json({
            "type": "error",
            "error": f"Unknown message type: {message_type}"
        })

async def handle_subscribe(
    websocket: WebSocket,
    user_id: str,
    workspace_id: str,
    data: dict
):
    """Subscribe to specific data streams"""
    channels = data.get("channels", [])
    
    for channel in channels:
        room_key = f"{workspace_id}:{channel}"
        if room_key not in manager.room_subscriptions:
            manager.room_subscriptions[room_key] = set()
        manager.room_subscriptions[room_key].add(user_id)
    
    await websocket.send_json({
        "type": "subscribed",
        "channels": channels,
        "timestamp": datetime.utcnow().isoformat()
    })

async def handle_start_stream(
    websocket: WebSocket,
    user_id: str,
    workspace_id: str,
    data: dict
):
    """Start streaming specific metrics"""
    stream_type = data.get("stream_type")
    interval = data.get("interval", 1000)  # milliseconds
    
    # Start async task for streaming
    task = asyncio.create_task(
        stream_metrics(websocket, workspace_id, stream_type, interval)
    )
    
    await websocket.send_json({
        "type": "stream_started",
        "stream_type": stream_type,
        "interval": interval
    })
```

### Real-time Data Streams

#### Metrics Stream
```python
async def stream_metrics(
    websocket: WebSocket,
    workspace_id: str,
    stream_type: str,
    interval: int
):
    """Stream real-time metrics at specified interval"""
    
    while True:
        try:
            metrics = await get_realtime_metrics(workspace_id, stream_type)
            
            await websocket.send_json({
                "type": "metrics_update",
                "stream_type": stream_type,
                "data": metrics,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            await asyncio.sleep(interval / 1000)
        
        except Exception as e:
            await websocket.send_json({
                "type": "stream_error",
                "stream_type": stream_type,
                "error": str(e)
            })
            break
```

### WebSocket Message Types

#### Client -> Server Messages

1. **Subscribe to Channels**
```json
{
    "type": "subscribe",
    "channels": [
        "dashboard_updates",
        "agent_performance",
        "alerts"
    ]
}
```

2. **Start Metrics Stream**
```json
{
    "type": "start_stream",
    "stream_type": "active_users",
    "interval": 5000,
    "filters": {
        "agent_id": "agent_123"
    }
}
```

3. **Request Snapshot**
```json
{
    "type": "get_metrics",
    "metrics": ["active_users", "credits_consumed", "error_rate"],
    "timeframe": "1h"
}
```

4. **Update Settings**
```json
{
    "type": "update_settings",
    "settings": {
        "notification_enabled": true,
        "update_frequency": "high"
    }
}
```

#### Server -> Client Messages

1. **Dashboard Update**
```json
{
    "type": "dashboard_update",
    "section": "executive_summary",
    "data": {
        "active_users": 3421,
        "credits_consumed": 125000,
        "success_rate": 94.5
    },
    "timestamp": "2024-01-15T14:30:00Z"
}
```

2. **Alert Notification**
```json
{
    "type": "alert",
    "severity": "critical",
    "title": "High Error Rate Detected",
    "message": "Error rate exceeded 5% threshold",
    "metric": "error_rate",
    "value": 0.067,
    "threshold": 0.05,
    "alert_id": "alert_123",
    "timestamp": "2024-01-15T14:30:00Z"
}
```

3. **Agent Performance Update**
```json
{
    "type": "agent_update",
    "agent_id": "agent_123",
    "metrics": {
        "executions": 45,
        "success_rate": 91.1,
        "avg_response_time": 234,
        "active_users": 12
    },
    "timestamp": "2024-01-15T14:30:00Z"
}
```

4. **User Activity Event**
```json
{
    "type": "user_event",
    "event": "execution_started",
    "user_id": "user_456",
    "agent_id": "agent_123",
    "execution_id": "exec_789",
    "timestamp": "2024-01-15T14:30:00Z"
}
```

### WebSocket Rooms and Broadcasting

```python
class RoomManager:
    async def join_room(
        self,
        user_id: str,
        room_name: str,
        websocket: WebSocket
    ):
        """Add user to a specific room"""
        room_key = f"room:{room_name}"
        if room_key not in self.active_connections:
            self.active_connections[room_key] = set()
        self.active_connections[room_key].add(websocket)
    
    async def leave_room(
        self,
        user_id: str,
        room_name: str,
        websocket: WebSocket
    ):
        """Remove user from a room"""
        room_key = f"room:{room_name}"
        if room_key in self.active_connections:
            self.active_connections[room_key].discard(websocket)
    
    async def broadcast_to_workspace(
        self,
        workspace_id: str,
        message: dict,
        exclude_user: str = None
    ):
        """Broadcast to all users in workspace"""
        room_key = f"workspace:{workspace_id}"
        await self.broadcast_to_room(room_key, message, exclude_user)
    
    async def send_to_user(
        self,
        user_id: str,
        message: dict
    ):
        """Send message to specific user"""
        if user_id in self.user_connections:
            await self.user_connections[user_id].send_json(message)
```

### WebSocket Authentication & Security

```python
async def validate_ws_token(token: str) -> Optional[User]:
    """Validate WebSocket connection token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        return await get_user(user_id)
    except jwt.InvalidTokenError:
        return None

async def check_rate_limit_ws(user_id: str, action: str) -> bool:
    """WebSocket-specific rate limiting"""
    key = f"ws_rate:{user_id}:{action}"
    count = await redis.incr(key)
    
    if count == 1:
        await redis.expire(key, 60)  # 1 minute window
    
    return count <= WS_RATE_LIMITS.get(action, 100)
```

### WebSocket Heartbeat

```python
async def websocket_heartbeat(websocket: WebSocket):
    """Send periodic heartbeat to keep connection alive"""
    while True:
        try:
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat()
            })
            await asyncio.sleep(30)  # Send heartbeat every 30 seconds
        except:
            break
```

### WebSocket Error Handling

```python
class WebSocketError:
    INVALID_TOKEN = (4001, "Invalid authentication token")
    TOKEN_EXPIRED = (4002, "Authentication token expired")
    ACCESS_DENIED = (4003, "Access denied to resource")
    RATE_LIMITED = (4004, "Rate limit exceeded")
    INVALID_MESSAGE = (4005, "Invalid message format")
    INTERNAL_ERROR = (4006, "Internal server error")

async def handle_ws_error(
    websocket: WebSocket,
    error_code: tuple
):
    """Handle WebSocket errors consistently"""
    code, reason = error_code
    await websocket.send_json({
        "type": "error",
        "code": code,
        "message": reason,
        "timestamp": datetime.utcnow().isoformat()
    })
    await websocket.close(code=code, reason=reason)
```

### WebSocket Scaling with Redis Pub/Sub

```python
class ScalableWebSocketManager:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.pubsub = self.redis.pubsub()
        
    async def publish_to_channel(
        self,
        channel: str,
        message: dict
    ):
        """Publish message to Redis for multi-server broadcasting"""
        await self.redis.publish(
            channel,
            json.dumps(message)
        )
    
    async def subscribe_to_redis_channels(self):
        """Subscribe to Redis channels for cross-server communication"""
        await self.pubsub.subscribe("analytics:broadcast")
        
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await self.handle_redis_message(data)
    
    async def handle_redis_message(self, data: dict):
        """Handle messages from Redis pub/sub"""
        workspace_id = data.get("workspace_id")
        if workspace_id:
            await manager.broadcast_to_workspace(
                workspace_id,
                data.get("message")
            )
```

## Implementation Priority
1. Basic WebSocket connection and auth
2. Real-time metrics streaming
3. Alert notifications
4. Room-based broadcasting
5. Redis pub/sub for scaling

## Success Metrics
- Connection stability > 99%
- Message delivery latency < 50ms
- Concurrent connections > 10,000
- Message throughput > 1000/second