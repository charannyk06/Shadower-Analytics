"""Unit tests for percentile calculator service."""

import pytest
import numpy as np
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.analytics.percentiles import PercentileCalculator


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    return session


@pytest.fixture
def percentile_calculator(mock_db_session):
    """Create a PercentileCalculator instance with mock database."""
    return PercentileCalculator(db=mock_db_session)


@pytest.fixture
def percentile_calculator_no_db():
    """Create a PercentileCalculator instance without database."""
    return PercentileCalculator()


class TestPercentileCalculator:
    """Test suite for PercentileCalculator."""

    # ===================================================================
    # INITIALIZATION TESTS
    # ===================================================================

    def test_service_initialization_with_db(self, percentile_calculator, mock_db_session):
        """Test service initializes correctly with database."""
        assert percentile_calculator.db == mock_db_session
        assert percentile_calculator.DEFAULT_PERCENTILES == [50, 75, 90, 95, 99]
        assert percentile_calculator.OUTLIER_IQR_MULTIPLIER == 1.5
        assert percentile_calculator.OUTLIER_STD_MULTIPLIER == 3.0

    def test_service_initialization_without_db(self, percentile_calculator_no_db):
        """Test service initializes correctly without database."""
        assert percentile_calculator_no_db.db is None

    # ===================================================================
    # CALCULATE_PERCENTILES TESTS
    # ===================================================================

    @pytest.mark.asyncio
    async def test_calculate_percentiles_basic(self):
        """Test basic percentile calculation."""
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = await PercentileCalculator.calculate_percentiles(values)

        assert "p50" in result
        assert "p75" in result
        assert "p90" in result
        assert "p95" in result
        assert "p99" in result
        assert "mean" in result
        assert "median" in result
        assert "std_dev" in result
        assert "min" in result
        assert "max" in result

        # Verify values
        assert result["p50"] == 5.5  # median
        assert result["median"] == 5.5
        assert result["mean"] == 5.5
        assert result["min"] == 1.0
        assert result["max"] == 10.0

    @pytest.mark.asyncio
    async def test_calculate_percentiles_empty_list(self):
        """Test percentile calculation with empty list."""
        values = []
        result = await PercentileCalculator.calculate_percentiles(values)

        assert result["p50"] == 0.0
        assert result["p75"] == 0.0
        assert result["p90"] == 0.0
        assert result["p95"] == 0.0
        assert result["p99"] == 0.0

    @pytest.mark.asyncio
    async def test_calculate_percentiles_single_value(self):
        """Test percentile calculation with single value."""
        values = [42.0]
        result = await PercentileCalculator.calculate_percentiles(values)

        assert result["p50"] == 42.0
        assert result["p75"] == 42.0
        assert result["p90"] == 42.0
        assert result["p95"] == 42.0
        assert result["p99"] == 42.0
        assert result["mean"] == 42.0
        assert result["median"] == 42.0
        assert result["min"] == 42.0
        assert result["max"] == 42.0

    @pytest.mark.asyncio
    async def test_calculate_percentiles_with_nan_values(self):
        """Test percentile calculation filters NaN values."""
        values = [1, 2, np.nan, 3, 4, np.nan, 5]
        result = await PercentileCalculator.calculate_percentiles(values)

        # Should calculate on [1, 2, 3, 4, 5] after filtering NaN
        assert result["count"] == 5
        assert result["mean"] == 3.0
        assert result["min"] == 1.0
        assert result["max"] == 5.0

    @pytest.mark.asyncio
    async def test_calculate_percentiles_custom_percentiles(self):
        """Test percentile calculation with custom percentiles."""
        values = list(range(1, 101))  # 1 to 100
        percentiles = [10, 25, 50, 75, 90]
        result = await PercentileCalculator.calculate_percentiles(values, percentiles)

        assert "p10" in result
        assert "p25" in result
        assert "p50" in result
        assert "p75" in result
        assert "p90" in result

        # Verify approximate values
        assert abs(result["p10"] - 10.45) < 1
        assert abs(result["p25"] - 25.75) < 1
        assert abs(result["p50"] - 50.5) < 1
        assert abs(result["p75"] - 75.25) < 1
        assert abs(result["p90"] - 90.55) < 1

    @pytest.mark.asyncio
    async def test_calculate_percentiles_large_dataset(self):
        """Test percentile calculation performance with large dataset."""
        # Test with 100k values
        values = list(range(100000))
        result = await PercentileCalculator.calculate_percentiles(values)

        assert result["count"] == 100000
        assert result["p50"] == 49999.5
        assert result["min"] == 0.0
        assert result["max"] == 99999.0

    @pytest.mark.asyncio
    async def test_calculate_percentiles_includes_variance(self):
        """Test that variance is calculated."""
        values = [1, 2, 3, 4, 5]
        result = await PercentileCalculator.calculate_percentiles(values)

        assert "variance" in result
        assert result["variance"] == 2.0  # variance of [1,2,3,4,5]

    # ===================================================================
    # RUNTIME_PERCENTILES TESTS
    # ===================================================================

    @pytest.mark.asyncio
    async def test_calculate_runtime_percentiles_success(self, percentile_calculator, mock_db_session):
        """Test runtime percentile calculation from database."""
        # Mock database response
        mock_row = MagicMock()
        mock_row.p50 = 10.5
        mock_row.p75 = 15.2
        mock_row.p90 = 20.8
        mock_row.p95 = 25.1
        mock_row.p99 = 30.5
        mock_row.mean = 12.3
        mock_row.std_dev = 5.2
        mock_row.min = 1.0
        mock_row.max = 35.0
        mock_row.count = 1000

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db_session.execute.return_value = mock_result

        result = await percentile_calculator.calculate_runtime_percentiles(
            workspace_id="123e4567-e89b-12d3-a456-426614174000",
            timeframe="7d"
        )

        assert result["p50"] == 10.5
        assert result["p75"] == 15.2
        assert result["p90"] == 20.8
        assert result["p95"] == 25.1
        assert result["p99"] == 30.5
        assert result["mean"] == 12.3
        assert result["std_dev"] == 5.2
        assert result["min"] == 1.0
        assert result["max"] == 35.0
        assert result["count"] == 1000

    @pytest.mark.asyncio
    async def test_calculate_runtime_percentiles_no_data(self, percentile_calculator, mock_db_session):
        """Test runtime percentile calculation with no data."""
        mock_row = MagicMock()
        mock_row.count = 0

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db_session.execute.return_value = mock_result

        result = await percentile_calculator.calculate_runtime_percentiles(
            workspace_id="123e4567-e89b-12d3-a456-426614174000",
            timeframe="7d"
        )

        # Should return zeros
        assert result["p50"] == 0.0
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_calculate_runtime_percentiles_requires_db(self, percentile_calculator_no_db):
        """Test runtime percentile calculation requires database."""
        with pytest.raises(ValueError, match="Database session required"):
            await percentile_calculator_no_db.calculate_runtime_percentiles(
                workspace_id="123e4567-e89b-12d3-a456-426614174000"
            )

    # ===================================================================
    # METRIC_PERCENTILES TESTS
    # ===================================================================

    @pytest.mark.asyncio
    async def test_calculate_metric_percentiles_runtime(self, percentile_calculator, mock_db_session):
        """Test metric percentile calculation for runtime."""
        mock_row = MagicMock()
        mock_row.p50 = 10.0
        mock_row.p75 = 15.0
        mock_row.p90 = 20.0
        mock_row.p95 = 25.0
        mock_row.p99 = 30.0
        mock_row.mean = 12.0
        mock_row.std_dev = 5.0
        mock_row.min = 1.0
        mock_row.max = 35.0
        mock_row.count = 500

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db_session.execute.return_value = mock_result

        result = await percentile_calculator.calculate_metric_percentiles(
            workspace_id="123e4567-e89b-12d3-a456-426614174000",
            metric_name="runtime_seconds",
            timeframe="7d"
        )

        assert result["metric"] == "runtime_seconds"
        assert result["p50"] == 10.0
        assert result["count"] == 500

    @pytest.mark.asyncio
    async def test_calculate_metric_percentiles_with_agent_id(self, percentile_calculator, mock_db_session):
        """Test metric percentile calculation with agent filter."""
        mock_row = MagicMock()
        mock_row.p50 = 10.0
        mock_row.count = 100
        mock_row.mean = 12.0
        mock_row.std_dev = 5.0
        mock_row.min = 1.0
        mock_row.max = 35.0
        mock_row.p75 = 15.0
        mock_row.p90 = 20.0
        mock_row.p95 = 25.0
        mock_row.p99 = 30.0

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db_session.execute.return_value = mock_result

        result = await percentile_calculator.calculate_metric_percentiles(
            workspace_id="123e4567-e89b-12d3-a456-426614174000",
            metric_name="credits_consumed",
            agent_id="agent-123"
        )

        assert result["metric"] == "credits_consumed"
        assert result["count"] == 100

    @pytest.mark.asyncio
    async def test_calculate_metric_percentiles_invalid_metric(self, percentile_calculator):
        """Test metric percentile calculation with invalid metric name."""
        with pytest.raises(ValueError, match="Invalid metric name"):
            await percentile_calculator.calculate_metric_percentiles(
                workspace_id="123e4567-e89b-12d3-a456-426614174000",
                metric_name="invalid_metric"
            )

    # ===================================================================
    # OUTLIER DETECTION TESTS
    # ===================================================================

    def test_detect_outliers_iqr_method(self):
        """Test outlier detection using IQR method."""
        # Create dataset with clear outliers
        values = [1, 2, 2, 3, 3, 3, 4, 4, 5, 100]  # 100 is an outlier
        result = PercentileCalculator.detect_outliers(values, method="iqr")

        assert result["outlier_count"] >= 1
        assert 100 in result["outliers"]
        assert result["method"] == "iqr"
        assert "lower_bound" in result
        assert "upper_bound" in result

    def test_detect_outliers_std_method(self):
        """Test outlier detection using standard deviation method."""
        values = list(range(1, 100)) + [1000]  # 1000 is an outlier
        result = PercentileCalculator.detect_outliers(values, method="std")

        assert result["outlier_count"] >= 1
        assert result["method"] == "std"
        assert 1000 in result["outliers"]

    def test_detect_outliers_empty_list(self):
        """Test outlier detection with empty list."""
        values = []
        result = PercentileCalculator.detect_outliers(values)

        assert result["outlier_count"] == 0
        assert result["outliers"] == []
        assert result["outlier_percentage"] == 0.0

    def test_detect_outliers_no_outliers(self):
        """Test outlier detection with no outliers."""
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = PercentileCalculator.detect_outliers(values, method="iqr")

        # Normal distribution should have few or no outliers
        assert result["outlier_percentage"] < 20

    def test_detect_outliers_with_nan(self):
        """Test outlier detection filters NaN values."""
        values = [1, 2, np.nan, 3, 4, 100]
        result = PercentileCalculator.detect_outliers(values, method="iqr")

        assert np.nan not in result["outliers"]
        assert 100 in result["outliers"]

    def test_detect_outliers_invalid_method(self):
        """Test outlier detection with invalid method."""
        values = [1, 2, 3, 4, 5]
        with pytest.raises(ValueError, match="Invalid method"):
            PercentileCalculator.detect_outliers(values, method="invalid")

    def test_detect_outliers_includes_indices(self):
        """Test outlier detection includes outlier indices."""
        values = [1, 2, 3, 4, 100, 5, 6]
        result = PercentileCalculator.detect_outliers(values, method="iqr")

        assert "outlier_indices" in result
        assert len(result["outlier_indices"]) == result["outlier_count"]
        assert 4 in result["outlier_indices"]  # index of 100

    # ===================================================================
    # PERCENTILE TRENDS TESTS
    # ===================================================================

    @pytest.mark.asyncio
    async def test_calculate_percentile_trends(self, percentile_calculator, mock_db_session):
        """Test percentile trends calculation."""
        mock_rows = [
            MagicMock(
                date=MagicMock(isoformat=lambda: "2024-01-01"),
                p50=10.0,
                p75=15.0,
                p90=20.0,
                p95=25.0,
                p99=30.0,
                mean=12.0,
                count=100
            ),
            MagicMock(
                date=MagicMock(isoformat=lambda: "2024-01-02"),
                p50=11.0,
                p75=16.0,
                p90=21.0,
                p95=26.0,
                p99=31.0,
                mean=13.0,
                count=110
            ),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_db_session.execute.return_value = mock_result

        result = await percentile_calculator.calculate_percentile_trends(
            workspace_id="123e4567-e89b-12d3-a456-426614174000",
            metric_name="runtime_seconds",
            days=7
        )

        assert result["metric"] == "runtime_seconds"
        assert result["days"] == 7
        assert result["total_days"] == 2
        assert len(result["trends"]) == 2
        assert result["trends"][0]["date"] == "2024-01-01"
        assert result["trends"][0]["p50"] == 10.0
        assert result["trends"][1]["date"] == "2024-01-02"
        assert result["trends"][1]["p50"] == 11.0

    @pytest.mark.asyncio
    async def test_calculate_percentile_trends_with_agent(self, percentile_calculator, mock_db_session):
        """Test percentile trends with agent filter."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db_session.execute.return_value = mock_result

        result = await percentile_calculator.calculate_percentile_trends(
            workspace_id="123e4567-e89b-12d3-a456-426614174000",
            metric_name="credits_consumed",
            days=30,
            agent_id="agent-456"
        )

        assert result["total_days"] == 0
        assert result["trends"] == []

    @pytest.mark.asyncio
    async def test_calculate_percentile_trends_invalid_metric(self, percentile_calculator):
        """Test percentile trends with invalid metric."""
        with pytest.raises(ValueError, match="Invalid metric name"):
            await percentile_calculator.calculate_percentile_trends(
                workspace_id="123e4567-e89b-12d3-a456-426614174000",
                metric_name="invalid_metric"
            )

    @pytest.mark.asyncio
    async def test_calculate_percentile_trends_requires_db(self, percentile_calculator_no_db):
        """Test percentile trends requires database."""
        with pytest.raises(ValueError, match="Database session required"):
            await percentile_calculator_no_db.calculate_percentile_trends(
                workspace_id="123e4567-e89b-12d3-a456-426614174000",
                metric_name="runtime_seconds"
            )

    # ===================================================================
    # EDGE CASES AND PERFORMANCE TESTS
    # ===================================================================

    @pytest.mark.asyncio
    async def test_percentiles_all_same_values(self):
        """Test percentile calculation when all values are the same."""
        values = [5.0] * 100
        result = await PercentileCalculator.calculate_percentiles(values)

        assert result["p50"] == 5.0
        assert result["p99"] == 5.0
        assert result["mean"] == 5.0
        assert result["std_dev"] == 0.0
        assert result["variance"] == 0.0

    @pytest.mark.asyncio
    async def test_percentiles_negative_values(self):
        """Test percentile calculation with negative values."""
        values = [-10, -5, 0, 5, 10]
        result = await PercentileCalculator.calculate_percentiles(values)

        assert result["mean"] == 0.0
        assert result["min"] == -10.0
        assert result["max"] == 10.0

    @pytest.mark.asyncio
    async def test_percentiles_floating_point_precision(self):
        """Test percentile calculation maintains precision."""
        values = [1.111111, 2.222222, 3.333333]
        result = await PercentileCalculator.calculate_percentiles(values)

        # Results should be properly rounded
        assert isinstance(result["mean"], float)
        assert isinstance(result["p50"], float)
