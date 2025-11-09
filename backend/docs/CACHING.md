# Redis Caching Layer - Implementation Guide

## Overview

This document describes the Redis-based caching layer implementation for Shadower Analytics. The caching layer provides high-performance data access with proper security, monitoring, and production-ready features.

## Architecture

### Components

1. **RedisClient** (`src/core/redis.py`)
   - Connection management with retry logic
   - Exponential backoff for connection failures
   - Health checking and reconnection

2. **CacheService** (`src/services/cache/redis_cache.py`)
   - High-level cache operations (get, set, delete, exists)
   - Input validation for cache keys
   - Pattern-based cache invalidation using SCAN

3. **Cache Invalidation** (`src/services/cache/invalidation.py`)
   - Event-driven invalidation strategies
   - Production-safe SCAN-based operations
   - Metric-specific, user-specific, and agent-specific invalidation

4. **Cache Metrics** (`src/services/cache/metrics.py`)
   - Prometheus metrics for monitoring
   - Hit/miss rates, error tracking, latency monitoring
   - Cache size and invalidation metrics

## Features

### Security

#### Redis Authentication
- **Password protection enabled by default**
- Development password: `shadower_redis_dev_password_change_in_production`
- **CRITICAL**: Change password in production using environment variable
- Generate strong password: `openssl rand -base64 32`

#### Input Validation
- Cache keys validated for:
  - Maximum length: 256 characters
  - Allowed characters: alphanumeric, `:`, `_`, `-`, `.`
  - Non-empty validation
- Prevents injection attacks and malformed keys

#### Network Security
- Development: Bind to `0.0.0.0` (for Docker networking)
- **Production**: Bind to `127.0.0.1` (localhost only)
- Protected mode enabled
- Configurable dangerous command renaming

### Reliability

#### Connection Retry Logic
- Automatic retry with exponential backoff
- Default: 5 retry attempts
- Backoff sequence: 2s, 4s, 8s, 16s, 32s
- Graceful degradation on failure

#### Production-Safe Operations
- **SCAN instead of KEYS** for pattern matching
- Prevents Redis blocking on large datasets
- Cursor-based iteration with configurable batch size

#### Race Condition Documentation
The SCAN-based invalidation has a known race condition:
- Keys created during SCAN iteration might be missed
- This is **acceptable** for cache invalidation use cases
- Cache will be repopulated on next request

### Monitoring

#### Prometheus Metrics

**Cache Operations:**
- `cache_hits_total` - Total cache hits by operation and key pattern
- `cache_misses_total` - Total cache misses
- `cache_errors_total` - Errors by operation and error type
- `cache_invalidations_total` - Invalidation events by pattern

**Performance:**
- `cache_operation_duration_seconds` - Operation latency histogram
  - Buckets: 1ms, 5ms, 10ms, 25ms, 50ms, 75ms, 100ms, 250ms, 500ms, 750ms, 1s

**Size:**
- `cache_keys_total` - Current number of cached keys

#### Metrics Endpoint
Access metrics at: `GET /api/v1/metrics`

Format: Prometheus-compatible format for scraping

### Configuration

#### Redis Configuration (`docker/redis/redis.conf`)

**Memory:**
```conf
maxmemory 512mb
maxmemory-policy allkeys-lru
maxmemory-samples 5
```

**Memory Optimization:**
```conf
lazyfree-lazy-eviction yes
lazyfree-lazy-expire yes
lazyfree-lazy-server-del yes
```

**Security:**
```conf
requirepass shadower_redis_dev_password_change_in_production
protected-mode yes
```

**Monitoring:**
```conf
slowlog-log-slower-than 10000
slowlog-max-len 128
notify-keyspace-events "Ex"
```

#### Application Configuration (`src/core/config.py`)

```python
REDIS_URL = "redis://:password@localhost:6379/0"
REDIS_PASSWORD = "shadower_redis_dev_password_change_in_production"
```

**Environment Variables (.env):**
```bash
REDIS_URL=redis://:your_password@localhost:6379/0
REDIS_PASSWORD=your_password
```

### TTL Strategy

Time-to-live values based on data freshness requirements:

```python
# Timeframe to TTL mapping
TIMEFRAME_TTL_MAP = {
    "24h": 300,      # 5 minutes
    "7d": 1800,      # 30 minutes
    "1w": 1800,      # 30 minutes
    "30d": 3600,     # 1 hour
    "1m": 3600,      # 1 hour
    "90d": 3600,     # 1 hour
    "3m": 3600,      # 1 hour
    "6m": 86400,     # 24 hours
    "1y": 86400,     # 24 hours
    "all": 86400,    # 24 hours
}
```

## Usage

### Basic Cache Operations

```python
from src.services.cache.redis_cache import CacheService
from src.core.redis import get_redis_client

# Initialize
redis = await get_redis_client()
cache = CacheService(redis)

# Get
value = await cache.get("user:123:profile")

# Set with TTL
await cache.set("user:123:profile", user_data, ttl=3600)

# Delete
await cache.delete("user:123:profile")

# Check existence
exists = await cache.exists("user:123:profile")

# Clear pattern
await cache.clear_pattern("user:123:*")
```

### Cache Invalidation

