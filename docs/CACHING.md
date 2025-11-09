# Caching Layer Documentation

## Overview

The Shadower Analytics platform implements a comprehensive Redis-based caching system to improve performance and reduce database load for frequently accessed analytics data.

## Architecture

### Components

1. **RedisClient** (`backend/src/core/redis.py`)
   - Core Redis connection management
   - Automatic JSON/Pickle serialization
   - Production-safe pattern-based operations (SCAN instead of KEYS)

2. **CacheKeys** (`backend/src/services/cache/keys.py`)
   - Centralized key naming conventions
   - TTL constants for different data types
   - Pattern generators for batch operations

3. **CacheService** (`backend/src/services/cache/redis_cache.py`)
   - High-level caching operations
   - Cache warming strategies
   - Workspace/agent invalidation
   - Cache statistics

4. **Cache Decorator** (`backend/src/services/cache/decorator.py`)
   - Automatic function result caching
   - Cache invalidation helpers
   - Batch caching support

5. **Event Handlers** (`backend/src/services/events/handlers.py`)
   - Automatic cache invalidation on data changes
   - Event-driven cache management

6. **Scheduled Jobs** (`jobs/maintenance/cache_maintenance.py`)
   - Cache cleanup and maintenance
   - Health monitoring
   - Priority data warming

## Usage

### Backend Caching

#### Using the Cache Decorator

```python
from services.cache import cached, CacheKeys

@cached(
    key_func=lambda workspace_id, timeframe, **_:
        CacheKeys.executive_dashboard(workspace_id, timeframe),
    ttl=CacheKeys.TTL_LONG
)
async def get_executive_metrics(workspace_id: str, timeframe: str):
    # Expensive database query
    return await db.fetch_metrics(workspace_id, timeframe)
```

#### Using CacheService Directly

```python
from services.cache import CacheService
from core.redis import get_redis_client

redis_client = await get_redis_client()
cache_service = CacheService(redis_client)

# Get or compute pattern
async def compute_metrics():
    return await db.fetch_complex_metrics()

metrics = await cache_service.get_or_compute(
    key="metrics:workspace:123",
    compute_func=compute_metrics,
    ttl=CacheKeys.TTL_MEDIUM
)
```

#### Cache Invalidation

```python
# Invalidate workspace cache
await cache_service.invalidate_workspace("ws123")

# Invalidate agent cache
await cache_service.invalidate_agent("agent456")

# Invalidate by pattern
from services.cache import invalidate_pattern
await invalidate_pattern("exec:dashboard:*")
```

### Frontend Caching (React Query)

#### Using Custom Hooks

```typescript
import { useExecutiveDashboard } from '@/hooks/api/useExecutiveDashboard';

function ExecutiveDashboard() {
  const { data, isLoading, error } = useExecutiveDashboard(
    {
      workspaceId: 'ws123',
      timeframe: '7d',
    },
    {
      skipCache: false,  // Set to true to bypass cache
      refetchInterval: 60000,  // Optional: refetch every minute
    }
  );

  // ...
}
```

#### Cache Key Management

```typescript
import { queryKeys, queryClient } from '@/lib/react-query';

// Invalidate executive dashboard cache
queryClient.invalidateQueries({
  queryKey: queryKeys.executive('ws123', '7d')
});

// Prefetch data
queryClient.prefetchQuery({
  queryKey: queryKeys.kpis('ws123'),
  queryFn: () => apiClient.get('/api/v1/executive/kpis?workspace_id=ws123')
});
```

## Cache Key Naming Conventions

### Format
```
<prefix>:<type>:<identifier>:<timeframe|date>
```

### Examples
```
exec:dashboard:ws123:7d          # Executive dashboard for workspace, 7 days
agent:analytics:agent456:30d     # Agent analytics, 30 days
user:activity:user789:2024-01-15 # User activity for specific date
metrics:agg:runs:ws123:daily     # Daily aggregated run metrics
query:result:abc123def456        # Cached query result (MD5 hash)
```

### TTL Guidelines

| Data Type | TTL | Use Case |
|-----------|-----|----------|
| SHORT (1m) | Real-time data | Live metrics, active users |
| MEDIUM (5m) | Frequently changing | KPIs, user activity |
| LONG (30m) | Relatively stable | Executive dashboards, analytics |
| HOUR (1h) | Slow changing | Aggregated metrics, trends |
| DAY (24h) | Static/Historical | Reports, historical data |

## Cache Invalidation Strategy

### Event-Based Invalidation

Events that trigger automatic cache invalidation:

1. **Agent Run Completed**
   - Invalidates: Agent-specific cache, workspace metrics, top agents
   - Pattern: `agent:*:<agent_id>:*`, `exec:dashboard:<workspace_id>:*`

2. **User Activity**
   - Invalidates: User activity cache, DAU/WAU/MAU metrics
   - Pattern: `user:activity:<user_id>:*`, `metrics:users:active:*`

