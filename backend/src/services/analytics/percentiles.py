"""Percentile calculations for performance metrics.

This module provides statistical percentile calculations for analyzing
performance distributions, identifying outliers, and tracking trends.

Security: All database queries enforce workspace isolation through RLS policies
and explicit access validation. Metric names are validated against a whitelist
to prevent SQL injection.
"""

import numpy as np
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, column, func as sql_func
import logging
import uuid
from ...utils.datetime import normalize_timeframe_to_interval

logger = logging.getLogger(__name__)


class PercentileCalculator:
    """Statistical percentile calculations for performance analysis.

    This service provides:
    - In-memory percentile calculations using numpy
    - Database-aggregated percentiles from analytics.agent_runs
    - Outlier detection using IQR and standard deviation methods
    - Percentile trend analysis over time

    Security:
    - All database methods validate workspace access
    - Metric names are validated against VALID_METRICS whitelist
    - Queries use parameterized statements (no f-string SQL injection)
    - RLS policies provide defense-in-depth at database layer
    """

    # Standard percentiles to calculate
    DEFAULT_PERCENTILES = [50, 75, 90, 95, 99]

    # Outlier detection thresholds
    OUTLIER_IQR_MULTIPLIER = 1.5  # Standard IQR method
    OUTLIER_STD_MULTIPLIER = 3.0  # Standard deviation method

    # Valid metric column names (whitelist for SQL safety)
    VALID_METRICS = ['runtime_seconds', 'credits_consumed', 'tokens_used']

    def __init__(self, db: Optional[AsyncSession] = None):
        """Initialize percentile calculator.

        Args:
            db: Database session for database-based calculations (optional)
        """
        self.db = db

    @staticmethod
    def calculate_percentiles(
        values: List[float],
        percentiles: List[int] = None
    ) -> Dict[str, float]:
        """Calculate percentiles for given values (synchronous, in-memory).

        This method is CPU-bound and performs no I/O, so it's synchronous.
        Uses numpy for efficient percentile calculations on large datasets.

        Args:
            values: List of numeric values
            percentiles: List of percentiles to calculate (default: [50, 75, 90, 95, 99])

        Returns:
            Dictionary containing percentile values and distribution metrics.
            Returns zeros for empty input.
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

    async def _verify_workspace_access(
        self,
        user_id: str,
        workspace_id: str
    ) -> bool:
        """Verify user has access to workspace (multi-tenant security).

        This method enforces application-layer workspace isolation in addition
        to database RLS policies (defense-in-depth).

        Args:
            user_id: User identifier from JWT token
            workspace_id: Workspace identifier

        Returns:
            True if user has access, False otherwise

        Note:
            RLS policies at database layer provide additional security.
            This is application-layer validation for defense-in-depth.
        """
        if not self.db:
            raise ValueError("Database session required for access validation")

        query = text("""
            SELECT 1
            FROM public.workspace_members
            WHERE user_id = :user_id
                AND workspace_id = :workspace_id
            LIMIT 1
        """)

        result = await self.db.execute(
            query,
            {"user_id": user_id, "workspace_id": workspace_id}
        )

        has_access = result.fetchone() is not None

        if not has_access:
            logger.warning(
                f"Workspace access denied",
                extra={
                    "user_id": user_id,
                    "workspace_id": workspace_id,
                    "method": "verify_workspace_access"
                }
            )

        return has_access

    async def calculate_runtime_percentiles(
        self,
        workspace_id: str,
        timeframe: str = "7d",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculate runtime percentiles from database.

        Args:
            workspace_id: Workspace identifier (must be valid UUID)
            timeframe: Time interval (e.g., '1h', '24h', '7d', '30d')
            user_id: Optional user ID for workspace access validation

        Returns:
            Dictionary containing runtime percentile metrics

        Raises:
            ValueError: If database session not provided, invalid timeframe, or invalid UUID format
            PermissionError: If user_id provided but lacks workspace access

        Security:
            - Validates workspace access if user_id provided
            - Validates UUID format to prevent injection
            - Uses parameterized queries (no SQL injection)
            - RLS policies enforce row-level security at database layer
        """
        if not self.db:
            raise ValueError("Database session required for database-based calculations")
        
        # Validate UUID format
        try:
            uuid.UUID(workspace_id)
        except ValueError:
            raise ValueError(f"Invalid workspace_id format: {workspace_id}. Must be a valid UUID.")

        # Validate workspace access (defense-in-depth)
        if user_id:
            has_access = await self._verify_workspace_access(user_id, workspace_id)
            if not has_access:
                raise PermissionError(
                    f"User {user_id} does not have access to workspace {workspace_id}"
                )

        # Normalize timeframe to PostgreSQL interval format
        normalized_timeframe = normalize_timeframe_to_interval(timeframe)

        logger.info(
            f"Calculating runtime percentiles",
            extra={
                "workspace_id": workspace_id,
                "timeframe": timeframe,
                "user_id": user_id
            }
        )

        start_time = time.time()

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
                AND started_at >= NOW() - CAST(:timeframe AS INTERVAL)
                AND runtime_seconds IS NOT NULL
        """)

        result = await self.db.execute(
            query,
            {"workspace_id": workspace_id, "timeframe": normalized_timeframe}
        )
        row = result.fetchone()

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Runtime percentiles calculated",
            extra={
                "workspace_id": workspace_id,
                "elapsed_ms": round(elapsed_ms, 2),
                "result_count": row.count if row else 0
            }
        )

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
        agent_id: Optional[str] = None,
<<<<<<< HEAD
        user_id: Optional[str] = None
=======
        current_user_id: Optional[str] = None
>>>>>>> 8960dd8 (Fix critical security issues and migration conflicts)
    ) -> Dict[str, Any]:
        """Calculate percentiles for any metric from database.

        SECURITY: This method uses a whitelist (VALID_METRICS) and separate
        query building to prevent SQL injection. The metric_name is validated
        before any SQL construction.

        Args:
            workspace_id: Workspace identifier (must be valid UUID)
            metric_name: Name of metric ('runtime_seconds', 'credits_consumed', 'tokens_used')
            timeframe: Time interval (e.g., '7d', '24h')
            agent_id: Optional agent identifier for agent-specific metrics
            user_id: Optional user ID for workspace access validation

        Returns:
            Dictionary containing metric percentile analysis

        Raises:
            ValueError: If metric_name not in VALID_METRICS, invalid timeframe, or invalid UUID format
            PermissionError: If user lacks workspace access

        Security:
            - Validates metric_name against VALID_METRICS whitelist
            - Validates UUID format to prevent injection
            - Uses separate queries per metric (no f-string interpolation)
            - Validates workspace access if user_id provided
            - Uses parameterized query parameters only
        """
        if not self.db:
            raise ValueError("Database session required for database-based calculations")

        # Validate UUID format
        try:
            uuid.UUID(workspace_id)
        except ValueError:
            raise ValueError(f"Invalid workspace_id format: {workspace_id}. Must be a valid UUID.")

        # Validate metric name against whitelist
        if metric_name not in self.VALID_METRICS:
            raise ValueError(
                f"Invalid metric name: '{metric_name}'. "
                f"Must be one of: {self.VALID_METRICS}"
            )

        # Validate agent_id UUID format if provided
        if agent_id:
            try:
                uuid.UUID(agent_id)
            except ValueError:
                raise ValueError(f"Invalid agent_id format: {agent_id}. Must be a valid UUID.")

        # Validate workspace access
        if user_id:
            has_access = await self._verify_workspace_access(user_id, workspace_id)
            if not has_access:
                raise PermissionError(
                    f"User {user_id} does not have access to workspace {workspace_id}"
                )

        # Normalize timeframe to PostgreSQL interval format
        normalized_timeframe = normalize_timeframe_to_interval(timeframe)

        logger.info(
            f"Calculating metric percentiles",
            extra={
                "workspace_id": workspace_id,
                "metric_name": metric_name,
                "timeframe": timeframe,
                "agent_id": agent_id,
                "user_id": user_id
            }
        )

        start_time = time.time()

        # Build separate queries per metric (safe from SQL injection)
        # Each query is hardcoded with the column name, not interpolated
        if metric_name == 'runtime_seconds':
            query_sql = """
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
                    AND started_at >= NOW() - CAST(:timeframe AS INTERVAL)
                    AND runtime_seconds IS NOT NULL
            """
        elif metric_name == 'credits_consumed':
            query_sql = """
                SELECT
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY credits_consumed) as p50,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY credits_consumed) as p75,
                    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY credits_consumed) as p90,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY credits_consumed) as p95,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY credits_consumed) as p99,
                    AVG(credits_consumed) as mean,
                    STDDEV(credits_consumed) as std_dev,
                    MIN(credits_consumed) as min,
                    MAX(credits_consumed) as max,
                    COUNT(*) as count
                FROM analytics.agent_runs
                WHERE workspace_id = :workspace_id
                    AND started_at >= NOW() - CAST(:timeframe AS INTERVAL)
                    AND credits_consumed IS NOT NULL
            """
        elif metric_name == 'tokens_used':
            query_sql = """
                SELECT
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY tokens_used) as p50,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY tokens_used) as p75,
                    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY tokens_used) as p90,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY tokens_used) as p95,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY tokens_used) as p99,
                    AVG(tokens_used) as mean,
                    STDDEV(tokens_used) as std_dev,
                    MIN(tokens_used) as min,
                    MAX(tokens_used) as max,
                    COUNT(*) as count
                FROM analytics.agent_runs
                WHERE workspace_id = :workspace_id
                    AND started_at >= NOW() - CAST(:timeframe AS INTERVAL)
                    AND tokens_used IS NOT NULL
            """
        else:
            # Should never reach here due to whitelist check above
            raise ValueError(f"Unexpected metric name: {metric_name}")

        # Add agent filter if provided
        params = {"workspace_id": workspace_id, "timeframe": normalized_timeframe}
        if agent_id:
            query_sql += " AND agent_id = :agent_id"
            params["agent_id"] = agent_id

        query = text(query_sql)
        result = await self.db.execute(query, params)
        row = result.fetchone()

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Metric percentiles calculated",
            extra={
                "workspace_id": workspace_id,
                "metric_name": metric_name,
                "elapsed_ms": round(elapsed_ms, 2),
                "result_count": row.count if row else 0
            }
        )

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

        Uses either IQR (Interquartile Range) or standard deviation method.
        Handles NaN values by filtering them out before analysis.

        Args:
            values: List of numeric values
            method: Detection method ('iqr' or 'std')

        Returns:
            Dictionary containing outlier analysis with:
            - outliers: List of outlier values
            - outlier_indices: Indices in the ORIGINAL input array (before NaN filtering)
            - outlier_count: Number of outliers found
            - outlier_percentage: Percentage of values that are outliers
            - lower_bound: Lower threshold for outlier detection
            - upper_bound: Upper threshold for outlier detection
            - method: Method used for detection

        Raises:
            ValueError: If method is not 'iqr' or 'std'
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

        # Track valid (non-NaN) indices in original array
        valid_mask = ~np.isnan(arr)
        arr_filtered = arr[valid_mask]

        if len(arr_filtered) == 0:
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
            q1 = np.percentile(arr_filtered, 25)
            q3 = np.percentile(arr_filtered, 75)
            iqr = q3 - q1
            lower_bound = q1 - (PercentileCalculator.OUTLIER_IQR_MULTIPLIER * iqr)
            upper_bound = q3 + (PercentileCalculator.OUTLIER_IQR_MULTIPLIER * iqr)
        elif method == "std":
            # Standard Deviation method
            mean = np.mean(arr_filtered)
            std = np.std(arr_filtered)
            lower_bound = mean - (PercentileCalculator.OUTLIER_STD_MULTIPLIER * std)
            upper_bound = mean + (PercentileCalculator.OUTLIER_STD_MULTIPLIER * std)
        else:
            raise ValueError(f"Invalid method: '{method}'. Must be 'iqr' or 'std'")

        # Find outliers in filtered array
        outlier_mask = (arr_filtered < lower_bound) | (arr_filtered > upper_bound)
        outliers = arr_filtered[outlier_mask].tolist()

        # Map back to original array indices
        original_indices = np.arange(len(arr))[valid_mask]
        outlier_indices = original_indices[outlier_mask].tolist()

        return {
            "outliers": outliers,
            "outlier_indices": outlier_indices,
            "outlier_count": len(outliers),
            "outlier_percentage": round((len(outliers) / len(arr_filtered)) * 100, 2),
            "lower_bound": round(float(lower_bound), 2),
            "upper_bound": round(float(upper_bound), 2),
            "method": method
        }

    async def calculate_percentile_trends(
        self,
        workspace_id: str,
        metric_name: str = "runtime_seconds",
        days: int = 7,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculate daily percentile trends over time.

        Args:
            workspace_id: Workspace identifier (must be valid UUID)
            metric_name: Metric to analyze (from VALID_METRICS)
            days: Number of days to analyze (must be positive)
            agent_id: Optional agent identifier
            user_id: Optional user ID for workspace access validation

        Returns:
            Dictionary containing daily percentile trends

        Raises:
            ValueError: If metric_name not in VALID_METRICS, invalid UUID format, or invalid days parameter
            PermissionError: If user lacks workspace access

        Security:
            - Validates metric_name against VALID_METRICS whitelist
            - Validates UUID format to prevent injection
            - Uses separate hardcoded queries (no SQL injection)
            - Validates workspace access if user_id provided
        """
        if not self.db:
            raise ValueError("Database session required for trend calculations")

        # Validate UUID format
        try:
            uuid.UUID(workspace_id)
        except ValueError:
            raise ValueError(f"Invalid workspace_id format: {workspace_id}. Must be a valid UUID.")

        # Validate days parameter
        if not isinstance(days, int) or days <= 0:
            raise ValueError(f"Invalid days parameter: {days}. Must be a positive integer.")
        
        if days > 365:
            raise ValueError(f"Days parameter too large: {days}. Maximum is 365 days.")

        # Validate metric name
        if metric_name not in self.VALID_METRICS:
            raise ValueError(
                f"Invalid metric name: '{metric_name}'. "
                f"Must be one of: {self.VALID_METRICS}"
            )

        # Validate agent_id UUID format if provided
        if agent_id:
            try:
                uuid.UUID(agent_id)
            except ValueError:
                raise ValueError(f"Invalid agent_id format: {agent_id}. Must be a valid UUID.")

        # Validate workspace access
        if user_id:
            has_access = await self._verify_workspace_access(user_id, workspace_id)
            if not has_access:
                raise PermissionError(
                    f"User {user_id} does not have access to workspace {workspace_id}"
                )

        logger.info(
            f"Calculating percentile trends",
            extra={
                "workspace_id": workspace_id,
                "metric_name": metric_name,
                "days": days,
                "agent_id": agent_id,
                "user_id": user_id
            }
        )

        # Build separate queries per metric (safe from SQL injection)
        if metric_name == 'runtime_seconds':
            query_sql = """
                SELECT
                    DATE(started_at) as date,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY runtime_seconds) as p50,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY runtime_seconds) as p75,
                    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY runtime_seconds) as p90,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY runtime_seconds) as p95,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY runtime_seconds) as p99,
                    AVG(runtime_seconds) as mean,
                    COUNT(*) as count
                FROM analytics.agent_runs
                WHERE workspace_id = :workspace_id
                    AND started_at >= CURRENT_DATE - (:days * INTERVAL '1 day')
                    AND runtime_seconds IS NOT NULL
            """
        elif metric_name == 'credits_consumed':
            query_sql = """
                SELECT
                    DATE(started_at) as date,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY credits_consumed) as p50,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY credits_consumed) as p75,
                    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY credits_consumed) as p90,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY credits_consumed) as p95,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY credits_consumed) as p99,
                    AVG(credits_consumed) as mean,
                    COUNT(*) as count
                FROM analytics.agent_runs
                WHERE workspace_id = :workspace_id
                    AND started_at >= CURRENT_DATE - (:days * INTERVAL '1 day')
                    AND credits_consumed IS NOT NULL
            """
        elif metric_name == 'tokens_used':
            query_sql = """
                SELECT
                    DATE(started_at) as date,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY tokens_used) as p50,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY tokens_used) as p75,
                    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY tokens_used) as p90,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY tokens_used) as p95,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY tokens_used) as p99,
                    AVG(tokens_used) as mean,
                    COUNT(*) as count
                FROM analytics.agent_runs
                WHERE workspace_id = :workspace_id
                    AND started_at >= CURRENT_DATE - (:days * INTERVAL '1 day')
                    AND tokens_used IS NOT NULL
            """
        else:
            raise ValueError(f"Unexpected metric name: {metric_name}")

        params = {"workspace_id": workspace_id, "days": days}

        if agent_id:
            query_sql += " AND agent_id = :agent_id"
            params["agent_id"] = agent_id

        query_sql += """
            GROUP BY DATE(started_at)
            ORDER BY DATE(started_at)
        """

        query = text(query_sql)
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

        logger.info(
            f"Percentile trends calculated",
            extra={
                "workspace_id": workspace_id,
                "metric_name": metric_name,
                "total_days": len(trends)
            }
        )

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