```python
from src.services.cache.invalidation import (
    invalidate_metric_cache,
    invalidate_user_cache,
    invalidate_agent_cache,
)

# Invalidate by metric type
await invalidate_metric_cache(redis, "cpu")

# Invalidate by user
await invalidate_user_cache(redis, "user_123")

# Invalidate by agent
await invalidate_agent_cache(redis, "agent_456")
```

### Key Naming Conventions

Use colon-separated hierarchical keys:

```
{entity}:{id}:{type}:{timeframe}
```

**Examples:**
```
metric:cpu:user:123:30d
user:123:profile
agent:456:stats:7d
workspace:789:metrics:all
```

## Best Practices

### 1. Key Design
- Use hierarchical naming with colons
- Include entity type, ID, and timeframe
- Keep keys under 256 characters
- Use only allowed characters: `a-zA-Z0-9:_-.`

### 2. TTL Selection
- Short data (< 1 day): 5-30 minutes
- Medium data (1 week): 30 minutes - 1 hour
- Long data (months): 1-24 hours
- Never set infinite TTL

### 3. Error Handling
- Cache failures should not break application
- Log cache errors but continue execution
- Return `None` on cache miss or error
- Track errors in Prometheus metrics

### 4. Invalidation
- Invalidate on data mutations (create, update, delete)
- Use pattern-based invalidation for related keys
- Prefer specific invalidation over broad patterns
- Monitor invalidation frequency

### 5. Security
- Always use authentication in production
- Bind to `127.0.0.1` in production
- Rotate passwords regularly
- Rename dangerous commands
- Monitor unauthorized access attempts

## Monitoring & Alerts

### Recommended Alerts

**Cache Hit Rate:**
```
Alert if: cache_hits / (cache_hits + cache_misses) < 0.7
Action: Review cache strategy and TTL values
```

**Cache Errors:**
```
Alert if: rate(cache_errors_total[5m]) > 10
Action: Check Redis health and connectivity
```

**High Latency:**
```
Alert if: cache_operation_duration_seconds{quantile="0.99"} > 0.1
Action: Check Redis performance and network
```

**Memory Usage:**
```
Alert if: redis_memory_used_bytes > 450MB (90% of 512MB)
Action: Increase memory limit or review eviction policy
```

### Grafana Dashboards

Recommended metrics to visualize:
1. Cache hit/miss rates over time
2. Operation latency (P50, P95, P99)
3. Error rates by type
4. Memory usage trend
5. Invalidation frequency
6. Active connections

## Troubleshooting

### Connection Failures

**Symptom:** Application can't connect to Redis

**Solutions:**
1. Check Redis is running: `docker ps | grep redis`
2. Verify password matches in config and Redis
3. Check network connectivity
4. Review Redis logs for errors
5. Verify connection retry attempts in application logs

### High Error Rate

**Symptom:** Increasing `cache_errors_total`

**Solutions:**
1. Check Redis health: `redis-cli ping`
2. Review slow query log
3. Check memory usage
4. Verify key validation errors
5. Monitor network issues

### Low Hit Rate

**Symptom:** Hit rate below 70%

**Solutions:**
1. Review TTL values (may be too short)
2. Check invalidation frequency
3. Verify keys are being set correctly
4. Analyze access patterns
5. Consider warming cache on startup

### Memory Issues

**Symptom:** Redis approaching memory limit

**Solutions:**
1. Increase `maxmemory` setting
2. Review eviction policy
3. Reduce TTL for less important data
4. Clean up unused keys
5. Consider key compression

## Production Checklist

- [ ] Change Redis password from default
- [ ] Update `REDIS_URL` with production password
- [ ] Bind Redis to `127.0.0.1` (not `0.0.0.0`)
- [ ] Enable `protected-mode yes`
- [ ] Set up Prometheus scraping
- [ ] Configure Grafana dashboards
- [ ] Set up alerting rules
- [ ] Test connection retry logic
- [ ] Verify cache invalidation works
- [ ] Load test cache performance
- [ ] Document key patterns for team
- [ ] Set up Redis backup strategy
- [ ] Configure Redis persistence settings
- [ ] Review and rename dangerous commands

## Performance Benchmarks

Expected performance (local Redis):
- Cache GET: < 1ms (P95)
- Cache SET: < 2ms (P95)
- Cache DELETE: < 1ms (P95)
- Pattern SCAN: 5-50ms (depends on key count)

Production targets:
- Hit rate: > 80%
- P95 latency: < 10ms
- Error rate: < 0.1%
- Memory usage: < 80% of allocated

## Future Enhancements

Potential improvements:
1. Cache warming strategies
2. Distributed caching with Redis Cluster
3. Read replicas for high availability
4. Cache statistics dashboard
5. Automated TTL optimization
6. Cache preloading for common queries
7. Multi-level caching (L1: memory, L2: Redis)
8. Cache compression for large values

## References

- [Redis Best Practices](https://redis.io/docs/manual/patterns/)
- [Prometheus Metrics](https://prometheus.io/docs/practices/naming/)
- [Cache Invalidation Strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/BestPractices.html)

## Support

For issues or questions:
- Create issue in repository
- Check Prometheus metrics: `/api/v1/metrics`
- Review Redis logs
- Consult this documentation

---

Last Updated: 2025-11-09
Version: 1.0.0
