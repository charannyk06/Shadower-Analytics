"""Celery application configuration for background task processing."""

from celery import Celery
from celery.schedules import crontab
from src.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery(
    'shadower_analytics',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        'src.tasks.aggregation',
        'src.tasks.maintenance',
        'src.tasks.exports',
        'src.tasks.alerts',
        'src.tasks.reports',
        'src.tasks.analytics',
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
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Worker settings
    worker_prefetch_multiplier=4,  # Prefetch 4 tasks per worker
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    worker_disable_rate_limits=False,  # Enable rate limiting

    # Result backend settings
    result_expires=86400,  # 24 hours
    result_persistent=True,
    result_compression='gzip',

    # Retry settings
    task_autoretry_for=(Exception,),
    task_retry_kwargs={'max_retries': 3},
    task_retry_backoff=True,
    task_retry_backoff_max=600,  # 10 minutes max backoff
    task_retry_jitter=True,

    # Performance settings
    task_compression='gzip',
    result_compression='gzip',

    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,

    # Security
    task_always_eager=False,  # Never execute tasks synchronously
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Aggregation tasks
    'hourly-rollup': {
        'task': 'src.tasks.aggregation.hourly_rollup',
        'schedule': crontab(minute=5),  # Run at 5 minutes past every hour
        'options': {'expires': 3600, 'priority': 5}
    },
    'daily-rollup': {
        'task': 'src.tasks.aggregation.daily_rollup',
        'schedule': crontab(hour=1, minute=0),  # Run at 1:00 AM daily
        'options': {'expires': 7200, 'priority': 5}
    },
    'weekly-rollup': {
        'task': 'src.tasks.aggregation.weekly_rollup',
        'schedule': crontab(day_of_week=1, hour=2, minute=0),  # Monday 2 AM
        'options': {'expires': 14400, 'priority': 5}
    },
    'refresh-materialized-views': {
        'task': 'src.tasks.aggregation.refresh_materialized_views',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
        'options': {'expires': 900, 'priority': 7}
    },

    # Analytics tasks
    'calculate-daily-metrics': {
        'task': 'src.tasks.analytics.calculate_daily_metrics',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
        'options': {'expires': 3600, 'priority': 6}
    },

    # Report tasks
    'generate-scheduled-reports': {
        'task': 'src.tasks.reports.generate_scheduled_reports',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
        'options': {'expires': 1800, 'priority': 4}
    },

    # Export tasks
    'cleanup-old-exports': {
        'task': 'src.tasks.exports.cleanup_old_exports',
        'schedule': crontab(hour=4, minute=0),  # Run at 4:00 AM daily
        'options': {'expires': 7200, 'priority': 3}
    },

    # Alert tasks
    'evaluate-alert-rules': {
        'task': 'src.tasks.alerts.evaluate_alert_rules',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
        'options': {'expires': 300, 'priority': 9}
    },
    'check-alert-escalations': {
        'task': 'src.tasks.alerts.check_escalations',
        'schedule': crontab(minute='*/10'),  # Every 10 minutes
        'options': {'expires': 600, 'priority': 8}
    },
    'cleanup-old-alerts': {
        'task': 'src.tasks.alerts.cleanup_old_alerts',
        'schedule': crontab(hour=4, minute=30),  # Run at 4:30 AM daily (30 min after export cleanup)
        'options': {'expires': 7200, 'priority': 3}
    },

    # Maintenance tasks
    'cleanup-old-data': {
        'task': 'src.tasks.maintenance.cleanup_old_data',
        'schedule': crontab(hour=3, minute=0),  # Run at 3:00 AM daily
        'options': {'expires': 7200, 'priority': 3}
    },
    'health-check': {
        'task': 'src.tasks.maintenance.health_check',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
        'options': {'expires': 300, 'priority': 10}
    },
}

# Task routing (optional - for advanced setups with multiple queues)
celery_app.conf.task_routes = {
    'src.tasks.aggregation.*': {'queue': 'aggregation'},
    'src.tasks.maintenance.*': {'queue': 'maintenance'},
    'src.tasks.exports.*': {'queue': 'exports'},
    'src.tasks.alerts.*': {'queue': 'alerts'},
    'src.tasks.reports.*': {'queue': 'reports'},
    'src.tasks.analytics.*': {'queue': 'analytics'},
}

# Queue configuration
celery_app.conf.task_default_queue = 'default'
celery_app.conf.task_default_exchange = 'default'
celery_app.conf.task_default_routing_key = 'default'


# Celery signals for logging and monitoring
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    logger.info(f"Request: {self.request!r}")
    return "Celery is working!"


# Event handlers
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup any additional periodic tasks after configuration."""
    logger.info("Celery periodic tasks configured")


@celery_app.on_after_finalize.connect
def setup_task_handlers(sender, **kwargs):
    """Setup task event handlers."""
    logger.info("Celery task handlers configured")
