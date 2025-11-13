"""WebSocket module for real-time updates."""

from .manager import manager, ConnectionManager
from .events import broadcaster, EventBroadcaster
from .pubsub import redis_pubsub, RedisPubSub, init_redis_pubsub, shutdown_redis_pubsub
from .errors import WebSocketErrorCode, handle_ws_error, send_error_message
from .rate_limit import rate_limiter, WebSocketRateLimiter
from .realtime_metrics import RealtimeMetricsService

__all__ = [
    "manager",
    "ConnectionManager",
    "broadcaster",
    "EventBroadcaster",
    "redis_pubsub",
    "RedisPubSub",
    "init_redis_pubsub",
    "shutdown_redis_pubsub",
    "WebSocketErrorCode",
    "handle_ws_error",
    "send_error_message",
    "rate_limiter",
    "WebSocketRateLimiter",
    "RealtimeMetricsService",
]
