# Specification: Caching Layer

## Feature Overview
Redis-based caching system to improve performance and reduce database load for frequently accessed analytics data.

## Technical Requirements
- Redis for in-memory caching
- Intelligent cache invalidation
- Time-based and event-based expiration
- Cache warming strategies
- Distributed caching support

## Implementation Details

### Redis Configuration

#### Connection Setup
```python
# backend/src/core/redis.py
import redis.asyncio as redis
from typing import Optional, Any
import json
import pickle
from datetime import timedelta

class RedisClient:
    def __init__(self, url: str):
        self.redis = redis.from_url(
            url,
            encoding="utf-8",
            decode_responses=False,  # Handle bytes for complex objects
            max_connections=50,
            socket_keepalive=True,
            socket_keepalive_options={
                1: 1,  # TCP_KEEPIDLE
                2: 1,  # TCP_KEEPINTVL
                3: 3,  # TCP_KEEPCNT
            }
        )
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        value = await self.redis.get(key)
        if value:
            try:
                # Try JSON first
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # Fall back to pickle for complex objects
                return pickle.loads(value)
        return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional expiration"""
        try:
            # Try JSON serialization first (faster)
            serialized = json.dumps(value)
        except (TypeError, ValueError):
            # Fall back to pickle for complex objects
            serialized = pickle.dumps(value)
        
        if expire:
            return await self.redis.setex(key, expire, serialized)
        return await self.redis.set(key, serialized)
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        return bool(await self.redis.delete(key))
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        return bool(await self.redis.exists(key))
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on existing key"""
        return await self.redis.expire(key, seconds)
    
    async def get_ttl(self, key: str) -> int:
        """Get time to live for key"""
        return await self.redis.ttl(key)
    
    async def flush_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        cursor = 0
        deleted = 0
        
        while True:
            cursor, keys = await self.redis.scan(
                cursor=cursor,
                match=pattern,
                count=100
            )
            
            if keys:
                deleted += await self.redis.delete(*keys)
            
            if cursor == 0:
                break
        
        return deleted
    
    async def close(self):
        """Close Redis connection"""
        await self.redis.close()

# Initialize
redis_client = RedisClient(settings.REDIS_URL)
```

### Cache Key Strategy

#### Key Naming Convention
```python
# backend/src/services/cache/keys.py
from typing import Optional, List
import hashlib
import json

class CacheKeys:
    """Centralized cache key management"""
    
    # Prefixes for different data types
    EXECUTIVE_PREFIX = "exec"
    AGENT_PREFIX = "agent"
    USER_PREFIX = "user"
    WORKSPACE_PREFIX = "ws"
    METRICS_PREFIX = "metrics"
    REPORT_PREFIX = "report"
    
    # TTL values (in seconds)
    TTL_SHORT = 60           # 1 minute
    TTL_MEDIUM = 300         # 5 minutes
    TTL_LONG = 1800          # 30 minutes
    TTL_HOUR = 3600          # 1 hour
    TTL_DAY = 86400          # 24 hours
    
    @staticmethod
    def executive_dashboard(
        workspace_id: str, 
        timeframe: str
    ) -> str:
        """Key for executive dashboard data"""
        return f"{CacheKeys.EXECUTIVE_PREFIX}:dashboard:{workspace_id}:{timeframe}"
    
    @staticmethod
    def agent_analytics(
        agent_id: str, 
        timeframe: str
    ) -> str:
        """Key for agent analytics"""
        return f"{CacheKeys.AGENT_PREFIX}:analytics:{agent_id}:{timeframe}"
    
    @staticmethod
    def user_activity(
        user_id: str, 
        date: str
    ) -> str:
        """Key for user activity data"""
        return f"{CacheKeys.USER_PREFIX}:activity:{user_id}:{date}"
    
    @staticmethod
    def workspace_metrics(
        workspace_id: str, 
        metric_type: str,
        date: str
    ) -> str:
        """Key for workspace metrics"""
        return f"{CacheKeys.WORKSPACE_PREFIX}:metrics:{workspace_id}:{metric_type}:{date}"
    
    @staticmethod
    def query_result(
        query_hash: str
    ) -> str:
        """Key for cached query results"""
        return f"query:result:{query_hash}"
    
    @staticmethod
    def generate_query_hash(
        query: str, 
        params: dict
    ) -> str:
        """Generate hash for query caching"""
        content = f"{query}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    @staticmethod
    def get_pattern(prefix: str, *parts) -> str:
        """Get pattern for batch operations"""
        key_parts = [prefix] + list(parts) + ['*']
        return ':'.join(key_parts)
```

