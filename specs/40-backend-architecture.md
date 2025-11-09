# Specification: Backend Architecture

## Overview
Complete backend architecture specification for the Shadower Analytics platform, defining microservices, API structure, data flow, and system design.

## Technical Requirements

### Microservices Architecture

#### Service Decomposition
```yaml
# architecture/services.yml
services:
  analytics-api:
    description: Main analytics API service
    port: 8000
    dependencies:
      - postgres
      - redis
      - message-queue
    responsibilities:
      - API gateway
      - Request routing
      - Authentication
      - Rate limiting
  
  metrics-processor:
    description: Real-time metrics processing
    port: 8001
    dependencies:
      - kafka
      - redis
      - timeseries-db
    responsibilities:
      - Event streaming
      - Metrics aggregation
      - Real-time calculations
  
  report-generator:
    description: Report generation service
    port: 8002
    dependencies:
      - postgres
      - s3
      - pdf-renderer
    responsibilities:
      - Report scheduling
      - Template rendering
      - Export generation
  
  notification-service:
    description: Notification and alert service
    port: 8003
    dependencies:
      - redis
      - smtp
      - webhook-queue
    responsibilities:
      - Alert processing
      - Email sending
      - Webhook delivery
  
  data-aggregator:
    description: Background data aggregation
    port: 8004
    dependencies:
      - postgres
      - redis
      - scheduler
    responsibilities:
      - Materialized view refresh
      - Data rollups
      - Archive management
```

### API Architecture

#### FastAPI Application Structure
```python
# backend/app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.redis import init_redis, close_redis
from app.middleware import (
    AuthenticationMiddleware,
    RateLimitMiddleware,
    LoggingMiddleware,
    MetricsMiddleware
)
from app.routers import (
    analytics,
    dashboard,
    reports,
    webhooks,
    admin
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    await init_db()
    await init_redis()
    yield
    # Shutdown
    await close_db()
    await close_redis()

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Shadower Analytics API",
        description="Analytics and monitoring for Shadower platform",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.ENABLE_DOCS else None,
        redoc_url="/api/redoc" if settings.ENABLE_DOCS else None
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Custom middleware
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthenticationMiddleware)
    
    # Include routers
    app.include_router(analytics.router, prefix="/api/v1/analytics")
    app.include_router(dashboard.router, prefix="/api/v1/dashboard")
    app.include_router(reports.router, prefix="/api/v1/reports")
    app.include_router(webhooks.router, prefix="/api/v1/webhooks")
    app.include_router(admin.router, prefix="/api/v1/admin")
    
    return app

if __name__ == "__main__":
    app = create_app()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.PORT,
        workers=settings.WORKERS,
        log_config=settings.LOGGING_CONFIG
    )
```

### Database Architecture

#### Database Service Layer
```python
# backend/app/services/database_service.py
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import asyncpg
from contextlib import asynccontextmanager

class DatabaseService:
    def __init__(self):
        self.engine = None
        self.async_session = None
        self.pool = None
    
    async def initialize(self):
        """Initialize database connections"""
        # Create async engine
        self.engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            poolclass=NullPool,
            connect_args={
                "server_settings": {"jit": "off"},
                "command_timeout": 60,
                "pool_size": 20,
                "max_overflow": 10
            }
        )
        
        # Create session factory
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create connection pool for raw queries
        self.pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=10,
            max_size=20,
            max_queries=50000,
            max_inactive_connection_lifetime=300
        )
    
    @asynccontextmanager
    async def get_session(self):
        """Get database session"""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def execute_query(
        self,
        query: str,
        params: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Execute raw SQL query"""
        async with self.pool.acquire() as connection:
            rows = await connection.fetch(query, *(params or {}).values())
            return [dict(row) for row in rows]
    
    async def execute_batch(
        self,
        queries: List[tuple[str, Dict]]
    ) -> List[Any]:
        """Execute multiple queries in transaction"""
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                results = []
                for query, params in queries:
                    result = await connection.fetch(query, *params.values())
                    results.append(result)
                return results

# Singleton instance
db_service = DatabaseService()
```

### Event-Driven Architecture

#### Event Bus Implementation
```python
# backend/app/core/event_bus.py
from typing import Dict, List, Callable, Any
import asyncio
from dataclasses import dataclass
from datetime import datetime
import json
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

@dataclass
class Event:
    type: str
    workspace_id: str
    data: Dict[str, Any]
    timestamp: datetime
    correlation_id: str

class EventBus:
    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = {}
        self.producer: Optional[AIOKafkaProducer] = None
        self.consumer: Optional[AIOKafkaConsumer] = None
    
    async def initialize(self):
        """Initialize Kafka connections"""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BROKERS,
            value_serializer=lambda v: json.dumps(v).encode()
        )
        await self.producer.start()
        
        self.consumer = AIOKafkaConsumer(
            'analytics-events',
            bootstrap_servers=settings.KAFKA_BROKERS,
            group_id='analytics-group',
            value_deserializer=lambda m: json.loads(m.decode())
        )
        await self.consumer.start()
    
    def subscribe(self, event_type: str, handler: Callable):
        """Subscribe to event type"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    async def publish(self, event: Event):
        """Publish event to bus"""
        await self.producer.send(
            'analytics-events',
            value={
                'type': event.type,
                'workspace_id': event.workspace_id,
                'data': event.data,
                'timestamp': event.timestamp.isoformat(),
                'correlation_id': event.correlation_id
            }
        )
        
        # Local handlers
        if event.type in self.handlers:
            for handler in self.handlers[event.type]:
                asyncio.create_task(handler(event))
    
    async def start_consuming(self):
        """Start consuming events"""
        async for msg in self.consumer:
            event_data = msg.value
            event = Event(
                type=event_data['type'],
                workspace_id=event_data['workspace_id'],
                data=event_data['data'],
                timestamp=datetime.fromisoformat(event_data['timestamp']),
                correlation_id=event_data['correlation_id']
            )
            
            if event.type in self.handlers:
                for handler in self.handlers[event.type]:
                    asyncio.create_task(handler(event))

# Event types
class EventTypes:
    AGENT_EXECUTED = "agent.executed"
    AGENT_FAILED = "agent.failed"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    CREDIT_CONSUMED = "credit.consumed"
    REPORT_GENERATED = "report.generated"
    ALERT_TRIGGERED = "alert.triggered"
    WORKSPACE_CREATED = "workspace.created"
    INTEGRATION_CONNECTED = "integration.connected"
```

