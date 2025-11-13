"""Celery tasks for processing notification queue."""

import logging
from datetime import datetime
from typing import List

from jobs.celeryconfig import app
from backend.src.core.database import get_db
from backend.src.services.notifications import NotificationSystem, NotificationChannelManager, TemplateEngine, PreferenceManager, DeliveryTracker
from backend.src.api.websocket.manager import get_connection_manager

logger = logging.getLogger(__name__)


@app.task(name="notifications.process_queue", bind=True, max_retries=3)
def process_notification_queue(self, batch_size: int = 100):
    """
    Process pending notifications from queue.

    Args:
        batch_size: Number of notifications to process in one batch
    """
    try:
        logger.info(f"Processing notification queue (batch_size={batch_size})")

        # Get database session (synchronous for Celery)
        # Note: In production, use proper async handling or sync session
        async def process():
            async for db in get_db():
                websocket_manager = get_connection_manager()
                channel_manager = NotificationChannelManager(websocket_manager)
                template_engine = TemplateEngine(db)
                preference_manager = PreferenceManager(db)
                delivery_tracker = DeliveryTracker(db)

                notification_system = NotificationSystem(
                    db=db,
                    channel_manager=channel_manager,
                    template_engine=template_engine,
                    preference_manager=preference_manager,
                    delivery_tracker=delivery_tracker,
                )

                # Get pending notifications
                from backend.src.models.database.tables import NotificationQueue
                from sqlalchemy import select, and_

                result = await db.execute(
                    select(NotificationQueue)
                    .where(
                        and_(
                            NotificationQueue.status == "pending",
                            NotificationQueue.scheduled_for <= datetime.utcnow(),
                            NotificationQueue.attempts < NotificationQueue.max_attempts,
                        )
                    )
                    .limit(batch_size)
                )
                notifications = result.scalars().all()

                processed = 0
                failed = 0

                for notification in notifications:
                    try:
                        success = await notification_system.process_notification(
                            notification.id
                        )
                        if success:
                            processed += 1
                        else:
                            failed += 1
                    except Exception as e:
                        logger.error(
                            f"Failed to process notification {notification.id}: {e}"
                        )
                        failed += 1

                logger.info(
                    f"Processed {processed} notifications, {failed} failed"
                )

                return {"processed": processed, "failed": failed}

        # Run async function
        import asyncio
        return asyncio.run(process())

    except Exception as e:
        logger.error(f"Error processing notification queue: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries * 60)


@app.task(name="notifications.retry_failed", bind=True)
def retry_failed_notifications(self):
    """Retry failed notifications that haven't exceeded max attempts."""
    try:
        logger.info("Retrying failed notifications")

        async def retry():
            async for db in get_db():
                from backend.src.models.database.tables import NotificationQueue
                from sqlalchemy import select, and_

                # Get failed notifications that can be retried
                result = await db.execute(
                    select(NotificationQueue).where(
                        and_(
                            NotificationQueue.status == "failed",
                            NotificationQueue.attempts < NotificationQueue.max_attempts,
                        )
                    )
                )
                notifications = result.scalars().all()

                retried = 0
                for notification in notifications:
                    # Reset to pending for retry
                    notification.status = "pending"
                    notification.error_message = None
                    retried += 1

                await db.commit()

                logger.info(f"Queued {retried} notifications for retry")
                return {"retried": retried}

        import asyncio
        return asyncio.run(retry())

    except Exception as e:
        logger.error(f"Error retrying failed notifications: {e}")
        raise


@app.task(name="notifications.cleanup_old", bind=True)
def cleanup_old_notifications(self, days: int = 90):
    """
    Clean up old read notifications.

    Args:
        days: Number of days to keep
    """
    try:
        logger.info(f"Cleaning up notifications older than {days} days")

        async def cleanup():
            async for db in get_db():
                from backend.src.models.database.tables import NotificationLog
                from sqlalchemy import delete, and_
                from datetime import timedelta

                cutoff_date = datetime.utcnow() - timedelta(days=days)

                # Delete old read notifications
                result = await db.execute(
                    delete(NotificationLog).where(
                        and_(
                            NotificationLog.sent_at < cutoff_date,
                            NotificationLog.read_at.isnot(None),
                        )
                    )
                )

                await db.commit()

                deleted_count = result.rowcount
                logger.info(f"Cleaned up {deleted_count} old notifications")
                return {"deleted": deleted_count}

        import asyncio
        return asyncio.run(cleanup())

    except Exception as e:
        logger.error(f"Error cleaning up old notifications: {e}")
        raise
