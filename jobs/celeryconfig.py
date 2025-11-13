"""Celery configuration for background tasks."""

import os
from celery import Celery
from celery.schedules import crontab

# Initialize Celery
app = Celery("shadower_analytics")

# Configure Celery using environment variables
app.conf.broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
app.conf.result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

# Task configuration
app.conf.task_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.result_serializer = "json"
app.conf.timezone = "UTC"
app.conf.enable_utc = True

# Task routes
app.conf.task_routes = {
    "aggregation.*": {"queue": "aggregation"},
    "alerts.*": {"queue": "alerts"},
    "notifications.*": {"queue": "notifications"},
    "maintenance.*": {"queue": "maintenance"},
}

# Scheduled tasks
app.conf.beat_schedule = {
    "hourly-rollup": {
        "task": "aggregation.hourly_rollup.run_hourly_rollup",
        "schedule": crontab(minute=0),  # Every hour
    },
    "daily-rollup": {
        "task": "aggregation.daily_rollup.run_daily_rollup",
        "schedule": crontab(hour=0, minute=15),  # Daily at 00:15
    },
    "weekly-rollup": {
        "task": "aggregation.weekly_rollup.run_weekly_rollup",
        "schedule": crontab(day_of_week=1, hour=1, minute=0),  # Mondays at 01:00
    },
    "monthly-rollup": {
        "task": "aggregation.monthly_rollup.run_monthly_rollup",
        "schedule": crontab(day_of_month=1, hour=2, minute=0),  # 1st of month at 02:00
    },
    "check-thresholds": {
        "task": "alerts.threshold_checker.check_all_thresholds",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
    "cleanup-old-data": {
        "task": "maintenance.cleanup.cleanup_old_data",
        "schedule": crontab(hour=3, minute=0),  # Daily at 03:00
    },
    # Cache maintenance tasks
    "cache-cleanup": {
        "task": "maintenance.cache_maintenance.cleanup_expired_cache",
        "schedule": crontab(hour=4, minute=0),  # Daily at 04:00
    },
    "cache-health-check": {
        "task": "maintenance.cache_maintenance.cache_health_check",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
    "cache-refresh-materialized": {
        "task": "maintenance.cache_maintenance.refresh_materialized_cache",
        "schedule": crontab(minute=30),  # Every hour at :30
    },
    "cache-warm-priority": {
        "task": "maintenance.cache_maintenance.warm_priority_cache",
        "schedule": crontab(hour="*/6", minute=0),  # Every 6 hours
    },
    # Notification tasks
    "process-notification-queue": {
        "task": "notifications.notification_processor.process_notification_queue",
        "schedule": crontab(minute="*/2"),  # Every 2 minutes
    },
    "retry-failed-notifications": {
        "task": "notifications.notification_processor.retry_failed_notifications",
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
    },
    "cleanup-old-notifications": {
        "task": "notifications.notification_processor.cleanup_old_notifications",
        "schedule": crontab(hour=5, minute=0),  # Daily at 05:00
    },
    "generate-daily-digests": {
        "task": "notifications.digest_sender.generate_daily_digests",
        "schedule": crontab(hour=7, minute=0),  # Daily at 07:00 UTC
    },
    "send-daily-digests": {
        "task": "notifications.digest_sender.send_daily_digests",
        "schedule": crontab(hour=8, minute=0),  # Daily at 08:00 UTC
    },
    "generate-weekly-digests": {
        "task": "notifications.digest_sender.generate_weekly_digests",
        "schedule": crontab(day_of_week=1, hour=7, minute=30),  # Mondays at 07:30 UTC
    },
    "send-weekly-digests": {
        "task": "notifications.digest_sender.send_weekly_digests",
        "schedule": crontab(day_of_week=1, hour=8, minute=30),  # Mondays at 08:30 UTC
    },
}

# Auto-discover tasks
app.autodiscover_tasks(["aggregation", "alerts", "notifications", "maintenance"])
