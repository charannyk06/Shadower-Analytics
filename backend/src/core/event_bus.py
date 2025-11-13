"""Event-driven architecture with Kafka-based event bus."""

from typing import Dict, List, Callable, Any, Optional, Awaitable
import asyncio
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import logging
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError

from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Event data structure."""
    type: str
    workspace_id: str
    data: Dict[str, Any]
    timestamp: datetime
    correlation_id: str
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "type": self.type,
            "workspace_id": self.workspace_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "user_id": self.user_id,
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary."""
        return cls(
            type=data["type"],
            workspace_id=data["workspace_id"],
            data=data["data"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            correlation_id=data["correlation_id"],
            user_id=data.get("user_id"),
            metadata=data.get("metadata")
        )


class EventTypes:
    """Standard event types for the platform."""

    # Agent events
    AGENT_EXECUTED = "agent.executed"
    AGENT_FAILED = "agent.failed"
    AGENT_CREATED = "agent.created"
    AGENT_UPDATED = "agent.updated"
    AGENT_DELETED = "agent.deleted"

    # User events
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"

    # Credit events
    CREDIT_CONSUMED = "credit.consumed"
    CREDIT_PURCHASED = "credit.purchased"
    CREDIT_REFUNDED = "credit.refunded"
    CREDIT_THRESHOLD_REACHED = "credit.threshold_reached"

    # Report events
    REPORT_GENERATED = "report.generated"
    REPORT_SCHEDULED = "report.scheduled"
    REPORT_FAILED = "report.failed"

    # Alert events
    ALERT_TRIGGERED = "alert.triggered"
    ALERT_RESOLVED = "alert.resolved"
    ALERT_ACKNOWLEDGED = "alert.acknowledged"

    # Workspace events
    WORKSPACE_CREATED = "workspace.created"
    WORKSPACE_UPDATED = "workspace.updated"
    WORKSPACE_DELETED = "workspace.deleted"

    # Integration events
    INTEGRATION_CONNECTED = "integration.connected"
    INTEGRATION_DISCONNECTED = "integration.disconnected"
    INTEGRATION_ERROR = "integration.error"

    # System events
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"
    SYSTEM_INFO = "system.info"


class EventBus:
    """Event bus implementation using Kafka for async event processing."""

    def __init__(self, kafka_brokers: Optional[str] = None):
        """Initialize event bus.

        Args:
            kafka_brokers: Comma-separated list of Kafka brokers
        """
        self.kafka_brokers = kafka_brokers or self._get_kafka_brokers()
        self.handlers: Dict[str, List[Callable[[Event], Awaitable[None]]]] = {}
        self.producer: Optional[AIOKafkaProducer] = None
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.consumer_task: Optional[asyncio.Task] = None
        self._running = False

    def _get_kafka_brokers(self) -> str:
        """Get Kafka brokers from settings or default."""
        # Try to get from environment or use default
        kafka_url = getattr(settings, "KAFKA_BROKERS", "localhost:9092")
        return kafka_url

    async def initialize(self):
        """Initialize Kafka connections."""
        logger.info(f"Initializing event bus with Kafka brokers: {self.kafka_brokers}")

        try:
            # Initialize producer
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.kafka_brokers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                compression_type="gzip",
                max_batch_size=16384,
                linger_ms=10,  # Wait up to 10ms to batch messages
                acks="all",  # Wait for all replicas
                retry_backoff_ms=100,
            )
            await self.producer.start()
            logger.info("Kafka producer started")

            # Initialize consumer
            self.consumer = AIOKafkaConsumer(
                'analytics-events',
                bootstrap_servers=self.kafka_brokers,
                group_id='analytics-group',
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=True,
                auto_commit_interval_ms=5000,
                session_timeout_ms=30000,
            )
            await self.consumer.start()
            logger.info("Kafka consumer started")

            self._running = True

        except KafkaError as e:
            logger.error(f"Failed to initialize Kafka: {e}")
            logger.warning("Event bus will operate in local-only mode")
            self.producer = None
            self.consumer = None

        except Exception as e:
            logger.error(f"Unexpected error initializing event bus: {e}")
            self.producer = None
            self.consumer = None

    def subscribe(self, event_type: str, handler: Callable[[Event], Awaitable[None]]):
        """Subscribe to event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Async function that handles the event

        Example:
            async def handle_agent_executed(event: Event):
                logger.info(f"Agent executed: {event.data}")

            event_bus.subscribe(EventTypes.AGENT_EXECUTED, handle_agent_executed)
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []

        self.handlers[event_type].append(handler)
        logger.info(f"Subscribed handler to event type: {event_type}")

    def unsubscribe(self, event_type: str, handler: Callable[[Event], Awaitable[None]]):
        """Unsubscribe from event type.

        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler function to remove
        """
        if event_type in self.handlers:
            try:
                self.handlers[event_type].remove(handler)
                logger.info(f"Unsubscribed handler from event type: {event_type}")
            except ValueError:
                logger.warning(f"Handler not found for event type: {event_type}")

    async def publish(self, event: Event):
        """Publish event to bus.

        Args:
            event: Event to publish

        Example:
            event = Event(
                type=EventTypes.AGENT_EXECUTED,
                workspace_id="ws_123",
                data={"agent_id": "agent_456", "duration": 1.5},
                timestamp=datetime.utcnow(),
                correlation_id="corr_789"
            )
            await event_bus.publish(event)
        """
        # Publish to Kafka if available
        if self.producer:
            try:
                await self.producer.send(
                    'analytics-events',
                    value=event.to_dict()
                )
                logger.debug(f"Published event to Kafka: {event.type}")
            except Exception as e:
                logger.error(f"Failed to publish event to Kafka: {e}")
                # Fall through to local handlers

        # Always execute local handlers immediately
        await self._execute_local_handlers(event)

    async def _execute_local_handlers(self, event: Event):
        """Execute local event handlers.

        Args:
            event: Event to process
        """
        if event.type in self.handlers:
            handlers = self.handlers[event.type]
            logger.debug(f"Executing {len(handlers)} local handlers for {event.type}")

            # Execute all handlers concurrently
            tasks = [handler(event) for handler in handlers]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Log any handler errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Handler {i} failed for {event.type}: {result}")

    async def start_consuming(self):
        """Start consuming events from Kafka.

        This should be run in a background task.

        Example:
            event_bus.consumer_task = asyncio.create_task(event_bus.start_consuming())
        """
        if not self.consumer:
            logger.warning("Consumer not initialized, cannot start consuming")
            return

        logger.info("Starting event consumption from Kafka...")

        try:
            async for msg in self.consumer:
                if not self._running:
                    break

                try:
                    event_data = msg.value
                    event = Event.from_dict(event_data)

                    logger.debug(f"Consumed event from Kafka: {event.type}")

                    # Execute handlers
                    await self._execute_local_handlers(event)

                except Exception as e:
                    logger.error(f"Error processing consumed event: {e}")
                    # Continue processing other events

        except asyncio.CancelledError:
            logger.info("Event consumption cancelled")
            raise

        except Exception as e:
            logger.error(f"Error in event consumption loop: {e}")

        finally:
            logger.info("Event consumption stopped")

    async def close(self):
        """Close event bus connections."""
        logger.info("Closing event bus...")

        self._running = False

        # Cancel consumer task
        if self.consumer_task:
            self.consumer_task.cancel()
            try:
                await self.consumer_task
            except asyncio.CancelledError:
                pass

        # Close consumer
        if self.consumer:
            try:
                await self.consumer.stop()
                logger.info("Kafka consumer stopped")
            except Exception as e:
                logger.error(f"Error stopping consumer: {e}")

        # Close producer
        if self.producer:
            try:
                await self.producer.stop()
                logger.info("Kafka producer stopped")
            except Exception as e:
                logger.error(f"Error stopping producer: {e}")

        logger.info("Event bus closed")

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "kafka_connected": self.producer is not None and self.consumer is not None,
            "handlers_count": {
                event_type: len(handlers)
                for event_type, handlers in self.handlers.items()
            },
            "total_handlers": sum(len(handlers) for handlers in self.handlers.values()),
            "event_types": list(self.handlers.keys()),
            "running": self._running,
        }


# Singleton instance
event_bus = EventBus()


async def get_event_bus() -> EventBus:
    """Get event bus instance.

    Returns:
        EventBus: Singleton event bus instance
    """
    if not event_bus.producer:
        await event_bus.initialize()
    return event_bus
