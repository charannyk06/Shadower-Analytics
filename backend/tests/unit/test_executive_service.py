"""Unit tests for executive metrics service."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.metrics.executive_service import ExecutiveMetricsService
from src.models.database.tables import ExecutionLog, WorkspaceMetric


class TestExecutiveMetricsService:
    """Test suite for ExecutiveMetricsService."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return ExecutiveMetricsService()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    def test_parse_timeframe_24h(self, service):
        """Test parsing 24h timeframe."""
        assert service._parse_timeframe("24h") == 1

    def test_parse_timeframe_7d(self, service):
        """Test parsing 7d timeframe."""
        assert service._parse_timeframe("7d") == 7

    def test_parse_timeframe_30d(self, service):
        """Test parsing 30d timeframe."""
        assert service._parse_timeframe("30d") == 30

    def test_parse_timeframe_90d(self, service):
        """Test parsing 90d timeframe."""
        assert service._parse_timeframe("90d") == 90

    def test_parse_timeframe_1y(self, service):
        """Test parsing 1y timeframe."""
        assert service._parse_timeframe("1y") == 365

    def test_parse_timeframe_invalid_defaults_to_30(self, service):
        """Test that invalid timeframe defaults to 30 days."""
        assert service._parse_timeframe("invalid") == 30

    @pytest.mark.asyncio
    async def test_calculate_daily_active_users_no_data(self, service, mock_db):
        """Test DAU calculation with no data returns 0."""
        mock_result = Mock()
        mock_result.scalar.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service._calculate_daily_active_users(
            mock_db, "test-workspace", datetime.now(timezone.utc)
        )

        assert result == 0
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_daily_active_users_with_data(self, service, mock_db):
        """Test DAU calculation with data."""
        mock_result = Mock()
        mock_result.scalar.return_value = 42
        mock_db.execute.return_value = mock_result

        result = await service._calculate_daily_active_users(
            mock_db, "test-workspace", datetime.now(timezone.utc)
        )

        assert result == 42

    @pytest.mark.asyncio
    async def test_calculate_success_rate_no_executions(self, service, mock_db):
        """Test success rate with no executions returns 0."""
        mock_result = Mock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=7)

        result = await service._calculate_success_rate(
            mock_db, "test-workspace", start, now
        )

        assert result == 0.0

    @pytest.mark.asyncio
    async def test_calculate_success_rate_all_successful(self, service, mock_db):
        """Test success rate with all successful executions."""
        # Mock total count
        total_mock = Mock()
        total_mock.scalar.return_value = 100

        # Mock success count
        success_mock = Mock()
        success_mock.scalar.return_value = 100

        mock_db.execute.side_effect = [total_mock, success_mock]

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=7)

        result = await service._calculate_success_rate(
            mock_db, "test-workspace", start, now
        )

        assert result == 100.0

    @pytest.mark.asyncio
    async def test_calculate_success_rate_partial(self, service, mock_db):
        """Test success rate with partial success."""
        # Mock total count
        total_mock = Mock()
        total_mock.scalar.return_value = 100

        # Mock success count
        success_mock = Mock()
        success_mock.scalar.return_value = 75

        mock_db.execute.side_effect = [total_mock, success_mock]

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=7)

        result = await service._calculate_success_rate(
            mock_db, "test-workspace", start, now
        )

        assert result == 75.0

    @pytest.mark.asyncio
    async def test_calculate_avg_execution_time_no_data(self, service, mock_db):
        """Test avg execution time with no data."""
        mock_result = Mock()
        mock_result.scalar.return_value = None
        mock_db.execute.return_value = mock_result

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=7)

        result = await service._calculate_avg_execution_time(
            mock_db, "test-workspace", start, now
        )

        assert result == 0.0

    @pytest.mark.asyncio
    async def test_calculate_avg_execution_time_with_data(self, service, mock_db):
        """Test avg execution time with data."""
        mock_result = Mock()
        mock_result.scalar.return_value = 123.456
        mock_db.execute.return_value = mock_result

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=7)

        result = await service._calculate_avg_execution_time(
            mock_db, "test-workspace", start, now
        )

        assert result == 123.46  # Rounded to 2 decimal places

    @pytest.mark.asyncio
    async def test_calculate_total_credits_no_data(self, service, mock_db):
        """Test total credits with no data."""
        mock_result = Mock()
        mock_result.scalar.return_value = None
        mock_db.execute.return_value = mock_result

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=7)

        result = await service._calculate_total_credits(
            mock_db, "test-workspace", start, now
        )

        assert result == 0

    @pytest.mark.asyncio
    async def test_calculate_total_credits_with_data(self, service, mock_db):
        """Test total credits with data."""
        mock_result = Mock()
        mock_result.scalar.return_value = 5000
        mock_db.execute.return_value = mock_result

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=7)

        result = await service._calculate_total_credits(
            mock_db, "test-workspace", start, now
        )

        assert result == 5000

    @pytest.mark.asyncio
    async def test_get_executive_overview_error_handling(self, service, mock_db):
        """Test that errors in overview return default values."""
        mock_db.execute.side_effect = Exception("Database error")

        result = await service.get_executive_overview(
            workspace_id="test-workspace",
            timeframe="30d",
            skip_cache=True,
            db=mock_db
        )

        # Should return default values without raising exception
        assert result["workspace_id"] == "test-workspace"
        assert result["dau"] == 0
        assert result["wau"] == 0
        assert result["mau"] == 0
        assert result["total_executions"] == 0
        assert result["success_rate"] == 0.0

    def test_get_default_overview_structure(self, service):
        """Test default overview has correct structure."""
        result = service._get_default_overview("test-workspace", "30d")

        assert "workspace_id" in result
        assert "timeframe" in result
        assert "period" in result
        assert "start" in result["period"]
        assert "end" in result["period"]
        assert "mrr" in result
        assert "churn_rate" in result
        assert "ltv" in result
        assert "dau" in result
        assert "wau" in result
        assert "mau" in result
        assert "total_executions" in result
        assert "success_rate" in result


class TestExecutiveMetricsServiceEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return ExecutiveMetricsService()

    @pytest.mark.asyncio
    async def test_service_without_db_session_raises_error(self, service):
        """Test that calling methods without db session raises error."""
        with pytest.raises(ValueError, match="Database session required"):
            await service.get_executive_overview(
                workspace_id="test-workspace",
                timeframe="30d",
                skip_cache=True
            )

    @pytest.mark.asyncio
    async def test_calculate_dau_database_error_returns_zero(self, service):
        """Test that database errors in DAU calculation return 0."""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Database connection failed")

        result = await service._calculate_daily_active_users(
            mock_db, "test-workspace", datetime.now(timezone.utc)
        )

        assert result == 0

    @pytest.mark.asyncio
    async def test_calculate_total_users(self, service):
        """Test calculating total unique users."""
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar.return_value = 150
        mock_db.execute.return_value = mock_result

        result = await service._calculate_total_users(mock_db, "test-workspace")

        assert result == 150

    @pytest.mark.asyncio
    async def test_calculate_active_agents(self, service):
        """Test calculating active agents."""
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar.return_value = 25
        mock_db.execute.return_value = mock_result

        result = await service._calculate_active_agents(mock_db, "test-workspace")

        assert result == 25
