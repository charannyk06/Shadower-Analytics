# Specification: Monitoring and Logging

## Overview
Define comprehensive monitoring, logging, and observability strategy for the analytics service including metrics, traces, logs, and alerts.

## Technical Requirements

### Logging Configuration

#### Structured Logging Setup
```python
# backend/config/logging.py
import logging
import json
from datetime import datetime
from pythonjsonlogger import jsonlogger

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['service'] = 'analytics-backend'
        log_record['environment'] = os.getenv('ENVIRONMENT', 'development')
        log_record['version'] = os.getenv('APP_VERSION', 'unknown')
        
        # Add request context if available
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        if hasattr(record, 'workspace_id'):
            log_record['workspace_id'] = record.workspace_id

def setup_logging():
    # Console handler with JSON formatting
    console_handler = logging.StreamHandler()
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s'
    )
    console_handler.setFormatter(formatter)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    # Configure third-party loggers
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    
    return root_logger
```

#### Application Logging
```python
# backend/middleware/logging_middleware.py
from fastapi import Request
import time
import uuid
from typing import Callable

class LoggingMiddleware:
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(__name__)
    
    async def __call__(self, request: Request, call_next: Callable):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timer
        start_time = time.time()
        
        # Log request
        self.logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host,
                "user_agent": request.headers.get("user-agent")
            }
        )
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            self.logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2)
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "duration_ms": round(duration * 1000, 2)
                },
                exc_info=True
            )
            raise
```

### Metrics Collection

#### Prometheus Metrics
```python
# backend/metrics/prometheus.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST
from fastapi import Response

# Define metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

active_users_gauge = Gauge(
    'analytics_active_users',
    'Current active users',
    ['workspace_id']
)

credits_consumed_total = Counter(
    'analytics_credits_consumed_total',
    'Total credits consumed',
    ['workspace_id', 'agent_id']
)

database_connections_gauge = Gauge(
    'database_connections',
    'Database connection pool status',
    ['state']  # idle, active, total
)

cache_operations_total = Counter(
    'cache_operations_total',
    'Cache operations',
    ['operation', 'result']  # get/set, hit/miss
)

background_jobs_total = Counter(
    'background_jobs_total',
    'Background job executions',
    ['job_type', 'status']
)

class MetricsMiddleware:
    async def __call__(self, request: Request, call_next):
        # Start timer
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        return response

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

#### Custom Application Metrics
```python
# backend/metrics/application.py
from dataclasses import dataclass
from typing import Dict, Any
import asyncio

@dataclass
class MetricsCollector:
    redis_client: Redis
    db_session: AsyncSession
    
    async def collect_business_metrics(self) -> Dict[str, Any]:
        """Collect business metrics for monitoring"""
        metrics = {}
        
        # Active users
        metrics['active_users'] = await self.get_active_users_count()
        
        # Credits consumption
        metrics['credits_consumed_today'] = await self.get_credits_consumed_today()
        
        # Error rates
        metrics['error_rate'] = await self.calculate_error_rate()
        
        # Agent performance
        metrics['agent_success_rates'] = await self.get_agent_success_rates()
        
        # Database metrics
        metrics['database'] = await self.get_database_metrics()
        
        # Cache metrics
        metrics['cache'] = await self.get_cache_metrics()
        
        return metrics
    
    async def export_to_prometheus(self, metrics: Dict[str, Any]):
        """Export metrics to Prometheus"""
        # Update Prometheus gauges
        for workspace_id, count in metrics['active_users'].items():
            active_users_gauge.labels(workspace_id=workspace_id).set(count)
        
        # Update database metrics
        db_metrics = metrics['database']
        database_connections_gauge.labels(state='active').set(db_metrics['active_connections'])
        database_connections_gauge.labels(state='idle').set(db_metrics['idle_connections'])
```

### Distributed Tracing

#### OpenTelemetry Configuration
```python
# backend/tracing/opentelemetry_config.py
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

def setup_tracing(app):
    """Configure OpenTelemetry tracing"""
    
    # Create resource
    resource = Resource.create({
        "service.name": "analytics-backend",
        "service.version": os.getenv("APP_VERSION", "unknown"),
        "deployment.environment": os.getenv("ENVIRONMENT", "development")
    })
    
    # Setup tracer provider
    provider = TracerProvider(resource=resource)
    
    # Configure OTLP exporter (for Jaeger/Tempo)
    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317"),
        insecure=True
    )
    
    # Add span processor
    span_processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(span_processor)
    
    # Set global tracer provider
    trace.set_tracer_provider(provider)
    
    # Instrument libraries
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    
    return trace.get_tracer(__name__)
```

#### Custom Span Creation
```python
# backend/tracing/custom_spans.py
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer(__name__)

