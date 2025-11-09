# Aggregation Jobs Documentation

## Overview

The aggregation jobs system provides background data processing for analytics, enabling efficient querying of large datasets through pre-computed rollups and aggregations.

## Architecture

### Components

1. **Celery Workers** - Process background tasks
2. **Celery Beat** - Schedules periodic tasks
3. **Redis** - Message broker and result backend
4. **PostgreSQL** - Data storage
5. **Flower** - Web-based monitoring UI (optional)

### Database Schema

#### Aggregation Tables

- `analytics.execution_metrics_hourly` - Hourly execution statistics
- `analytics.execution_metrics_daily` - Daily execution rollups
- `analytics.user_activity_hourly` - Hourly user activity aggregations
- `analytics.credit_consumption_hourly` - Hourly credit usage tracking

#### Materialized Views

- `analytics.mv_daily_user_metrics` - Daily user metrics summary
- `analytics.mv_hourly_execution_stats` - Hourly execution statistics
- `analytics.mv_workspace_summary` - Workspace-level summary data

## Task Schedule

### Periodic Tasks

| Task | Schedule | Description | Timeout |
|------|----------|-------------|---------|
| `hourly_rollup` | Every hour at :05 | Aggregate last hour's data | 1 hour |
| `daily_rollup` | Daily at 1:00 AM | Aggregate previous day's data | 2 hours |
| `weekly_rollup` | Monday at 2:00 AM | Aggregate previous week's data | 4 hours |
| `refresh_materialized_views` | Every 15 minutes | Refresh materialized views | 15 minutes |
| `cleanup_old_data` | Daily at 3:00 AM | Remove old data per retention policy | 2 hours |
| `health_check` | Every 5 minutes | System health monitoring | 5 minutes |

## Configuration

### Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
CELERY_BROKER_URL=redis://host:6379/1
CELERY_RESULT_BACKEND=redis://host:6379/2

# Optional
APP_ENV=production  # development, staging, production
HOURLY_ROLLUP_ENABLED=true
DAILY_ROLLUP_ENABLED=true
WEEKLY_ROLLUP_ENABLED=true
MONTHLY_ROLLUP_ENABLED=true
```

### Feature Flags

Toggle individual rollup tasks via settings in `src/core/config.py`:

```python
HOURLY_ROLLUP_ENABLED: bool = True
DAILY_ROLLUP_ENABLED: bool = True
WEEKLY_ROLLUP_ENABLED: bool = True
MONTHLY_ROLLUP_ENABLED: bool = True
```

## Deployment

### Docker Compose

Start all services:

```bash
docker-compose up -d
```

Start specific services:

```bash
# Backend API only
docker-compose up -d backend

# Celery worker only
docker-compose up -d celery-worker

# Celery beat (scheduler) only
docker-compose up -d celery-beat

# Flower monitoring
docker-compose up -d flower
```

### Manual Deployment

#### Start Celery Worker

```bash
cd backend
celery -A src.celery_app worker --loglevel=info --concurrency=4
```

#### Start Celery Beat

```bash
cd backend
celery -A src.celery_app beat --loglevel=info
```

#### Start Flower Monitoring

```bash
cd backend
celery -A src.celery_app flower --port=5555
```

Access Flower at http://localhost:5555

## Database Migrations

### Apply Migrations

```bash
cd backend
alembic upgrade head
```

### Create Materialized Views

Materialized views are created automatically via the aggregation service.
To manually create them:

```python
from src.core.database import async_session_maker
from src.services.aggregation.materialized import create_materialized_views

async def setup_views():
    async with async_session_maker() as db:
        result = await create_materialized_views(db)
        print(result)
```

## Manual Task Execution

### Trigger Tasks Manually

```python
from src.tasks.aggregation import hourly_rollup_task, daily_rollup_task
from datetime import datetime

# Trigger hourly rollup for specific hour
hourly_rollup_task.apply_async(
    args=[datetime(2025, 1, 9, 14, 0).isoformat()]
)

# Trigger daily rollup for specific date
daily_rollup_task.apply_async(
    args=[datetime(2025, 1, 9).isoformat()]
)
```

### Backfill Historical Data

```python
from src.tasks.aggregation import backfill_aggregations_task

# Backfill hourly data for date range
backfill_aggregations_task.apply_async(
    kwargs={
        'start_date': '2025-01-01T00:00:00',
        'end_date': '2025-01-09T00:00:00',
        'granularity': 'hourly'
    }
)
```

## Monitoring

### Flower UI

Access Flower at http://localhost:5555 to:
- Monitor task execution
- View worker status
- Inspect task history
- Retry failed tasks
- Revoke running tasks

### Health Checks

Health check task runs every 5 minutes and monitors:
- Database connectivity
- Recent aggregation activity
- Data freshness
- Overall system health

View health check results in Flower or query directly:

```python
from src.tasks.maintenance import health_check_task

