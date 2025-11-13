"""Prometheus metrics collection and exposition."""

import time
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from typing import Callable

# HTTP Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests in progress',
    ['method', 'endpoint']
)

# Business Metrics
active_users_gauge = Gauge(
    'analytics_active_users',
    'Current number of active users',
    ['workspace_id']
)

credits_consumed_total = Counter(
    'analytics_credits_consumed_total',
    'Total credits consumed',
    ['workspace_id', 'agent_id']
)

analytics_queries_total = Counter(
    'analytics_queries_total',
    'Total analytics queries executed',
    ['query_type', 'workspace_id']
)

analytics_query_duration_seconds = Histogram(
    'analytics_query_duration_seconds',
    'Analytics query execution time',
    ['query_type'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
)

# Database Metrics
database_connections_gauge = Gauge(
    'database_connections',
    'Database connection pool status',
    ['state']  # idle, active, total
)

database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Database query execution time',
    ['operation'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)
)

database_errors_total = Counter(
    'database_errors_total',
    'Total database errors',
    ['error_type']
)

# Cache Metrics
cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'result']  # operation: get/set/delete, result: hit/miss/success/error
)

cache_operation_duration_seconds = Histogram(
    'cache_operation_duration_seconds',
    'Cache operation duration',
    ['operation'],
    buckets=(0.0001, 0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05)
)

cache_size_bytes = Gauge(
    'cache_size_bytes',
    'Current cache size in bytes'
)

cache_items_total = Gauge(
    'cache_items_total',
    'Total number of items in cache'
)

# Background Job Metrics
background_jobs_total = Counter(
    'background_jobs_total',
    'Total background job executions',
    ['job_type', 'status']  # status: success, failure
)

background_job_duration_seconds = Histogram(
    'background_job_duration_seconds',
    'Background job execution time',
    ['job_type'],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0, 3600.0)
)

# Export Metrics
exports_total = Counter(
    'exports_total',
    'Total data exports',
    ['format', 'status']  # format: csv/json/pdf/excel, status: success/failure
)

export_duration_seconds = Histogram(
    'export_duration_seconds',
    'Data export generation time',
    ['format'],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
)

# WebSocket Metrics
websocket_connections_active = Gauge(
    'websocket_connections_active',
    'Number of active WebSocket connections',
    ['workspace_id']
)

websocket_messages_total = Counter(
    'websocket_messages_total',
    'Total WebSocket messages',
    ['direction', 'message_type']  # direction: sent/received
)

# Alert Metrics
alerts_triggered_total = Counter(
    'alerts_triggered_total',
    'Total alerts triggered',
    ['alert_type', 'severity']
)

alerts_sent_total = Counter(
    'alerts_sent_total',
    'Total alert notifications sent',
    ['channel', 'status']  # channel: email/slack/teams, status: success/failure
)


class PrometheusMiddleware:
    """Middleware to collect HTTP metrics for Prometheus."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next: Callable):
        # Skip metrics endpoint to avoid recursion
        if request.url.path == "/metrics" or request.url.path == "/api/v1/metrics":
            return await call_next(request)

        # Normalize endpoint path (remove IDs, UUIDs, etc.)
        endpoint = self._normalize_path(request.url.path)

        # Track in-progress requests
        http_requests_in_progress.labels(
            method=request.method,
            endpoint=endpoint
        ).inc()

        # Start timer
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Record metrics
            duration = time.time() - start_time

            http_requests_total.labels(
                method=request.method,
                endpoint=endpoint,
                status=response.status_code
            ).inc()

            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=endpoint
            ).observe(duration)

            return response

        except Exception as e:
            # Record error
            duration = time.time() - start_time

            http_requests_total.labels(
                method=request.method,
                endpoint=endpoint,
                status=500
            ).inc()

            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=endpoint
            ).observe(duration)

            raise

        finally:
            # Decrement in-progress counter
            http_requests_in_progress.labels(
                method=request.method,
                endpoint=endpoint
            ).dec()

    def _normalize_path(self, path: str) -> str:
        """Normalize URL path to reduce cardinality.

        Replace IDs, UUIDs, and other variable parts with placeholders.
        """
        import re

        # Replace UUIDs
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{uuid}',
            path,
            flags=re.IGNORECASE
        )

        # Replace numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)

        # Replace dates (YYYY-MM-DD)
        path = re.sub(r'/\d{4}-\d{2}-\d{2}', '/{date}', path)

        return path


async def get_metrics() -> Response:
    """Generate Prometheus metrics response.

    Returns:
        Response containing metrics in Prometheus format
    """
    metrics = generate_latest()
    return Response(content=metrics, media_type=CONTENT_TYPE_LATEST)
