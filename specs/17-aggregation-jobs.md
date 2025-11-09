# Specification: Aggregation Jobs

## Feature Overview
Background jobs for data aggregation, rollups, and pre-computation to maintain performance at scale.

## Technical Requirements
- Scheduled job execution
- Incremental aggregation
- Error recovery
- Job monitoring
- Resource management

## Implementation Details

### Job Definitions
```python
# backend/src/jobs/aggregation/hourly_rollup.py
from celery import Celery
from datetime import datetime, timedelta

app = Celery('aggregation')

@app.task(name='hourly_rollup')
async def hourly_rollup():
    """Aggregate data every hour"""
    end_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(hours=1)
    
    # Aggregate execution metrics
    await aggregate_execution_metrics(start_time, end_time)
    
    # Aggregate user activity
    await aggregate_user_activity(start_time, end_time)
    
    # Aggregate credit consumption
    await aggregate_credit_consumption(start_time, end_time)
    
    # Update materialized views
    await refresh_materialized_views()

@app.task(name='daily_rollup')
async def daily_rollup():
    """Daily aggregation job"""
    yesterday = datetime.utcnow().date() - timedelta(days=1)
    
    # Daily aggregations
    await aggregate_daily_metrics(yesterday)
    await calculate_daily_health_scores(yesterday)
    await generate_daily_reports(yesterday)

async def aggregate_execution_metrics(start_time, end_time):
    """Aggregate execution metrics for time period"""
    query = """
        INSERT INTO analytics.execution_metrics_hourly (
            workspace_id,
            hour,
            total_executions,
            successful_executions,
            failed_executions,
            avg_runtime,
            p95_runtime,
            total_credits
        )
        SELECT 
            workspace_id,
            DATE_TRUNC('hour', started_at) as hour,
            COUNT(*) as total_executions,
            COUNT(*) FILTER (WHERE status = 'completed'),
            COUNT(*) FILTER (WHERE status = 'failed'),
            AVG(runtime_seconds),
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY runtime_seconds),
            SUM(credits_consumed)
        FROM public.agent_runs
        WHERE started_at >= $1 AND started_at < $2
        GROUP BY workspace_id, DATE_TRUNC('hour', started_at)
        ON CONFLICT (workspace_id, hour)
        DO UPDATE SET
            total_executions = EXCLUDED.total_executions,
            successful_executions = EXCLUDED.successful_executions,
            failed_executions = EXCLUDED.failed_executions,
            avg_runtime = EXCLUDED.avg_runtime,
            p95_runtime = EXCLUDED.p95_runtime,
            total_credits = EXCLUDED.total_credits,
            updated_at = NOW()
    """
    await db.execute(query, start_time, end_time)
```

### Job Scheduling
```python
# backend/src/jobs/scheduler.py
from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    'hourly-rollup': {
        'task': 'hourly_rollup',
        'schedule': crontab(minute=5),  # Run at 5 minutes past every hour
    },
    'daily-rollup': {
        'task': 'daily_rollup',
        'schedule': crontab(hour=1, minute=0),  # Run at 1:00 AM daily
    },
    'weekly-rollup': {
        'task': 'weekly_rollup',
        'schedule': crontab(day_of_week=1, hour=2, minute=0),  # Monday 2 AM
    },
    'cleanup-old-data': {
        'task': 'cleanup_old_data',
        'schedule': crontab(hour=3, minute=0),  # Run at 3:00 AM daily
    },
    'refresh-materialized-views': {
        'task': 'refresh_materialized_views',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    }
}
```

## Testing Requirements
- Job execution tests
- Aggregation accuracy validation
- Error recovery tests
- Performance under load

## Performance Targets
- Hourly rollup: <5 minutes
- Daily rollup: <15 minutes
- View refresh: <2 minutes

## Security Considerations
- Job execution permissions
- Resource limits
- Audit logging