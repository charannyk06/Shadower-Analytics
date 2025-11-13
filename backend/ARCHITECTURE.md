# Backend Architecture Implementation

## Overview

This document describes the implementation of the complete backend architecture for Shadower Analytics, following the microservices architecture pattern with event-driven design.

## Architecture Components

### 1. API Gateway (`src/api/main.py`)

The main FastAPI application with enhanced lifespan management:

```python
from src.api.main import app

# Run with:
# uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Features:**
- Lifespan context manager for startup/shutdown
- Middleware stack (CORS, GZip, Security, Logging, Rate Limiting)
- Automatic resource cleanup
- Redis and database connection management

### 2. Database Service Layer (`src/services/database_service.py`)

Advanced database service with connection pooling:

```python
from src.services.database_service import get_db_service

# Usage
db_service = await get_db_service()

# Execute raw SQL
results = await db_service.execute_query(
    "SELECT * FROM users WHERE workspace_id = $1",
    params={"workspace_id": "ws_123"}
)

# Batch operations
await db_service.execute_batch([
    ("INSERT INTO logs (user_id, action) VALUES ($1, $2)", {"user_id": "1", "action": "login"}),
    ("INSERT INTO logs (user_id, action) VALUES ($1, $2)", {"user_id": "2", "action": "logout"}),
])
```

**Features:**
- AsyncPG connection pooling (10-20 connections)
- SQLAlchemy session management
- Raw query support
- Batch operations
- Transaction management
- Health checks

### 3. Event Bus (`src/core/event_bus.py`)

Event-driven architecture using Kafka:

```python
from src.core.event_bus import get_event_bus, Event, EventTypes
from datetime import datetime
import uuid

# Get event bus
event_bus = await get_event_bus()

# Publish event
event = Event(
    type=EventTypes.AGENT_EXECUTED,
    workspace_id="ws_123",
    data={"agent_id": "agent_456", "duration": 1.5},
    timestamp=datetime.utcnow(),
    correlation_id=str(uuid.uuid4())
)
await event_bus.publish(event)

# Subscribe to events
async def handle_agent_executed(event: Event):
    print(f"Agent executed: {event.data}")

event_bus.subscribe(EventTypes.AGENT_EXECUTED, handle_agent_executed)
```

**Features:**
- Kafka-based event streaming
- Local handler execution
- Event types enumeration
- Pub/sub pattern
- Graceful degradation (works without Kafka)
- Asynchronous processing

### 4. Multi-Layer Cache (`src/services/cache/enhanced_cache.py`)

Enhanced caching with local memory and Redis:

```python
from src.services.cache.enhanced_cache import get_cache_service, cached

# Get cache service
cache_service = await get_cache_service()

# Manual caching
await cache_service.set("user:123", user_data, ttl=3600)
user_data = await cache_service.get("user:123")

# Using decorator
@cached(prefix="metrics", ttl=300, key_params=["workspace_id", "metric_type"])
async def get_metrics(workspace_id: str, metric_type: str):
    # Expensive computation
    return compute_metrics(workspace_id, metric_type)
```

**Features:**
- Two-tier caching (local + Redis)
- Automatic cache key generation
- Decorator for easy integration
- Cache statistics
- TTL-based expiration
- Pattern-based invalidation

### 5. Background Tasks (`src/celery_app.py`)

Celery for asynchronous task processing:

```bash
# Start Celery worker
celery -A src.celery_app worker --loglevel=info --queue=default,aggregation,alerts

# Start Celery beat (scheduler)
celery -A src.celery_app beat --loglevel=info

# Monitor with Flower
celery -A src.celery_app flower --port=5555
```

**Scheduled Tasks:**
- Hourly/daily/weekly rollups
- Materialized view refresh (every 15 min)
- Alert evaluation (every 5 min)
- Report generation (every 30 min)
- Data cleanup (daily at 3 AM)
- Health checks (every 5 min)

### 6. gRPC Services (`proto/analytics.proto`)

High-performance inter-service communication:

```bash
# Generate Python code
python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./src/grpc_generated \
    --grpc_python_out=./src/grpc_generated \
    ./proto/analytics.proto
```

**Services:**
- GetMetrics: Retrieve metrics with filtering
- StreamMetrics: Real-time metric streaming
- CalculateAggregates: Aggregate calculations
- GetWorkspaceSummary: Workspace analytics
- GetAgentPerformance: Agent performance metrics

## Integration Example

Complete example integrating all components:

```python
from fastapi import FastAPI, Depends
from src.services.database_service import get_db_service
from src.core.event_bus import get_event_bus, Event, EventTypes
from src.services.cache.enhanced_cache import cached
from datetime import datetime
import uuid

