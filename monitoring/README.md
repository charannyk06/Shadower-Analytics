# Monitoring and Observability

This directory contains configuration files for monitoring, logging, and observability of the Shadower Analytics service.

## Overview

The analytics service includes comprehensive monitoring capabilities:

- **Structured Logging**: JSON-formatted logs with request context and trace IDs
- **Metrics Collection**: Prometheus metrics for HTTP requests, database, cache, and business metrics
- **Distributed Tracing**: OpenTelemetry integration for request tracing across services
- **Error Tracking**: Sentry integration for error monitoring and alerting
- **Health Checks**: Comprehensive health check endpoints for all dependencies
- **Alerting**: Prometheus alert rules for critical conditions
- **Log Aggregation**: Fluentd configuration for centralized log management
- **Dashboards**: Grafana dashboard for visualization

## Components

### 1. Structured Logging

Location: `backend/src/config/logging.py`

**Features:**
- JSON-formatted logs with timestamp, service, environment, version
- Request context (request_id, user_id, workspace_id)
- Trace context integration (trace_id, span_id)
- Configurable log levels for third-party libraries

**Environment Variables:**
```bash
APP_ENV=production                    # Environment name
APP_VERSION=1.0.0                    # Application version
```

**Usage:**
```python
from src.config.logging import get_logger

logger = get_logger(__name__)
logger.info("Processing request", extra={"user_id": user_id})
```

### 2. Prometheus Metrics

Location: `backend/src/monitoring/prometheus.py`

**Available Metrics:**

**HTTP Metrics:**
- `http_requests_total` - Total HTTP requests by method, endpoint, status
- `http_request_duration_seconds` - Request latency histogram
- `http_requests_in_progress` - Active requests gauge

**Business Metrics:**
- `analytics_active_users` - Active users per workspace
- `analytics_credits_consumed_total` - Credits consumed counter
- `analytics_queries_total` - Analytics query counter

**Database Metrics:**
- `database_connections` - Connection pool status (active, idle, total)
- `database_query_duration_seconds` - Query execution time
- `database_errors_total` - Database error counter

**Cache Metrics:**
- `cache_operations_total` - Cache operations (hit/miss)
- `cache_operation_duration_seconds` - Cache operation latency
- `cache_size_bytes` - Current cache size
- `cache_items_total` - Total cached items

**Metrics Endpoint:**
```
GET /metrics        # Prometheus metrics in exposition format
GET /api/v1/metrics # Alternative metrics endpoint
```

### 3. Distributed Tracing

Location: `backend/src/monitoring/tracing.py`

**Features:**
- Automatic instrumentation of FastAPI, SQLAlchemy, Redis, HTTP clients
- Custom span creation with decorators
- Trace context propagation
- OTLP exporter for Jaeger/Tempo

**Environment Variables:**
```bash
OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317  # OTLP collector endpoint
OTEL_EXPORTER_INSECURE=true                 # Use insecure connection
OTEL_CONSOLE_EXPORT=false                   # Export to console (debug)
```

**Usage:**
```python
from src.monitoring.tracing import trace_operation, add_span_attributes

@trace_operation("calculate_analytics")
async def calculate_analytics(workspace_id: str):
    add_span_attributes({"workspace_id": workspace_id})
    # Your code here
```

### 4. Error Tracking (Sentry)

Location: `backend/src/monitoring/sentry_config.py`

**Features:**
- Automatic error capture with stack traces
- Performance monitoring with transaction sampling
- Breadcrumb tracking for debugging
- Custom error filtering
- User context attachment

**Environment Variables:**
```bash
SENTRY_DSN=https://xxx@sentry.io/xxx        # Sentry DSN
SENTRY_TRACES_SAMPLE_RATE=0.1              # Traces sample rate (0.0-1.0)
SENTRY_PROFILES_SAMPLE_RATE=0.1            # Profiles sample rate (0.0-1.0)
```

**Usage:**
```python
from src.monitoring.sentry_config import capture_exception, set_user_context

try:
    risky_operation()
except Exception as e:
    capture_exception(e, context={"workspace_id": workspace_id})
```

### 5. Health Checks

Location: `backend/src/monitoring/health.py`

**Endpoints:**

```bash
GET /health                 # Basic health check (fast)
GET /health/detailed        # Comprehensive health check (all dependencies)
GET /ready                  # Kubernetes readiness probe
GET /live                   # Kubernetes liveness probe
```

**Checked Services:**
- Database (PostgreSQL)
- Cache (Redis)
- WebSocket service
- Background jobs (Celery)
- External services (Main App)

### 6. Alerting Rules

Location: `monitoring/alerts.yml`

**Alert Groups:**

**analytics_alerts:**
- HighErrorRate - Error rate > 5%
- DatabaseConnectionPoolExhausted - < 5 idle connections
- DatabaseConnectionFailures - High DB error rate
- HighMemoryUsage - Memory > 90%
- HighCPUUsage - CPU > 80%
- HighAPILatencyP95 - P95 latency > 1s
- HighAPILatencyP99 - P99 latency > 3s
- CreditConsumptionSpike - Unusual credit usage
- LowCacheHitRate - Hit rate < 70%
- BackgroundJobFailures - Job failure rate > 10%
- ServiceDown - Service unavailable
- ExportFailures - High export error rate

**database_performance:**
- SlowDatabaseQueries - P95 query time > 0.5s
- DatabaseQueryTimeout - P99 query time > 2.5s

**Usage with Prometheus:**
```bash
# Load alerts in Prometheus config
rule_files:
  - "alerts.yml"
```

### 7. Log Aggregation

Location: `monitoring/fluentd.conf`

