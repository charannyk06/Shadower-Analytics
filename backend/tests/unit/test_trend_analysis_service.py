"""
Unit tests for TrendAnalysisService

Tests the trend analysis functionality including:
- Time series decomposition
- Pattern detection
- Forecasting
- Statistical analysis
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from src.services.analytics.trend_analysis_service import TrendAnalysisService


@pytest.fixture
def mock_db():
    """Mock database session"""
    return AsyncMock()


@pytest.fixture
def trend_service(mock_db):
    """Create TrendAnalysisService instance with mocked dependencies"""
    return TrendAnalysisService(mock_db)


@pytest.fixture
def sample_time_series():
    """Generate sample time series data for testing"""
    dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
    # Generate trend with some seasonality
    trend = np.linspace(100, 150, 30)
    seasonal = 10 * np.sin(np.linspace(0, 4 * np.pi, 30))
    noise = np.random.normal(0, 5, 30)
    values = trend + seasonal + noise

    return pd.DataFrame({"timestamp": dates, "value": values}).set_index("timestamp")


class TestTrendAnalysisService:
    """Test suite for TrendAnalysisService"""

    @pytest.mark.asyncio
    async def test_parse_timeframe(self, trend_service):
        """Test timeframe parsing"""
        assert trend_service._parse_timeframe("7d") == 7
        assert trend_service._parse_timeframe("30d") == 30
        assert trend_service._parse_timeframe("90d") == 90
        assert trend_service._parse_timeframe("1y") == 365
        assert trend_service._parse_timeframe("invalid") == 30  # default

    @pytest.mark.asyncio
    async def test_calculate_overview(self, trend_service, sample_time_series):
        """Test trend overview calculation"""
        overview = await trend_service._calculate_overview(sample_time_series, "executions")

        assert "currentValue" in overview
        assert "previousValue" in overview
        assert "change" in overview
        assert "changePercentage" in overview
        assert "trend" in overview
        assert overview["trend"] in ["increasing", "decreasing", "stable", "volatile"]
        assert "trendStrength" in overview
        assert 0 <= overview["trendStrength"] <= 100
        assert "confidence" in overview
        assert 0 <= overview["confidence"] <= 1

    @pytest.mark.asyncio
    async def test_detect_period(self, trend_service, sample_time_series):
        """Test seasonal period detection"""
        period = trend_service._detect_period(sample_time_series)
        assert isinstance(period, int)
        assert period >= 2

    @pytest.mark.asyncio
    async def test_get_period_name(self, trend_service):
        """Test period name classification"""
        assert trend_service._get_period_name(1) == "daily"
        assert trend_service._get_period_name(7) == "weekly"
        assert trend_service._get_period_name(30) == "monthly"
        assert trend_service._get_period_name(90) == "quarterly"
        assert trend_service._get_period_name(365) == "yearly"

    @pytest.mark.asyncio
    async def test_classify_seasonality(self, trend_service):
        """Test seasonality type classification"""
        assert trend_service._classify_seasonality(1) == "daily"
        assert trend_service._classify_seasonality(7) == "weekly"
        assert trend_service._classify_seasonality(30) == "monthly"
        assert trend_service._classify_seasonality(90) == "quarterly"
        assert trend_service._classify_seasonality(365) == "yearly"

    @pytest.mark.asyncio
    async def test_detect_growth_pattern(self, trend_service, sample_time_series):
        """Test growth pattern detection"""
        growth = trend_service._detect_growth_pattern(sample_time_series)

        assert "type" in growth
        assert growth["type"] in ["linear", "exponential", "logarithmic", "polynomial"]
        assert "rate" in growth
        assert "acceleration" in growth
        assert "projectedGrowth" in growth

    @pytest.mark.asyncio
    async def test_prepare_time_series(self, trend_service, sample_time_series):
        """Test time series preparation with statistics"""
        result = trend_service._prepare_time_series(sample_time_series)

        assert "data" in result
        assert "statistics" in result
        assert len(result["data"]) == len(sample_time_series)

        # Check statistics
        stats = result["statistics"]
        assert "mean" in stats
        assert "median" in stats
        assert "stdDev" in stats
        assert "variance" in stats
        assert "skewness" in stats
        assert "kurtosis" in stats
        assert "autocorrelation" in stats

        # Check data points
        for point in result["data"]:
            assert "timestamp" in point
            assert "value" in point
            assert "movingAverage" in point
            assert "upperBound" in point
            assert "lowerBound" in point
            assert "isAnomaly" in point

    @pytest.mark.asyncio
    async def test_calculate_period_comparison(self, trend_service, sample_time_series):
        """Test period comparison calculation"""
        comparison = trend_service._calculate_period_comparison(sample_time_series)

        assert "currentPeriod" in comparison
        assert "previousPeriod" in comparison
        assert "change" in comparison
        assert "changePercentage" in comparison

        # Check period structure
        assert "start" in comparison["currentPeriod"]
        assert "end" in comparison["currentPeriod"]
        assert "value" in comparison["currentPeriod"]
        assert "avg" in comparison["currentPeriod"]

    @pytest.mark.asyncio
    async def test_insufficient_data_response(self, trend_service):
        """Test response for insufficient data"""
        response = trend_service._insufficient_data_response("workspace-123", "executions", "30d")

        assert response["workspaceId"] == "workspace-123"
        assert response["metric"] == "executions"
        assert response["timeframe"] == "30d"
        assert response["error"] == "insufficient_data"
        assert "message" in response

    @pytest.mark.asyncio
    async def test_empty_overview(self, trend_service):
        """Test empty overview structure"""
        overview = trend_service._empty_overview()

        assert overview["currentValue"] == 0
        assert overview["previousValue"] == 0
        assert overview["change"] == 0
        assert overview["changePercentage"] == 0
        assert overview["trend"] == "stable"
        assert overview["trendStrength"] == 0
        assert overview["confidence"] == 0

    @pytest.mark.asyncio
    async def test_empty_forecast(self, trend_service):
        """Test empty forecast structure"""
        forecast = trend_service._empty_forecast()

        assert "shortTerm" in forecast
        assert "longTerm" in forecast
        assert "accuracy" in forecast
        assert len(forecast["shortTerm"]) == 0
        assert len(forecast["longTerm"]) == 0
        assert "mape" in forecast["accuracy"]
        assert "rmse" in forecast["accuracy"]
        assert "r2" in forecast["accuracy"]

    @pytest.mark.asyncio
    async def test_detect_cycles(self, trend_service, sample_time_series):
        """Test cyclical pattern detection"""
        cycles = trend_service._detect_cycles(sample_time_series)

        # Cycles should be a list
        assert isinstance(cycles, list)

        # If cycles detected, check structure
        if len(cycles) > 0:
            cycle = cycles[0]
            assert "period" in cycle
            assert "amplitude" in cycle
            assert "phase" in cycle
            assert "significance" in cycle
            assert 0 <= cycle["significance"] <= 1

    @pytest.mark.asyncio
    async def test_build_time_series_query(self, trend_service):
        """Test SQL query building for different metrics"""
        workspace_id = "test-workspace"
        start_date = datetime(2024, 1, 1)

        # Test different metric types
        metrics = ["executions", "users", "credits", "errors", "success_rate"]

        for metric in metrics:
            query = trend_service._build_time_series_query(metric, workspace_id, start_date)
            assert isinstance(query, str)
            assert workspace_id in query
            assert "SELECT" in query.upper()
            assert "FROM" in query.upper()


class TestTrendAnalysisIntegration:
    """Integration tests for TrendAnalysisService"""

    @pytest.mark.asyncio
    async def test_analyze_trend_with_insufficient_data(self, trend_service, mock_db):
        """Test trend analysis with insufficient data"""
        # Mock database to return insufficient data
        mock_db.execute = AsyncMock(
            return_value=Mock(
                fetchall=Mock(
                    return_value=[(datetime(2024, 1, 1), 100), (datetime(2024, 1, 2), 105)]
                )
            )
        )

        result = await trend_service.analyze_trend("workspace-123", "executions", "30d")

        assert result["error"] == "insufficient_data"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_get_trend_recommendation(self, trend_service):
        """Test trend recommendation generation"""
        # Test different trend types
        assert isinstance(trend_service._get_trend_recommendation("increasing", 20), str)
        assert isinstance(trend_service._get_trend_recommendation("decreasing", -20), str)
        assert isinstance(trend_service._get_trend_recommendation("stable", 2), str)
        assert isinstance(trend_service._get_trend_recommendation("volatile", 50), str)
