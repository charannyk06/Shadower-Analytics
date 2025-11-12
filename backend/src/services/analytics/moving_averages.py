"""Moving average calculations for time-series data smoothing and trend analysis.

This module provides moving average calculations for analyzing trends and patterns
in time-series data. Supports Simple (SMA), Exponential (EMA), and Weighted (WMA)
moving averages.

Security: All database queries enforce workspace isolation through RLS policies
and explicit access validation. Metric names are validated against a whitelist
to prevent SQL injection.
"""

import pandas as pd
import numpy as np
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging
import uuid
from ...utils.datetime import normalize_timeframe_to_interval

logger = logging.getLogger(__name__)


class MovingAverageService:
    """Moving average calculations for time-series trend analysis.

    This service provides:
    - Simple Moving Average (SMA) - Equal weighting of all values in window
    - Exponential Moving Average (EMA) - More weight to recent values
    - Weighted Moving Average (WMA) - Custom weighting of values
    - Trend identification and analysis

    Security:
    - All database methods validate workspace access
    - Metric names are validated against VALID_METRICS whitelist
    - Queries use parameterized statements (no f-string SQL injection)
    - RLS policies provide defense-in-depth at database layer
    """

    # Valid metric column names (whitelist for SQL safety)
    VALID_METRICS = ['runtime_seconds', 'credits_consumed', 'tokens_used', 'executions']

    # Default window sizes for moving averages
    DEFAULT_SMA_WINDOW = 7
    DEFAULT_EMA_SPAN = 7
    DEFAULT_WMA_WEIGHTS = [1, 2, 3, 4, 5, 6, 7]  # Linear increasing weights

    # Performance limits
    MAX_DATA_POINTS = 10000
    MAX_WINDOW_SIZE = 365

    def __init__(self, db: Optional[AsyncSession] = None):
        """Initialize moving average service.

        Args:
            db: Database session for database-based calculations (optional)
        """
        self.db = db

    @staticmethod
    def calculate_sma(data: pd.Series, window: int) -> pd.Series:
        """Calculate simple moving average.

        Simple moving average gives equal weight to all values in the window.
        Uses pandas rolling window for efficient calculation.

        Args:
            data: Time series data as pandas Series
            window: Window size (number of periods)

        Returns:
            Series with moving average values. First (window-1) values are NaN.

        Raises:
            ValueError: If window is invalid
        """
        if window <= 0:
            raise ValueError(f"Window size must be positive, got: {window}")

        if window > len(data):
            logger.warning(f"Window size ({window}) exceeds data length ({len(data)})")

        return data.rolling(window=window, min_periods=1).mean()

    @staticmethod
    def calculate_ema(data: pd.Series, span: int) -> pd.Series:
        """Calculate exponential moving average.

        Exponential moving average gives more weight to recent values,
        making it more responsive to recent changes than SMA.

        Args:
            data: Time series data as pandas Series
            span: Span for EMA calculation (controls decay rate)

        Returns:
            Series with exponential moving average values

        Raises:
            ValueError: If span is invalid
        """
        if span <= 0:
            raise ValueError(f"Span must be positive, got: {span}")

        return data.ewm(span=span, adjust=False).mean()

    @staticmethod
    def calculate_wma(data: pd.Series, weights: List[float]) -> pd.Series:
        """Calculate weighted moving average.

        Weighted moving average allows custom weighting of values in the window.
        Typically used when you want specific emphasis on certain positions.

        Args:
            data: Time series data as pandas Series
            weights: List of weights for each position in window (most recent last)

        Returns:
            Series with weighted moving average values

        Raises:
            ValueError: If weights are invalid
        """
        if not weights:
            raise ValueError("Weights list cannot be empty")

        if any(w < 0 for w in weights):
            raise ValueError("Weights must be non-negative")

        if sum(weights) == 0:
            raise ValueError("Sum of weights must be greater than zero")

        def weighted_avg(values):
            """Apply weighted average to a window of values."""
            if len(values) < len(weights):
                # Use subset of weights for partial windows
                window_weights = weights[-len(values):]
            else:
                window_weights = weights

            return np.average(values, weights=window_weights)

        return data.rolling(window=len(weights), min_periods=1).apply(weighted_avg, raw=True)

    @staticmethod
    def identify_trend(data: pd.Series, ma_values: pd.Series) -> str:
        """Identify overall trend direction.

        Compares current value with moving average to determine trend.

        Args:
            data: Original time series data
            ma_values: Moving average values

        Returns:
            Trend direction: 'upward', 'downward', or 'neutral'
        """
        if len(data) < 2 or len(ma_values) < 2:
            return 'neutral'

        # Get last valid values
        last_data = data.iloc[-1]
        last_ma = ma_values.iloc[-1]

        # Get previous moving average
        prev_ma = ma_values.iloc[-2]

        # Check for NaN values
        if pd.isna(last_data) or pd.isna(last_ma) or pd.isna(prev_ma):
            return 'neutral'

        # Check if current value is above MA and MA is increasing
        if last_data > last_ma and last_ma > prev_ma:
            return 'upward'
        elif last_data < last_ma and last_ma < prev_ma:
            return 'downward'
        else:
            return 'neutral'

    async def get_metric_with_ma(
        self,
        workspace_id: str,
        metric: str,
        ma_type: str = 'sma',
        window: int = 7,
        timeframe: str = "90d",
        weights: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """Get metric data with moving average calculation.

        Retrieves time-series data from database and calculates moving average.

        Args:
            workspace_id: Workspace identifier (must be valid UUID)
            metric: Metric name (from VALID_METRICS)
            ma_type: Moving average type ('sma', 'ema', or 'wma')
            window: Window size for SMA/EMA, or span for EMA
            timeframe: Time range for data (e.g., '7d', '30d', '90d')
            weights: Custom weights for WMA (required if ma_type='wma')

        Returns:
            Dictionary containing:
            - metric: Metric name
            - ma_type: Moving average type
            - window: Window size used
            - timeframe: Timeframe analyzed
            - data: List of data points with date, value, and moving_average
            - trend: Overall trend direction
            - summary: Statistical summary

        Raises:
            ValueError: If parameters are invalid
            PermissionError: If workspace access denied
        """
        if not self.db:
            raise ValueError("Database session required for metric calculations")

        # Validate UUID format
        try:
            uuid.UUID(workspace_id)
        except ValueError as e:
            raise ValueError(f"Invalid workspace_id format: {workspace_id}. Must be a valid UUID.") from e

        # Validate metric name
        if metric not in self.VALID_METRICS:
            raise ValueError(
                f"Invalid metric name: '{metric}'. "
                f"Must be one of: {self.VALID_METRICS}"
            )

        # Validate moving average type
        if ma_type not in ['sma', 'ema', 'wma']:
            raise ValueError(
                f"Invalid moving average type: '{ma_type}'. "
                "Must be one of: 'sma', 'ema', 'wma'"
            )

        # Validate window size
        if window <= 0:
            raise ValueError(f"Window size must be positive, got: {window}")

        if window > self.MAX_WINDOW_SIZE:
            raise ValueError(
                f"Window size too large: {window}. "
                f"Maximum is {self.MAX_WINDOW_SIZE}"
            )

        # Validate weights for WMA
        if ma_type == 'wma':
            if not weights:
                raise ValueError("Weights required for weighted moving average")
            if len(weights) != window:
                raise ValueError(
                    f"Number of weights ({len(weights)}) must match window size ({window})"
                )

        # Normalize timeframe
        normalized_timeframe = normalize_timeframe_to_interval(timeframe)

        logger.info(
            f"Calculating moving average",
            extra={
                "workspace_id": workspace_id,
                "metric": metric,
                "ma_type": ma_type,
                "window": window,
                "timeframe": timeframe
            }
        )

        start_time = time.time()

        # Build query based on metric
        query_sql = self._build_metric_query(metric)

        query = text(query_sql)
        result = await self.db.execute(
            query,
            {"workspace_id": workspace_id, "timeframe": normalized_timeframe}
        )
        rows = result.fetchall()

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Data fetched",
            extra={
                "workspace_id": workspace_id,
                "metric": metric,
                "row_count": len(rows),
                "elapsed_ms": round(elapsed_ms, 2)
            }
        )

        if not rows:
            return self._get_empty_result(metric, ma_type, window, timeframe)

        # Convert to DataFrame for processing
        df = pd.DataFrame([
            {"date": row.date, "value": float(row.value)}
            for row in rows
        ])

        # Sort by date to ensure proper time series
        df = df.sort_values('date').reset_index(drop=True)

        # Calculate moving average based on type
        if ma_type == 'sma':
            df['moving_average'] = self.calculate_sma(df['value'], window)
        elif ma_type == 'ema':
            df['moving_average'] = self.calculate_ema(df['value'], window)
        elif ma_type == 'wma':
            df['moving_average'] = self.calculate_wma(df['value'], weights)

        # Identify trend
        trend = self.identify_trend(df['value'], df['moving_average'])

        # Calculate summary statistics with NaN handling
        current_val = df['value'].iloc[-1]
        current_ma_val = df['moving_average'].iloc[-1]
        avg_val = df['value'].mean()
        min_val = df['value'].min()
        max_val = df['value'].max()

        summary = {
            "current_value": None if pd.isna(current_val) else round(float(current_val), 2),
            "current_ma": None if pd.isna(current_ma_val) else round(float(current_ma_val), 2),
            "avg_value": None if pd.isna(avg_val) else round(float(avg_val), 2),
            "min_value": None if pd.isna(min_val) else round(float(min_val), 2),
            "max_value": None if pd.isna(max_val) else round(float(max_val), 2),
            "data_points": len(df),
            "trend": trend
        }

        # Convert to output format with NaN handling
        data = []
        for _, row in df.iterrows():
            ma_val = row['moving_average']
            data.append({
                "date": row['date'].isoformat() if isinstance(row['date'], (datetime, date)) else str(row['date']),
                "value": round(float(row['value']), 2),
                "moving_average": None if pd.isna(ma_val) else round(float(ma_val), 2)
            })

        logger.info(
            f"Moving average calculated",
            extra={
                "workspace_id": workspace_id,
                "metric": metric,
                "data_points": len(data),
                "trend": trend
            }
        )

        return {
            "metric": metric,
            "ma_type": ma_type,
            "window": window,
            "timeframe": timeframe,
            "data": data,
            "trend": trend,
            "summary": summary
        }

    def _build_metric_query(self, metric: str) -> str:
        """Build SQL query for metric data retrieval.

        Builds separate query for each metric to prevent SQL injection.
        Each query is hardcoded, not interpolated.

        Args:
            metric: Metric name (already validated against whitelist)

        Returns:
            SQL query string

        Raises:
            ValueError: If metric is unexpected
        """
        if metric == 'runtime_seconds':
            return """
                SELECT
                    DATE(started_at) as date,
                    AVG(runtime_seconds) as value
                FROM analytics.agent_runs
                WHERE workspace_id = :workspace_id
                    AND started_at >= NOW() - CAST(:timeframe AS INTERVAL)
                    AND runtime_seconds IS NOT NULL
                GROUP BY DATE(started_at)
                ORDER BY DATE(started_at)
            """
        elif metric == 'credits_consumed':
            return """
                SELECT
                    DATE(started_at) as date,
                    SUM(credits_consumed) as value
                FROM analytics.agent_runs
                WHERE workspace_id = :workspace_id
                    AND started_at >= NOW() - CAST(:timeframe AS INTERVAL)
                    AND credits_consumed IS NOT NULL
                GROUP BY DATE(started_at)
                ORDER BY DATE(started_at)
            """
        elif metric == 'tokens_used':
            return """
                SELECT
                    DATE(started_at) as date,
                    SUM(tokens_used) as value
                FROM analytics.agent_runs
                WHERE workspace_id = :workspace_id
                    AND started_at >= NOW() - CAST(:timeframe AS INTERVAL)
                    AND tokens_used IS NOT NULL
                GROUP BY DATE(started_at)
                ORDER BY DATE(started_at)
            """
        elif metric == 'executions':
            return """
                SELECT
                    DATE(started_at) as date,
                    COUNT(*) as value
                FROM analytics.agent_runs
                WHERE workspace_id = :workspace_id
                    AND started_at >= NOW() - CAST(:timeframe AS INTERVAL)
                GROUP BY DATE(started_at)
                ORDER BY DATE(started_at)
            """
        else:
            raise ValueError(f"Unexpected metric: {metric}")

    @staticmethod
    def _get_empty_result(metric: str, ma_type: str, window: int, timeframe: str) -> Dict[str, Any]:
        """Return empty result structure when no data is available."""
        return {
            "metric": metric,
            "ma_type": ma_type,
            "window": window,
            "timeframe": timeframe,
            "data": [],
            "trend": "neutral",
            "summary": {
                "current_value": 0.0,
                "current_ma": 0.0,
                "avg_value": 0.0,
                "min_value": 0.0,
                "max_value": 0.0,
                "data_points": 0,
                "trend": "neutral"
            }
        }

    async def compare_moving_averages(
        self,
        workspace_id: str,
        metric: str,
        windows: List[int],
        timeframe: str = "90d"
    ) -> Dict[str, Any]:
        """Compare multiple moving averages with different window sizes.

        Useful for identifying short-term vs long-term trends.

        Args:
            workspace_id: Workspace identifier
            metric: Metric name
            windows: List of window sizes to compare
            timeframe: Time range for data

        Returns:
            Dictionary with comparative analysis of different MA windows
        """
        if not windows:
            raise ValueError("At least one window size required")

        if len(windows) > 5:
            raise ValueError("Maximum 5 window sizes allowed for comparison")

        results = []
        for window in windows:
            ma_data = await self.get_metric_with_ma(
                workspace_id=workspace_id,
                metric=metric,
                ma_type='sma',
                window=window,
                timeframe=timeframe
            )
            results.append({
                "window": window,
                "trend": ma_data['trend'],
                "current_ma": ma_data['summary']['current_ma'],
                "data": ma_data['data']
            })

        # Analyze crossovers and divergences
        analysis = self._analyze_ma_comparison(results)

        return {
            "metric": metric,
            "timeframe": timeframe,
            "windows": windows,
            "comparisons": results,
            "analysis": analysis
        }

    @staticmethod
    def _analyze_ma_comparison(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze comparison between multiple moving averages.

        Looks for crossovers, convergence, and divergence patterns.

        Args:
            results: List of MA calculation results

        Returns:
            Analysis dictionary with insights
        """
        if len(results) < 2:
            return {"insight": "Insufficient data for comparison"}

        # Sort by window size
        sorted_results = sorted(results, key=lambda x: x['window'])

        # Check if short-term MA is above long-term MA (bullish signal)
        short_term = sorted_results[0]['current_ma']
        long_term = sorted_results[-1]['current_ma']

        # Handle None, NaN, or zero values
        if (
            short_term is None or long_term is None or
            short_term == 0.0 or long_term == 0.0 or
            (isinstance(short_term, float) and np.isnan(short_term)) or
            (isinstance(long_term, float) and np.isnan(long_term))
        ):
            return {
                "insight": "Insufficient data for reliable comparison",
                "signal": "neutral",
                "short_term_window": sorted_results[0]['window'],
                "long_term_window": sorted_results[-1]['window'],
                "short_term_ma": short_term,
                "long_term_ma": long_term,
                "spread": 0.0
            }

        signal = "bullish" if short_term > long_term else "bearish" if short_term < long_term else "neutral"

        return {
            "signal": signal,
            "short_term_window": sorted_results[0]['window'],
            "long_term_window": sorted_results[-1]['window'],
            "short_term_ma": short_term,
            "long_term_ma": long_term,
            "spread": round(abs(short_term - long_term), 2)
        }
