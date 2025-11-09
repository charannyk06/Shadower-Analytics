# Specification: WebSocket Real-time Updates

## Feature Overview
Real-time bidirectional communication system using WebSockets for live dashboard updates, notifications, and activity feeds.

## Technical Requirements
- WebSocket server integrated with FastAPI
- Auto-reconnection with exponential backoff
- Room-based subscriptions (workspace isolation)
- Event filtering and throttling
- Horizontal scaling support with Redis pub/sub

## Implementation Details

### Backend WebSocket Server

#### WebSocket Manager
```python
# backend/src/api/websocket/manager.py
from typing import Dict, Set, List, Optional
from fastapi import WebSocket
import json
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
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
        user_info: Dict
    ):
        """Accept new WebSocket connection"""
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
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"WebSocket connected: {connection_id} to workspace {workspace_id}")
    
    def disconnect(self, connection_id: str, workspace_id: str):
        """Remove WebSocket connection"""
        if workspace_id in self.active_connections:
            self.active_connections[workspace_id].pop(connection_id, None)
            
            # Clean up empty workspace
            if not self.active_connections[workspace_id]:
                del self.active_connections[workspace_id]
        
        # Clean up user info and subscriptions
        self.connection_users.pop(connection_id, None)
        self.subscriptions.pop(connection_id, None)
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(
        self, 
        connection_id: str, 
        message: Dict
    ):
        """Send message to specific connection"""
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
        exclude_connection: Optional[str] = None
    ):
        """Broadcast message to all connections in workspace"""
        if workspace_id not in self.active_connections:
            return
        
        disconnected = []
        
        for conn_id, websocket in self.active_connections[workspace_id].items():
            if conn_id == exclude_connection:
                continue
            
            try:
                # Check subscription
                event_type = message.get("event")
                if event_type and event_type not in self.subscriptions.get(conn_id, set()):
                    continue
                
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {conn_id}: {e}")
                disconnected.append(conn_id)
        
        # Clean up disconnected clients
        for conn_id in disconnected:
            self.disconnect(conn_id, workspace_id)
    
    async def subscribe(
        self, 
        connection_id: str, 
        event_types: List[str]
    ):
        """Subscribe connection to event types"""
        if connection_id in self.subscriptions:
            self.subscriptions[connection_id].update(event_types)
            
            await self.send_personal_message(
                connection_id,
                {
                    "event": "subscribed",
                    "event_types": list(self.subscriptions[connection_id]),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    async def unsubscribe(
        self, 
        connection_id: str, 
        event_types: List[str]
    ):
        """Unsubscribe connection from event types"""
        if connection_id in self.subscriptions:
            for event_type in event_types:
                self.subscriptions[connection_id].discard(event_type)
            
            await self.send_personal_message(
                connection_id,
                {
                    "event": "unsubscribed",
                    "event_types": event_types,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    def get_workspace_connections(
        self, 
        workspace_id: str
    ) -> List[str]:
        """Get all connection IDs for a workspace"""
        return list(self.active_connections.get(workspace_id, {}).keys())
    
    def get_connection_count(
        self, 
        workspace_id: Optional[str] = None
    ) -> int:
        """Get count of active connections"""
        if workspace_id:
            return len(self.active_connections.get(workspace_id, {}))
        
        total = 0
        for connections in self.active_connections.values():
            total += len(connections)
        return total

# Global instance
manager = ConnectionManager()
```

