# WebSocket Real-time Updates Guide

## Overview

The Shadower-Analytics platform now supports real-time bidirectional communication using WebSockets. This enables live dashboard updates, notifications, and activity feeds without requiring page refreshes.

## Features

- **Real-time Updates**: Live execution tracking, metrics updates, and alerts
- **Workspace Isolation**: Room-based subscriptions ensure data security
- **Auto-reconnection**: Exponential backoff strategy for reliable connections
- **Event Filtering**: Subscribe only to events you need
- **Horizontal Scaling**: Redis pub/sub support for multi-instance deployments
- **JWT Authentication**: Secure WebSocket connections with token validation

## Backend Architecture

### Components

1. **Connection Manager** (`backend/src/api/websocket/manager.py`)
   - Manages active WebSocket connections
   - Handles workspace-based isolation
   - Manages event subscriptions per connection

2. **Event Broadcaster** (`backend/src/api/websocket/events.py`)
   - Broadcasts events to workspace subscribers
   - Supports various event types (execution, metrics, alerts)

3. **Redis Pub/Sub** (`backend/src/api/websocket/pubsub.py`)
   - Enables horizontal scaling across multiple server instances
   - Routes messages between server instances

4. **WebSocket Routes** (`backend/src/api/routes/websocket.py`)
   - JWT authentication for connections
   - Message handling and routing

### WebSocket Endpoint

**URL**: `ws://localhost:8000/ws` (or `wss://` for production)

**Query Parameters**:
- `token` (required): JWT authentication token
- `workspace_id` (optional): Workspace to connect to (defaults to token workspace)

**Example Connection**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws?token=YOUR_JWT_TOKEN&workspace_id=workspace-123');
```

### Event Types

#### Client → Server Messages

1. **Subscribe to Events**
```json
{
  "type": "subscribe",
  "event_types": ["execution_started", "execution_completed", "metrics_update", "alert"]
}
```

2. **Unsubscribe from Events**
```json
{
  "type": "unsubscribe",
  "event_types": ["execution_started"]
}
```

3. **Heartbeat (Ping)**
```json
{
  "type": "ping"
}
```

4. **Request Metrics**
```json
{
  "type": "request_metrics",
  "metric_type": "executions"
}
```

#### Server → Client Events

1. **Connection Confirmed**
```json
{
  "event": "connected",
  "connection_id": "uuid",
  "workspace_id": "workspace-123",
  "timestamp": "2025-11-09T12:00:00Z"
}
```

2. **Execution Started**
```json
{
  "event": "execution_started",
  "data": {
    "agent_id": "agent-123",
    "run_id": "run-456",
    "user_id": "user-789",
    "started_at": "2025-11-09T12:00:00Z"
  },
  "timestamp": "2025-11-09T12:00:00Z"
}
```

3. **Execution Completed**
```json
{
  "event": "execution_completed",
  "data": {
    "agent_id": "agent-123",
    "run_id": "run-456",
    "success": true,
    "runtime_seconds": 45.2,
    "credits_consumed": 0.15,
    "completed_at": "2025-11-09T12:00:45Z"
  },
  "timestamp": "2025-11-09T12:00:45Z"
}
```

4. **Metrics Update**
```json
{
  "event": "metrics_update",
  "data": {
    "total_executions": 1234,
    "active_agents": 5,
    "credits_consumed": 123.45,
    "avg_runtime": 32.5
  },
  "timestamp": "2025-11-09T12:00:00Z"
}
```

5. **Alert**
```json
{
  "event": "alert",
  "data": {
    "type": "credit_limit",
    "message": "Credit limit approaching",
    "priority": "high"
  },
  "priority": "high",
  "timestamp": "2025-11-09T12:00:00Z"
}
```

### Broadcasting Events from Backend

```python
from backend.src.api.websocket import broadcaster

# Broadcast execution started
await broadcaster.broadcast_execution_started(
    workspace_id="workspace-123",
    agent_id="agent-456",
    run_id="run-789",
    user_id="user-123"
)

# Broadcast execution completed
await broadcaster.broadcast_execution_completed(
    workspace_id="workspace-123",
    agent_id="agent-456",
    run_id="run-789",
    success=True,
    runtime_seconds=45.2,
    credits_consumed=0.15
)

# Broadcast metrics update
await broadcaster.broadcast_metrics_update(
    workspace_id="workspace-123",
    metrics={
        "total_executions": 1234,
        "active_agents": 5,
        "credits_consumed": 123.45
    }
)

# Broadcast alert
await broadcaster.broadcast_alert(
    workspace_id="workspace-123",
    alert_type="credit_limit",
    alert_data={
        "message": "Credit limit approaching",
        "priority": "high"
    }
)
```

## Frontend Integration

### React Hook: `useWebSocket`

```typescript
import { useWebSocket } from '@/hooks/useWebSocket';

