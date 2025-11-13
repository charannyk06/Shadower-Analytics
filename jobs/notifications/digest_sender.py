"""Celery tasks for sending digest notifications."""

import logging
from datetime import datetime, timedelta
from typing import List

from jobs.celeryconfig import app
from backend.src.core.database import get_db
from backend.src.services.notifications import (
    NotificationSystem,
    NotificationChannelManager,
    TemplateEngine,
    PreferenceManager,
    DeliveryTracker,
    DigestBuilder,
)
from backend.src.api.websocket.manager import get_connection_manager

logger = logging.getLogger(__name__)


@app.task(name="notifications.send_daily_digests", bind=True)
def send_daily_digests(self):
    """Send daily digest notifications to all subscribed users."""
    try:
        logger.info("Sending daily digest notifications")

        async def send_digests():
            async for db in get_db():
                # Initialize services
                websocket_manager = get_connection_manager()
                channel_manager = NotificationChannelManager(websocket_manager)
                template_engine = TemplateEngine(db)
                preference_manager = PreferenceManager(db)
                delivery_tracker = DeliveryTracker(db)
                digest_builder = DigestBuilder(db)

                notification_system = NotificationSystem(
                    db=db,
                    channel_manager=channel_manager,
                    template_engine=template_engine,
                    preference_manager=preference_manager,
                    delivery_tracker=delivery_tracker,
                )

                # Get pending daily digests
                pending_digests = await digest_builder.get_pending_digests(
                    digest_type="daily"
                )

                sent = 0
                failed = 0

                for digest in pending_digests:
                    try:
                        success = await digest_builder.send_digest(
                            digest.id, notification_system
                        )
                        if success:
                            sent += 1
                        else:
                            failed += 1
                    except Exception as e:
                        logger.error(f"Failed to send digest {digest.id}: {e}")
                        failed += 1

                logger.info(f"Sent {sent} daily digests, {failed} failed")
                return {"sent": sent, "failed": failed}

        import asyncio
        return asyncio.run(send_digests())

    except Exception as e:
        logger.error(f"Error sending daily digests: {e}")
        raise


@app.task(name="notifications.send_weekly_digests", bind=True)
def send_weekly_digests(self):
    """Send weekly digest notifications to all subscribed users."""
    try:
        logger.info("Sending weekly digest notifications")

        async def send_digests():
            async for db in get_db():
                # Initialize services
                websocket_manager = get_connection_manager()
                channel_manager = NotificationChannelManager(websocket_manager)
                template_engine = TemplateEngine(db)
                preference_manager = PreferenceManager(db)
                delivery_tracker = DeliveryTracker(db)
                digest_builder = DigestBuilder(db)

                notification_system = NotificationSystem(
                    db=db,
                    channel_manager=channel_manager,
                    template_engine=template_engine,
                    preference_manager=preference_manager,
                    delivery_tracker=delivery_tracker,
                )

                # Get pending weekly digests
                pending_digests = await digest_builder.get_pending_digests(
                    digest_type="weekly"
                )

                sent = 0
                failed = 0

                for digest in pending_digests:
                    try:
                        success = await digest_builder.send_digest(
                            digest.id, notification_system
                        )
                        if success:
                            sent += 1
                        else:
                            failed += 1
                    except Exception as e:
                        logger.error(f"Failed to send digest {digest.id}: {e}")
                        failed += 1

                logger.info(f"Sent {sent} weekly digests, {failed} failed")
                return {"sent": sent, "failed": failed}

        import asyncio
        return asyncio.run(send_digests())

    except Exception as e:
        logger.error(f"Error sending weekly digests: {e}")
        raise


@app.task(name="notifications.generate_daily_digests", bind=True)
def generate_daily_digests(self):
    """Generate daily digests for all active users."""
    try:
        logger.info("Generating daily digests for all users")

        async def generate():
            async for db in get_db():
                digest_builder = DigestBuilder(db)

                # Calculate period (yesterday)
                period_end = datetime.utcnow().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                period_start = period_end - timedelta(days=1)

                # Get all active workspaces and users
                # TODO: Query actual users from database
                # For now, this is a placeholder
                users_to_digest = []  # [(user_id, workspace_id), ...]

                generated = 0
                for user_id, workspace_id in users_to_digest:
                    try:
                        digest_id = await digest_builder.queue_digest(
                            user_id=user_id,
                            workspace_id=workspace_id,
                            digest_type="daily",
                            period_start=period_start,
                            period_end=period_end,
                        )
                        if digest_id:
                            generated += 1
                    except Exception as e:
                        logger.error(
                            f"Failed to generate digest for user {user_id}: {e}"
                        )

                logger.info(f"Generated {generated} daily digests")
                return {"generated": generated}

        import asyncio
        return asyncio.run(generate())

    except Exception as e:
        logger.error(f"Error generating daily digests: {e}")
        raise


@app.task(name="notifications.generate_weekly_digests", bind=True)
def generate_weekly_digests(self):
    """Generate weekly digests for all active users."""
    try:
        logger.info("Generating weekly digests for all users")

        async def generate():
            async for db in get_db():
                digest_builder = DigestBuilder(db)

                # Calculate period (last week)
                period_end = datetime.utcnow().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                period_start = period_end - timedelta(days=7)

                # Get all active workspaces and users
                # TODO: Query actual users from database
                users_to_digest = []  # [(user_id, workspace_id), ...]

                generated = 0
                for user_id, workspace_id in users_to_digest:
                    try:
                        digest_id = await digest_builder.queue_digest(
                            user_id=user_id,
                            workspace_id=workspace_id,
                            digest_type="weekly",
                            period_start=period_start,
                            period_end=period_end,
                        )
                        if digest_id:
                            generated += 1
                    except Exception as e:
                        logger.error(
                            f"Failed to generate digest for user {user_id}: {e}"
                        )

                logger.info(f"Generated {generated} weekly digests")
                return {"generated": generated}

        import asyncio
        return asyncio.run(generate())

    except Exception as e:
        logger.error(f"Error generating weekly digests: {e}")
        raise