#### WebSocket Endpoint
```python
# backend/src/api/routes/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from typing import Optional, Dict, Any
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    workspace_id: Optional[str] = Query(None)
):
    """Main WebSocket endpoint"""
    
    connection_id = str(uuid.uuid4())
    user_info = None
    
    try:
        # Verify JWT token
        user_info = await jwt_auth.verify_token_ws(token)
        
        # Use workspace from token if not provided
        if not workspace_id:
            workspace_id = user_info.get('workspace_id')
        
        # Validate workspace access
        if workspace_id not in user_info.get('workspaces', []):
            await websocket.close(code=4003, reason="No workspace access")
            return
        
        # Connect
        await manager.connect(
            websocket, 
            connection_id, 
            workspace_id, 
            user_info
        )
        
        # Handle messages
        while True:
            data = await websocket.receive_json()
            await handle_websocket_message(
                connection_id, 
                workspace_id, 
                data, 
                user_info
            )
            
    except WebSocketDisconnect:
        manager.disconnect(connection_id, workspace_id)
        logger.info(f"Client {connection_id} disconnected normally")
        
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")
        manager.disconnect(connection_id, workspace_id)
        
        try:
            await websocket.close(code=4000, reason=str(e))
        except:
            pass

async def handle_websocket_message(
    connection_id: str,
    workspace_id: str,
    message: Dict[str, Any],
    user_info: Dict[str, Any]
):
    """Handle incoming WebSocket messages"""
    
    msg_type = message.get("type")
    
    if msg_type == "subscribe":
        # Subscribe to events
        event_types = message.get("event_types", [])
        await manager.subscribe(connection_id, event_types)
        
    elif msg_type == "unsubscribe":
        # Unsubscribe from events
        event_types = message.get("event_types", [])
        await manager.unsubscribe(connection_id, event_types)
        
    elif msg_type == "ping":
        # Heartbeat
        await manager.send_personal_message(
            connection_id,
            {
                "event": "pong",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    elif msg_type == "request_metrics":
        # Request specific metrics update
        metric_type = message.get("metric_type")
        await send_metrics_update(
            connection_id, 
            workspace_id, 
            metric_type
        )
    
    else:
        logger.warning(f"Unknown message type: {msg_type}")
```

#### Event Broadcasting
```python
# backend/src/api/websocket/events.py
from typing import Dict, Any
from datetime import datetime
import asyncio

class EventBroadcaster:
    """Broadcast events to WebSocket clients"""
    
    @staticmethod
    async def broadcast_execution_started(
        workspace_id: str,
        agent_id: str,
        run_id: str,
        user_id: str
    ):
        """Broadcast when agent execution starts"""
        message = {
            "event": "execution_started",
            "data": {
                "agent_id": agent_id,
                "run_id": run_id,
                "user_id": user_id,
                "started_at": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await manager.broadcast_to_workspace(workspace_id, message)
    
    @staticmethod
    async def broadcast_execution_completed(
        workspace_id: str,
        agent_id: str,
        run_id: str,
        success: bool,
        runtime_seconds: float,
        credits_consumed: float
    ):
        """Broadcast when agent execution completes"""
        message = {
            "event": "execution_completed",
            "data": {
                "agent_id": agent_id,
                "run_id": run_id,
                "success": success,
                "runtime_seconds": runtime_seconds,
                "credits_consumed": credits_consumed,
                "completed_at": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await manager.broadcast_to_workspace(workspace_id, message)
    
    @staticmethod
    async def broadcast_metrics_update(
        workspace_id: str,
        metrics: Dict[str, Any]
    ):
        """Broadcast metrics update"""
        message = {
            "event": "metrics_update",
            "data": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await manager.broadcast_to_workspace(workspace_id, message)
    
    @staticmethod
    async def broadcast_alert(
        workspace_id: str,
        alert_type: str,
        alert_data: Dict[str, Any]
    ):
        """Broadcast alert notification"""
        message = {
            "event": "alert",
            "data": {
                "type": alert_type,
                **alert_data
            },
            "timestamp": datetime.utcnow().isoformat(),
            "priority": alert_data.get("priority", "medium")
        }
        
        await manager.broadcast_to_workspace(workspace_id, message)

# Global instance
broadcaster = EventBroadcaster()
```

