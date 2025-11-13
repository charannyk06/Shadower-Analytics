"""Delivery tracker for notification metrics and monitoring."""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from src.models.database.tables import NotificationLog, NotificationQueue

logger = logging.getLogger(__name__)


class DeliveryTracker:
    """Tracker for notification delivery metrics and status."""

    def __init__(self, db: AsyncSession):
        """
        Initialize delivery tracker.

        Args:
            db: Database session
        """
        self.db = db
        logger.info("DeliveryTracker initialized")

    async def track_delivery(
        self,
        notification_id: str,
        channel: str,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        """
        Track notification delivery status.

        Args:
            notification_id: Notification ID
            channel: Channel used
            status: Delivery status
            error: Optional error message
        """
        try:
            logger.info(
                f"Tracking delivery for notification {notification_id} "
                f"channel={channel} status={status}"
            )

            # Additional tracking logic can be added here
            # For example, sending to external monitoring systems,
            # updating metrics tables, etc.

        except Exception as e:
            logger.error(f"Failed to track delivery: {e}")

    async def get_delivery_metrics(
        self,
        workspace_id: Optional[str] = None,
        notification_type: Optional[str] = None,
        channel: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get delivery metrics for notifications.

        Args:
            workspace_id: Optional workspace filter
            notification_type: Optional notification type filter
            channel: Optional channel filter
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Dict with delivery metrics
        """
        # Default to last 30 days if no date range specified
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Build filters
        filters = [
            NotificationLog.sent_at >= start_date,
            NotificationLog.sent_at <= end_date,
        ]

        if workspace_id:
            filters.append(NotificationLog.workspace_id == workspace_id)
        if notification_type:
            filters.append(NotificationLog.notification_type == notification_type)
        if channel:
            filters.append(NotificationLog.channel == channel)

        # Get all notifications matching filters
        result = await self.db.execute(
            select(NotificationLog).where(and_(*filters))
        )
        notifications = result.scalars().all()

        # Calculate metrics
        total_sent = len(notifications)
        total_delivered = sum(
            1 for n in notifications if n.delivery_status in ["delivered", "read", "clicked"]
        )
        total_failed = sum(
            1 for n in notifications if n.delivery_status == "failed"
        )
        total_bounced = sum(
            1 for n in notifications if n.delivery_status == "bounced"
        )
        total_read = sum(
            1 for n in notifications if n.read_at is not None
        )
        total_clicked = sum(
            1 for n in notifications if n.clicked_at is not None
        )

        # Calculate rates
        delivery_rate = (
            (total_delivered / total_sent * 100) if total_sent > 0 else 0
        )
        open_rate = (
            (total_read / total_delivered * 100) if total_delivered > 0 else 0
        )
        click_through_rate = (
            (total_clicked / total_read * 100) if total_read > 0 else 0
        )

        # Calculate average delivery time
        delivery_times = []
        for n in notifications:
            if n.delivered_at and n.sent_at:
                delivery_times.append(
                    (n.delivered_at - n.sent_at).total_seconds()
                )

        avg_delivery_time = (
            sum(delivery_times) / len(delivery_times) if delivery_times else 0
        )

        return {
            "total_sent": total_sent,
            "total_delivered": total_delivered,
            "total_failed": total_failed,
            "total_bounced": total_bounced,
            "total_read": total_read,
            "total_clicked": total_clicked,
            "delivery_rate": round(delivery_rate, 2),
            "open_rate": round(open_rate, 2),
            "click_through_rate": round(click_through_rate, 2),
            "avg_delivery_time_seconds": round(avg_delivery_time, 2),
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
        }

    async def get_channel_performance(
        self, workspace_id: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get performance metrics by channel.

        Args:
            workspace_id: Workspace ID
            days: Number of days to analyze

        Returns:
            List of channel performance metrics
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get notifications grouped by channel
        result = await self.db.execute(
            select(
                NotificationLog.channel,
                func.count(NotificationLog.id).label("total_sent"),
            )
            .where(
                and_(
                    NotificationLog.workspace_id == workspace_id,
                    NotificationLog.sent_at >= start_date,
                )
            )
            .group_by(NotificationLog.channel)
        )
        channel_data = result.all()

        performance = []
        for channel, total_sent in channel_data:
            metrics = await self.get_delivery_metrics(
                workspace_id=workspace_id,
                channel=channel,
                start_date=start_date,
            )
            metrics["channel"] = channel
            performance.append(metrics)

        return performance

    async def get_notification_type_performance(
        self, workspace_id: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get performance metrics by notification type.

        Args:
            workspace_id: Workspace ID
            days: Number of days to analyze

        Returns:
            List of notification type performance metrics
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get notifications grouped by type
        result = await self.db.execute(
            select(
                NotificationLog.notification_type,
                func.count(NotificationLog.id).label("total_sent"),
            )
            .where(
                and_(
                    NotificationLog.workspace_id == workspace_id,
                    NotificationLog.sent_at >= start_date,
                )
            )
            .group_by(NotificationLog.notification_type)
        )
        type_data = result.all()

        performance = []
        for notification_type, total_sent in type_data:
            metrics = await self.get_delivery_metrics(
                workspace_id=workspace_id,
                notification_type=notification_type,
                start_date=start_date,
            )
            metrics["notification_type"] = notification_type
            performance.append(metrics)

        return performance

    async def get_failed_notifications(
        self,
        workspace_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[NotificationLog]:
        """
        Get recently failed notifications.

        Args:
            workspace_id: Optional workspace filter
            limit: Maximum number of results

        Returns:
            List of failed notifications
        """
        filters = [NotificationLog.delivery_status == "failed"]

        if workspace_id:
            filters.append(NotificationLog.workspace_id == workspace_id)

        result = await self.db.execute(
            select(NotificationLog)
            .where(and_(*filters))
            .order_by(NotificationLog.sent_at.desc())
            .limit(limit)
        )
        notifications = result.scalars().all()
        return list(notifications)

    async def get_pending_count(
        self, workspace_id: Optional[str] = None
    ) -> int:
        """
        Get count of pending notifications in queue.

        Args:
            workspace_id: Optional workspace filter

        Returns:
            Count of pending notifications
        """
        filters = [NotificationQueue.status == "pending"]

        if workspace_id:
            # Note: workspace_id is stored in payload
            # This query would need adjustment based on actual schema
            pass

        result = await self.db.execute(
            select(func.count(NotificationQueue.id)).where(and_(*filters))
        )
        count = result.scalar()
        return count or 0

    async def get_retry_count(
        self, notification_id: str
    ) -> int:
        """
        Get retry count for a notification.

        Args:
            notification_id: Notification ID

        Returns:
            Number of retry attempts
        """
        result = await self.db.execute(
            select(NotificationQueue).where(
                NotificationQueue.id == notification_id
            )
        )
        notification = result.scalar_one_or_none()

        if notification:
            return notification.attempts

        return 0

    async def should_retry(
        self, notification_id: str
    ) -> bool:
        """
        Check if a failed notification should be retried.

        Args:
            notification_id: Notification ID

        Returns:
            True if should retry
        """
        result = await self.db.execute(
            select(NotificationQueue).where(
                NotificationQueue.id == notification_id
            )
        )
        notification = result.scalar_one_or_none()

        if not notification:
            return False

        return (
            notification.status == "failed"
            and notification.attempts < notification.max_attempts
        )

    async def mark_for_retry(
        self, notification_id: str, scheduled_for: Optional[datetime] = None
    ) -> bool:
        """
        Mark a failed notification for retry.

        Args:
            notification_id: Notification ID
            scheduled_for: Optional scheduled retry time

        Returns:
            True if marked for retry
        """
        result = await self.db.execute(
            select(NotificationQueue).where(
                NotificationQueue.id == notification_id
            )
        )
        notification = result.scalar_one_or_none()

        if not notification or not await self.should_retry(notification_id):
            return False

        notification.status = "pending"
        notification.scheduled_for = scheduled_for or datetime.utcnow()
        notification.error_message = None

        await self.db.commit()

        logger.info(f"Marked notification {notification_id} for retry")
        return True
