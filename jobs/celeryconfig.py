"""Celery configuration for background tasks."""

import os
from celery import Celery
from celery.schedules import crontab

# Initialize Celery
app = Celery('shadower_analytics')

# Configure Celery using environment variables
app.conf.broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
app.conf.result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')

# Task configuration
app.conf.task_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.result_serializer = 'json'
app.conf.timezone = 'UTC'
app.conf.enable_utc = True

# Task routes
app.conf.task_routes = {
    'aggregation.*': {'queue': 'aggregation'},
    'alerts.*': {'queue': 'alerts'},
    'maintenance.*': {'queue': 'maintenance'},
}

# Scheduled tasks
app.conf.beat_schedule = {
    'hourly-rollup': {
        'task': 'aggregation.hourly_rollup.run_hourly_rollup',
        'schedule': crontab(minute=0),  # Every hour
    },
    'daily-rollup': {
        'task': 'aggregation.daily_rollup.run_daily_rollup',
        'schedule': crontab(hour=0, minute=15),  # Daily at 00:15
    },
    'weekly-rollup': {
        'task': 'aggregation.weekly_rollup.run_weekly_rollup',
        'schedule': crontab(day_of_week=1, hour=1, minute=0),  # Mondays at 01:00
    },
    'monthly-rollup': {
        'task': 'aggregation.monthly_rollup.run_monthly_rollup',
        'schedule': crontab(day_of_month=1, hour=2, minute=0),  # 1st of month at 02:00
    },
    'check-thresholds': {
        'task': 'alerts.threshold_checker.check_all_thresholds',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'cleanup-old-data': {
        'task': 'maintenance.cleanup.cleanup_old_data',
        'schedule': crontab(hour=3, minute=0),  # Daily at 03:00
    },
}

# Auto-discover tasks
app.autodiscover_tasks(['aggregation', 'alerts', 'maintenance'])