function MyComponent() {
  const { connectionStatus, sendMessage, subscribe, unsubscribe } = useWebSocket({
    workspaceId: 'workspace-123',
    autoReconnect: true,
    maxReconnectAttempts: 5,
    onMessage: (event) => {
      const data = JSON.parse(event.data);
      console.log('Received:', data);
    }
  });

  return (
    <div>
      Status: {connectionStatus}
    </div>
  );
}
```

### Components

#### LiveExecutionCounter
Displays real-time execution counts and recent activity.

```tsx
import { LiveExecutionCounter } from '@/components/realtime';

function Dashboard() {
  return <LiveExecutionCounter workspaceId="workspace-123" />;
}
```

#### RealtimeMetrics
Shows live metrics with auto-updates.

```tsx
import { RealtimeMetrics } from '@/components/realtime';

function Dashboard() {
  return <RealtimeMetrics workspaceId="workspace-123" />;
}
```

#### WebSocketProvider
Global WebSocket context provider.

```tsx
import { WebSocketProvider } from '@/components/realtime';

function App({ children }) {
  return (
    <WebSocketProvider>
      {children}
    </WebSocketProvider>
  );
}
```

## Configuration

### Environment Variables

**Backend** (`.env`):
```env
REDIS_URL=redis://localhost:6379/0
ENABLE_REALTIME=true
```

**Frontend** (`.env.local`):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

### Production Configuration

For production, ensure:
1. Use WSS (WebSocket Secure) protocol
2. Redis is properly configured for pub/sub
3. Load balancer supports WebSocket connections (sticky sessions or shared state via Redis)
4. JWT tokens are properly validated

## Performance Targets

- **Connection establishment**: <500ms
- **Message latency**: <100ms
- **Concurrent connections**: 1000+ per instance
- **Message throughput**: 10,000 msg/sec
- **Reconnection time**: <2 seconds

## Security

- **JWT Authentication**: Required for all connections
- **Workspace Isolation**: Enforced at connection and broadcast level
- **Rate Limiting**: Per-connection message rate limits
- **Message Size Limits**: Max 1MB per message
- **Token Validation**: Expiration and blacklist checks

## Scaling

### Multi-instance Deployment

The system uses Redis pub/sub to enable horizontal scaling:

1. Each server instance maintains local WebSocket connections
2. Events are published to Redis channels (e.g., `workspace:{workspace_id}`)
3. All instances subscribe to relevant workspace channels
4. Messages are broadcast to local connections only

### Load Balancing

Configure your load balancer to:
- Support WebSocket protocol upgrades
- Use IP hash or cookies for sticky sessions (optional)
- Set appropriate timeouts (recommended: 60s+)

## Monitoring

### Connection Metrics

```python
from backend.src.api.websocket import manager

# Get connection count
total_connections = manager.get_connection_count()
workspace_connections = manager.get_connection_count('workspace-123')

# Get workspace connection IDs
connection_ids = manager.get_workspace_connections('workspace-123')
```

### Logs

WebSocket events are logged at various levels:
- INFO: Connections, disconnections
- DEBUG: Message handling, subscriptions
- ERROR: Connection failures, message errors

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Check JWT token validity
   - Verify workspace access permissions
   - Ensure WebSocket endpoint is accessible

2. **Disconnections**
   - Check network stability
   - Verify Redis connection (for scaling)
   - Review server logs for errors

3. **Messages Not Received**
   - Verify subscription to event types
   - Check workspace ID matches
   - Ensure broadcaster is being called correctly

4. **Scaling Issues**
   - Verify Redis pub/sub is running
   - Check all instances are subscribed to workspace channels
   - Review Redis connection logs

## Testing

### Manual Testing

Use wscat for manual WebSocket testing:

```bash
npm install -g wscat
wscat -c "ws://localhost:8000/ws?token=YOUR_JWT_TOKEN"

# Send subscribe message
> {"type":"subscribe","event_types":["execution_started"]}

# Send ping
> {"type":"ping"}
```

### Automated Testing

```python
import pytest
import asyncio
from fastapi.testclient import TestClient
from fastapi import WebSocket

async def test_websocket_connection():
    client = TestClient(app)
    with client.websocket_connect("/ws?token=valid_token") as websocket:
        data = websocket.receive_json()
        assert data["event"] == "connected"
```

## Future Enhancements

- [ ] Compression for messages (WebSocket permessage-deflate)
- [ ] Binary message support for large payloads
- [ ] Presence tracking (online users)
- [ ] Typing indicators
- [ ] Direct messaging between users
- [ ] Message history/replay
- [ ] WebSocket over HTTP/2 (WebTransport)

## Support

For issues or questions:
- Check logs in `backend/logs/`
- Review connection status in browser DevTools
- File issue on GitHub with WebSocket logs