#### Redis Pub/Sub for Scaling
```python
# backend/src/api/websocket/pubsub.py
import redis.asyncio as redis
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

class RedisPubSub:
    """Redis pub/sub for multi-instance WebSocket scaling"""
    
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.pubsub = self.redis.pubsub()
        self.subscriptions = {}
        self.running = False
    
    async def start(self):
        """Start listening to Redis pub/sub"""
        self.running = True
        asyncio.create_task(self._listen())
    
    async def stop(self):
        """Stop listening"""
        self.running = False
        await self.pubsub.unsubscribe()
        await self.redis.close()
    
    async def publish(
        self, 
        channel: str, 
        message: Dict
    ):
        """Publish message to Redis channel"""
        await self.redis.publish(
            channel,
            json.dumps(message)
        )
    
    async def subscribe_workspace(
        self, 
        workspace_id: str
    ):
        """Subscribe to workspace channel"""
        channel = f"workspace:{workspace_id}"
        await self.pubsub.subscribe(channel)
        self.subscriptions[channel] = workspace_id
    
    async def unsubscribe_workspace(
        self, 
        workspace_id: str
    ):
        """Unsubscribe from workspace channel"""
        channel = f"workspace:{workspace_id}"
        await self.pubsub.unsubscribe(channel)
        self.subscriptions.pop(channel, None)
    
    async def _listen(self):
        """Listen for Redis pub/sub messages"""
        while self.running:
            try:
                message = await self.pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )
                
                if message and message['type'] == 'message':
                    await self._handle_message(message)
                    
            except Exception as e:
                logger.error(f"Redis pub/sub error: {e}")
                await asyncio.sleep(5)
    
    async def _handle_message(
        self, 
        message: Dict
    ):
        """Handle pub/sub message"""
        channel = message['channel'].decode()
        data = json.loads(message['data'])
        
        # Extract workspace_id from channel
        if channel.startswith('workspace:'):
            workspace_id = channel.split(':', 1)[1]
            
            # Broadcast to local WebSocket connections
            await manager.broadcast_to_workspace(
                workspace_id, 
                data
            )

# Initialize for multi-instance support
redis_pubsub = RedisPubSub(settings.REDIS_URL)
```

### Frontend WebSocket Client

#### WebSocket Hook
```typescript
// frontend/src/hooks/useWebSocket.ts
import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'react-hot-toast';

interface WebSocketOptions {
  workspaceId?: string;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onMessage?: (event: MessageEvent) => void;
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
}

interface WebSocketHook {
  sendMessage: (message: any) => void;
  subscribe: (eventTypes: string[]) => void;
  unsubscribe: (eventTypes: string[]) => void;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  reconnect: () => void;
}

export function useWebSocket(options: WebSocketOptions = {}): WebSocketHook {
  const {
    workspaceId,
    autoReconnect = true,
    reconnectInterval = 1000,
    maxReconnectAttempts = 5,
    onMessage,
    onOpen,
    onClose,
    onError,
  } = options;

  const { token, user } = useAuth();
  const [connectionStatus, setConnectionStatus] = useState<
    'connecting' | 'connected' | 'disconnected' | 'error'
  >('disconnected');
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectCount = useRef(0);
  const reconnectTimeout = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    if (!token) {
      console.error('No auth token available');
      return;
    }

    const wsUrl = new URL(process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws');
    wsUrl.searchParams.append('token', token);
    
    if (workspaceId) {
      wsUrl.searchParams.append('workspace_id', workspaceId);
    }

    setConnectionStatus('connecting');

    try {
      ws.current = new WebSocket(wsUrl.toString());

      ws.current.onopen = (event) => {
        setConnectionStatus('connected');
        reconnectCount.current = 0;
        console.log('WebSocket connected');
        
        // Send initial subscriptions
        if (ws.current?.readyState === WebSocket.OPEN) {
          ws.current.send(JSON.stringify({
            type: 'subscribe',
            event_types: [
              'execution_started',
              'execution_completed',
              'metrics_update',
              'alert'
            ]
          }));
        }
        
        onOpen?.(event);
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket message:', data);
          
          // Handle specific event types
          switch (data.event) {
            case 'connected':
              console.log('Connection confirmed:', data.connection_id);
              break;
              
            case 'execution_completed':
              // Could trigger a refetch of metrics
              break;
              
            case 'alert':
              if (data.data.priority === 'high') {
                toast.error(data.data.message || 'High priority alert');
              }
              break;
          }
          
          onMessage?.(event);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.current.onclose = (event) => {
        setConnectionStatus('disconnected');
        console.log('WebSocket disconnected:', event.code, event.reason);
        
        // Auto reconnect logic
        if (autoReconnect && reconnectCount.current < maxReconnectAttempts) {
          const delay = reconnectInterval * Math.pow(2, reconnectCount.current);
          reconnectCount.current++;
          
          console.log(`Reconnecting in ${delay}ms (attempt ${reconnectCount.current})`);
          
          reconnectTimeout.current = setTimeout(() => {
            connect();
          }, delay);
        }
        
        onClose?.(event);
      };

      ws.current.onerror = (event) => {
        setConnectionStatus('error');
        console.error('WebSocket error:', event);
        onError?.(event);
      };
      
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      setConnectionStatus('error');
    }
  }, [token, workspaceId, autoReconnect, reconnectInterval, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
    }
    
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      console.error('WebSocket not connected');
    }
  }, []);

  const subscribe = useCallback((eventTypes: string[]) => {
    sendMessage({
      type: 'subscribe',
      event_types: eventTypes
    });
  }, [sendMessage]);

  const unsubscribe = useCallback((eventTypes: string[]) => {
    sendMessage({
      type: 'unsubscribe',
      event_types: eventTypes
    });
  }, [sendMessage]);

  const reconnect = useCallback(() => {
    disconnect();
    reconnectCount.current = 0;
    connect();
  }, [connect, disconnect]);

  // Connect on mount
  useEffect(() => {
    connect();
    
    // Heartbeat
    const heartbeatInterval = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // Every 30 seconds
    
    return () => {
      clearInterval(heartbeatInterval);
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    sendMessage,
    subscribe,
    unsubscribe,
    connectionStatus,
    reconnect
  };
}
```

