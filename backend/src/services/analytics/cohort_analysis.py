"""Cohort analysis for user retention and behavioral tracking."""

from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, distinct
import asyncio
from asyncio import Semaphore
from enum import Enum
import logging

from ...models.database.tables import UserActivity, ExecutionLog
from ..cache.decorator import cached
from ..cache.keys import CacheKeys

logger = logging.getLogger(__name__)


class CohortType(str, Enum):
    """Enum for cohort types."""
    SIGNUP = "signup"
    ACTIVATION = "activation"
    FEATURE_ADOPTION = "feature_adoption"
    CUSTOM = "custom"


class CohortPeriod(str, Enum):
    """Enum for cohort periods."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class CohortAnalysisService:
    """Advanced cohort analysis service for user retention and LTV calculation."""

    # Constants for retention periods
    RETENTION_PERIODS = {
        "day0": 0,
        "day1": 1,
        "day7": 7,
        "day14": 14,
        "day30": 30,
        "day60": 60,
        "day90": 90
    }

    # Limit concurrent cohort processing to prevent connection pool exhaustion
    MAX_CONCURRENT_COHORTS = 10

    # Maximum date range to prevent performance issues
    MAX_DATE_RANGE_DAYS = 90

    def __init__(self, db: AsyncSession):
        self.db = db

    @cached(
        key_func=lambda self, workspace_id, cohort_type, cohort_period, start_date=None, end_date=None, **_:
            CacheKeys.cohort_analysis(
                workspace_id,
                f"{cohort_type}_{cohort_period}",
                start_date.isoformat() if start_date else "default",
                end_date.isoformat() if end_date else "default"
            ),
        ttl=CacheKeys.TTL_LONG  # 30 minutes cache
    )
    async def generate_cohort_analysis(
        self,
        workspace_id: str,
        cohort_type: str = CohortType.SIGNUP,
        cohort_period: str = CohortPeriod.MONTHLY,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive cohort analysis.

        Args:
            workspace_id: The workspace ID
            cohort_type: 'signup', 'activation', 'feature_adoption', or 'custom'
            cohort_period: 'daily', 'weekly', or 'monthly'
            start_date: Start date for analysis
            end_date: End date for analysis

        Returns:
            Complete cohort analysis with metrics and comparisons

        Raises:
            ValueError: If date range exceeds maximum allowed
        """
        # Use timezone-aware datetime
        now = datetime.now(timezone.utc).date()

        if not start_date:
            start_date = now - timedelta(days=180)
        if not end_date:
            end_date = now

        # Validate date range to prevent performance issues
        date_range_days = (end_date - start_date).days
        if date_range_days > self.MAX_DATE_RANGE_DAYS:
            logger.warning(
                "Date range exceeds maximum allowed",
                extra={
                    "workspace_id": workspace_id,
                    "requested_days": date_range_days,
                    "max_days": self.MAX_DATE_RANGE_DAYS
                }
            )
            raise ValueError(
                f"Date range cannot exceed {self.MAX_DATE_RANGE_DAYS} days. "
                f"Requested: {date_range_days} days"
            )

        logger.info(
            "Advanced cohort analysis requested",
            extra={
                "workspace_id": workspace_id,
                "cohort_type": cohort_type,
                "cohort_period": cohort_period,
                "date_range": f"{start_date} to {end_date}"
            }
        )

        # Generate cohort dates based on period
        cohort_dates = self._generate_cohort_dates(cohort_period, start_date, end_date)

        # Process cohorts in parallel with concurrency limit
        semaphore = Semaphore(self.MAX_CONCURRENT_COHORTS)

        async def _analyze_with_limit(cohort_date: date) -> Optional[Dict[str, Any]]:
            async with semaphore:
                return await self._analyze_cohort(workspace_id, cohort_date, cohort_type)

        cohort_tasks = [_analyze_with_limit(cohort_date) for cohort_date in cohort_dates]
        cohorts_data = await asyncio.gather(*cohort_tasks)

        # Filter out empty cohorts
        cohorts = [c for c in cohorts_data if c is not None]

        logger.info(
            "Cohort analysis completed",
            extra={
                "workspace_id": workspace_id,
                "total_cohorts": len(cohorts),
                "empty_cohorts": len([c for c in cohorts_data if c is None])
            }
        )

        # Calculate comparison metrics
        comparison = self._calculate_comparison(cohorts)

        return {
            "cohortType": cohort_type,
            "cohortPeriod": cohort_period,
            "cohorts": cohorts,
            "comparison": comparison
        }

    async def _analyze_cohort(
        self,
        workspace_id: str,
        cohort_date: date,
        cohort_type: str
    ) -> Optional[Dict[str, Any]]:
        """Analyze a single cohort."""

        # Get cohort users based on cohort type
        cohort_users = await self._get_cohort_users(workspace_id, cohort_date, cohort_type)

        if not cohort_users:
            return None

        cohort_size = len(cohort_users)

        # Calculate all metrics in parallel for better performance
        retention_task = self._calculate_retention_periods(
            workspace_id,
            cohort_users,
            cohort_date
        )

        metrics_task = self._calculate_cohort_metrics(
            workspace_id,
            cohort_users,
            cohort_date,
            cohort_size
        )

        segments_task = self._calculate_segment_retention(
            workspace_id,
            cohort_users,
            cohort_date
        )

        retention, metrics, segments = await asyncio.gather(
            retention_task,
            metrics_task,
            segments_task
        )

        return {
            "cohortId": f"{cohort_date.isoformat()}_{cohort_type}",
            "cohortDate": cohort_date.isoformat(),
            "cohortSize": cohort_size,
            "retention": retention,
            "metrics": metrics,
            "segments": segments
        }

    async def _get_cohort_users(
        self,
        workspace_id: str,
        cohort_date: date,
        cohort_type: str
    ) -> List[str]:
        """Get users for a cohort based on cohort type."""

        # Validate cohort type
        try:
            cohort_type_enum = CohortType(cohort_type)
        except ValueError:
            logger.warning(f"Invalid cohort type: {cohort_type}, defaulting to signup")
            cohort_type_enum = CohortType.SIGNUP

        if cohort_type_enum == CohortType.SIGNUP:
            # Users who first appeared on this date
            query = select(distinct(UserActivity.user_id)).where(
                and_(
                    UserActivity.workspace_id == workspace_id,
                    func.date(UserActivity.created_at) == cohort_date
                )
            )
        elif cohort_type_enum == CohortType.ACTIVATION:
            # Users who had their first meaningful action on this date
            query = select(distinct(UserActivity.user_id)).where(
                and_(
                    UserActivity.workspace_id == workspace_id,
                    func.date(UserActivity.created_at) == cohort_date,
                    UserActivity.event_type == 'feature_use'
                )
            )
        elif cohort_type_enum == CohortType.FEATURE_ADOPTION:
            # Users who adopted a key feature on this date
            query = select(distinct(UserActivity.user_id)).where(
                and_(
                    UserActivity.workspace_id == workspace_id,
                    func.date(UserActivity.created_at) == cohort_date,
                    UserActivity.event_name.like('%feature%')
                )
            )
        else:  # CUSTOM
            # Default to signup behavior
            query = select(distinct(UserActivity.user_id)).where(
                and_(
                    UserActivity.workspace_id == workspace_id,
                    func.date(UserActivity.created_at) == cohort_date
                )
            )

        result = await self.db.execute(query)
        return [row[0] for row in result.fetchall()]

    async def _calculate_retention_periods(
        self,
        workspace_id: str,
        cohort_users: List[str],
        cohort_date: date
    ) -> Dict[str, float]:
        """Calculate retention for standard periods."""

        cohort_size = len(cohort_users)
        if cohort_size == 0:
            return {period: 0.0 for period in self.RETENTION_PERIODS.keys()}

        max_days = max(self.RETENTION_PERIODS.values())
        end_date = cohort_date + timedelta(days=max_days)

        # Optimized: Get all retention data in single query
        retention_query = select(
            func.date(UserActivity.created_at).label('activity_date'),
            func.count(distinct(UserActivity.user_id)).label('active_users')
        ).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                UserActivity.user_id.in_(cohort_users),
                func.date(UserActivity.created_at) >= cohort_date,
                func.date(UserActivity.created_at) <= end_date
            )
        ).group_by(
            func.date(UserActivity.created_at)
        )

        result = await self.db.execute(retention_query)
        retention_data = {row.activity_date: row.active_users for row in result.fetchall()}

        # Calculate retention percentages
        retention = {}
        for period_name, days_offset in self.RETENTION_PERIODS.items():
            check_date = cohort_date + timedelta(days=days_offset)
            retained_users = retention_data.get(check_date, 0)
            retention_rate = (retained_users / cohort_size * 100) if cohort_size > 0 else 0
            retention[period_name] = round(retention_rate, 2)

        return retention

    async def _calculate_cohort_metrics(
        self,
        workspace_id: str,
        cohort_users: List[str],
        cohort_date: date,
        cohort_size: int
    ) -> Dict[str, float]:
        """Calculate revenue, LTV, churn rate, and engagement metrics using combined query."""

        if cohort_size == 0:
            return {
                "avgRevenue": 0.0,
                "ltv": 0.0,
                "churnRate": 0.0,
                "engagementScore": 0.0
            }

        # Combine revenue and engagement queries
        revenue_query = select(
            func.avg(ExecutionLog.credits_used).label('avg_revenue'),
            func.sum(ExecutionLog.credits_used).label('total_revenue'),
            func.count(ExecutionLog.id).label('total_executions')
        ).where(
            and_(
                ExecutionLog.workspace_id == workspace_id,
                ExecutionLog.user_id.in_(cohort_users)
            )
        )

        engagement_query = select(
            func.count(UserActivity.id).label('total_events')
        ).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                UserActivity.user_id.in_(cohort_users)
            )
        )

        # Use timezone-aware datetime for churn calculation
        thirty_days_ago = datetime.now(timezone.utc).date() - timedelta(days=30)
        churn_query = select(func.count(distinct(UserActivity.user_id))).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                UserActivity.user_id.in_(cohort_users),
                func.date(UserActivity.created_at) >= thirty_days_ago
            )
        )

        # Execute queries in parallel
        revenue_result, engagement_result, active_result = await asyncio.gather(
            self.db.execute(revenue_query),
            self.db.execute(engagement_query),
            self.db.execute(churn_query)
        )

        # Process revenue data
        revenue_data = revenue_result.fetchone()
        avg_revenue = revenue_data.avg_revenue or 0.0
        total_revenue = revenue_data.total_revenue or 0.0

        # Process engagement data
        total_events = engagement_result.scalar() or 0
        engagement_score = min(100.0, (total_events / cohort_size / 10)) if cohort_size > 0 else 0

        # Process churn data
        active_users = active_result.scalar() or 0
        churned_users = cohort_size - active_users
        churn_rate = (churned_users / cohort_size * 100) if cohort_size > 0 else 0

        # Simple LTV calculation: average revenue * expected lifetime (in months)
        # Using engagement score as a proxy for lifetime
        expected_lifetime_months = max(1, engagement_score / 10)
        ltv = avg_revenue * expected_lifetime_months

        return {
            "avgRevenue": round(avg_revenue, 2),
            "ltv": round(ltv, 2),
            "churnRate": round(churn_rate, 2),
            "engagementScore": round(engagement_score, 2)
        }

    async def _calculate_segment_retention(
        self,
        workspace_id: str,
        cohort_users: List[str],
        cohort_date: date
    ) -> List[Dict[str, Any]]:
        """Calculate retention by user segments (device type, country, etc.)."""

        if not cohort_users:
            return []

        # Segment by device type
        device_query = select(
            UserActivity.device_type,
            func.count(distinct(UserActivity.user_id)).label('user_count')
        ).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                UserActivity.user_id.in_(cohort_users),
                UserActivity.device_type.isnot(None)
            )
        ).group_by(UserActivity.device_type)

        device_result = await self.db.execute(device_query)
        segments = []

        cohort_size = len(cohort_users)
        for row in device_result.fetchall():
            segment_users = row.user_count or 0
            retention_rate = (segment_users / cohort_size * 100) if cohort_size > 0 else 0

            segments.append({
                "segment": row.device_type or "Unknown",
                "count": segment_users,
                "retention": round(retention_rate, 2)
            })

        return segments

    def _calculate_comparison(self, cohorts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comparison metrics across cohorts."""

        if not cohorts:
            return {
                "bestPerforming": None,
                "worstPerforming": None,
                "avgRetention": 0.0,
                "trend": "stable"
            }

        # Find best and worst performing cohorts based on day30 retention
        cohorts_with_retention = [
            (c["cohortId"], c["retention"].get("day30", 0))
            for c in cohorts
        ]

        cohorts_with_retention.sort(key=lambda x: x[1], reverse=True)

        best_performing = cohorts_with_retention[0][0] if cohorts_with_retention else None
        worst_performing = cohorts_with_retention[-1][0] if cohorts_with_retention else None

        # Calculate average retention
        avg_retention = sum(c[1] for c in cohorts_with_retention) / len(cohorts_with_retention) if cohorts_with_retention else 0

        # Determine trend (compare first half vs second half chronologically)
        # Sort by cohort date to ensure chronological order
        cohorts_sorted = sorted(cohorts, key=lambda x: x["cohortDate"])
        mid_point = len(cohorts_sorted) // 2

        if mid_point > 0:
            first_half_avg = sum(c["retention"].get("day30", 0) for c in cohorts_sorted[:mid_point]) / mid_point
            second_half_avg = sum(c["retention"].get("day30", 0) for c in cohorts_sorted[mid_point:]) / (len(cohorts_sorted) - mid_point)

            if second_half_avg > first_half_avg * 1.1:
                trend = "improving"
            elif second_half_avg < first_half_avg * 0.9:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        return {
            "bestPerforming": best_performing,
            "worstPerforming": worst_performing,
            "avgRetention": round(avg_retention, 2),
            "trend": trend
        }

    def _generate_cohort_dates(
        self,
        cohort_period: str,
        start_date: date,
        end_date: date
    ) -> List[date]:
        """Generate list of cohort dates based on period."""

        # Validate cohort period
        try:
            period_enum = CohortPeriod(cohort_period)
        except ValueError:
            logger.warning(f"Invalid cohort period: {cohort_period}, defaulting to monthly")
            period_enum = CohortPeriod.MONTHLY

        cohort_dates = []
        current_date = start_date

        if period_enum == CohortPeriod.DAILY:
            while current_date <= end_date:
                cohort_dates.append(current_date)
                current_date += timedelta(days=1)

        elif period_enum == CohortPeriod.WEEKLY:
            # Find first Monday on or after start_date
            first_monday = current_date
            while first_monday.weekday() != 0:
                first_monday += timedelta(days=1)
                if first_monday > end_date:
                    break

            # If start_date to first Monday is >= 3 days, include start_date as partial week
            if (first_monday - current_date).days >= 3 and current_date <= end_date:
                cohort_dates.append(current_date)

            # Add weekly cohorts from first Monday
            current_date = first_monday
            while current_date <= end_date:
                cohort_dates.append(current_date)
                current_date += timedelta(weeks=1)

        elif period_enum == CohortPeriod.MONTHLY:
            # Start from the first day of the month
            current_date = current_date.replace(day=1)

            while current_date <= end_date:
                cohort_dates.append(current_date)
                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)

        return cohort_dates