**Features:**
- Forward protocol support for application logs
- Docker container log tailing
- GeoIP enrichment for client IPs
- Error log throttling
- Sensitive data redaction
- Elasticsearch output with ILM

**Environment Variables:**
```bash
ELASTICSEARCH_HOST=elasticsearch           # Elasticsearch host
ELASTICSEARCH_PORT=9200                   # Elasticsearch port
ELASTICSEARCH_SCHEME=http                 # http or https
ELASTICSEARCH_USER=elastic                # Username (if auth enabled)
ELASTICSEARCH_PASSWORD=secret             # Password (if auth enabled)
```

**Log Indices:**
- `analytics-YYYY.MM.DD` - Standard application logs
- `analytics-errors-YYYY.MM.DD` - Error logs only
- `analytics-metrics-YYYY.MM.DD` - Metrics logs
- `analytics-performance-YYYY.MM.DD` - Performance logs

### 8. Grafana Dashboard

Location: `monitoring/grafana-dashboard.json`

**Panels:**
1. Request Rate - Requests per second by method
2. Error Rate - Percentage of failed requests
3. P95/P99 Latency - Response time percentiles
4. Active Users - Current active users
5. Credits Consumed - Hourly credit consumption rate
6. Database Connections - Pool status
7. Cache Hit Rate - Cache effectiveness
8. Background Jobs - Job success/failure rates
9. Request Distribution - Traffic by endpoint
10. WebSocket Connections - Active connections
11. Database Query Performance - Query latency
12. Export Performance - Export success/failure
13. System Resources - Memory usage
14. System Resources - CPU usage
15. Alert Status - Active alerts count
16. Request Rate (Current) - Real-time request rate
17. Average Response Time - Current average latency

**Import:**
1. Open Grafana UI
2. Navigate to Dashboards → Import
3. Upload `monitoring/grafana-dashboard.json`
4. Select Prometheus datasource
5. Click Import

## Quick Start

### 1. Local Development

```bash
# Start monitoring stack with Docker Compose
cd monitoring
docker-compose up -d

# Services will be available at:
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)
# - Jaeger: http://localhost:16686
# - Elasticsearch: http://localhost:9200
```

### 2. Configure Environment

```bash
# Copy example env file
cp backend/.env.example backend/.env

# Edit .env and add:
SENTRY_DSN=your-sentry-dsn
OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317
ELASTICSEARCH_HOST=localhost
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Run Application

```bash
cd backend
uvicorn src.api.main:app --reload
```

### 5. Verify Monitoring

```bash
# Check metrics
curl http://localhost:8000/metrics

# Check health
curl http://localhost:8000/health/detailed

# View logs (should be JSON formatted)
tail -f logs/app.log | jq
```

## Production Deployment

### 1. Infrastructure Setup

**Prometheus:**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'analytics-backend'
    static_configs:
      - targets: ['analytics-api:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

**Grafana:**
- Import dashboard from `grafana-dashboard.json`
- Configure Prometheus datasource
- Set up alert notifications

**Fluentd:**
- Deploy Fluentd DaemonSet in Kubernetes
- Configure Elasticsearch endpoint
- Mount `fluentd.conf`

**Jaeger/Tempo:**
- Deploy OTLP collector
- Configure trace storage backend
- Set retention policies

### 2. Environment Variables

```bash
# Required for production
export APP_ENV=production
export APP_VERSION=$(git describe --tags)
export SENTRY_DSN=your-production-sentry-dsn
export OTEL_EXPORTER_OTLP_ENDPOINT=tempo-collector:4317
export ELASTICSEARCH_HOST=elasticsearch-cluster
export ELASTICSEARCH_USER=analytics
export ELASTICSEARCH_PASSWORD=secure-password
```

### 3. Alert Configuration

**Slack Integration:**
```yaml
# alertmanager.yml
receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#analytics-alerts'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

**PagerDuty Integration:**
```yaml
receivers:
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
```

## Monitoring Best Practices

1. **Logging:**
   - Always include context (request_id, user_id, workspace_id)
   - Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)
   - Never log sensitive information (passwords, tokens, PII)

2. **Metrics:**
   - Keep cardinality low (avoid high-cardinality labels like user IDs)
   - Use histograms for latency, counters for events, gauges for snapshots
   - Add business metrics alongside technical metrics

3. **Tracing:**
   - Sample traces appropriately (10% in production)
   - Add meaningful span attributes
   - Use trace context for correlation

4. **Alerts:**
   - Alert on symptoms, not causes
   - Include runbook links in alert annotations
   - Set appropriate thresholds and durations

5. **Health Checks:**
   - Keep liveness probes simple (no dependencies)
   - Use readiness probes for dependency checks
   - Set appropriate timeout values

## Troubleshooting

### High Memory Usage
```bash
# Check metric
curl localhost:8000/metrics | grep container_memory

# View detailed stats
curl localhost:8000/health/detailed
```

### Missing Traces
```bash
# Verify OTLP endpoint
echo $OTEL_EXPORTER_OTLP_ENDPOINT

# Check application logs
grep "tracing" logs/app.log
```

### Sentry Not Receiving Errors
```bash
# Verify DSN is set
echo $SENTRY_DSN

# Test Sentry
python -c "import sentry_sdk; sentry_sdk.init('$SENTRY_DSN'); sentry_sdk.capture_message('test')"
```

### Metrics Not Appearing in Prometheus
```bash
# Check Prometheus targets
curl http://prometheus:9090/api/v1/targets

# Verify metrics endpoint
curl http://analytics-api:8000/metrics
```

## Support

For issues or questions:
- Check runbooks: https://docs.shadower.ai/runbooks
- Create issue: https://github.com/shadower/analytics/issues
- Contact: devops@shadower.ai
