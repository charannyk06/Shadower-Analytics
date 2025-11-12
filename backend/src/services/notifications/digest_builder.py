"""Digest builder for periodic summary notifications."""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from src.models.database.tables import (
    DigestQueue,
    NotificationLog,
    ExecutionLog,
    UserActivity,
)
from src.models.schemas.notifications import DigestTypeEnum

logger = logging.getLogger(__name__)


class DigestBuilder:
    """Builder for creating and sending periodic digest notifications."""

    def __init__(self, db: AsyncSession):
        """
        Initialize digest builder.

        Args:
            db: Database session
        """
        self.db = db
        logger.info("DigestBuilder initialized")

    async def build_digest(
        self,
        user_id: str,
        workspace_id: str,
        digest_type: str,
        period_start: datetime,
        period_end: datetime,
    ) -> Dict[str, Any]:
        """
        Build digest for a user and workspace.

        Args:
            user_id: User ID
            workspace_id: Workspace ID
            digest_type: Type of digest (daily, weekly, monthly)
            period_start: Start of period
            period_end: End of period

        Returns:
            Dict with digest data
        """
        try:
            # Gather events from the period
            events = await self._gather_events(
                user_id, workspace_id, period_start, period_end
            )

            # Calculate summary statistics
            summary_stats = await self._calculate_summary_stats(
                user_id, workspace_id, period_start, period_end
            )

            digest_data = {
                "user_id": user_id,
                "workspace_id": workspace_id,
                "digest_type": digest_type,
                "period_start": period_start,
                "period_end": period_end,
                "events": events,
                "summary_stats": summary_stats,
            }

            logger.info(
                f"Built {digest_type} digest for user {user_id} "
                f"with {len(events)} events"
            )

            return digest_data

        except Exception as e:
            logger.error(f"Failed to build digest: {e}")
            return {}

    async def _gather_events(
        self,
        user_id: str,
        workspace_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Gather events for digest period.

        Args:
            user_id: User ID
            workspace_id: Workspace ID
            period_start: Start of period
            period_end: End of period

        Returns:
            List of events
        """
        events = []

        # Get notifications from the period
        result = await self.db.execute(
            select(NotificationLog).where(
                and_(
                    NotificationLog.user_id == user_id,
                    NotificationLog.workspace_id == workspace_id,
                    NotificationLog.sent_at >= period_start,
                    NotificationLog.sent_at <= period_end,
                    NotificationLog.notification_type.like("alert_%"),
                )
            )
            .order_by(NotificationLog.sent_at.desc())
            .limit(50)  # Limit to most recent 50 alerts
        )
        notifications = result.scalars().all()

        for notification in notifications:
            events.append({
                "type": "alert",
                "notification_type": notification.notification_type,
                "subject": notification.subject,
                "preview": notification.preview,
                "timestamp": notification.sent_at.isoformat(),
                "read": notification.read_at is not None,
            })

        # Get user activity from the period
        activity_result = await self.db.execute(
            select(UserActivity).where(
                and_(
                    UserActivity.user_id == user_id,
                    UserActivity.workspace_id == workspace_id,
                    UserActivity.created_at >= period_start,
                    UserActivity.created_at <= period_end,
                )
            )
            .limit(100)
        )
        activities = activity_result.scalars().all()

        # Aggregate activity by type
        activity_counts = {}
        for activity in activities:
            event_type = activity.event_type
            activity_counts[event_type] = activity_counts.get(event_type, 0) + 1

        # Add activity summary to events
        if activity_counts:
            events.append({
                "type": "activity_summary",
                "counts": activity_counts,
                "total": len(activities),
            })

        return events

    async def _calculate_summary_stats(
        self,
        user_id: str,
        workspace_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> Dict[str, Any]:
        """
        Calculate summary statistics for digest.

        Args:
            user_id: User ID
            workspace_id: Workspace ID
            period_start: Start of period
            period_end: End of period

        Returns:
            Dict with summary statistics
        """
        stats = {}

        # Count executions
        exec_result = await self.db.execute(
            select(func.count(ExecutionLog.id)).where(
                and_(
                    ExecutionLog.user_id == user_id,
                    ExecutionLog.workspace_id == workspace_id,
                    ExecutionLog.started_at >= period_start,
                    ExecutionLog.started_at <= period_end,
                )
            )
        )
        total_executions = exec_result.scalar() or 0
        stats["total_executions"] = total_executions

        # Count successful executions
        success_result = await self.db.execute(
            select(func.count(ExecutionLog.id)).where(
                and_(
                    ExecutionLog.user_id == user_id,
                    ExecutionLog.workspace_id == workspace_id,
                    ExecutionLog.status == "success",
                    ExecutionLog.started_at >= period_start,
                    ExecutionLog.started_at <= period_end,
                )
            )
        )
        successful_executions = success_result.scalar() or 0
        stats["successful_executions"] = successful_executions

        # Calculate success rate
        stats["success_rate"] = (
            (successful_executions / total_executions * 100)
            if total_executions > 0
            else 0
        )

        # Count activity
        activity_result = await self.db.execute(
            select(func.count(UserActivity.id)).where(
                and_(
                    UserActivity.user_id == user_id,
                    UserActivity.workspace_id == workspace_id,
                    UserActivity.created_at >= period_start,
                    UserActivity.created_at <= period_end,
                )
            )
        )
        total_activity = activity_result.scalar() or 0
        stats["total_activity"] = total_activity

        # Count alerts
        alert_result = await self.db.execute(
            select(func.count(NotificationLog.id)).where(
                and_(
                    NotificationLog.user_id == user_id,
                    NotificationLog.workspace_id == workspace_id,
                    NotificationLog.notification_type.like("alert_%"),
                    NotificationLog.sent_at >= period_start,
                    NotificationLog.sent_at <= period_end,
                )
            )
        )
        total_alerts = alert_result.scalar() or 0
        stats["total_alerts"] = total_alerts

        # Calculate previous period stats for comparison
        period_duration = period_end - period_start
        prev_period_start = period_start - period_duration
        prev_period_end = period_start

        prev_exec_result = await self.db.execute(
            select(func.count(ExecutionLog.id)).where(
                and_(
                    ExecutionLog.user_id == user_id,
                    ExecutionLog.workspace_id == workspace_id,
                    ExecutionLog.started_at >= prev_period_start,
                    ExecutionLog.started_at < prev_period_end,
                )
            )
        )
        prev_executions = prev_exec_result.scalar() or 0

        if prev_executions > 0:
            stats["executions_change"] = round(
                ((total_executions - prev_executions) / prev_executions * 100), 2
            )
        else:
            stats["executions_change"] = 0

        return stats

    async def queue_digest(
        self,
        user_id: str,
        workspace_id: str,
        digest_type: str,
        period_start: datetime,
        period_end: datetime,
    ) -> Optional[str]:
        """
        Queue a digest for sending.

        Args:
            user_id: User ID
            workspace_id: Workspace ID
            digest_type: Type of digest
            period_start: Start of period
            period_end: End of period

        Returns:
            Digest ID or None if failed
        """
        try:
            # Build digest data
            digest_data = await self.build_digest(
                user_id, workspace_id, digest_type, period_start, period_end
            )

            if not digest_data:
                return None

            # Create digest queue entry
            digest_id = str(uuid4())
            digest_entry = DigestQueue(
                id=digest_id,
                user_id=user_id,
                workspace_id=workspace_id,
                digest_type=digest_type,
                period_start=period_start,
                period_end=period_end,
                events=digest_data.get("events", []),
                summary_stats=digest_data.get("summary_stats", {}),
                is_sent=False,
            )

            self.db.add(digest_entry)
            await self.db.commit()
            await self.db.refresh(digest_entry)

            logger.info(f"Queued digest {digest_id} for user {user_id}")
            return digest_id

        except Exception as e:
            logger.error(f"Failed to queue digest: {e}")
            return None

    async def send_digest(
        self, digest_id: str, notification_system
    ) -> bool:
        """
        Send a queued digest.

        Args:
            digest_id: Digest ID
            notification_system: NotificationSystem instance

        Returns:
            True if sent successfully
        """
        try:
            # Get digest from queue
            result = await self.db.execute(
                select(DigestQueue).where(DigestQueue.id == digest_id)
            )
            digest = result.scalar_one_or_none()

            if not digest or digest.is_sent:
                logger.warning(
                    f"Digest {digest_id} not found or already sent"
                )
                return False

            # Prepare notification data
            notification_data = {
                "workspace_name": "Your Workspace",  # TODO: Get from workspace table
                "date": digest.period_end.strftime("%Y-%m-%d"),
                "active_users": digest.summary_stats.get("total_activity", 0),
                "active_users_change": "0",  # TODO: Calculate
                "total_executions": digest.summary_stats.get("total_executions", 0),
                "executions_change": digest.summary_stats.get("executions_change", 0),
                "success_rate": round(digest.summary_stats.get("success_rate", 0), 1),
                "summary_text": await self._generate_summary_text(digest),
                "dashboard_url": f"/workspaces/{digest.workspace_id}/dashboard",
            }

            # Send notification
            result = await notification_system.send_notification(
                notification_type=f"digest_{digest.digest_type}",
                recipients=[digest.user_id],
                data=notification_data,
                workspace_id=digest.workspace_id,
                priority="normal",
            )

            if result.get("queued_count", 0) > 0:
                # Mark digest as sent
                digest.is_sent = True
                digest.sent_at = datetime.utcnow()
                digest.notification_id = result.get("notification_ids", [None])[0]
                await self.db.commit()

                logger.info(f"Sent digest {digest_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to send digest {digest_id}: {e}")
            return False

    async def _generate_summary_text(
        self, digest: DigestQueue
    ) -> str:
        """
        Generate summary text for digest.

        Args:
            digest: Digest queue entry

        Returns:
            Summary text
        """
        stats = digest.summary_stats

        total_executions = stats.get("total_executions", 0)
        success_rate = stats.get("success_rate", 0)
        executions_change = stats.get("executions_change", 0)

        if total_executions == 0:
            return "No activity during this period."

        if success_rate >= 95:
            performance = "excellent"
        elif success_rate >= 80:
            performance = "good"
        else:
            performance = "needs attention"

        if executions_change > 10:
            trend = "Activity is up significantly!"
        elif executions_change > 0:
            trend = "Activity is trending upward."
        elif executions_change < -10:
            trend = "Activity has decreased."
        else:
            trend = "Activity remains steady."

        return f"{trend} Performance is {performance} with a {success_rate:.1f}% success rate."

    async def get_pending_digests(
        self, digest_type: Optional[str] = None
    ) -> List[DigestQueue]:
        """
        Get pending digests to be sent.

        Args:
            digest_type: Optional filter by digest type

        Returns:
            List of pending digests
        """
        filters = [
            DigestQueue.is_sent == False,
            DigestQueue.period_end <= datetime.utcnow(),
        ]

        if digest_type:
            filters.append(DigestQueue.digest_type == digest_type)

        result = await self.db.execute(
            select(DigestQueue)
            .where(and_(*filters))
            .order_by(DigestQueue.period_end.asc())
        )
        digests = result.scalars().all()
        return list(digests)

    async def preview_digest(
        self,
        workspace_id: str,
        digest_type: str,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Preview a digest without sending.

        Args:
            workspace_id: Workspace ID
            digest_type: Type of digest
            period_start: Optional start (defaults based on digest_type)
            period_end: Optional end (defaults to now)

        Returns:
            Dict with preview data
        """
        # Set default period based on digest type
        if not period_end:
            period_end = datetime.utcnow()

        if not period_start:
            if digest_type == DigestTypeEnum.DAILY.value:
                period_start = period_end - timedelta(days=1)
            elif digest_type == DigestTypeEnum.WEEKLY.value:
                period_start = period_end - timedelta(weeks=1)
            elif digest_type == DigestTypeEnum.MONTHLY.value:
                period_start = period_end - timedelta(days=30)
            else:
                period_start = period_end - timedelta(days=1)

        # For preview, use the first user in the workspace
        # In production, this should get actual user ID
        user_id = "preview_user"  # TODO: Get from context

        digest_data = await self.build_digest(
            user_id, workspace_id, digest_type, period_start, period_end
        )

        return {
            "subject": f"{digest_type.capitalize()} Digest",
            "preview": await self._generate_summary_text(
                type("DigestQueue", (), digest_data)()  # Quick mock
            ),
            "events_count": len(digest_data.get("events", [])),
            "summary_stats": digest_data.get("summary_stats", {}),
            "formatted_content": "Preview content would be rendered here",
        }