#### Real-time Component Examples
```typescript
// frontend/src/components/realtime/LiveExecutionCounter.tsx
import { useState, useEffect } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { motion, AnimatePresence } from 'framer-motion';

export function LiveExecutionCounter({ workspaceId }: { workspaceId: string }) {
  const [executionCount, setExecutionCount] = useState(0);
  const [recentExecutions, setRecentExecutions] = useState<any[]>([]);
  
  const { connectionStatus } = useWebSocket({
    workspaceId,
    onMessage: (event) => {
      const data = JSON.parse(event.data);
      
      if (data.event === 'execution_started') {
        setExecutionCount(prev => prev + 1);
        setRecentExecutions(prev => [
          data.data,
          ...prev.slice(0, 9) // Keep last 10
        ]);
      }
    }
  });

  return (
    <div className="p-4 bg-white rounded-lg shadow">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Live Executions</h3>
        <ConnectionIndicator status={connectionStatus} />
      </div>
      
      <div className="text-3xl font-bold text-blue-600">
        <motion.span
          key={executionCount}
          initial={{ scale: 1.2, color: '#3b82f6' }}
          animate={{ scale: 1, color: '#1f2937' }}
          transition={{ duration: 0.3 }}
        >
          {executionCount.toLocaleString()}
        </motion.span>
        <span className="text-sm font-normal text-gray-500 ml-2">
          executions today
        </span>
      </div>
      
      <div className="mt-4 space-y-2">
        <AnimatePresence>
          {recentExecutions.map((execution, index) => (
            <motion.div
              key={execution.run_id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              transition={{ delay: index * 0.05 }}
              className="text-sm text-gray-600"
            >
              Agent {execution.agent_id.slice(0, 8)} started
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

function ConnectionIndicator({ status }: { status: string }) {
  const colors = {
    connected: 'bg-green-500',
    connecting: 'bg-yellow-500',
    disconnected: 'bg-red-500',
    error: 'bg-red-500'
  };

  return (
    <div className="flex items-center gap-2">
      <div className={`w-2 h-2 rounded-full ${colors[status]} animate-pulse`} />
      <span className="text-xs text-gray-500 capitalize">{status}</span>
    </div>
  );
}
```

## Testing Requirements
- Unit tests for WebSocket manager
- Integration tests for pub/sub
- Load tests for concurrent connections
- Reconnection logic tests
- Message ordering tests

## Performance Targets
- Connection establishment: <500ms
- Message latency: <100ms
- Support 1000+ concurrent connections
- Message throughput: 10,000 msg/sec
- Reconnection time: <2 seconds

## Security Considerations
- JWT token validation on connection
- Rate limiting per connection
- Message size limits (max 1MB)
- Workspace isolation enforcement
- Prevent connection flooding