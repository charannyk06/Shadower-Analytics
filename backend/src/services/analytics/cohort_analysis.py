"""Cohort analysis for user retention and behavioral tracking."""

from datetime import date, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, distinct
import asyncio

from ...models.database.tables import UserActivity, ExecutionLog
from ..cache.decorator import cached
from ..cache.keys import CacheKeys


class CohortAnalysisService:
    """Advanced cohort analysis service for user retention and LTV calculation."""

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
        cohort_type: str = "signup",
        cohort_period: str = "monthly",
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
        """
        if not start_date:
            start_date = date.today() - timedelta(days=180)
        if not end_date:
            end_date = date.today()

        # Generate cohort dates based on period
        cohort_dates = self._generate_cohort_dates(cohort_period, start_date, end_date)

        # Process cohorts in parallel for better performance
        cohort_tasks = [
            self._analyze_cohort(workspace_id, cohort_date, cohort_type)
            for cohort_date in cohort_dates
        ]
        cohorts_data = await asyncio.gather(*cohort_tasks)

        # Filter out empty cohorts
        cohorts = [c for c in cohorts_data if c is not None]

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

        # Calculate retention metrics
        retention = await self._calculate_retention_periods(
            workspace_id,
            cohort_users,
            cohort_date
        )

        # Calculate revenue and LTV metrics
        metrics = await self._calculate_cohort_metrics(
            workspace_id,
            cohort_users,
            cohort_date,
            cohort_size
        )

        # Get segment breakdown
        segments = await self._calculate_segment_retention(
            workspace_id,
            cohort_users,
            cohort_date
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

        if cohort_type == "signup":
            # Users who first appeared on this date
            query = select(distinct(UserActivity.user_id)).where(
                and_(
                    UserActivity.workspace_id == workspace_id,
                    func.date(UserActivity.created_at) == cohort_date
                )
            )
        elif cohort_type == "activation":
            # Users who had their first meaningful action on this date
            query = select(distinct(UserActivity.user_id)).where(
                and_(
                    UserActivity.workspace_id == workspace_id,
                    func.date(UserActivity.created_at) == cohort_date,
                    UserActivity.event_type == 'feature_use'
                )
            )
        elif cohort_type == "feature_adoption":
            # Users who adopted a key feature on this date
            query = select(distinct(UserActivity.user_id)).where(
                and_(
                    UserActivity.workspace_id == workspace_id,
                    func.date(UserActivity.created_at) == cohort_date,
                    UserActivity.event_name.like('%feature%')
                )
            )
        else:  # custom
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

        periods = {
            "day0": 0,
            "day1": 1,
            "day7": 7,
            "day14": 14,
            "day30": 30,
            "day60": 60,
            "day90": 90
        }

        cohort_size = len(cohort_users)
        max_days = max(periods.values())
        end_date = cohort_date + timedelta(days=max_days)

        # Performance optimization: batch processing for large cohorts
        # PostgreSQL typically supports up to 32,767 parameters
        batch_size = 5000
        retention_data = {}
        
        if len(cohort_users) <= batch_size:
            # Single query for small cohorts
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
        else:
            # Batch processing for large cohorts
            for i in range(0, len(cohort_users), batch_size):
                batch = cohort_users[i:i + batch_size]
                retention_query = select(
                    func.date(UserActivity.created_at).label('activity_date'),
                    func.count(distinct(UserActivity.user_id)).label('active_users')
                ).where(
                    and_(
                        UserActivity.workspace_id == workspace_id,
                        UserActivity.user_id.in_(batch),
                        func.date(UserActivity.created_at) >= cohort_date,
                        func.date(UserActivity.created_at) <= end_date
                    )
                ).group_by(
                    func.date(UserActivity.created_at)
                )

                result = await self.db.execute(retention_query)
                for row in result.fetchall():
                    retention_data[row.activity_date] = retention_data.get(row.activity_date, 0) + row.active_users

        # Calculate retention percentages
        retention = {}
        for period_name, days_offset in periods.items():
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
        """Calculate revenue, LTV, churn rate, and engagement metrics.
        
        Note: This method uses in_() with cohort_users list. For very large cohorts
        (>5000 users), consider implementing batching similar to _calculate_retention_periods.
        However, cohort sizes are typically bounded by daily/weekly/monthly signups.
        """

        # Calculate average revenue (from credits used)
        revenue_query = select(
            func.avg(ExecutionLog.credits_used).label('avg_revenue'),
            func.sum(ExecutionLog.credits_used).label('total_revenue')
        ).where(
            and_(
                ExecutionLog.workspace_id == workspace_id,
                ExecutionLog.user_id.in_(cohort_users)
            )
        )

        revenue_result = await self.db.execute(revenue_query)
        revenue_data = revenue_result.fetchone()

        avg_revenue = revenue_data.avg_revenue or 0.0

        # Calculate engagement score
        engagement_query = select(
            func.count(UserActivity.id).label('total_events')
        ).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                UserActivity.user_id.in_(cohort_users)
            )
        )

        engagement_result = await self.db.execute(engagement_query)
        total_events = engagement_result.scalar() or 0
        engagement_score = min(100.0, (total_events / cohort_size / 10)) if cohort_size > 0 else 0

        # Calculate churn rate (users who haven't been active in 30 days)
        thirty_days_ago = date.today() - timedelta(days=30)
        active_recent_query = select(func.count(distinct(UserActivity.user_id))).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                UserActivity.user_id.in_(cohort_users),
                func.date(UserActivity.created_at) >= thirty_days_ago
            )
        )

        active_result = await self.db.execute(active_recent_query)
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
        """Calculate retention by user segments (device type, country, etc.).
        
        Note: This method uses in_() with cohort_users list. For very large cohorts
        (>5000 users), consider implementing batching similar to _calculate_retention_periods.
        However, cohort sizes are typically bounded by daily/weekly/monthly signups.
        """

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

        for row in device_result.fetchall():
            segment_users = row.user_count or 0
            cohort_size = len(cohort_users)
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

        # Sort by retention rate to find best/worst performers
        sorted_by_retention = sorted(cohorts_with_retention, key=lambda x: x[1], reverse=True)

        best_performing = sorted_by_retention[0][0] if sorted_by_retention else None
        worst_performing = sorted_by_retention[-1][0] if sorted_by_retention else None

        # Calculate average retention
        avg_retention = sum(c[1] for c in cohorts_with_retention) / len(cohorts_with_retention) if cohorts_with_retention else 0

        # Determine trend (compare first half vs second half chronologically)
        # Note: cohorts_with_retention maintains the original chronological order from input
        mid_point = len(cohorts_with_retention) // 2
        if mid_point > 0:
            first_half_avg = sum(c[1] for c in cohorts_with_retention[:mid_point]) / mid_point
            second_half_avg = sum(c[1] for c in cohorts_with_retention[mid_point:]) / (len(cohorts_with_retention) - mid_point)

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

        cohort_dates = []
        current_date = start_date

        if cohort_period == "daily":
            while current_date <= end_date:
                cohort_dates.append(current_date)
                current_date += timedelta(days=1)

        elif cohort_period == "weekly":
            # Start from the first Monday
            while current_date.weekday() != 0 and current_date <= end_date:
                current_date += timedelta(days=1)

            while current_date <= end_date:
                cohort_dates.append(current_date)
                current_date += timedelta(weeks=1)

        elif cohort_period == "monthly":
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
