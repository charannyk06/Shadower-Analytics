"""User activity tracking and analytics service."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case, distinct, text
from collections import defaultdict
import asyncio

from ...models.database.tables import UserActivity, UserSegment


class UserActivityService:
    """Service for user activity tracking and analytics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_activity(
        self,
        workspace_id: str,
        timeframe: str,
        segment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive user activity analytics."""

        end_date = datetime.utcnow()
        start_date = self._calculate_start_date(timeframe)

        # Get user IDs for segment if specified
        user_filter = None
        if segment_id:
            user_filter = await self._get_segment_users(segment_id)

        # Parallel fetch all metrics
        results = await asyncio.gather(
            self._get_activity_metrics(workspace_id, start_date, end_date, user_filter),
            self._get_session_analytics(workspace_id, start_date, end_date, user_filter),
            self._get_feature_usage(workspace_id, start_date, end_date, user_filter),
            self._get_user_journeys(workspace_id, start_date, end_date, user_filter),
            self._get_retention_data(workspace_id, start_date, end_date, user_filter),
            self._get_user_segments(workspace_id)
        )

        return {
            "workspaceId": workspace_id,
            "timeframe": timeframe,
            "activityMetrics": results[0],
            "sessionAnalytics": results[1],
            "featureUsage": results[2],
            "userJourney": results[3],
            "retention": results[4],
            "segments": results[5]
        }

    async def _get_activity_metrics(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
        user_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Calculate DAU/WAU/MAU and engagement metrics."""

        # Build base query
        base_conditions = [
            UserActivity.workspace_id == workspace_id,
            UserActivity.created_at.between(start_date, end_date)
        ]
        if user_filter:
            base_conditions.append(UserActivity.user_id.in_(user_filter))

        # Get daily active users
        dau_query = select(func.count(distinct(UserActivity.user_id))).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                func.date(UserActivity.created_at) == func.current_date()
            )
        )
        dau_result = await self.db.execute(dau_query)
        dau = dau_result.scalar() or 0

        # Get weekly active users
        wau_query = select(func.count(distinct(UserActivity.user_id))).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                UserActivity.created_at >= func.current_date() - timedelta(days=7)
            )
        )
        wau_result = await self.db.execute(wau_query)
        wau = wau_result.scalar() or 0

        # Get monthly active users
        mau_query = select(func.count(distinct(UserActivity.user_id))).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                UserActivity.created_at >= func.current_date() - timedelta(days=30)
            )
        )
        mau_result = await self.db.execute(mau_query)
        mau = mau_result.scalar() or 0

        # Get activity by date
        activity_by_date = await self._get_activity_by_date(workspace_id, start_date, end_date)

        # Calculate engagement score
        engagement_score = await self._calculate_engagement_score(workspace_id, start_date, end_date)

        # Get activity distribution
        activity_by_hour = await self._get_activity_by_hour(workspace_id, start_date, end_date)
        activity_by_day = await self._get_activity_by_day_of_week(workspace_id, start_date, end_date)

        return {
            "dau": dau,
            "wau": wau,
            "mau": mau,
            "newUsers": 0,  # TODO: Implement based on user creation date
            "returningUsers": 0,  # TODO: Implement
            "reactivatedUsers": 0,  # TODO: Implement
            "churnedUsers": 0,  # TODO: Implement
            "avgSessionsPerUser": 0.0,  # TODO: Implement
            "avgSessionDuration": 0.0,  # TODO: Implement
            "bounceRate": 0.0,  # TODO: Implement
            "engagementScore": engagement_score,
            "activityByHour": activity_by_hour,
            "activityByDayOfWeek": activity_by_day,
            "activityByDate": activity_by_date
        }

    async def _get_activity_by_date(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get activity grouped by date."""

        query = select(
            func.date(UserActivity.created_at).label('date'),
            func.count(distinct(UserActivity.user_id)).label('active_users'),
            func.count(distinct(UserActivity.session_id)).label('sessions'),
            func.count(UserActivity.id).label('events')
        ).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                UserActivity.created_at.between(start_date, end_date)
            )
        ).group_by(
            func.date(UserActivity.created_at)
        ).order_by(
            func.date(UserActivity.created_at)
        )

        result = await self.db.execute(query)
        rows = result.fetchall()

        return [
            {
                "date": row.date.isoformat() if row.date else "",
                "activeUsers": row.active_users or 0,
                "sessions": row.sessions or 0,
                "events": row.events or 0
            }
            for row in rows
        ]

    async def _get_activity_by_hour(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[int]:
        """Get activity distribution by hour of day."""

        query = select(
            func.extract('hour', UserActivity.created_at).label('hour'),
            func.count(UserActivity.id).label('count')
        ).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                UserActivity.created_at.between(start_date, end_date)
            )
        ).group_by(
            func.extract('hour', UserActivity.created_at)
        )

        result = await self.db.execute(query)
        rows = result.fetchall()

        # Initialize 24-hour array
        activity = [0] * 24
        for row in rows:
            if row.hour is not None:
                activity[int(row.hour)] = row.count or 0

        return activity

    async def _get_activity_by_day_of_week(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[int]:
        """Get activity distribution by day of week."""

        query = select(
            func.extract('dow', UserActivity.created_at).label('day'),
            func.count(UserActivity.id).label('count')
        ).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                UserActivity.created_at.between(start_date, end_date)
            )
        ).group_by(
            func.extract('dow', UserActivity.created_at)
        )

        result = await self.db.execute(query)
        rows = result.fetchall()

        # Initialize 7-day array
        activity = [0] * 7
        for row in rows:
            if row.day is not None:
                activity[int(row.day)] = row.count or 0

        return activity

    async def _calculate_engagement_score(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Calculate overall engagement score (0-100)."""

        # Simple engagement score based on activity frequency
        query = select(func.count(UserActivity.id)).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                UserActivity.created_at.between(start_date, end_date)
            )
        )

        result = await self.db.execute(query)
        total_events = result.scalar() or 0

        # Normalize to 0-100 scale (simple implementation)
        # TODO: Enhance with weighted scoring
        score = min(100.0, (total_events / 1000) * 100)

        return round(score, 2)

    async def _get_session_analytics(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
        user_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Analyze session patterns."""

        # Get session count and metrics
        query = select(
            func.count(distinct(UserActivity.session_id)).label('total_sessions')
        ).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                UserActivity.created_at.between(start_date, end_date),
                UserActivity.session_id.isnot(None)
            )
        )

        result = await self.db.execute(query)
        total_sessions = result.scalar() or 0

        return {
            "totalSessions": total_sessions,
            "avgSessionLength": 0.0,  # TODO: Implement
            "medianSessionLength": 0.0,  # TODO: Implement
            "sessionLengthDistribution": {
                "0-30s": 0,
                "30s-2m": 0,
                "2m-5m": 0,
                "5m-15m": 0,
                "15m-30m": 0,
                "30m+": 0
            },
            "deviceBreakdown": {
                "desktop": 0,
                "mobile": 0,
                "tablet": 0
            },
            "browserBreakdown": {},
            "locationBreakdown": {}
        }

    async def _get_feature_usage(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
        user_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Analyze feature usage patterns."""

        query = select(
            UserActivity.event_name,
            func.count(UserActivity.id).label('usage_count'),
            func.count(distinct(UserActivity.user_id)).label('unique_users')
        ).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                UserActivity.created_at.between(start_date, end_date),
                UserActivity.event_type == 'feature_use',
                UserActivity.event_name.isnot(None)
            )
        ).group_by(
            UserActivity.event_name
        ).order_by(
            func.count(UserActivity.id).desc()
        )

        result = await self.db.execute(query)
        features = result.fetchall()

        # Get total users for adoption rate
        total_users_query = select(func.count(distinct(UserActivity.user_id))).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                UserActivity.created_at.between(start_date, end_date)
            )
        )
        total_users_result = await self.db.execute(total_users_query)
        total_users = total_users_result.scalar() or 1

        feature_list = []
        for feature in features:
            adoption_rate = (feature.unique_users / total_users * 100) if total_users > 0 else 0

            feature_list.append({
                "featureName": feature.event_name or "Unknown",
                "category": "General",  # TODO: Extract from metadata
                "usageCount": feature.usage_count or 0,
                "uniqueUsers": feature.unique_users or 0,
                "avgTimeSpent": 0.0,  # TODO: Implement
                "adoptionRate": round(adoption_rate, 2),
                "retentionRate": 0.0  # TODO: Implement
            })

        return {
            "features": feature_list,
            "adoptionFunnel": [],  # TODO: Implement
            "topFeatures": [
                {
                    "feature": f["featureName"],
                    "usage": f["usageCount"],
                    "trend": "stable"
                }
                for f in feature_list[:10]
            ],
            "unusedFeatures": []  # TODO: Implement
        }

    async def _get_user_journeys(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
        user_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Analyze user navigation patterns."""

        # Get entry points
        entry_query = select(
            UserActivity.page_path,
            func.count(distinct(UserActivity.session_id)).label('count')
        ).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                UserActivity.created_at.between(start_date, end_date),
                UserActivity.event_type == 'page_view',
                UserActivity.page_path.isnot(None)
            )
        ).group_by(
            UserActivity.page_path
        ).order_by(
            func.count(distinct(UserActivity.session_id)).desc()
        ).limit(10)

        result = await self.db.execute(entry_query)
        entry_points = result.fetchall()

        return {
            "commonPaths": [],  # TODO: Implement path analysis
            "entryPoints": [
                {
                    "page": ep.page_path or "/",
                    "count": ep.count or 0,
                    "bounceRate": 0.0  # TODO: Calculate
                }
                for ep in entry_points
            ],
            "exitPoints": [],  # TODO: Implement
            "conversionPaths": []  # TODO: Implement
        }

    async def _get_retention_data(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
        user_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get retention and cohort data."""

        return {
            "retentionCurve": [],  # TODO: Implement
            "cohorts": [],  # TODO: Implement
            "churnAnalysis": {
                "churnRate": 0.0,
                "avgLifetime": 0.0,
                "riskSegments": []
            }
        }

    async def _get_user_segments(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get user segments."""

        query = select(UserSegment).where(UserSegment.workspace_id == workspace_id)

        result = await self.db.execute(query)
        segments = result.scalars().all()

        return [
            {
                "segmentName": segment.segment_name,
                "segmentType": segment.segment_type or "behavioral",
                "userCount": segment.user_count or 0,
                "characteristics": [],  # TODO: Parse from criteria
                "avgEngagement": segment.avg_engagement or 0.0,
                "avgRevenue": 0.0  # TODO: Implement
            }
            for segment in segments
        ]

    async def _get_segment_users(self, segment_id: str) -> List[str]:
        """Get list of user IDs in a segment."""

        query = select(UserSegment).where(UserSegment.id == segment_id)
        result = await self.db.execute(query)
        segment = result.scalar_one_or_none()

        if not segment:
            return []

        # TODO: Implement user filtering based on segment criteria
        return []

    def _calculate_start_date(self, timeframe: str) -> datetime:
        """Calculate start date based on timeframe."""

        end_date = datetime.utcnow()

        timeframe_map = {
            "7d": 7,
            "30d": 30,
            "90d": 90,
            "1y": 365
        }

        days = timeframe_map.get(timeframe, 30)
        return end_date - timedelta(days=days)