### Cache Architecture

#### Multi-Layer Cache Strategy
```python
# backend/app/services/cache_service.py
from typing import Optional, Any, Dict
import redis.asyncio as redis
import pickle
import hashlib
import json
from datetime import timedelta

class CacheService:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.local_cache: Dict[str, Any] = {}
    
    async def initialize(self):
        """Initialize cache connections"""
        self.redis_client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=False,
            max_connections=50
        )
    
    def _generate_key(self, prefix: str, params: Dict) -> str:
        """Generate cache key from parameters"""
        param_str = json.dumps(params, sort_keys=True)
        hash_str = hashlib.md5(param_str.encode()).hexdigest()
        return f"{prefix}:{hash_str}"
    
    async def get(
        self,
        key: str,
        default: Optional[Any] = None
    ) -> Optional[Any]:
        """Get value from cache"""
        # Check local cache first
        if key in self.local_cache:
            return self.local_cache[key]
        
        # Check Redis
        value = await self.redis_client.get(key)
        if value:
            deserialized = pickle.loads(value)
            # Update local cache
            self.local_cache[key] = deserialized
            return deserialized
        
        return default
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = 3600
    ):
        """Set value in cache"""
        serialized = pickle.dumps(value)
        
        # Set in Redis
        if ttl:
            await self.redis_client.setex(key, ttl, serialized)
        else:
            await self.redis_client.set(key, serialized)
        
        # Update local cache
        self.local_cache[key] = value
    
    async def delete(self, pattern: str):
        """Delete keys matching pattern"""
        cursor = 0
        while True:
            cursor, keys = await self.redis_client.scan(
                cursor,
                match=pattern,
                count=100
            )
            
            if keys:
                await self.redis_client.delete(*keys)
                # Remove from local cache
                for key in keys:
                    self.local_cache.pop(key.decode(), None)
            
            if cursor == 0:
                break
    
    async def increment(
        self,
        key: str,
        amount: int = 1,
        ttl: Optional[int] = None
    ) -> int:
        """Increment counter"""
        value = await self.redis_client.incrby(key, amount)
        if ttl:
            await self.redis_client.expire(key, ttl)
        return value

# Cache decorator
def cached(
    prefix: str,
    ttl: int = 3600,
    key_params: Optional[List[str]] = None
):
    """Decorator for caching function results"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_params = {}
            if key_params:
                for param in key_params:
                    if param in kwargs:
                        cache_params[param] = kwargs[param]
            
            cache_key = cache_service._generate_key(prefix, cache_params)
            
            # Check cache
            cached_value = await cache_service.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            await cache_service.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator
```

### Background Task Processing

#### Celery Task Configuration
```python
# backend/app/tasks/celery_app.py
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    'analytics',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['app.tasks.analytics', 'app.tasks.reports', 'app.tasks.alerts']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'refresh-materialized-views': {
        'task': 'app.tasks.analytics.refresh_materialized_views',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    'calculate-daily-metrics': {
        'task': 'app.tasks.analytics.calculate_daily_metrics',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
    'generate-scheduled-reports': {
        'task': 'app.tasks.reports.generate_scheduled_reports',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    'check-alert-conditions': {
        'task': 'app.tasks.alerts.check_alert_conditions',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'cleanup-old-data': {
        'task': 'app.tasks.analytics.cleanup_old_data',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}
```

### Service Communication

#### gRPC Service Definition
```protobuf
// backend/proto/analytics.proto
syntax = "proto3";

package analytics;

service AnalyticsService {
    rpc GetMetrics(MetricsRequest) returns (MetricsResponse);
    rpc StreamMetrics(StreamRequest) returns (stream MetricUpdate);
    rpc CalculateAggregates(AggregateRequest) returns (AggregateResponse);
}

message MetricsRequest {
    string workspace_id = 1;
    string metric_type = 2;
    int64 start_time = 3;
    int64 end_time = 4;
    repeated string filters = 5;
}

message MetricsResponse {
    repeated Metric metrics = 1;
    int64 total_count = 2;
}

message Metric {
    string id = 1;
    string type = 2;
    double value = 3;
    int64 timestamp = 4;
    map<string, string> tags = 5;
}

message StreamRequest {
    string workspace_id = 1;
    repeated string metric_types = 2;
}

message MetricUpdate {
    Metric metric = 1;
    string event_type = 2;
}
```

## Implementation Priority
1. Core API structure
2. Database service layer
3. Cache implementation
4. Event bus setup
5. Background task processing

## Success Metrics
- API response time < 200ms (p95)
- Service uptime > 99.9%
- Zero message loss in event bus
- Cache hit rate > 70%