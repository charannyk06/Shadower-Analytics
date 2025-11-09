"""Unit tests for user activity service."""

import pytest
from datetime import datetime, timedelta, date
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.analytics.user_activity import UserActivityService
from src.services.analytics.retention_analysis import RetentionAnalysisService


class TestUserActivityService:
    """Test suite for UserActivityService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create UserActivityService instance."""
        return UserActivityService(mock_db)

    @pytest.mark.asyncio
    async def test_calculate_start_date_7d(self, service):
        """Test start date calculation for 7 day timeframe."""
        result = service._calculate_start_date("7d")
        expected = datetime.utcnow() - timedelta(days=7)

        # Check within 1 second tolerance
        assert abs((result - expected).total_seconds()) < 1

    @pytest.mark.asyncio
    async def test_calculate_start_date_30d(self, service):
        """Test start date calculation for 30 day timeframe."""
        result = service._calculate_start_date("30d")
        expected = datetime.utcnow() - timedelta(days=30)

        assert abs((result - expected).total_seconds()) < 1

    @pytest.mark.asyncio
    async def test_calculate_start_date_1y(self, service):
        """Test start date calculation for 1 year timeframe."""
        result = service._calculate_start_date("1y")
        expected = datetime.utcnow() - timedelta(days=365)

        assert abs((result - expected).total_seconds()) < 1

    @pytest.mark.asyncio
    async def test_calculate_engagement_score(self, service, mock_db):
        """Test engagement score calculation."""
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalar.return_value = 500  # 500 events
        mock_db.execute.return_value = mock_result

        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        score = await service._calculate_engagement_score(
            "test-workspace", start_date, end_date
        )

        # 500 events should give a score of 50.0
        assert score == 50.0

    @pytest.mark.asyncio
    async def test_calculate_engagement_score_max(self, service, mock_db):
        """Test engagement score caps at 100."""
        # Mock database query result with high event count
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5000  # Many events
        mock_db.execute.return_value = mock_result

        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        score = await service._calculate_engagement_score(
            "test-workspace", start_date, end_date
        )

        # Score should be capped at 100
        assert score == 100.0

    @pytest.mark.asyncio
    async def test_calculate_avg_sessions_per_user(self, service, mock_db):
        """Test average sessions per user calculation."""
        # Mock database query result
        mock_row = MagicMock()
        mock_row.total_sessions = 1000
        mock_row.total_users = 100

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        avg_sessions = await service._calculate_avg_sessions_per_user(
            "test-workspace", start_date, end_date
        )

        # 1000 sessions / 100 users = 10.0
        assert avg_sessions == 10.0

    @pytest.mark.asyncio
    async def test_calculate_avg_sessions_zero_users(self, service, mock_db):
        """Test average sessions when there are no users."""
        # Mock database query with zero users
        mock_row = MagicMock()
        mock_row.total_sessions = 0
        mock_row.total_users = 0

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        avg_sessions = await service._calculate_avg_sessions_per_user(
            "test-workspace", start_date, end_date
        )

        # Should return 0.0 for zero users
        assert avg_sessions == 0.0

    @pytest.mark.asyncio
    async def test_get_device_breakdown(self, service, mock_db):
        """Test device breakdown calculation."""
        # Mock database query results
        mock_rows = [
            MagicMock(device_type="desktop", count=100),
            MagicMock(device_type="mobile", count=50),
            MagicMock(device_type="tablet", count=25),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_db.execute.return_value = mock_result

        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        breakdown = await service._get_device_breakdown(
            "test-workspace", start_date, end_date
        )

        assert breakdown["desktop"] == 100
        assert breakdown["mobile"] == 50
        assert breakdown["tablet"] == 25


class TestRetentionAnalysisService:
    """Test suite for RetentionAnalysisService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create RetentionAnalysisService instance."""
        return RetentionAnalysisService(mock_db)

    @pytest.mark.asyncio
    async def test_generate_cohort_dates_daily(self, service):
        """Test cohort date generation for daily cohorts."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 3)

        cohort_dates = service._generate_cohort_dates("daily", start_date, end_date)

        assert len(cohort_dates) == 3
        assert cohort_dates[0] == date(2024, 1, 1)
        assert cohort_dates[1] == date(2024, 1, 2)
        assert cohort_dates[2] == date(2024, 1, 3)

    @pytest.mark.asyncio
    async def test_generate_cohort_dates_weekly(self, service):
        """Test cohort date generation for weekly cohorts."""
        start_date = date(2024, 1, 1)  # Monday
        end_date = date(2024, 1, 15)

        cohort_dates = service._generate_cohort_dates("weekly", start_date, end_date)

        # Should generate 3 Mondays
        assert len(cohort_dates) == 3
        # All dates should be Mondays (weekday 0)
        for cohort_date in cohort_dates:
            assert cohort_date.weekday() == 0

    @pytest.mark.asyncio
    async def test_generate_cohort_dates_monthly(self, service):
        """Test cohort date generation for monthly cohorts."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 3, 20)

        cohort_dates = service._generate_cohort_dates("monthly", start_date, end_date)

        # Should generate 3 months (Jan, Feb, Mar)
        assert len(cohort_dates) == 3
        # All dates should be first day of month
        for cohort_date in cohort_dates:
            assert cohort_date.day == 1

    @pytest.mark.asyncio
    async def test_calculate_retention_curve_no_users(self, service, mock_db):
        """Test retention curve calculation with no users."""
        # Mock empty cohort
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        cohort_date = date(2024, 1, 1)

        curve = await service.calculate_retention_curve(
            "test-workspace", cohort_date, days=7
        )

        # Should return empty list for no users
        assert curve == []


class TestIPAnonymization:
    """Test suite for IP anonymization."""

    def test_anonymize_ipv4(self):
        """Test IPv4 address anonymization."""
        from src.core.privacy import anonymize_ip

        result = anonymize_ip("192.168.1.100")
        assert result == "192.168.1.0"

    def test_anonymize_ipv4_already_masked(self):
        """Test IPv4 address that's already masked."""
        from src.core.privacy import anonymize_ip

        result = anonymize_ip("192.168.1.0")
        assert result == "192.168.1.0"

    def test_anonymize_ipv6(self):
        """Test IPv6 address anonymization."""
        from src.core.privacy import anonymize_ip

        result = anonymize_ip("2001:0db8:85a3:0000:0000:8a2e:0370:7334")
        # Should mask last 80 bits
        assert result.startswith("2001:db8:85a3")

    def test_anonymize_invalid_ip(self):
        """Test invalid IP address."""
        from src.core.privacy import anonymize_ip

        result = anonymize_ip("invalid-ip")
        assert result is None

    def test_anonymize_none(self):
        """Test None input."""
        from src.core.privacy import anonymize_ip

        result = anonymize_ip(None)
        assert result is None

    def test_anonymize_empty_string(self):
        """Test empty string input."""
        from src.core.privacy import anonymize_ip

        result = anonymize_ip("")
        assert result is None


class TestCacheKeys:
    """Test suite for cache key generation."""

    def test_user_activity_analytics_key(self):
        """Test user activity analytics cache key generation."""
        from src.services.cache.keys import CacheKeys

        key = CacheKeys.user_activity_analytics("workspace-123", "30d")
        assert key == "user:analytics:workspace-123:30d"

    def test_user_activity_analytics_key_with_segment(self):
        """Test cache key with segment ID."""
        from src.services.cache.keys import CacheKeys

        key = CacheKeys.user_activity_analytics("workspace-123", "30d", "segment-456")
        assert key == "user:analytics:workspace-123:30d:segment-456"

    def test_retention_curve_key(self):
        """Test retention curve cache key generation."""
        from src.services.cache.keys import CacheKeys

        key = CacheKeys.retention_curve("workspace-123", "2024-01-01", 90)
        assert key == "user:retention:curve:workspace-123:2024-01-01:90"

    def test_cohort_analysis_key(self):
        """Test cohort analysis cache key generation."""
        from src.services.cache.keys import CacheKeys

        key = CacheKeys.cohort_analysis(
            "workspace-123", "monthly", "2024-01-01", "2024-03-31"
        )
        assert key == "user:cohort:workspace-123:monthly:2024-01-01:2024-03-31"

    def test_churn_analysis_key(self):
        """Test churn analysis cache key generation."""
        from src.services.cache.keys import CacheKeys

        key = CacheKeys.churn_analysis("workspace-123", "30d")
        assert key == "user:churn:workspace-123:30d"
