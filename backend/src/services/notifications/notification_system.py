"""Core notification system service."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from src.models.database.tables import (
    NotificationQueue,
    NotificationLog,
    NotificationPreference,
)
from src.models.schemas.notifications import (
    NotificationChannelEnum,
    NotificationPriorityEnum,
    NotificationStatusEnum,
    DeliveryStatusEnum,
)
from .channel_manager import NotificationChannelManager
from .template_engine import TemplateEngine
from .preference_manager import PreferenceManager
from .delivery_tracker import DeliveryTracker

logger = logging.getLogger(__name__)


class NotificationSystem:
    """Core notification system for multi-channel notification delivery."""

    def __init__(
        self,
        db: AsyncSession,
        channel_manager: NotificationChannelManager,
        template_engine: TemplateEngine,
        preference_manager: PreferenceManager,
        delivery_tracker: DeliveryTracker,
    ):
        """
        Initialize notification system.

        Args:
            db: Database session
            channel_manager: Channel manager for sending notifications
            template_engine: Template engine for rendering notifications
            preference_manager: Preference manager for user settings
            delivery_tracker: Delivery tracker for metrics
        """
        self.db = db
        self.channel_manager = channel_manager
        self.template_engine = template_engine
        self.preference_manager = preference_manager
        self.delivery_tracker = delivery_tracker
        logger.info("NotificationSystem initialized")

    async def send_notification(
        self,
        notification_type: str,
        recipients: List[str],
        data: Dict[str, Any],
        workspace_id: str,
        priority: str = "normal",
        channels: Optional[List[str]] = None,
        scheduled_for: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Send notification through user-preferred channels.

        Args:
            notification_type: Type of notification (e.g., 'alert_critical', 'digest_daily')
            recipients: List of user IDs to send to
            data: Notification data for template rendering
            workspace_id: Workspace ID
            priority: Priority level (low, normal, high, urgent)
            channels: Optional list of channels to send to (overrides user preferences)
            scheduled_for: Optional scheduled delivery time

        Returns:
            Dict with notification IDs and status
        """
        logger.info(
            f"Sending notification type={notification_type} to {len(recipients)} recipients"
        )

        notification_ids = []
        queued_count = 0
        failed_count = 0

        for recipient_id in recipients:
            try:
                # Get user's preferred channels if not specified
                if channels is None:
                    user_channels = await self.preference_manager.get_enabled_channels(
                        user_id=recipient_id,
                        workspace_id=workspace_id,
                        notification_type=notification_type,
                    )
                else:
                    user_channels = channels

                # Queue notification for each channel
                for channel in user_channels:
                    notification_id = await self._queue_notification(
                        notification_type=notification_type,
                        recipient_id=recipient_id,
                        channel=channel,
                        data=data,
                        workspace_id=workspace_id,
                        priority=priority,
                        scheduled_for=scheduled_for,
                    )
                    notification_ids.append(notification_id)
                    queued_count += 1

            except Exception as e:
                logger.error(
                    f"Failed to queue notification for recipient {recipient_id}: {e}"
                )
                failed_count += 1

        logger.info(
            f"Queued {queued_count} notifications, {failed_count} failed"
        )

        return {
            "notification_ids": notification_ids,
            "queued_count": queued_count,
            "failed_count": failed_count,
            "message": f"Successfully queued {queued_count} notifications",
        }

    async def _queue_notification(
        self,
        notification_type: str,
        recipient_id: str,
        channel: str,
        data: Dict[str, Any],
        workspace_id: str,
        priority: str = "normal",
        scheduled_for: Optional[datetime] = None,
    ) -> str:
        """
        Queue a single notification for delivery.

        Args:
            notification_type: Type of notification
            recipient_id: User ID
            channel: Notification channel
            data: Notification data
            workspace_id: Workspace ID
            priority: Priority level
            scheduled_for: Scheduled delivery time

        Returns:
            Notification ID
        """
        notification_id = str(uuid4())

        # Create notification queue entry
        queue_entry = NotificationQueue(
            id=notification_id,
            notification_type=notification_type,
            recipient_id=recipient_id,
            recipient_email=data.get("recipient_email"),
            channel=channel,
            priority=priority,
            payload={
                "data": data,
                "workspace_id": workspace_id,
                "notification_type": notification_type,
            },
            status=NotificationStatusEnum.PENDING.value,
            scheduled_for=scheduled_for or datetime.utcnow(),
            attempts=0,
            max_attempts=3,
        )

        self.db.add(queue_entry)
        await self.db.commit()
        await self.db.refresh(queue_entry)

        logger.debug(
            f"Queued notification {notification_id} for {recipient_id} via {channel}"
        )

        return notification_id

    async def process_notification(self, notification_id: str) -> bool:
        """
        Process a queued notification.

        Args:
            notification_id: Notification ID to process

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get notification from queue
            result = await self.db.execute(
                select(NotificationQueue).where(
                    NotificationQueue.id == notification_id
                )
            )
            notification = result.scalar_one_or_none()

            if not notification:
                logger.warning(f"Notification {notification_id} not found")
                return False

            # Update status to processing
            notification.status = NotificationStatusEnum.PROCESSING.value
            notification.attempts += 1
            notification.last_attempt_at = datetime.utcnow()
            await self.db.commit()

            # Render template
            content = await self.template_engine.render(
                notification_type=notification.notification_type,
                channel=notification.channel,
                data=notification.payload.get("data", {}),
            )

            if not content:
                raise Exception("Failed to render template")

            # Send through channel
            success = await self.channel_manager.send(
                channel=notification.channel,
                recipient_id=notification.recipient_id,
                recipient_email=notification.recipient_email,
                content=content,
            )

            if success:
                # Update queue status
                notification.status = NotificationStatusEnum.DELIVERED.value
                notification.delivered_at = datetime.utcnow()

                # Log delivery
                await self._log_notification(
                    notification_id=notification_id,
                    user_id=notification.recipient_id,
                    workspace_id=notification.payload.get("workspace_id"),
                    notification_type=notification.notification_type,
                    channel=notification.channel,
                    content=content,
                    delivery_status=DeliveryStatusEnum.DELIVERED.value,
                )

                # Track delivery
                await self.delivery_tracker.track_delivery(
                    notification_id=notification_id,
                    channel=notification.channel,
                    status="delivered",
                )

                await self.db.commit()
                logger.info(
                    f"Successfully processed notification {notification_id}"
                )
                return True
            else:
                raise Exception("Channel send failed")

        except Exception as e:
            logger.error(
                f"Failed to process notification {notification_id}: {e}"
            )

            # Update failure status
            notification.status = NotificationStatusEnum.FAILED.value
            notification.failed_at = datetime.utcnow()
            notification.error_message = str(e)

            # Log failure
            await self._log_notification(
                notification_id=notification_id,
                user_id=notification.recipient_id,
                workspace_id=notification.payload.get("workspace_id"),
                notification_type=notification.notification_type,
                channel=notification.channel,
                content=content if 'content' in locals() else {},
                delivery_status=DeliveryStatusEnum.FAILED.value,
            )

            await self.db.commit()

            # Track failure
            await self.delivery_tracker.track_delivery(
                notification_id=notification_id,
                channel=notification.channel,
                status="failed",
                error=str(e),
            )

            return False

    async def _log_notification(
        self,
        notification_id: str,
        user_id: str,
        workspace_id: str,
        notification_type: str,
        channel: str,
        content: Dict[str, Any],
        delivery_status: str,
    ) -> None:
        """
        Log notification to history.

        Args:
            notification_id: Notification ID
            user_id: User ID
            workspace_id: Workspace ID
            notification_type: Notification type
            channel: Channel used
            content: Rendered content
            delivery_status: Delivery status
        """
        log_entry = NotificationLog(
            id=str(uuid4()),
            notification_id=notification_id,
            user_id=user_id,
            workspace_id=workspace_id,
            notification_type=notification_type,
            channel=channel,
            subject=content.get("subject"),
            preview=content.get("preview"),
            full_content=str(content.get("body")),
            sent_at=datetime.utcnow(),
            delivery_status=delivery_status,
            tracking_data={},
        )

        self.db.add(log_entry)
        logger.debug(f"Logged notification {notification_id}")

    async def get_notifications(
        self,
        user_id: str,
        workspace_id: Optional[str] = None,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Get user's notifications.

        Args:
            user_id: User ID
            workspace_id: Optional workspace ID filter
            unread_only: Only return unread notifications
            limit: Maximum number of notifications
            offset: Offset for pagination

        Returns:
            Dict with notifications and metadata
        """
        filters = [NotificationLog.user_id == user_id]

        if workspace_id:
            filters.append(NotificationLog.workspace_id == workspace_id)

        if unread_only:
            filters.append(NotificationLog.read_at.is_(None))

        # Get notifications
        result = await self.db.execute(
            select(NotificationLog)
            .where(and_(*filters))
            .order_by(NotificationLog.sent_at.desc())
            .limit(limit)
            .offset(offset)
        )
        notifications = result.scalars().all()

        # Get unread count
        unread_result = await self.db.execute(
            select(NotificationLog)
            .where(
                and_(
                    NotificationLog.user_id == user_id,
                    NotificationLog.read_at.is_(None),
                    *([NotificationLog.workspace_id == workspace_id] if workspace_id else [])
                )
            )
        )
        unread_count = len(unread_result.scalars().all())

        return {
            "notifications": notifications,
            "total": len(notifications),
            "unread_count": unread_count,
            "has_more": len(notifications) == limit,
        }

    async def mark_as_read(
        self, notification_ids: List[str], user_id: str
    ) -> int:
        """
        Mark notifications as read.

        Args:
            notification_ids: List of notification IDs
            user_id: User ID (for security check)

        Returns:
            Number of notifications updated
        """
        result = await self.db.execute(
            select(NotificationLog).where(
                and_(
                    NotificationLog.id.in_(notification_ids),
                    NotificationLog.user_id == user_id,
                    NotificationLog.read_at.is_(None),
                )
            )
        )
        notifications = result.scalars().all()

        updated_count = 0
        for notification in notifications:
            notification.read_at = datetime.utcnow()
            if notification.delivery_status == DeliveryStatusEnum.DELIVERED.value:
                notification.delivery_status = DeliveryStatusEnum.READ.value
            updated_count += 1

        await self.db.commit()

        logger.info(f"Marked {updated_count} notifications as read for user {user_id}")
        return updated_count

    async def get_unread_count(
        self, user_id: str, workspace_id: Optional[str] = None
    ) -> int:
        """
        Get unread notification count.

        Args:
            user_id: User ID
            workspace_id: Optional workspace ID filter

        Returns:
            Unread count
        """
        filters = [
            NotificationLog.user_id == user_id,
            NotificationLog.read_at.is_(None),
            NotificationLog.channel == NotificationChannelEnum.IN_APP.value,
        ]

        if workspace_id:
            filters.append(NotificationLog.workspace_id == workspace_id)

        result = await self.db.execute(
            select(NotificationLog).where(and_(*filters))
        )
        notifications = result.scalars().all()

        return len(notifications)

    async def send_digest(
        self, workspace_id: str, digest_type: str, period: str
    ) -> Dict[str, Any]:
        """
        Send periodic digest notifications.

        This method is implemented in the DigestBuilder class.
        See digest_builder.py for implementation.

        Args:
            workspace_id: Workspace ID
            digest_type: Type of digest
            period: Time period

        Returns:
            Dict with digest send status
        """
        # This will be implemented by DigestBuilder
        logger.info(f"Digest sending for workspace {workspace_id} type={digest_type}")
        return {"status": "not_implemented"}

    async def manage_subscription(
        self, user_id: str, notification_type: str, action: str
    ) -> Dict[str, Any]:
        """
        Manage notification subscriptions.

        This method is implemented in the PreferenceManager class.
        See preference_manager.py for implementation.

        Args:
            user_id: User ID
            notification_type: Type of notification
            action: Action to perform (subscribe/unsubscribe)

        Returns:
            Dict with subscription status
        """
        # This will be implemented by PreferenceManager
        logger.info(
            f"Subscription management for user {user_id} type={notification_type} action={action}"
        )
        return {"status": "not_implemented"}