### Cache Decorator

#### Automatic Caching Decorator
```python
# backend/src/services/cache/decorator.py
from functools import wraps
from typing import Optional, Callable, Any
import asyncio
import logging

logger = logging.getLogger(__name__)

def cached(
    key_func: Callable[..., str],
    ttl: int = CacheKeys.TTL_MEDIUM,
    skip_cache: bool = False,
    invalidate_on: Optional[List[str]] = None
):
    """Decorator for automatic caching of function results"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Allow cache bypass
            if skip_cache or kwargs.get('skip_cache', False):
                return await func(*args, **kwargs)
            
            # Generate cache key
            cache_key = key_func(*args, **kwargs)
            
            # Try to get from cache
            try:
                cached_value = await redis_client.get(cache_key)
                
                if cached_value is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_value
            except Exception as e:
                logger.error(f"Cache read error: {e}")
                # Continue to fetch from source
            
            # Cache miss - fetch from source
            logger.debug(f"Cache miss: {cache_key}")
            result = await func(*args, **kwargs)
            
            # Store in cache
            try:
                await redis_client.set(cache_key, result, expire=ttl)
                logger.debug(f"Cached result: {cache_key}")
            except Exception as e:
                logger.error(f"Cache write error: {e}")
                # Return result even if caching fails
            
            return result
        
        # Add cache invalidation method
        async def invalidate(*args, **kwargs):
            cache_key = key_func(*args, **kwargs)
            await redis_client.delete(cache_key)
            logger.debug(f"Invalidated cache: {cache_key}")
        
        wrapper.invalidate = invalidate
        return wrapper
    return decorator
```

### Cache Service

#### Main Caching Service
```python
# backend/src/services/cache/cache_service.py
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
    
    async def get_or_compute(
        self,
        key: str,
        compute_func: Callable,
        ttl: int = CacheKeys.TTL_MEDIUM
    ) -> Any:
        """Get from cache or compute and cache"""
        # Check cache
        value = await self.redis.get(key)
        
        if value is not None:
            return value
        
        # Compute value
        value = await compute_func()
        
        # Cache it
        await self.redis.set(key, value, expire=ttl)
        
        return value
    
    async def invalidate_workspace(self, workspace_id: str):
        """Invalidate all cache for a workspace"""
        patterns = [
            f"{CacheKeys.EXECUTIVE_PREFIX}:*:{workspace_id}:*",
            f"{CacheKeys.WORKSPACE_PREFIX}:*:{workspace_id}:*",
            f"{CacheKeys.METRICS_PREFIX}:*:{workspace_id}:*",
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = await self.redis.flush_pattern(pattern)
            total_deleted += deleted
        
        logger.info(f"Invalidated {total_deleted} cache entries for workspace {workspace_id}")
        return total_deleted
    
    async def invalidate_agent(self, agent_id: str):
        """Invalidate all cache for an agent"""
        pattern = f"{CacheKeys.AGENT_PREFIX}:*:{agent_id}:*"
        deleted = await self.redis.flush_pattern(pattern)
        
        logger.info(f"Invalidated {deleted} cache entries for agent {agent_id}")
        return deleted
    
    async def warm_cache(self, workspace_id: str):
        """Pre-populate cache with common queries"""
        from ..metrics import MetricsService
        
        metrics_service = MetricsService()
        timeframes = ['24h', '7d', '30d']
        
        tasks = []
        for timeframe in timeframes:
            # Executive dashboard
            tasks.append(
                self._warm_executive_dashboard(workspace_id, timeframe)
            )
            
            # Top agents
            tasks.append(
                self._warm_top_agents(workspace_id, timeframe)
            )
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"Cache warming completed: {successful}/{len(results)} successful")
        
        return successful
    
    async def _warm_executive_dashboard(
        self, 
        workspace_id: str, 
        timeframe: str
    ):
        """Warm executive dashboard cache"""
        from ..metrics import MetricsService
        
        key = CacheKeys.executive_dashboard(workspace_id, timeframe)
        metrics_service = MetricsService()
        
        data = await metrics_service.get_executive_metrics(
            workspace_id, 
            timeframe
        )
        
        await self.redis.set(key, data, expire=CacheKeys.TTL_LONG)
        return key
    
    async def _warm_top_agents(
        self, 
        workspace_id: str, 
        timeframe: str
    ):
        """Warm top agents cache"""
        from ..metrics import AgentMetricsService
        
        key = f"{CacheKeys.AGENT_PREFIX}:top:{workspace_id}:{timeframe}"
        agent_service = AgentMetricsService()
        
        data = await agent_service.get_top_agents(
            workspace_id, 
            timeframe,
            limit=10
        )
        
        await self.redis.set(key, data, expire=CacheKeys.TTL_MEDIUM)
        return key
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        info = await self.redis.redis.info()
        
        return {
            "used_memory": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "total_commands_processed": info.get("total_commands_processed"),
            "keyspace_hits": info.get("keyspace_hits"),
            "keyspace_misses": info.get("keyspace_misses"),
            "hit_rate": self._calculate_hit_rate(
                info.get("keyspace_hits", 0),
                info.get("keyspace_misses", 0)
            ),
            "evicted_keys": info.get("evicted_keys"),
            "expired_keys": info.get("expired_keys"),
        }
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate"""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)

# Initialize
cache_service = CacheService(redis_client)
```