@app.get("/api/v1/metrics/{workspace_id}")
@cached(prefix="workspace_metrics", ttl=300, key_params=["workspace_id"])
async def get_workspace_metrics(workspace_id: str):
    """Get workspace metrics with caching and event publishing."""

    # Get database service
    db_service = await get_db_service()

    # Query metrics
    metrics = await db_service.execute_query(
        """
        SELECT metric_type, value, timestamp
        FROM metrics
        WHERE workspace_id = $1
        ORDER BY timestamp DESC
        LIMIT 100
        """,
        params={"workspace_id": workspace_id}
    )

    # Publish event
    event_bus = await get_event_bus()
    await event_bus.publish(Event(
        type=EventTypes.SYSTEM_INFO,
        workspace_id=workspace_id,
        data={"action": "metrics_accessed", "count": len(metrics)},
        timestamp=datetime.utcnow(),
        correlation_id=str(uuid.uuid4())
    ))

    return {"workspace_id": workspace_id, "metrics": metrics}
```

## Performance Targets

| Metric | Target | Implementation |
|--------|--------|----------------|
| API Response Time (p95) | < 200ms | Multi-layer caching, connection pooling |
| Service Uptime | > 99.9% | Health checks, auto-restart, monitoring |
| Event Bus Message Loss | 0% | Kafka persistence, acknowledgments |
| Cache Hit Rate | > 70% | Two-tier cache, smart TTL |
| Database Connections | 20-50 | AsyncPG pool, connection reuse |
| Concurrent Requests | 10,000+ | Async I/O, worker processes |

## Deployment

### Docker Compose (Development)

```yaml
version: '3.8'
services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/analytics
      - REDIS_URL=redis://redis:6379
      - KAFKA_BROKERS=kafka:9092
    depends_on:
      - postgres
      - redis
      - kafka

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: analytics
      POSTGRES_PASSWORD: password

  redis:
    image: redis:7-alpine

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    environment:
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181

  celery-worker:
    build: ./backend
    command: celery -A src.celery_app worker --loglevel=info
    depends_on:
      - redis
      - postgres

  celery-beat:
    build: ./backend
    command: celery -A src.celery_app beat --loglevel=info
    depends_on:
      - redis
```

### Production Deployment

1. **Build Docker image:**
```bash
docker build -t shadower-analytics:latest .
```

2. **Deploy to Kubernetes:**
```bash
kubectl apply -f k8s/
```

3. **Configure environment variables:**
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `KAFKA_BROKERS`: Kafka broker addresses
- `CELERY_BROKER_URL`: Celery broker (Redis/RabbitMQ)
- `JWT_SECRET_KEY`: Strong secret for JWT signing

## Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Detailed health with services
curl http://localhost:8000/health/detailed
```

### Metrics

- **Prometheus**: `http://localhost:8000/metrics`
- **Flower (Celery)**: `http://localhost:5555`
- **Cache Stats**: Available via API endpoint

### Logging

Structured JSON logging with correlation IDs for request tracing.

## Security

1. **JWT Authentication**: All endpoints require valid JWT tokens
2. **Rate Limiting**: Per-workspace rate limits
3. **CORS**: Configured allowed origins
4. **Security Headers**: X-Frame-Options, CSP, etc.
5. **Connection Security**: TLS for production
6. **Data Encryption**: At rest and in transit

## Troubleshooting

### Database Connection Issues

```python
# Check pool stats
db_service = await get_db_service()
stats = await db_service.get_pool_stats()
print(stats)

# Health check
healthy = await db_service.health_check()
```

### Cache Not Working

```python
# Check cache stats
cache_service = await get_cache_service()
stats = cache_service.get_stats()
print(stats)
```

### Event Bus Issues

```python
# Check event bus stats
event_bus = await get_event_bus()
stats = event_bus.get_stats()
print(stats)
```

## References

- [Architecture Documentation](./architecture/README.md)
- [Service Definitions](./architecture/services.yml)
- [gRPC Documentation](./proto/README.md)
- [API Documentation](./docs/api.md)

## Next Steps

1. Implement service discovery (Consul/etcd)
2. Add distributed tracing (Jaeger)
3. Implement circuit breakers
4. Add API gateway rate limiting per user
5. Implement request/response compression
6. Add GraphQL support for flexible queries
7. Implement WebSocket for real-time updates
8. Add multi-region support
