"""Unit tests for moving averages service."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date

from src.services.analytics.moving_averages import MovingAverageService


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    return session


@pytest.fixture
def ma_service(mock_db_session):
    """Create a MovingAverageService instance with mock database."""
    return MovingAverageService(db=mock_db_session)


@pytest.fixture
def ma_service_no_db():
    """Create a MovingAverageService instance without database."""
    return MovingAverageService()


class TestMovingAverageService:
    """Test suite for MovingAverageService."""

    # ===================================================================
    # INITIALIZATION TESTS
    # ===================================================================

    def test_service_initialization_with_db(self, ma_service, mock_db_session):
        """Test service initializes correctly with database."""
        assert ma_service.db == mock_db_session
        assert ma_service.VALID_METRICS == ['runtime_seconds', 'credits_consumed', 'tokens_used', 'executions']
        assert ma_service.DEFAULT_SMA_WINDOW == 7
        assert ma_service.DEFAULT_EMA_SPAN == 7
        assert ma_service.MAX_WINDOW_SIZE == 365

    def test_service_initialization_without_db(self, ma_service_no_db):
        """Test service initializes correctly without database."""
        assert ma_service_no_db.db is None

    # ===================================================================
    # CALCULATE_SMA TESTS
    # ===================================================================

    def test_calculate_sma_basic(self):
        """Test basic simple moving average calculation."""
        data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        window = 3

        result = MovingAverageService.calculate_sma(data, window)

        assert len(result) == len(data)
        assert not pd.isna(result.iloc[-1])
        # Last value should be average of last 3 values: (8+9+10)/3 = 9
        assert abs(result.iloc[-1] - 9.0) < 0.01

    def test_calculate_sma_window_1(self):
        """Test SMA with window size 1 (should equal original values)."""
        data = pd.Series([1, 2, 3, 4, 5])
        window = 1

        result = MovingAverageService.calculate_sma(data, window)

        pd.testing.assert_series_equal(result, data)

    def test_calculate_sma_invalid_window_negative(self):
        """Test SMA with negative window size."""
        data = pd.Series([1, 2, 3, 4, 5])

        with pytest.raises(ValueError, match="Window size must be positive"):
            MovingAverageService.calculate_sma(data, -1)

    def test_calculate_sma_invalid_window_zero(self):
        """Test SMA with zero window size."""
        data = pd.Series([1, 2, 3, 4, 5])

        with pytest.raises(ValueError, match="Window size must be positive"):
            MovingAverageService.calculate_sma(data, 0)

    def test_calculate_sma_window_larger_than_data(self):
        """Test SMA with window size larger than data length."""
        data = pd.Series([1, 2, 3])
        window = 10

        # Should not raise error, but will warn
        result = MovingAverageService.calculate_sma(data, window)

        assert len(result) == len(data)
        # With min_periods=1, should still calculate something
        assert not pd.isna(result.iloc[-1])

    def test_calculate_sma_empty_data(self):
        """Test SMA with empty data."""
        data = pd.Series([])
        window = 3

        result = MovingAverageService.calculate_sma(data, window)

        assert len(result) == 0

    # ===================================================================
    # CALCULATE_EMA TESTS
    # ===================================================================

    def test_calculate_ema_basic(self):
        """Test basic exponential moving average calculation."""
        data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        span = 3

        result = MovingAverageService.calculate_ema(data, span)

        assert len(result) == len(data)
        assert not pd.isna(result.iloc[-1])
        # EMA should give more weight to recent values
        assert result.iloc[-1] > data.iloc[-5:].mean()

    def test_calculate_ema_responds_faster_than_sma(self):
        """Test that EMA responds faster to changes than SMA."""
        # Data with sudden spike
        data = pd.Series([10, 10, 10, 10, 10, 100, 100, 100])
        window = 5

        sma = MovingAverageService.calculate_sma(data, window)
        ema = MovingAverageService.calculate_ema(data, window)

        # EMA should be higher than SMA at the end (more responsive to spike)
        assert ema.iloc[-1] > sma.iloc[-1]

    def test_calculate_ema_invalid_span_negative(self):
        """Test EMA with negative span."""
        data = pd.Series([1, 2, 3, 4, 5])

        with pytest.raises(ValueError, match="Span must be positive"):
            MovingAverageService.calculate_ema(data, -1)

    def test_calculate_ema_invalid_span_zero(self):
        """Test EMA with zero span."""
        data = pd.Series([1, 2, 3, 4, 5])

        with pytest.raises(ValueError, match="Span must be positive"):
            MovingAverageService.calculate_ema(data, 0)

    # ===================================================================
    # CALCULATE_WMA TESTS
    # ===================================================================

    def test_calculate_wma_basic(self):
        """Test basic weighted moving average calculation."""
        data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        weights = [1, 2, 3, 4, 5]  # More weight to recent values

        result = MovingAverageService.calculate_wma(data, weights)

        assert len(result) == len(data)
        assert not pd.isna(result.iloc[-1])

    def test_calculate_wma_equal_weights_equals_sma(self):
        """Test WMA with equal weights should approximate SMA."""
        data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        window = 3
        weights = [1, 1, 1]  # Equal weights

        wma = MovingAverageService.calculate_wma(data, weights)
        sma = MovingAverageService.calculate_sma(data, window)

        # Should be very close
        assert abs(wma.iloc[-1] - sma.iloc[-1]) < 0.01

    def test_calculate_wma_empty_weights(self):
        """Test WMA with empty weights list."""
        data = pd.Series([1, 2, 3, 4, 5])

        with pytest.raises(ValueError, match="Weights list cannot be empty"):
            MovingAverageService.calculate_wma(data, [])

    def test_calculate_wma_negative_weights(self):
        """Test WMA with negative weights."""
        data = pd.Series([1, 2, 3, 4, 5])
        weights = [1, -2, 3]

        with pytest.raises(ValueError, match="Weights must be non-negative"):
            MovingAverageService.calculate_wma(data, weights)

    def test_calculate_wma_zero_sum_weights(self):
        """Test WMA with weights that sum to zero."""
        data = pd.Series([1, 2, 3, 4, 5])
        weights = [0, 0, 0]

        with pytest.raises(ValueError, match="Sum of weights must be greater than zero"):
            MovingAverageService.calculate_wma(data, weights)

    def test_calculate_wma_increasing_weights(self):
        """Test WMA with linearly increasing weights."""
        data = pd.Series([1, 2, 3, 4, 5])
        weights = [1, 2, 3, 4, 5]  # More weight to recent

        result = MovingAverageService.calculate_wma(data, weights)

        # Last value should weight recent values more heavily
        # Manual calculation: (1*1 + 2*2 + 3*3 + 4*4 + 5*5) / (1+2+3+4+5)
        expected = (1*1 + 2*2 + 3*3 + 4*4 + 5*5) / (1+2+3+4+5)
        assert abs(result.iloc[-1] - expected) < 0.01

    # ===================================================================
    # IDENTIFY_TREND TESTS
    # ===================================================================

    def test_identify_trend_upward(self):
        """Test trend identification for upward trend."""
        data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        ma_values = pd.Series([1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5])

        trend = MovingAverageService.identify_trend(data, ma_values)

        assert trend == 'upward'

    def test_identify_trend_downward(self):
        """Test trend identification for downward trend."""
        data = pd.Series([10, 9, 8, 7, 6, 5, 4, 3, 2, 1])
        ma_values = pd.Series([10, 9.5, 9, 8.5, 8, 7.5, 7, 6.5, 6, 5.5])

        trend = MovingAverageService.identify_trend(data, ma_values)

        assert trend == 'downward'

    def test_identify_trend_neutral(self):
        """Test trend identification for neutral/sideways trend."""
        data = pd.Series([5, 5, 5, 5, 5, 5, 5, 5, 5, 5])
        ma_values = pd.Series([5, 5, 5, 5, 5, 5, 5, 5, 5, 5])

        trend = MovingAverageService.identify_trend(data, ma_values)

        assert trend == 'neutral'

    def test_identify_trend_insufficient_data(self):
        """Test trend identification with insufficient data."""
        data = pd.Series([1])
        ma_values = pd.Series([1])

        trend = MovingAverageService.identify_trend(data, ma_values)

        assert trend == 'neutral'

    def test_identify_trend_empty_data(self):
        """Test trend identification with empty data."""
        data = pd.Series([])
        ma_values = pd.Series([])

        trend = MovingAverageService.identify_trend(data, ma_values)

        assert trend == 'neutral'

    # ===================================================================
    # GET_METRIC_WITH_MA TESTS (DATABASE OPERATIONS)
    # ===================================================================

    @pytest.mark.asyncio
    async def test_get_metric_with_ma_requires_db(self, ma_service_no_db):
        """Test that get_metric_with_ma requires database session."""
        with pytest.raises(ValueError, match="Database session required"):
            await ma_service_no_db.get_metric_with_ma(
                workspace_id="123e4567-e89b-12d3-a456-426614174000",
                metric="runtime_seconds"
            )

    @pytest.mark.asyncio
    async def test_get_metric_with_ma_invalid_workspace_id(self, ma_service):
        """Test validation of workspace ID format."""
        with pytest.raises(ValueError, match="Invalid workspace_id format"):
            await ma_service.get_metric_with_ma(
                workspace_id="invalid-uuid",
                metric="runtime_seconds"
            )

    @pytest.mark.asyncio
    async def test_get_metric_with_ma_invalid_metric(self, ma_service):
        """Test validation of metric name."""
        with pytest.raises(ValueError, match="Invalid metric name"):
            await ma_service.get_metric_with_ma(
                workspace_id="123e4567-e89b-12d3-a456-426614174000",
                metric="invalid_metric"
            )

    @pytest.mark.asyncio
    async def test_get_metric_with_ma_invalid_ma_type(self, ma_service):
        """Test validation of moving average type."""
        with pytest.raises(ValueError, match="Invalid moving average type"):
            await ma_service.get_metric_with_ma(
                workspace_id="123e4567-e89b-12d3-a456-426614174000",
                metric="runtime_seconds",
                ma_type="invalid_type"
            )

    @pytest.mark.asyncio
    async def test_get_metric_with_ma_invalid_window_negative(self, ma_service):
        """Test validation of negative window size."""
        with pytest.raises(ValueError, match="Window size must be positive"):
            await ma_service.get_metric_with_ma(
                workspace_id="123e4567-e89b-12d3-a456-426614174000",
                metric="runtime_seconds",
                window=-5
            )

    @pytest.mark.asyncio
    async def test_get_metric_with_ma_window_too_large(self, ma_service):
        """Test validation of window size exceeding maximum."""
        with pytest.raises(ValueError, match="Window size too large"):
            await ma_service.get_metric_with_ma(
                workspace_id="123e4567-e89b-12d3-a456-426614174000",
                metric="runtime_seconds",
                window=500
            )

    @pytest.mark.asyncio
    async def test_get_metric_with_ma_wma_requires_weights(self, ma_service):
        """Test that WMA requires weights parameter."""
        with pytest.raises(ValueError, match="Weights required"):
            await ma_service.get_metric_with_ma(
                workspace_id="123e4567-e89b-12d3-a456-426614174000",
                metric="runtime_seconds",
                ma_type="wma",
                window=7
            )

    @pytest.mark.asyncio
    async def test_get_metric_with_ma_wma_weights_length_mismatch(self, ma_service):
        """Test that WMA weights length must match window size."""
        with pytest.raises(ValueError, match="Number of weights.*must match window size"):
            await ma_service.get_metric_with_ma(
                workspace_id="123e4567-e89b-12d3-a456-426614174000",
                metric="runtime_seconds",
                ma_type="wma",
                window=7,
                weights=[1, 2, 3]  # Only 3 weights, but window is 7
            )

    @pytest.mark.asyncio
    async def test_get_metric_with_ma_success_sma(self, ma_service, mock_db_session):
        """Test successful SMA calculation with database data."""
        # Mock database response
        mock_row1 = MagicMock()
        mock_row1.date = date(2024, 1, 1)
        mock_row1.value = 10.0

        mock_row2 = MagicMock()
        mock_row2.date = date(2024, 1, 2)
        mock_row2.value = 20.0

        mock_row3 = MagicMock()
        mock_row3.date = date(2024, 1, 3)
        mock_row3.value = 30.0

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row1, mock_row2, mock_row3]
        mock_db_session.execute.return_value = mock_result

        result = await ma_service.get_metric_with_ma(
            workspace_id="123e4567-e89b-12d3-a456-426614174000",
            metric="runtime_seconds",
            ma_type="sma",
            window=2,
            timeframe="7d"
        )

        assert result is not None
        assert result['metric'] == 'runtime_seconds'
        assert result['ma_type'] == 'sma'
        assert result['window'] == 2
        assert len(result['data']) == 3
        assert 'trend' in result
        assert 'summary' in result

    @pytest.mark.asyncio
    async def test_get_metric_with_ma_empty_data(self, ma_service, mock_db_session):
        """Test handling of empty database result."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db_session.execute.return_value = mock_result

        result = await ma_service.get_metric_with_ma(
            workspace_id="123e4567-e89b-12d3-a456-426614174000",
            metric="runtime_seconds",
            ma_type="sma",
            window=7
        )

        assert result is not None
        assert result['metric'] == 'runtime_seconds'
        assert len(result['data']) == 0
        assert result['trend'] == 'neutral'
        assert result['summary']['data_points'] == 0

    # ===================================================================
    # BUILD_METRIC_QUERY TESTS
    # ===================================================================

    def test_build_metric_query_runtime_seconds(self, ma_service):
        """Test query building for runtime_seconds metric."""
        query = ma_service._build_metric_query('runtime_seconds')

        assert 'runtime_seconds' in query
        assert 'AVG(runtime_seconds)' in query
        assert 'analytics.agent_runs' in query

    def test_build_metric_query_credits_consumed(self, ma_service):
        """Test query building for credits_consumed metric."""
        query = ma_service._build_metric_query('credits_consumed')

        assert 'credits_consumed' in query
        assert 'SUM(credits_consumed)' in query
        assert 'analytics.agent_runs' in query

    def test_build_metric_query_tokens_used(self, ma_service):
        """Test query building for tokens_used metric."""
        query = ma_service._build_metric_query('tokens_used')

        assert 'tokens_used' in query
        assert 'SUM(tokens_used)' in query
        assert 'analytics.agent_runs' in query

    def test_build_metric_query_executions(self, ma_service):
        """Test query building for executions metric."""
        query = ma_service._build_metric_query('executions')

        assert 'COUNT(*)' in query
        assert 'analytics.agent_runs' in query

    def test_build_metric_query_invalid_metric(self, ma_service):
        """Test query building with invalid metric raises error."""
        with pytest.raises(ValueError, match="Unexpected metric"):
            ma_service._build_metric_query('invalid_metric')

    # ===================================================================
    # COMPARE_MOVING_AVERAGES TESTS
    # ===================================================================

    @pytest.mark.asyncio
    async def test_compare_moving_averages_empty_windows(self, ma_service):
        """Test comparison with empty windows list."""
        with pytest.raises(ValueError, match="At least one window size required"):
            await ma_service.compare_moving_averages(
                workspace_id="123e4567-e89b-12d3-a456-426614174000",
                metric="runtime_seconds",
                windows=[]
            )

    @pytest.mark.asyncio
    async def test_compare_moving_averages_too_many_windows(self, ma_service):
        """Test comparison with too many windows."""
        with pytest.raises(ValueError, match="Maximum 5 window sizes allowed"):
            await ma_service.compare_moving_averages(
                workspace_id="123e4567-e89b-12d3-a456-426614174000",
                metric="runtime_seconds",
                windows=[7, 14, 21, 28, 30, 60]  # 6 windows, max is 5
            )

    # ===================================================================
    # ANALYZE_MA_COMPARISON TESTS
    # ===================================================================

    def test_analyze_ma_comparison_insufficient_data(self):
        """Test comparison analysis with insufficient data."""
        results = [{"window": 7, "current_ma": 10.0}]

        analysis = MovingAverageService._analyze_ma_comparison(results)

        assert "insight" in analysis
        assert "Insufficient data" in analysis["insight"]

    def test_analyze_ma_comparison_bullish_signal(self):
        """Test comparison analysis with bullish signal."""
        results = [
            {"window": 7, "current_ma": 20.0, "trend": "upward"},
            {"window": 30, "current_ma": 15.0, "trend": "upward"}
        ]

        analysis = MovingAverageService._analyze_ma_comparison(results)

        assert analysis["signal"] == "bullish"
        assert analysis["short_term_ma"] > analysis["long_term_ma"]

    def test_analyze_ma_comparison_bearish_signal(self):
        """Test comparison analysis with bearish signal."""
        results = [
            {"window": 7, "current_ma": 10.0, "trend": "downward"},
            {"window": 30, "current_ma": 15.0, "trend": "downward"}
        ]

        analysis = MovingAverageService._analyze_ma_comparison(results)

        assert analysis["signal"] == "bearish"
        assert analysis["short_term_ma"] < analysis["long_term_ma"]

    def test_analyze_ma_comparison_neutral_signal(self):
        """Test comparison analysis with neutral signal."""
        results = [
            {"window": 7, "current_ma": 15.0, "trend": "neutral"},
            {"window": 30, "current_ma": 15.0, "trend": "neutral"}
        ]

        analysis = MovingAverageService._analyze_ma_comparison(results)

        assert analysis["signal"] == "neutral"
        assert analysis["spread"] == 0.0

    # ===================================================================
    # PERFORMANCE TESTS
    # ===================================================================

    def test_calculate_sma_large_dataset_performance(self):
        """Test SMA calculation performance with large dataset."""
        # 10,000 data points
        data = pd.Series(range(10000))
        window = 100

        import time
        start = time.time()
        result = MovingAverageService.calculate_sma(data, window)
        elapsed = time.time() - start

        assert len(result) == 10000
        assert elapsed < 1.0  # Should complete in less than 1 second

    def test_calculate_ema_large_dataset_performance(self):
        """Test EMA calculation performance with large dataset."""
        # 10,000 data points
        data = pd.Series(range(10000))
        span = 100

        import time
        start = time.time()
        result = MovingAverageService.calculate_ema(data, span)
        elapsed = time.time() - start

        assert len(result) == 10000
        assert elapsed < 1.0  # Should complete in less than 1 second
