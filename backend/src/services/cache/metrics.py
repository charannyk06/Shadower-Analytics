"""Cache metrics for Prometheus monitoring."""

from prometheus_client import Counter, Histogram, Gauge
import time
from functools import wraps
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)

# Cache operation counters
cache_hits = Counter(
    "cache_hits_total", "Total number of cache hits", ["operation", "key_pattern"]
)

cache_misses = Counter(
    "cache_misses_total", "Total number of cache misses", ["operation", "key_pattern"]
)

cache_errors = Counter(
    "cache_errors_total",
    "Total number of cache operation errors",
    ["operation", "error_type"],
)

cache_invalidations = Counter(
    "cache_invalidations_total",
    "Total number of cache invalidations",
    ["pattern"],
)

# Cache operation latency
cache_operation_duration = Histogram(
    "cache_operation_duration_seconds",
    "Cache operation duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0),
)

# Cache size metrics
cache_keys_total = Gauge("cache_keys_total", "Total number of keys in cache")


def track_cache_operation(operation: str):
    """Decorator to track cache operation metrics.

    Args:
        operation: Name of the cache operation (get, set, delete, etc.)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                cache_operation_duration.labels(operation=operation).observe(duration)
                return result
            except Exception as e:
                cache_errors.labels(
                    operation=operation, error_type=type(e).__name__
                ).inc()
                logger.error(f"Cache operation {operation} failed: {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                cache_operation_duration.labels(operation=operation).observe(duration)
                return result
            except Exception as e:
                cache_errors.labels(
                    operation=operation, error_type=type(e).__name__
                ).inc()
                logger.error(f"Cache operation {operation} failed: {e}")
                raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def record_cache_hit(operation: str, key_pattern: str = "unknown"):
    """Record a cache hit."""
    cache_hits.labels(operation=operation, key_pattern=key_pattern).inc()


def record_cache_miss(operation: str, key_pattern: str = "unknown"):
    """Record a cache miss."""
    cache_misses.labels(operation=operation, key_pattern=key_pattern).inc()


def record_cache_error(operation: str, error_type: str):
    """Record a cache error."""
    cache_errors.labels(operation=operation, error_type=error_type).inc()


def record_cache_invalidation(pattern: str):
    """Record a cache invalidation."""
    cache_invalidations.labels(pattern=pattern).inc()


def update_cache_size(size: int):
    """Update the cache size gauge."""
    cache_keys_total.set(size)
