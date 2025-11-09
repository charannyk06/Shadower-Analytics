"""Retention analysis service for user cohorts."""

from typing import List, Dict, Any
from datetime import datetime, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, distinct

from ...models.database.tables import UserActivity


class RetentionAnalysisService:
    """Service for analyzing user retention and cohorts."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_retention_curve(
        self,
        workspace_id: str,
        cohort_date: date,
        days: int = 90
    ) -> List[Dict[str, Any]]:
        """Calculate retention curve for a cohort."""

        # Get users who were active on cohort_date
        cohort_query = select(distinct(UserActivity.user_id)).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                func.date(UserActivity.created_at) == cohort_date
            )
        )

        cohort_result = await self.db.execute(cohort_query)
        cohort_users = [row[0] for row in cohort_result.fetchall()]
        cohort_size = len(cohort_users)

        if cohort_size == 0:
            return []

        retention_curve = []

        # Calculate retention for each day
        for day_offset in range(days + 1):
            check_date = cohort_date + timedelta(days=day_offset)

            # Count how many cohort users were active on this day
            retention_query = select(func.count(distinct(UserActivity.user_id))).where(
                and_(
                    UserActivity.workspace_id == workspace_id,
                    UserActivity.user_id.in_(cohort_users),
                    func.date(UserActivity.created_at) == check_date
                )
            )

            result = await self.db.execute(retention_query)
            retained_users = result.scalar() or 0

            retention_rate = (retained_users / cohort_size * 100) if cohort_size > 0 else 0

            retention_curve.append({
                "day": day_offset,
                "retentionRate": round(retention_rate, 2),
                "activeUsers": retained_users
            })

        return retention_curve

    async def generate_cohort_analysis(
        self,
        workspace_id: str,
        cohort_type: str = "monthly",
        start_date: date = None,
        end_date: date = None
    ) -> List[Dict[str, Any]]:
        """Generate cohort analysis for user retention."""

        if not start_date:
            start_date = date.today() - timedelta(days=180)
        if not end_date:
            end_date = date.today()

        cohorts = []

        # Generate cohort dates based on type
        cohort_dates = self._generate_cohort_dates(cohort_type, start_date, end_date)

        for cohort_date in cohort_dates:
            # Get cohort size (users active on that date)
            cohort_query = select(func.count(distinct(UserActivity.user_id))).where(
                and_(
                    UserActivity.workspace_id == workspace_id,
                    func.date(UserActivity.created_at) == cohort_date
                )
            )

            result = await self.db.execute(cohort_query)
            cohort_size = result.scalar() or 0

            if cohort_size == 0:
                continue

            # Calculate retention for key periods
            retention = await self._calculate_cohort_retention_periods(
                workspace_id,
                cohort_date,
                cohort_size
            )

            cohorts.append({
                "cohortDate": cohort_date.isoformat(),
                "cohortSize": cohort_size,
                "retention": retention
            })

        return cohorts

    async def _calculate_cohort_retention_periods(
        self,
        workspace_id: str,
        cohort_date: date,
        cohort_size: int
    ) -> Dict[str, float]:
        """Calculate retention for standard periods (day1, day7, etc.)."""

        periods = {
            "day1": 1,
            "day7": 7,
            "day14": 14,
            "day30": 30,
            "day60": 60,
            "day90": 90
        }

        retention = {}

        # Get cohort users
        cohort_query = select(distinct(UserActivity.user_id)).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                func.date(UserActivity.created_at) == cohort_date
            )
        )

        cohort_result = await self.db.execute(cohort_query)
        cohort_users = [row[0] for row in cohort_result.fetchall()]

        for period_name, days_offset in periods.items():
            check_date = cohort_date + timedelta(days=days_offset)

            # Count retained users
            retention_query = select(func.count(distinct(UserActivity.user_id))).where(
                and_(
                    UserActivity.workspace_id == workspace_id,
                    UserActivity.user_id.in_(cohort_users),
                    func.date(UserActivity.created_at) == check_date
                )
            )

            result = await self.db.execute(retention_query)
            retained_users = result.scalar() or 0

            retention_rate = (retained_users / cohort_size * 100) if cohort_size > 0 else 0
            retention[period_name] = round(retention_rate, 2)

        return retention

    async def analyze_churn(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Analyze user churn patterns."""

        # Get users who were active before period
        before_period_query = select(distinct(UserActivity.user_id)).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                UserActivity.created_at < start_date
            )
        )
        before_period_result = await self.db.execute(before_period_query)
        before_period_users = set(row[0] for row in before_period_result.fetchall())

        # Get users who were active during the period
        during_period_query = select(distinct(UserActivity.user_id)).where(
            and_(
                UserActivity.workspace_id == workspace_id,
                UserActivity.created_at.between(start_date, end_date)
            )
        )
        during_period_result = await self.db.execute(during_period_query)
        during_period_users = set(row[0] for row in during_period_result.fetchall())

        # Users who churned: active before, not active during
        churned_users = len(before_period_users - during_period_users)
        start_users = len(before_period_users)

        churn_rate = (churned_users / start_users * 100) if start_users > 0 else 0

        return {
            "churnRate": round(churn_rate, 2),
            "avgLifetime": 0.0,  # TODO: Calculate average user lifetime
            "riskSegments": []  # TODO: Identify at-risk segments
        }

    def _generate_cohort_dates(
        self,
        cohort_type: str,
        start_date: date,
        end_date: date
    ) -> List[date]:
        """Generate list of cohort dates based on type."""

        cohort_dates = []
        current_date = start_date

        if cohort_type == "daily":
            while current_date <= end_date:
                cohort_dates.append(current_date)
                current_date += timedelta(days=1)

        elif cohort_type == "weekly":
            # Start from the first Monday
            while current_date.weekday() != 0 and current_date <= end_date:
                current_date += timedelta(days=1)

            while current_date <= end_date:
                cohort_dates.append(current_date)
                current_date += timedelta(weeks=1)

        elif cohort_type == "monthly":
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
