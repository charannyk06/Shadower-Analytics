"""Secure Trend Analysis Service with parameterized queries and proper validation."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging

import numpy as np
import pandas as pd
from scipy import stats, signal
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import acf
from sklearn.linear_model import LinearRegression
from prophet import Prophet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import ValidationError

from ...models.trend_analysis import TrendAnalysisResponse
from .trend_analysis_constants import *

logger = logging.getLogger(__name__)


class TrendAnalysisService:
    """Secure advanced time-series analysis and trend detection service."""

    def __init__(self, db: AsyncSession):
        """Initialize the trend analysis service.

        Args:
            db: Async database session
        """
        self.db = db

    async def analyze_trend(
        self,
        workspace_id: str,
        metric: str,
        timeframe: str,
        user_id: Optional[str] = None  # For cache scoping
    ) -> Dict[str, Any]:
        """Perform comprehensive trend analysis on a metric with security validation.

        Args:
            workspace_id: The workspace to analyze
            metric: The metric to analyze
            timeframe: Time window
            user_id: Optional user ID for cache scoping

        Returns:
            Comprehensive trend analysis results

        Raises:
            ValueError: If inputs are invalid
            PermissionError: If workspace access is denied
        """
        try:
            # Input validation
            self._validate_inputs(workspace_id, metric, timeframe)

            # Workspace access validation (defense in depth)
            await self._validate_workspace_access(workspace_id, user_id)

            # Check cache first
            cached_result = await self._get_cached_analysis(
                workspace_id, metric, timeframe, user_id
            )
            if cached_result:
                return cached_result

            # Get time series data using parameterized query
            time_series_data = await self._get_time_series_secure(
                workspace_id, metric, timeframe
            )

            if not time_series_data or len(time_series_data) < MIN_DATA_POINTS_FOR_ANALYSIS:
                return self._insufficient_data_response(workspace_id, metric, timeframe)

            # Convert to pandas DataFrame
            df = pd.DataFrame(time_series_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            df.set_index('timestamp', inplace=True)

            # Perform parallel analysis using asyncio.to_thread for CPU-bound operations
            results = await asyncio.gather(
                asyncio.to_thread(self._calculate_overview, df, metric),
                asyncio.to_thread(self._perform_decomposition, df),
                asyncio.to_thread(self._detect_patterns, df),
                asyncio.to_thread(self._generate_comparisons, df, timeframe),
                self._find_correlations(workspace_id, metric, df),
                asyncio.to_thread(self._generate_forecast, df, metric),
                return_exceptions=True
            )

            # Check for exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error in analysis step {i}: {result}", exc_info=True)
                    results[i] = self._get_fallback_result(i)

            # Prepare time series with statistics
            time_series_with_stats = self._prepare_time_series(df)

            # Generate insights based on all analyses
            insights = self._generate_insights(
                df, results[0], results[2], results[3], results[5]
            )

            # Build complete analysis result
            analysis_result = {
                "workspaceId": workspace_id,
                "metric": metric,
                "timeframe": timeframe,
                "overview": results[0],
                "timeSeries": time_series_with_stats,
                "decomposition": results[1],
                "patterns": results[2],
                "comparisons": results[3],
                "correlations": results[4],
                "forecast": results[5],
                "insights": insights
            }

            # Cache the result
            await self._cache_analysis(
                workspace_id, metric, timeframe, analysis_result, user_id
            )

            return analysis_result

        except (ValueError, PermissionError) as e:
            logger.warning(f"Validation error in trend analysis: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in trend analysis: {e}", exc_info=True)
            raise

    def _validate_inputs(
        self,
        workspace_id: str,
        metric: str,
        timeframe: str
    ) -> None:
        """Validate input parameters.

        Args:
            workspace_id: Workspace ID to validate
            metric: Metric name to validate
            timeframe: Timeframe to validate

        Raises:
            ValueError: If any input is invalid
        """
        # Validate workspace_id format (UUID)
        if not workspace_id or len(workspace_id) < 10:
            raise ValueError("Invalid workspace_id format")

        # Validate metric
        if metric not in ALLOWED_METRICS:
            raise ValueError(
                MSG_INVALID_METRIC.format(", ".join(ALLOWED_METRICS))
            )

        # Validate timeframe
        if timeframe not in ALLOWED_TIMEFRAMES:
            raise ValueError(
                MSG_INVALID_TIMEFRAME.format(", ".join(ALLOWED_TIMEFRAMES))
            )

    async def _validate_workspace_access(
        self,
        workspace_id: str,
        user_id: Optional[str]
    ) -> None:
        """Validate user has access to workspace (defense in depth).

        Args:
            workspace_id: Workspace to check
            user_id: User to validate

        Raises:
            PermissionError: If access is denied
        """
        # If no user_id provided, skip validation (API layer handles it)
        if not user_id:
            return

        # Query to check workspace access
        query = text("""
            SELECT EXISTS(
                SELECT 1
                FROM public.workspace_members
                WHERE workspace_id = :workspace_id
                AND user_id = :user_id
            )
        """)

        result = await self.db.execute(
            query,
            {"workspace_id": workspace_id, "user_id": user_id}
        )
        has_access = result.scalar()

        if not has_access:
            logger.warning(
                f"Unauthorized access attempt: user {user_id} to workspace {workspace_id}"
            )
            raise PermissionError(MSG_UNAUTHORIZED_ACCESS)

    async def _get_time_series_secure(
        self,
        workspace_id: str,
        metric: str,
        timeframe: str
    ) -> List[Dict[str, Any]]:
        """Fetch time series data using parameterized queries (SQL injection safe).

        Args:
            workspace_id: Workspace identifier
            metric: Metric name (pre-validated)
            timeframe: Time window (pre-validated)

        Returns:
            List of timestamp-value pairs
        """
        # Parse timeframe
        days = TIMEFRAME_DAYS.get(timeframe, DEFAULT_TIMEFRAME_DAYS)
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get parameterized query and parameters
        query_text, params = self._build_time_series_query_secure(
            metric, workspace_id, start_date
        )

        # Execute with bind parameters
        result = await self.db.execute(text(query_text), params)
        rows = result.fetchall()

        return [
            {
                "timestamp": row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                "value": float(row[1]) if row[1] is not None else 0.0
            }
            for row in rows
        ]

    def _build_time_series_query_secure(
        self,
        metric: str,
        workspace_id: str,
        start_date: datetime
    ) -> Tuple[str, Dict[str, Any]]:
        """Build parameterized SQL query (SQL injection safe).

        Args:
            metric: Metric type (pre-validated)
            workspace_id: Workspace ID
            start_date: Start date for query

        Returns:
            Tuple of (query_string, parameters_dict)
        """
        # Common parameters
        params = {
            "workspace_id": workspace_id,
            "start_date": start_date
        }

        # Metric-specific queries with bind parameters
        metric_queries = {
            "executions": """
                SELECT
                    DATE_TRUNC('day', created_at) as timestamp,
                    COUNT(*) as value
                FROM analytics.agent_executions
                WHERE workspace_id = :workspace_id
                    AND created_at >= :start_date
                GROUP BY DATE_TRUNC('day', created_at)
                ORDER BY timestamp
            """,
            "users": """
                SELECT
                    DATE_TRUNC('day', created_at) as timestamp,
                    COUNT(DISTINCT user_id) as value
                FROM analytics.user_activity
                WHERE workspace_id = :workspace_id
                    AND created_at >= :start_date
                GROUP BY DATE_TRUNC('day', created_at)
                ORDER BY timestamp
            """,
            "credits": """
                SELECT
                    DATE_TRUNC('day', created_at) as timestamp,
                    COALESCE(SUM(credits_consumed), 0) as value
                FROM analytics.agent_executions
                WHERE workspace_id = :workspace_id
                    AND created_at >= :start_date
                GROUP BY DATE_TRUNC('day', created_at)
                ORDER BY timestamp
            """,
            "errors": """
                SELECT
                    DATE_TRUNC('day', created_at) as timestamp,
                    COUNT(*) as value
                FROM analytics.agent_executions
                WHERE workspace_id = :workspace_id
                    AND status = 'failed'
                    AND created_at >= :start_date
                GROUP BY DATE_TRUNC('day', created_at)
                ORDER BY timestamp
            """,
            "success_rate": """
                SELECT
                    DATE_TRUNC('day', created_at) as timestamp,
                    (COUNT(*) FILTER (WHERE status = 'completed') * 100.0 /
                     NULLIF(COUNT(*), 0)) as value
                FROM analytics.agent_executions
                WHERE workspace_id = :workspace_id
                    AND created_at >= :start_date
                GROUP BY DATE_TRUNC('day', created_at)
                ORDER BY timestamp
            """,
            "revenue": """
                SELECT
                    DATE_TRUNC('day', created_at) as timestamp,
                    COALESCE(SUM(revenue_amount), 0) as value
                FROM analytics.revenue_tracking
                WHERE workspace_id = :workspace_id
                    AND created_at >= :start_date
                GROUP BY DATE_TRUNC('day', created_at)
                ORDER BY timestamp
            """
        }

        query = metric_queries.get(metric, metric_queries["executions"])
        return query, params

    def _calculate_overview(
        self,
        df: pd.DataFrame,
        metric: str
    ) -> Dict[str, Any]:
        """Calculate trend overview and high-level statistics."""
        if df.empty or len(df) < 2:
            return self._empty_overview()

        current_value = float(df['value'].iloc[-1])
        previous_value = float(df['value'].iloc[0])

        # Calculate change
        change = current_value - previous_value
        change_percentage = (change / previous_value * 100) if previous_value != 0 else 0

        # Determine trend using linear regression
        X = np.arange(len(df)).reshape(-1, 1)
        y = df['value'].values

        model = LinearRegression()
        model.fit(X, y)
        slope = model.coef_[0]
        r_squared = model.score(X, y)

        # Determine trend direction
        std_y = np.std(y)
        if abs(slope) < (std_y * STABLE_TREND_THRESHOLD):
            trend = 'stable'
        elif slope > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'

        # Calculate volatility
        returns = df['value'].pct_change().dropna()
        volatility = float(returns.std() * 100) if len(returns) > 0 else 0

        if volatility > VOLATILITY_THRESHOLD:
            trend = 'volatile'

        # Trend strength (0-100)
        trend_strength = min(abs(r_squared * 100), 100)

        # Statistical confidence
        confidence = float(r_squared)

        return {
            "currentValue": current_value,
            "previousValue": previous_value,
            "change": change,
            "changePercentage": change_percentage,
            "trend": trend,
            "trendStrength": trend_strength,
            "confidence": confidence
        }

    # ... [Continue with rest of methods - I'll add them in next messages due to length]
