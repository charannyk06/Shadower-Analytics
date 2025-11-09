"""Redis pub/sub for multi-instance WebSocket scaling."""

import redis.asyncio as redis
import json
import asyncio
import logging
from typing import Dict, Set, Optional

from .manager import manager

logger = logging.getLogger(__name__)


class RedisPubSub:
    """Redis pub/sub for multi-instance WebSocket scaling."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        self.pubsub = None
        self.subscriptions: Dict[str, str] = {}
        self.running = False
        self._listen_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start listening to Redis pub/sub."""
        if self.running:
            logger.warning("RedisPubSub already running")
            return

        try:
            self.redis = redis.from_url(
                self.redis_url, decode_responses=True, encoding="utf-8"
            )
            self.pubsub = self.redis.pubsub()
            self.running = True

            # Start listening task
            self._listen_task = asyncio.create_task(self._listen())
            logger.info("RedisPubSub started successfully")

        except Exception as e:
            logger.error(f"Failed to start RedisPubSub: {e}")
            self.running = False
            raise

    async def stop(self):
        """Stop listening."""
        if not self.running:
            return

        self.running = False

        # Cancel listen task
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

        # Unsubscribe and close
        if self.pubsub:
            try:
                await self.pubsub.unsubscribe()
                await self.pubsub.close()
            except Exception as e:
                logger.error(f"Error closing pubsub: {e}")

        if self.redis:
            try:
                await self.redis.close()
            except Exception as e:
                logger.error(f"Error closing redis connection: {e}")

        logger.info("RedisPubSub stopped")

    async def publish(self, channel: str, message: Dict):
        """Publish message to Redis channel."""
        if not self.redis:
            logger.error("Redis not initialized")
            return

        try:
            await self.redis.publish(channel, json.dumps(message))
            logger.debug(f"Published message to channel {channel}")
        except Exception as e:
            logger.error(f"Error publishing to Redis: {e}")

    async def subscribe_workspace(self, workspace_id: str):
        """Subscribe to workspace channel."""
        if not self.pubsub:
            logger.error("PubSub not initialized")
            return

        channel = f"workspace:{workspace_id}"
        try:
            await self.pubsub.subscribe(channel)
            self.subscriptions[channel] = workspace_id
            logger.info(f"Subscribed to {channel}")
        except Exception as e:
            logger.error(f"Error subscribing to {channel}: {e}")

    async def unsubscribe_workspace(self, workspace_id: str):
        """Unsubscribe from workspace channel."""
        if not self.pubsub:
            return

        channel = f"workspace:{workspace_id}"
        try:
            await self.pubsub.unsubscribe(channel)
            self.subscriptions.pop(channel, None)
            logger.info(f"Unsubscribed from {channel}")
        except Exception as e:
            logger.error(f"Error unsubscribing from {channel}: {e}")

    async def _listen(self):
        """Listen for Redis pub/sub messages."""
        if not self.pubsub:
            logger.error("PubSub not initialized")
            return

        logger.info("Starting to listen for Redis pub/sub messages")

        while self.running:
            try:
                message = await self.pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )

                if message and message["type"] == "message":
                    await self._handle_message(message)

            except asyncio.CancelledError:
                logger.info("Listen task cancelled")
                break
            except Exception as e:
                logger.error(f"Redis pub/sub error: {e}")
                await asyncio.sleep(5)

    async def _handle_message(self, message: Dict):
        """Handle pub/sub message."""
        try:
            channel = message["channel"]
            data = json.loads(message["data"])

            # Extract workspace_id from channel
            if channel.startswith("workspace:"):
                workspace_id = channel.split(":", 1)[1]

                # Broadcast to local WebSocket connections
                await manager.broadcast_to_workspace(workspace_id, data)
                logger.debug(
                    f"Relayed message from Redis to workspace {workspace_id}"
                )

        except Exception as e:
            logger.error(f"Error handling pub/sub message: {e}")


# Global instance - will be initialized in main.py
redis_pubsub: Optional[RedisPubSub] = None


async def init_redis_pubsub(redis_url: str):
    """Initialize Redis pub/sub."""
    global redis_pubsub
    redis_pubsub = RedisPubSub(redis_url)
    await redis_pubsub.start()
    return redis_pubsub


async def shutdown_redis_pubsub():
    """Shutdown Redis pub/sub."""
    global redis_pubsub
    if redis_pubsub:
        await redis_pubsub.stop()