def trace_operation(name: str):
    """Decorator for tracing functions"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(name) as span:
                try:
                    # Add span attributes
                    span.set_attribute("function", func.__name__)
                    span.set_attribute("module", func.__module__)
                    
                    # Execute function
                    result = await func(*args, **kwargs)
                    
                    # Mark as successful
                    span.set_status(Status(StatusCode.OK))
                    
                    return result
                    
                except Exception as e:
                    # Record exception
                    span.record_exception(e)
                    span.set_status(
                        Status(StatusCode.ERROR, str(e))
                    )
                    raise
        
        return wrapper
    return decorator

# Usage example
@trace_operation("calculate_analytics")
async def calculate_analytics(workspace_id: str):
    span = trace.get_current_span()
    span.set_attribute("workspace_id", workspace_id)
    
    # Perform calculations
    results = await perform_calculations(workspace_id)
    
    span.set_attribute("result_count", len(results))
    return results
```

### Error Tracking

#### Sentry Integration
```python
# backend/error_tracking/sentry_config.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

def setup_sentry():
    """Configure Sentry error tracking"""
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        environment=os.getenv("ENVIRONMENT", "development"),
        release=os.getenv("APP_VERSION", "unknown"),
        
        integrations=[
            FastApiIntegration(
                transaction_style="endpoint"
            ),
            SqlalchemyIntegration(),
            RedisIntegration(),
            CeleryIntegration()
        ],
        
        # Performance monitoring
        traces_sample_rate=0.1,  # 10% of transactions
        profiles_sample_rate=0.1,  # 10% profiling
        
        # Error filtering
        before_send=filter_errors,
        
        # Additional options
        attach_stacktrace=True,
        send_default_pii=False,
        max_breadcrumbs=50
    )

def filter_errors(event, hint):
    """Filter errors before sending to Sentry"""
    # Don't send 404 errors
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']
        if isinstance(exc_value, HTTPException) and exc_value.status_code == 404:
            return None
    
    # Add custom context
    if hasattr(g, 'user_id'):
        event['user'] = {'id': g.user_id}
    
    if hasattr(g, 'workspace_id'):
        event['tags']['workspace_id'] = g.workspace_id
    
    return event
```

### Health Checks

#### Health Check Endpoints
```python
# backend/health/checks.py
from typing import Dict, Any
import asyncio
from datetime import datetime

class HealthChecker:
    def __init__(self, db_session, redis_client):
        self.db = db_session
        self.redis = redis_client
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            start = time.time()
            await self.db.execute("SELECT 1")
            latency = (time.time() - start) * 1000
            
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        try:
            start = time.time()
            await self.redis.ping()
            latency = (time.time() - start) * 1000
            
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_external_services(self) -> Dict[str, Any]:
        """Check external service connectivity"""
        checks = {}
        
        # Check main app API
        try:
            response = await httpx.get(
                f"{MAIN_APP_URL}/health",
                timeout=5
            )
            checks['main_app'] = {
                "status": "healthy" if response.status_code == 200 else "degraded",
                "latency_ms": response.elapsed.total_seconds() * 1000
            }
        except:
            checks['main_app'] = {"status": "unhealthy"}
        
        return checks
    
    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """Run all health checks"""
        checks = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_external_services()
        )
        
        overall_status = "healthy"
        if any(c.get("status") == "unhealthy" for c in checks):
            overall_status = "unhealthy"
        elif any(c.get("status") == "degraded" for c in checks):
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": checks[0],
                "redis": checks[1],
                "external": checks[2]
            }
        }
```

### Alerting Rules

#### Prometheus Alert Rules
```yaml
# monitoring/alerts.yml
groups:
  - name: analytics_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
          service: analytics
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} for {{ $labels.instance }}"
      
      # Database connection issues
      - alert: DatabaseConnectionPoolExhausted
        expr: database_connections{state="idle"} < 5
        for: 2m
        labels:
          severity: warning
          service: analytics
        annotations:
          summary: "Database connection pool nearly exhausted"
          description: "Only {{ $value }} idle connections remaining"
      
      # High memory usage
      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.9
        for: 5m
        labels:
          severity: warning
          service: analytics
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is {{ $value | humanizePercentage }}"
      
      # API latency
      - alert: HighAPILatency
        expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 1
        for: 5m
        labels:
          severity: warning
          service: analytics
        annotations:
          summary: "High API latency detected"
          description: "95th percentile latency is {{ $value }}s"
      
      # Credit consumption spike
      - alert: CreditConsumptionSpike
        expr: rate(analytics_credits_consumed_total[1h]) > 10000
        for: 5m
        labels:
          severity: info
          service: analytics
        annotations:
          summary: "Unusual credit consumption detected"
          description: "Credit consumption rate is {{ $value }} per hour"
```

### Log Aggregation

#### Fluentd Configuration
```yaml
# monitoring/fluentd.conf
<source>
  @type forward
  port 24224
  bind 0.0.0.0
</source>

<filter analytics.**>
  @type record_transformer
  <record>
    hostname "#{Socket.gethostname}"
    environment "#{ENV['ENVIRONMENT']}"
    service "analytics"
  </record>
</filter>

<filter analytics.error>
  @type throttle
  group_key workspace_id
  group_bucket_period_s 60
  group_bucket_limit 10
  group_drop_logs true
</filter>

<match analytics.**>
  @type elasticsearch
  host elasticsearch
  port 9200
  logstash_format true
  logstash_prefix analytics
  <buffer>
    @type memory
    flush_interval 10s
  </buffer>
</match>
```

### Dashboard Configuration

#### Grafana Dashboard JSON
```json
{
  "dashboard": {
    "title": "Analytics Service Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total[5m])) by (method)"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) / sum(rate(http_requests_total[5m]))"
          }
        ]
      },
      {
        "title": "P95 Latency",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Active Users",
        "targets": [
          {
            "expr": "sum(analytics_active_users)"
          }
        ]
      },
      {
        "title": "Credits Consumed",
        "targets": [
          {
            "expr": "sum(rate(analytics_credits_consumed_total[1h]))"
          }
        ]
      }
    ]
  }
}
```

## Implementation Priority
1. Structured logging setup
2. Prometheus metrics collection
3. Health check endpoints
4. Error tracking with Sentry
5. Distributed tracing

## Success Metrics
- Log ingestion rate > 10K/second
- Metric collection latency < 100ms
- Alert response time < 1 minute
- Dashboard load time < 2 seconds