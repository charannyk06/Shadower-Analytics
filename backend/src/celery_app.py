"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab
from src.core.config import settings

# Initialize Celery app
celery_app = Celery(
    'shadower_analytics',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        'src.tasks.aggregation',
        'src.tasks.maintenance',
        'src.tasks.exports',
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Task execution settings
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,

    # Result backend settings
    result_expires=86400,  # 24 hours
    result_persistent=True,

    # Retry settings
    task_autoretry_for=(Exception,),
    task_retry_kwargs={'max_retries': 3},
    task_retry_backoff=True,
    task_retry_backoff_max=600,  # 10 minutes max backoff
    task_retry_jitter=True,

    # Performance settings
    worker_disable_rate_limits=True,
    task_compression='gzip',
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'hourly-rollup': {
        'task': 'tasks.aggregation.hourly_rollup',
        'schedule': crontab(minute=5),  # Run at 5 minutes past every hour
        'options': {'expires': 3600}  # Task expires after 1 hour
    },
    'daily-rollup': {
        'task': 'tasks.aggregation.daily_rollup',
        'schedule': crontab(hour=1, minute=0),  # Run at 1:00 AM daily
        'options': {'expires': 7200}  # Task expires after 2 hours
    },
    'weekly-rollup': {
        'task': 'tasks.aggregation.weekly_rollup',
        'schedule': crontab(day_of_week=1, hour=2, minute=0),  # Monday 2 AM
        'options': {'expires': 14400}  # Task expires after 4 hours
    },
    'cleanup-old-data': {
        'task': 'tasks.maintenance.cleanup_old_data',
        'schedule': crontab(hour=3, minute=0),  # Run at 3:00 AM daily
        'options': {'expires': 7200}  # Task expires after 2 hours
    },
    'refresh-materialized-views': {
        'task': 'tasks.aggregation.refresh_materialized_views',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
        'options': {'expires': 900}  # Task expires after 15 minutes
    },
    'health-check': {
        'task': 'tasks.maintenance.health_check',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
        'options': {'expires': 300}  # Task expires after 5 minutes
    },
    'cleanup-old-exports': {
        'task': 'tasks.exports.cleanup_old_exports',
        'schedule': crontab(hour=4, minute=0),  # Run at 4:00 AM daily
        'options': {'expires': 7200}  # Task expires after 2 hours
    }
}

# Task routing (optional - for advanced setups with multiple queues)
celery_app.conf.task_routes = {
    'tasks.aggregation.*': {'queue': 'aggregation'},
    'tasks.maintenance.*': {'queue': 'maintenance'},
    'tasks.exports.*': {'queue': 'exports'},
}
