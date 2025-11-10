"""Percentile calculations for performance metrics."""

import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


class PercentileCalculator:
    """Statistical percentile calculations for performance analysis."""

    # Standard percentiles to calculate
    DEFAULT_PERCENTILES = [50, 75, 90, 95, 99]

    # Outlier detection thresholds
    OUTLIER_IQR_MULTIPLIER = 1.5  # Standard IQR method
    OUTLIER_STD_MULTIPLIER = 3.0  # Standard deviation method

    def __init__(self, db: Optional[AsyncSession] = None):
        """Initialize percentile calculator.

        Args:
            db: Database session for database-based calculations (optional)
        """
        self.db = db

    @staticmethod
    def _parse_timeframe(timeframe: str) -> str:
        """Parse timeframe shorthand to PostgreSQL interval format.

        Args:
            timeframe: Shorthand format like '7d', '24h', '30d', '1h'

        Returns:
            PostgreSQL interval format like '7 days', '24 hours', '30 days', '1 hour'
        """
        import re
        match = re.match(r'^(\d+)([hd])$', timeframe)
        if not match:
            # If already in correct format or unknown, return as-is
            return timeframe
        
        value, unit = match.groups()
        unit_map = {
            'h': 'hours',
            'd': 'days'
        }
        return f"{value} {unit_map[unit]}"

    @staticmethod
    async def calculate_percentiles(
        values: List[float],
        percentiles: List[int] = None
    ) -> Dict[str, float]:
        """Calculate percentiles for given values.

        Args:
            values: List of numeric values
            percentiles: List of percentiles to calculate (default: [50, 75, 90, 95, 99])

        Returns:
            Dictionary containing percentile values and distribution metrics
        """
        if percentiles is None:
            percentiles = PercentileCalculator.DEFAULT_PERCENTILES

        if not values:
            return {f"p{p}": 0.0 for p in percentiles}

        # Convert to numpy array for efficient calculations
        arr = np.array(values, dtype=float)

        # Remove NaN values
        arr = arr[~np.isnan(arr)]

        if len(arr) == 0:
            return {f"p{p}": 0.0 for p in percentiles}

        results = {}

        # Calculate percentiles
        for p in percentiles:
            results[f"p{p}"] = float(np.percentile(arr, p))

        # Add distribution metrics
        results['mean'] = float(np.mean(arr))
        results['median'] = float(np.median(arr))
        results['std_dev'] = float(np.std(arr))
        results['min'] = float(np.min(arr))
        results['max'] = float(np.max(arr))

        # Add additional statistical measures
        results['variance'] = float(np.var(arr))
        results['count'] = len(arr)

        return results

    async def calculate_runtime_percentiles(
        self,
        workspace_id: str,
        timeframe: str = "7d"
    ) -> Dict[str, Any]:
        """Calculate runtime percentiles from database.

        Args:
            workspace_id: Workspace identifier
            timeframe: Time interval (e.g., '1h', '24h', '7d', '30d')

        Returns:
            Dictionary containing runtime percentile metrics
        """
        if not self.db:
            raise ValueError("Database session required for database-based calculations")

        # Parse timeframe to PostgreSQL interval format
        parsed_timeframe = self._parse_timeframe(timeframe)

        query = text("""
            SELECT
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY runtime_seconds) as p50,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY runtime_seconds) as p75,
                PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY runtime_seconds) as p90,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY runtime_seconds) as p95,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY runtime_seconds) as p99,
                AVG(runtime_seconds) as mean,
                STDDEV(runtime_seconds) as std_dev,
                MIN(runtime_seconds) as min,
                MAX(runtime_seconds) as max,
                COUNT(*) as count
            FROM analytics.agent_runs
            WHERE workspace_id = :workspace_id
                AND started_at >= NOW() - INTERVAL :timeframe
                AND runtime_seconds IS NOT NULL
        """)

        result = await self.db.execute(
            query,
            {"workspace_id": workspace_id, "timeframe": parsed_timeframe}
        )
        row = result.fetchone()

        if not row or row.count == 0:
            return {
                "p50": 0.0,
                "p75": 0.0,
                "p90": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "mean": 0.0,
                "std_dev": 0.0,
                "min": 0.0,
                "max": 0.0,
                "count": 0
            }

        return {
            "p50": round(float(row.p50 or 0), 2),
            "p75": round(float(row.p75 or 0), 2),
            "p90": round(float(row.p90 or 0), 2),
            "p95": round(float(row.p95 or 0), 2),
            "p99": round(float(row.p99 or 0), 2),
            "mean": round(float(row.mean or 0), 2),
            "std_dev": round(float(row.std_dev or 0), 2),
            "min": round(float(row.min or 0), 2),
            "max": round(float(row.max or 0), 2),
            "count": row.count
        }

    async def calculate_metric_percentiles(
        self,
        workspace_id: str,
        metric_name: str,
        timeframe: str = "7d",
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculate percentiles for any metric from database.

        Args:
            workspace_id: Workspace identifier
            metric_name: Name of the metric column (e.g., 'runtime_seconds', 'credits_consumed', 'tokens_used')
            timeframe: Time interval
            agent_id: Optional agent identifier for agent-specific metrics

        Returns:
            Dictionary containing metric percentile analysis
        """
        if not self.db:
            raise ValueError("Database session required for database-based calculations")

        # Validate metric name to prevent SQL injection
        valid_metrics = ['runtime_seconds', 'credits_consumed', 'tokens_used']
        if metric_name not in valid_metrics:
            raise ValueError(f"Invalid metric name. Must be one of: {valid_metrics}")

        # Parse timeframe to PostgreSQL interval format
        parsed_timeframe = self._parse_timeframe(timeframe)

        # Build query with optional agent filter
        where_clause = "WHERE workspace_id = :workspace_id AND started_at >= NOW() - INTERVAL :timeframe"
        params = {"workspace_id": workspace_id, "timeframe": parsed_timeframe}

        if agent_id:
            where_clause += " AND agent_id = :agent_id"
            params["agent_id"] = agent_id

        query = text(f"""
            SELECT
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY {metric_name}) as p50,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {metric_name}) as p75,
                PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY {metric_name}) as p90,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY {metric_name}) as p95,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY {metric_name}) as p99,
                AVG({metric_name}) as mean,
                STDDEV({metric_name}) as std_dev,
                MIN({metric_name}) as min,
                MAX({metric_name}) as max,
                COUNT(*) as count
            FROM analytics.agent_runs
            {where_clause}
                AND {metric_name} IS NOT NULL
        """)

        result = await self.db.execute(query, params)
        row = result.fetchone()

        if not row or row.count == 0:
            return self._get_empty_percentile_result()

        return {
            "metric": metric_name,
            "p50": round(float(row.p50 or 0), 2),
            "p75": round(float(row.p75 or 0), 2),
            "p90": round(float(row.p90 or 0), 2),
            "p95": round(float(row.p95 or 0), 2),
            "p99": round(float(row.p99 or 0), 2),
            "mean": round(float(row.mean or 0), 2),
            "std_dev": round(float(row.std_dev or 0), 2),
            "min": round(float(row.min or 0), 2),
            "max": round(float(row.max or 0), 2),
            "count": row.count
        }

    @staticmethod
    def detect_outliers(
        values: List[float],
        method: str = "iqr"
    ) -> Dict[str, Any]:
        """Detect outliers in a dataset.

        Args:
            values: List of numeric values
            method: Detection method ('iqr' or 'std')

        Returns:
            Dictionary containing outlier analysis
        """
        if not values:
            return {
                "outliers": [],
                "outlier_indices": [],
                "outlier_count": 0,
                "outlier_percentage": 0.0,
                "lower_bound": 0.0,
                "upper_bound": 0.0,
                "method": method
            }

        arr = np.array(values, dtype=float)
        nan_mask = ~np.isnan(arr)
        original_indices = np.arange(len(arr))[nan_mask]
        arr = arr[nan_mask]

        if len(arr) == 0:
            return {
                "outliers": [],
                "outlier_indices": [],
                "outlier_count": 0,
                "outlier_percentage": 0.0,
                "lower_bound": 0.0,
                "upper_bound": 0.0,
                "method": method
            }

        if method == "iqr":
            # Interquartile Range method
            q1 = np.percentile(arr, 25)
            q3 = np.percentile(arr, 75)
            iqr = q3 - q1
            lower_bound = q1 - (PercentileCalculator.OUTLIER_IQR_MULTIPLIER * iqr)
            upper_bound = q3 + (PercentileCalculator.OUTLIER_IQR_MULTIPLIER * iqr)
        elif method == "std":
            # Standard Deviation method
            mean = np.mean(arr)
            std = np.std(arr)
            lower_bound = mean - (PercentileCalculator.OUTLIER_STD_MULTIPLIER * std)
            upper_bound = mean + (PercentileCalculator.OUTLIER_STD_MULTIPLIER * std)
        else:
            raise ValueError(f"Invalid method: {method}. Must be 'iqr' or 'std'")

        # Find outliers
        outlier_mask = (arr < lower_bound) | (arr > upper_bound)
        outliers = arr[outlier_mask].tolist()
        outlier_indices = original_indices[outlier_mask].tolist()

        return {
            "outliers": outliers,
            "outlier_indices": outlier_indices,
            "outlier_count": len(outliers),
            "outlier_percentage": round((len(outliers) / len(arr)) * 100, 2),
            "lower_bound": round(float(lower_bound), 2),
            "upper_bound": round(float(upper_bound), 2),
            "method": method
        }

    async def calculate_percentile_trends(
        self,
        workspace_id: str,
        metric_name: str = "runtime_seconds",
        days: int = 7,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculate daily percentile trends over time.

        Args:
            workspace_id: Workspace identifier
            metric_name: Metric to analyze
            days: Number of days to analyze
            agent_id: Optional agent identifier

        Returns:
            Dictionary containing daily percentile trends
        """
        if not self.db:
            raise ValueError("Database session required for trend calculations")

        # Validate metric name
        valid_metrics = ['runtime_seconds', 'credits_consumed', 'tokens_used']
        if metric_name not in valid_metrics:
            raise ValueError(f"Invalid metric name. Must be one of: {valid_metrics}")

        where_clause = "WHERE workspace_id = :workspace_id AND started_at >= CURRENT_DATE - INTERVAL :days"
        params = {"workspace_id": workspace_id, "days": f"{days} days"}

        if agent_id:
            where_clause += " AND agent_id = :agent_id"
            params["agent_id"] = agent_id

        query = text(f"""
            SELECT
                DATE(started_at) as date,
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY {metric_name}) as p50,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {metric_name}) as p75,
                PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY {metric_name}) as p90,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY {metric_name}) as p95,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY {metric_name}) as p99,
                AVG({metric_name}) as mean,
                COUNT(*) as count
            FROM analytics.agent_runs
            {where_clause}
                AND {metric_name} IS NOT NULL
            GROUP BY DATE(started_at)
            ORDER BY DATE(started_at)
        """)

        result = await self.db.execute(query, params)
        rows = result.fetchall()

        trends = []
        for row in rows:
            trends.append({
                "date": row.date.isoformat(),
                "p50": round(float(row.p50 or 0), 2),
                "p75": round(float(row.p75 or 0), 2),
                "p90": round(float(row.p90 or 0), 2),
                "p95": round(float(row.p95 or 0), 2),
                "p99": round(float(row.p99 or 0), 2),
                "mean": round(float(row.mean or 0), 2),
                "count": row.count
            })

        return {
            "metric": metric_name,
            "days": days,
            "trends": trends,
            "total_days": len(trends)
        }

    @staticmethod
    def _get_empty_percentile_result() -> Dict[str, Any]:
        """Return empty percentile result structure."""
        return {
            "p50": 0.0,
            "p75": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "mean": 0.0,
            "std_dev": 0.0,
            "min": 0.0,
            "max": 0.0,
            "count": 0
        }