### Cache Usage Examples

#### Executive Dashboard with Caching
```python
# backend/src/api/routes/executive.py
from fastapi import APIRouter, Depends, Query
from typing import Dict, Any

router = APIRouter()

@router.get("/executive/overview")
@cached(
    key_func=lambda workspace_id, timeframe, **_: 
        CacheKeys.executive_dashboard(workspace_id, timeframe),
    ttl=CacheKeys.TTL_LONG
)
async def get_executive_overview(
    workspace_id: str,
    timeframe: str = Query("7d", regex="^(24h|7d|30d|90d)$"),
    current_user: Dict[str, Any] = Depends(jwt_auth.get_current_user),
    skip_cache: bool = Query(False, description="Skip cache")
):
    """Get executive dashboard with caching"""
    
    # Validate access
    await WorkspaceAccess.validate_workspace_access(
        current_user, 
        workspace_id
    )
    
    # This will be cached automatically by decorator
    metrics = await metrics_service.get_executive_metrics(
        workspace_id,
        timeframe
    )
    
    return {
        "workspace_id": workspace_id,
        "timeframe": timeframe,
        "metrics": metrics,
        "cached_at": datetime.utcnow() if not skip_cache else None
    }
```

#### Query Result Caching
```python
# backend/src/services/metrics/base.py
class BaseMetricsService:
    async def execute_query_cached(
        self,
        query: str,
        params: Dict[str, Any],
        ttl: int = CacheKeys.TTL_MEDIUM
    ) -> List[Dict]:
        """Execute query with result caching"""
        
        # Generate cache key from query
        query_hash = CacheKeys.generate_query_hash(query, params)
        cache_key = CacheKeys.query_result(query_hash)
        
        # Try cache first
        cached_result = await redis_client.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Execute query
        result = await self.db.fetch_all(query, params)
        
        # Cache result
        await redis_client.set(cache_key, result, expire=ttl)
        
        return result
```

### Cache Invalidation

#### Event-Based Invalidation
```python
# backend/src/services/events/handlers.py
from typing import Dict, Any

class EventHandlers:
    @staticmethod
    async def on_agent_run_completed(event: Dict[str, Any]):
        """Handle agent run completion"""
        agent_id = event.get('agent_id')
        workspace_id = event.get('workspace_id')
        
        # Invalidate related caches
        await cache_service.invalidate_agent(agent_id)
        
        # Invalidate workspace metrics (more selective)
        patterns = [
            CacheKeys.executive_dashboard(workspace_id, "*"),
            f"{CacheKeys.METRICS_PREFIX}:runs:{workspace_id}:*"
        ]
        
        for pattern in patterns:
            await redis_client.flush_pattern(pattern)
    
    @staticmethod
    async def on_user_activity(event: Dict[str, Any]):
        """Handle user activity event"""
        user_id = event.get('user_id')
        workspace_id = event.get('workspace_id')
        
        # Only invalidate DAU/WAU/MAU caches
        patterns = [
            f"{CacheKeys.METRICS_PREFIX}:users:active:{workspace_id}:*",
            CacheKeys.user_activity(user_id, "*")
        ]
        
        for pattern in patterns:
            await redis_client.flush_pattern(pattern)
```