result = health_check_task.apply_async()
print(result.get())
```

### Logging

Logs are output to stdout/stderr and can be viewed:

```bash
# Docker logs
docker-compose logs -f celery-worker
docker-compose logs -f celery-beat

# Manual deployment
# Logs appear in terminal where worker/beat was started
```

## Performance Tuning

### Worker Concurrency

Adjust worker concurrency based on available CPU cores:

```bash
# 4 concurrent workers
celery -A src.celery_app worker --concurrency=4

# Autoscale between 2-8 workers
celery -A src.celery_app worker --autoscale=8,2
```

### Task Timeouts

Configure in `src/celery_app.py`:

```python
celery_app.conf.update(
    task_time_limit=3600,  # Hard limit (1 hour)
    task_soft_time_limit=3300,  # Soft limit (55 minutes)
)
```

### Queue Routing

Tasks are routed to specific queues for isolation:

- `aggregation` queue - Aggregation tasks
- `maintenance` queue - Maintenance tasks

Start workers for specific queues:

```bash
celery -A src.celery_app worker -Q aggregation
celery -A src.celery_app worker -Q maintenance
```

## Troubleshooting

### Tasks Not Running

1. Check Celery beat is running
2. Verify Redis connectivity
3. Check worker logs for errors
4. Verify task schedule in Flower

### Slow Performance

1. Check database query performance
2. Verify indices exist on aggregation tables
3. Adjust worker concurrency
4. Consider partitioning large tables

### Failed Tasks

1. View error in Flower UI
2. Check worker logs
3. Retry task manually
4. Fix underlying issue and rerun

### Database Lock Issues

If you encounter lock timeouts:

1. Ensure `CONCURRENTLY` is used for materialized view refreshes
2. Check for long-running queries blocking aggregations
3. Consider running heavy tasks during low-traffic periods

## Performance Targets

| Task | Target Duration | Max Duration |
|------|----------------|--------------|
| Hourly rollup | < 5 minutes | 10 minutes |
| Daily rollup | < 15 minutes | 30 minutes |
| Weekly rollup | < 30 minutes | 1 hour |
| View refresh | < 2 minutes | 5 minutes |
| Health check | < 30 seconds | 1 minute |

## Security Considerations

### Resource Limits

- Tasks have hard timeouts to prevent runaway processes
- Workers restart after processing 1000 tasks to prevent memory leaks
- Database connection pooling limits concurrent connections

### Access Control

- Celery tasks run with database credentials from environment
- Redis should be password-protected in production
- Flower UI should be behind authentication in production

### Data Retention

The cleanup task removes old data based on retention policy:
- Raw execution logs: 90 days (configurable)
- User activity events: 90 days (configurable)
- Hourly aggregations: 180 days (2x retention)
- Daily aggregations: Permanent

## Testing

### Run Tests

```bash
cd backend
pytest tests/test_aggregation_jobs.py -v
```

### Test Coverage

```bash
pytest tests/test_aggregation_jobs.py --cov=src.services.aggregation --cov=src.tasks
```

## API Reference

### Tasks

#### `hourly_rollup_task(target_hour: str = None)`

Aggregate data for a specific hour.

**Args:**
- `target_hour` (optional): ISO format datetime string

**Returns:**
- Dictionary with rollup results

#### `daily_rollup_task(target_date: str = None)`

Aggregate data for a specific day.

**Args:**
- `target_date` (optional): ISO format date string

**Returns:**
- Dictionary with rollup results

#### `refresh_materialized_views_task()`

Refresh all materialized views.

**Returns:**
- Dictionary with refresh results

#### `cleanup_old_data_task(retention_days: int = 90)`

Clean up old data based on retention policy.

**Args:**
- `retention_days`: Number of days to retain

**Returns:**
- Dictionary with cleanup results

#### `health_check_task()`

Perform system health checks.

**Returns:**
- Dictionary with health status

## Support

For issues or questions:
1. Check logs in Flower UI
2. Review worker logs
3. Consult this documentation
4. Contact the development team

## Future Enhancements

- [ ] Parallel aggregation processing
- [ ] Custom aggregation windows
- [ ] Real-time aggregation streaming
- [ ] Advanced anomaly detection
- [ ] Automatic performance tuning
- [ ] Multi-region replication
