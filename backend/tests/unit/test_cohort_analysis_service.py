"""Unit tests for cohort analysis service."""

import pytest
from datetime import datetime, timedelta, date
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.analytics.cohort_analysis import CohortAnalysisService


class TestCohortAnalysisService:
    """Test suite for CohortAnalysisService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create CohortAnalysisService instance."""
        return CohortAnalysisService(mock_db)

    @pytest.mark.asyncio
    async def test_generate_cohort_dates_daily(self, service):
        """Test daily cohort date generation."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 5)

        dates = service._generate_cohort_dates("daily", start_date, end_date)

        assert len(dates) == 5
        assert dates[0] == date(2024, 1, 1)
        assert dates[-1] == date(2024, 1, 5)

    @pytest.mark.asyncio
    async def test_generate_cohort_dates_weekly(self, service):
        """Test weekly cohort date generation."""
        # Start from Monday
        start_date = date(2024, 1, 1)  # Monday
        end_date = date(2024, 1, 29)

        dates = service._generate_cohort_dates("weekly", start_date, end_date)

        # Should generate 5 Mondays
        assert len(dates) == 5
        # All dates should be Mondays
        for d in dates:
            assert d.weekday() == 0

    @pytest.mark.asyncio
    async def test_generate_cohort_dates_monthly(self, service):
        """Test monthly cohort date generation."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 4, 15)

        dates = service._generate_cohort_dates("monthly", start_date, end_date)

        # Should generate 4 months (Jan, Feb, Mar, Apr)
        assert len(dates) == 4
        # All dates should be first of month
        for d in dates:
            assert d.day == 1

    @pytest.mark.asyncio
    async def test_get_cohort_users_signup(self, service, mock_db):
        """Test getting cohort users for signup type."""
        # Mock database query result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("user1",),
            ("user2",),
            ("user3",),
        ]
        mock_db.execute.return_value = mock_result

        cohort_date = date(2024, 1, 1)
        users = await service._get_cohort_users("workspace-1", cohort_date, "signup")

        assert len(users) == 3
        assert "user1" in users
        assert "user2" in users
        assert "user3" in users

    @pytest.mark.asyncio
    async def test_calculate_retention_periods(self, service, mock_db):
        """Test retention period calculation."""
        cohort_users = ["user1", "user2", "user3"]
        cohort_date = date(2024, 1, 1)

        # Mock retention data
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (date(2024, 1, 1), 3),  # day0: 100% (3/3)
            (date(2024, 1, 2), 2),  # day1: 66.67% (2/3)
            (date(2024, 1, 8), 2),  # day7: 66.67% (2/3)
            (date(2024, 1, 31), 1), # day30: 33.33% (1/3)
        ]
        mock_db.execute.return_value = mock_result

        retention = await service._calculate_retention_periods(
            "workspace-1",
            cohort_users,
            cohort_date
        )

        assert "day0" in retention
        assert "day1" in retention
        assert "day7" in retention
        assert "day30" in retention

        assert retention["day0"] == 100.0  # 3/3 * 100
        assert retention["day1"] == 66.67  # 2/3 * 100
        assert retention["day7"] == 66.67  # 2/3 * 100
        assert retention["day30"] == 33.33  # 1/3 * 100

    @pytest.mark.asyncio
    async def test_calculate_cohort_metrics(self, service, mock_db):
        """Test cohort metrics calculation."""
        cohort_users = ["user1", "user2"]
        cohort_date = date(2024, 1, 1)
        cohort_size = 2

        # Mock revenue query result
        revenue_row = MagicMock()
        revenue_row.avg_revenue = 100.0
        revenue_row.total_revenue = 200.0

        revenue_result = MagicMock()
        revenue_result.fetchone.return_value = revenue_row

        # Mock engagement query result
        engagement_result = MagicMock()
        engagement_result.scalar.return_value = 50  # 50 events

        # Mock churn query result
        churn_result = MagicMock()
        churn_result.scalar.return_value = 1  # 1 active user

        # Configure mock to return different results for different queries
        mock_db.execute.side_effect = [
            revenue_result,
            engagement_result,
            churn_result,
        ]

        metrics = await service._calculate_cohort_metrics(
            "workspace-1",
            cohort_users,
            cohort_date,
            cohort_size
        )

        assert "avgRevenue" in metrics
        assert "ltv" in metrics
        assert "churnRate" in metrics
        assert "engagementScore" in metrics

        assert metrics["avgRevenue"] == 100.0
        assert metrics["churnRate"] == 50.0  # 1 churned out of 2 = 50%

    @pytest.mark.asyncio
    async def test_calculate_segment_retention(self, service, mock_db):
        """Test segment retention calculation."""
        cohort_users = ["user1", "user2", "user3"]
        cohort_date = date(2024, 1, 1)

        # Mock segment data
        desktop_row = MagicMock()
        desktop_row.device_type = "desktop"
        desktop_row.user_count = 2

        mobile_row = MagicMock()
        mobile_row.device_type = "mobile"
        mobile_row.user_count = 1

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [desktop_row, mobile_row]
        mock_db.execute.return_value = mock_result

        segments = await service._calculate_segment_retention(
            "workspace-1",
            cohort_users,
            cohort_date
        )

        assert len(segments) == 2

        desktop_segment = next(s for s in segments if s["segment"] == "desktop")
        assert desktop_segment["count"] == 2
        assert desktop_segment["retention"] == 66.67  # 2/3 * 100

        mobile_segment = next(s for s in segments if s["segment"] == "mobile")
        assert mobile_segment["count"] == 1
        assert mobile_segment["retention"] == 33.33  # 1/3 * 100

    @pytest.mark.asyncio
    async def test_calculate_comparison_empty_cohorts(self, service):
        """Test comparison calculation with empty cohorts."""
        comparison = service._calculate_comparison([])

        assert comparison["bestPerforming"] is None
        assert comparison["worstPerforming"] is None
        assert comparison["avgRetention"] == 0.0
        assert comparison["trend"] == "stable"

    @pytest.mark.asyncio
    async def test_calculate_comparison_improving_trend(self, service):
        """Test comparison calculation with improving trend."""
        cohorts = [
            {
                "cohortId": "2024-01-01_signup",
                "retention": {"day30": 20.0}
            },
            {
                "cohortId": "2024-02-01_signup",
                "retention": {"day30": 30.0}
            },
            {
                "cohortId": "2024-03-01_signup",
                "retention": {"day30": 40.0}
            },
            {
                "cohortId": "2024-04-01_signup",
                "retention": {"day30": 50.0}
            },
        ]

        comparison = service._calculate_comparison(cohorts)

        assert comparison["bestPerforming"] == "2024-04-01_signup"
        assert comparison["worstPerforming"] == "2024-01-01_signup"
        assert comparison["avgRetention"] == 35.0
        assert comparison["trend"] == "improving"

    @pytest.mark.asyncio
    async def test_calculate_comparison_declining_trend(self, service):
        """Test comparison calculation with declining trend."""
        cohorts = [
            {
                "cohortId": "2024-01-01_signup",
                "retention": {"day30": 50.0}
            },
            {
                "cohortId": "2024-02-01_signup",
                "retention": {"day30": 40.0}
            },
            {
                "cohortId": "2024-03-01_signup",
                "retention": {"day30": 30.0}
            },
            {
                "cohortId": "2024-04-01_signup",
                "retention": {"day30": 20.0}
            },
        ]

        comparison = service._calculate_comparison(cohorts)

        assert comparison["bestPerforming"] == "2024-01-01_signup"
        assert comparison["worstPerforming"] == "2024-04-01_signup"
        assert comparison["avgRetention"] == 35.0
        assert comparison["trend"] == "declining"

    @pytest.mark.asyncio
    async def test_calculate_comparison_stable_trend(self, service):
        """Test comparison calculation with stable trend."""
        cohorts = [
            {
                "cohortId": "2024-01-01_signup",
                "retention": {"day30": 30.0}
            },
            {
                "cohortId": "2024-02-01_signup",
                "retention": {"day30": 32.0}
            },
            {
                "cohortId": "2024-03-01_signup",
                "retention": {"day30": 31.0}
            },
            {
                "cohortId": "2024-04-01_signup",
                "retention": {"day30": 33.0}
            },
        ]

        comparison = service._calculate_comparison(cohorts)

        assert comparison["trend"] == "stable"

    @pytest.mark.asyncio
    async def test_analyze_cohort_empty_users(self, service, mock_db):
        """Test cohort analysis with no users."""
        # Mock empty user result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        cohort_date = date(2024, 1, 1)
        result = await service._analyze_cohort("workspace-1", cohort_date, "signup")

        assert result is None

    @pytest.mark.asyncio
    async def test_retention_calculation_zero_cohort_size(self, service, mock_db):
        """Test retention calculation handles zero cohort size gracefully."""
        cohort_users = []
        cohort_date = date(2024, 1, 1)

        # Mock empty result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        retention = await service._calculate_retention_periods(
            "workspace-1",
            cohort_users,
            cohort_date
        )

        # All retention rates should be 0
        assert all(rate == 0.0 for rate in retention.values())