#### Scheduled Invalidation
```python
# backend/src/jobs/cache_maintenance.py
import asyncio
from datetime import datetime, timedelta

async def cleanup_expired_cache():
    """Scheduled job to clean up stale cache entries"""
    
    # Get all keys with pattern
    patterns_to_check = [
        f"{CacheKeys.EXECUTIVE_PREFIX}:*",
        f"{CacheKeys.AGENT_PREFIX}:*",
        f"{CacheKeys.METRICS_PREFIX}:*",
    ]
    
    total_cleaned = 0
    
    for pattern in patterns_to_check:
        cursor = 0
        while True:
            cursor, keys = await redis_client.redis.scan(
                cursor=cursor,
                match=pattern,
                count=100
            )
            
            for key in keys:
                ttl = await redis_client.get_ttl(key)
                
                # Remove keys without TTL (shouldn't happen)
                if ttl == -1:
                    await redis_client.delete(key)
                    total_cleaned += 1
            
            if cursor == 0:
                break
    
    logger.info(f"Cleaned up {total_cleaned} stale cache entries")
    return total_cleaned

async def refresh_materialized_cache():
    """Refresh cache for materialized views"""
    
    # Get all active workspaces
    workspaces = await get_active_workspaces()
    
    tasks = []
    for workspace in workspaces:
        tasks.append(cache_service.warm_cache(workspace.id))
    
    await asyncio.gather(*tasks, return_exceptions=True)
```

### Frontend Caching

#### React Query Configuration
```typescript
// frontend/src/lib/react-query.ts
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,      // 5 minutes
      cacheTime: 1000 * 60 * 30,     // 30 minutes
      refetchOnWindowFocus: false,
      retry: 2,
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
});

// Cache key factory
export const queryKeys = {
  executive: (workspaceId: string, timeframe: string) => 
    ['executive', workspaceId, timeframe],
  
  agents: (workspaceId: string) => 
    ['agents', workspaceId],
  
  agentDetail: (agentId: string, timeframe: string) => 
    ['agent', agentId, timeframe],
  
  users: (workspaceId: string, filters: any) => 
    ['users', workspaceId, filters],
  
  metrics: (type: string, params: any) => 
    ['metrics', type, params],
};
```

#### Hook with Caching
```typescript
// frontend/src/hooks/api/useExecutiveDashboard.ts
import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/react-query';
import apiClient from '@/lib/api/client';

export function useExecutiveDashboard(
  workspaceId: string,
  timeframe: string,
  options?: {
    skipCache?: boolean;
    refetchInterval?: number;
  }
) {
  return useQuery({
    queryKey: queryKeys.executive(workspaceId, timeframe),
    
    queryFn: async () => {
      const response = await apiClient.get('/executive/overview', {
        params: {
          workspace_id: workspaceId,
          timeframe,
          skip_cache: options?.skipCache || false
        }
      });
      return response.data;
    },
    
    staleTime: options?.skipCache ? 0 : 1000 * 60 * 5, // 5 min
    
    refetchInterval: options?.refetchInterval,
    
    // Cache for 30 minutes
    cacheTime: 1000 * 60 * 30,
  });
}
```

## Testing Requirements
- Unit tests for cache operations
- Integration tests for cache invalidation
- Performance tests for cache hit/miss scenarios
- Load tests for concurrent cache access
- Cache eviction policy tests

## Performance Targets
- Cache hit rate: >80%
- Cache operation latency: <5ms
- Cache warm-up time: <30 seconds
- Memory usage: <500MB for 10,000 keys

## Security Considerations
- Use separate Redis databases for different environments
- Implement key namespacing to prevent collisions
- Never cache sensitive unencrypted data
- Set appropriate TTLs to prevent stale data
- Monitor for cache poisoning attempts