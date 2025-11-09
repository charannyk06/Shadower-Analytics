"""Unit tests for trend analysis service."""

import pytest
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from unittest.mock import AsyncMock, MagicMock, patch

from backend.src.services.analytics.trend_analysis import TrendAnalysisService


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    return db


@pytest.fixture
def trend_service(mock_db):
    """Create trend analysis service instance."""
    return TrendAnalysisService(mock_db)


@pytest.fixture
def sample_time_series():
    """Create sample time series data."""
    dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
    values = np.random.normal(100, 10, 30) + np.arange(30) * 2  # Upward trend

    return [
        {
            'timestamp': date.isoformat(),
            'value': float(value)
        }
        for date, value in zip(dates, values)
    ]


class TestTrendAnalysisService:
    """Test cases for TrendAnalysisService."""

    def test_parse_timeframe(self, trend_service):
        """Test timeframe parsing."""
        assert trend_service._parse_timeframe('7d') == 7
        assert trend_service._parse_timeframe('30d') == 30
        assert trend_service._parse_timeframe('90d') == 90
        assert trend_service._parse_timeframe('1y') == 365
        assert trend_service._parse_timeframe('invalid') == 30  # default

    def test_get_period_name(self, trend_service):
        """Test period name mapping."""
        assert trend_service._get_period_name(1) == 'daily'
        assert trend_service._get_period_name(7) == 'weekly'
        assert trend_service._get_period_name(30) == 'monthly'
        assert trend_service._get_period_name(90) == 'quarterly'

    def test_detect_period(self, trend_service):
        """Test period detection."""
        # Create sample data with weekly pattern
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        values = [100 + 10 * (i % 7) for i in range(30)]
        df = pd.DataFrame({'value': values}, index=dates)

        period = trend_service._detect_period(df)
        assert isinstance(period, int)
        assert period > 0

    def test_insufficient_data_response(self, trend_service):
        """Test insufficient data response."""
        response = trend_service._insufficient_data_response(
            'workspace-123',
            'executions',
            '30d'
        )

        assert response['workspaceId'] == 'workspace-123'
        assert response['metric'] == 'executions'
        assert response['timeframe'] == '30d'
        assert response['error'] == 'insufficient_data'
        assert 'message' in response

    @pytest.mark.asyncio
    async def test_calculate_overview(self, trend_service):
        """Test trend overview calculation."""
        # Create simple upward trend
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        values = np.arange(30) + 100
        df = pd.DataFrame({'value': values}, index=dates)

        overview = await trend_service._calculate_overview(df)

        assert 'currentValue' in overview
        assert 'previousValue' in overview
        assert 'change' in overview
        assert 'changePercentage' in overview
        assert 'trend' in overview
        assert overview['trend'] == 'increasing'
        assert overview['change'] > 0

    def test_detect_growth_pattern(self, trend_service):
        """Test growth pattern detection."""
        # Create linear growth
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        values = np.arange(30) * 2 + 100
        df = pd.DataFrame({'value': values}, index=dates)

        pattern = trend_service._detect_growth_pattern(df)

        assert 'type' in pattern
        assert 'rate' in pattern
        assert 'acceleration' in pattern
        assert 'projectedGrowth' in pattern
        assert pattern['type'] in ['linear', 'exponential', 'logarithmic', 'polynomial']

    def test_detect_seasonality(self, trend_service):
        """Test seasonality detection."""
        # Create data with weekly seasonality
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        values = [100 + 20 * np.sin(2 * np.pi * i / 7) for i in range(30)]
        df = pd.DataFrame({'value': values}, index=dates)

        seasonality = trend_service._detect_seasonality(df)

        assert 'detected' in seasonality
        assert 'type' in seasonality
        assert 'strength' in seasonality
        assert 'peakPeriods' in seasonality
        assert 'lowPeriods' in seasonality

    def test_detect_cycles(self, trend_service):
        """Test cycle detection."""
        # Create cyclical data
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        values = [100 + 10 * np.sin(2 * np.pi * i / 7) for i in range(30)]
        df = pd.DataFrame({'value': values}, index=dates)

        cycles = trend_service._detect_cycles(df)

        assert isinstance(cycles, list)
        # Cycles may or may not be detected depending on data quality

    def test_simple_forecast(self, trend_service):
        """Test simple linear forecast."""
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        values = np.arange(30) + 100
        df = pd.DataFrame({'value': values}, index=dates)

        forecast = trend_service._simple_forecast(df)

        assert 'shortTerm' in forecast
        assert 'longTerm' in forecast
        assert 'accuracy' in forecast
        assert len(forecast['shortTerm']) == 7  # 7 days forecast

    def test_prepare_time_series(self, trend_service):
        """Test time series preparation."""
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        values = np.random.normal(100, 10, 30)
        df = pd.DataFrame({'value': values}, index=dates)

        result = trend_service._prepare_time_series(df)

        assert 'data' in result
        assert 'statistics' in result
        assert len(result['data']) == 30

        # Check statistics
        stats = result['statistics']
        assert 'mean' in stats
        assert 'median' in stats
        assert 'stdDev' in stats
        assert 'variance' in stats
        assert 'skewness' in stats
        assert 'kurtosis' in stats

    @pytest.mark.asyncio
    async def test_generate_comparisons(self, trend_service):
        """Test comparison generation."""
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        values = np.arange(30) + 100
        df = pd.DataFrame({'value': values}, index=dates)

        comparisons = await trend_service._generate_comparisons(
            df, 'workspace-123', 'executions'
        )

        assert 'periodComparison' in comparisons
        assert 'yearOverYear' in comparisons
        assert 'benchmarks' in comparisons

        period_comp = comparisons['periodComparison']
        assert 'currentPeriod' in period_comp
        assert 'previousPeriod' in period_comp
        assert 'change' in period_comp
        assert 'changePercentage' in period_comp

    @pytest.mark.asyncio
    async def test_generate_insights(self, trend_service):
        """Test insight generation."""
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        values = np.arange(30) * 10 + 100  # Strong upward trend
        df = pd.DataFrame({'value': values}, index=dates)

        overview = {
            'trend': 'increasing',
            'changePercentage': 50,
            'confidence': 95
        }

        insights = await trend_service._generate_insights(df, overview)

        assert isinstance(insights, list)
        if len(insights) > 0:
            insight = insights[0]
            assert 'type' in insight
            assert 'title' in insight
            assert 'description' in insight
            assert 'impact' in insight
            assert 'confidence' in insight
            assert 'recommendation' in insight


class TestBuildMetricQuery:
    """Test metric query building."""

    def test_build_executions_query(self, trend_service):
        """Test executions metric query."""
        query, params = trend_service._build_metric_query('executions')

        assert 'agent_executions' in query
        assert ':workspace_id' in query  # Parameterized query
        assert 'COUNT(*)' in query
        assert params == {}  # Empty params dict

    def test_build_users_query(self, trend_service):
        """Test users metric query."""
        query, params = trend_service._build_metric_query('users')

        assert 'agent_executions' in query
        assert 'COUNT(DISTINCT user_id)' in query
        assert ':workspace_id' in query

    def test_build_credits_query(self, trend_service):
        """Test credits metric query."""
        query, params = trend_service._build_metric_query('credits')

        assert 'credit_transactions' in query
        assert 'SUM(credits_used)' in query or 'COALESCE' in query
        assert ':workspace_id' in query

    def test_build_success_rate_query(self, trend_service):
        """Test success rate metric query."""
        query, params = trend_service._build_metric_query('success_rate')

        assert 'agent_executions' in query
        assert 'completed' in query
        assert ':workspace_id' in query


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