3. **Workspace Updated**
   - Invalidates: All workspace-related caches
   - Pattern: `exec:*:<workspace_id>:*`, `ws:*:<workspace_id>:*`

4. **Credit Transaction**
   - Invalidates: Credit metrics, executive dashboard
   - Pattern: `metrics:credits:<workspace_id>:*`

### Scheduled Invalidation

| Job | Schedule | Purpose |
|-----|----------|---------|
| Cache Cleanup | Daily 04:00 | Remove stale keys without TTL |
| Health Check | Every 15min | Monitor cache health metrics |
| Refresh Materialized | Hourly :30 | Refresh frequently accessed data |
| Warm Priority | Every 6h | Pre-populate high-priority caches |

## Performance Targets

### Goals
- Cache hit rate: **>80%**
- Cache operation latency: **<5ms**
- Cache warm-up time: **<30 seconds**
- Memory usage: **<500MB** for 10,000 keys

### Monitoring

Get cache statistics:

```python
from services.cache import CacheService

stats = await cache_service.get_cache_stats()
print(f"Hit rate: {stats['hit_rate_percent']}%")
print(f"Memory used: {stats['used_memory']}")
print(f"Evicted keys: {stats['evicted_keys']}")
```

## Configuration

### Environment Variables

```bash
# Redis connection
REDIS_URL=redis://localhost:6379/0

# Celery (for cache jobs)
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

### Redis Configuration

Key settings in `docker/redis/redis.conf`:

```conf
maxmemory 512mb                  # Maximum memory for cache
maxmemory-policy allkeys-lru     # Eviction policy
lazyfree-lazy-eviction yes       # Async eviction
hz 10                            # Expiration checks per second
```

## Testing

### Run Unit Tests

```bash
cd backend
pytest tests/unit/test_cache_redis.py -v
```

### Run Integration Tests

```bash
# Requires Redis to be running
docker-compose up -d redis

pytest tests/integration/test_cache_integration.py -v -m integration
```

### Performance Tests

```bash
pytest tests/integration/test_cache_integration.py::TestCachePerformance -v
```

## Best Practices

### DO

✅ Use cache keys from `CacheKeys` class for consistency
✅ Set appropriate TTLs based on data volatility
✅ Use `skip_cache` parameter for debugging
✅ Invalidate cache on data mutations
✅ Monitor cache hit rates regularly
✅ Use SCAN-based operations for pattern matching

### DON'T

❌ Don't cache sensitive unencrypted data
❌ Don't use `KEYS` command in production (use `flush_pattern` instead)
❌ Don't set infinite TTLs (always set expiration)
❌ Don't cache data larger than 1MB
❌ Don't ignore eviction warnings
❌ Don't hardcode cache keys (use `CacheKeys`)

## Troubleshooting

### Low Cache Hit Rate

**Symptoms:** Hit rate < 60%

**Solutions:**
1. Check if TTLs are too short
2. Verify cache warming is running
3. Review invalidation patterns (may be too aggressive)
4. Increase memory if evictions are high

### High Memory Usage

**Symptoms:** Memory usage near `maxmemory` limit

**Solutions:**
1. Review and reduce TTLs for less important data
2. Increase `maxmemory` in redis.conf
3. Check for keys without TTL (cache cleanup job)
4. Verify eviction policy is appropriate

### Cache Stampede

**Symptoms:** Multiple concurrent requests computing same data

**Solutions:**
1. Implement request coalescing
2. Use probabilistic early expiration
3. Pre-warm cache before expiration
4. Consider using Redis locks for expensive computations

## Security Considerations

1. **Access Control**
   - Use separate Redis databases for different environments
   - Set `requirepass` in production
   - Implement key namespacing

2. **Data Sensitivity**
   - Never cache PII without encryption
   - Use shorter TTLs for sensitive data
   - Implement cache access logging for audit

3. **Denial of Service**
   - Set `maxmemory` limits
   - Monitor for cache poisoning attempts
   - Rate limit cache invalidation endpoints

## Migration Guide

### Adding Caching to Existing Endpoints

1. Create a service method with `@cached` decorator:
```python
@cached(
    key_func=lambda workspace_id, **_: f"mymetric:{workspace_id}",
    ttl=CacheKeys.TTL_MEDIUM
)
async def get_my_metrics(workspace_id: str):
    return await db.fetch_my_metrics(workspace_id)
```

2. Update route to use cached service:
```python
@router.get("/my-metrics")
async def my_metrics(workspace_id: str, skip_cache: bool = False):
    return await get_my_metrics(workspace_id, skip_cache=skip_cache)
```

3. Add cache invalidation to related mutation endpoints:
```python
@router.post("/update-data")
async def update_data(workspace_id: str):
    # Update data
    await db.update(workspace_id)

    # Invalidate cache
    await cache_service.invalidate_workspace(workspace_id)
```

## Support

For issues or questions about the caching layer:
1. Check logs: `docker-compose logs redis`
2. Review cache stats: `GET /api/v1/cache/stats`
3. Run diagnostics: `pytest tests/integration/test_cache_integration.py`
