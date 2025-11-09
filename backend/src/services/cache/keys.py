"""Cache key management and naming conventions."""

from typing import List, Dict, Any
import hashlib
import json


class CacheKeys:
    """Centralized cache key management with standardized naming conventions."""

    # Prefixes for different data types
    EXECUTIVE_PREFIX = "exec"
    AGENT_PREFIX = "agent"
    USER_PREFIX = "user"
    WORKSPACE_PREFIX = "ws"
    METRICS_PREFIX = "metrics"
    REPORT_PREFIX = "report"
    QUERY_PREFIX = "query"

    # TTL values (in seconds)
    TTL_SHORT = 60  # 1 minute
    TTL_MEDIUM = 300  # 5 minutes
    TTL_LONG = 1800  # 30 minutes
    TTL_HOUR = 3600  # 1 hour
    TTL_DAY = 86400  # 24 hours

    @staticmethod
    def executive_dashboard(workspace_id: str, timeframe: str) -> str:
        """
        Key for executive dashboard data.

        Args:
            workspace_id: Workspace identifier
            timeframe: Time period (e.g., '24h', '7d', '30d')

        Returns:
            Cache key string
        """
        return f"{CacheKeys.EXECUTIVE_PREFIX}:dashboard:{workspace_id}:{timeframe}"

    @staticmethod
    def agent_analytics(agent_id: str, timeframe: str) -> str:
        """
        Key for agent analytics data.

        Args:
            agent_id: Agent identifier
            timeframe: Time period

        Returns:
            Cache key string
        """
        return f"{CacheKeys.AGENT_PREFIX}:analytics:{agent_id}:{timeframe}"

    @staticmethod
    def agent_top(workspace_id: str, timeframe: str, limit: int = 10) -> str:
        """
        Key for top agents in workspace.

        Args:
            workspace_id: Workspace identifier
            timeframe: Time period
            limit: Number of top agents (default: 10)

        Returns:
            Cache key string

        Note:
            The limit parameter is included in the cache key, meaning that calls
            with different limit values will create separate cache entries. This
            includes the case where limit is omitted (using default of 10) vs
            explicitly passing limit=10 - both will use the same cache entry.
        """
        return f"{CacheKeys.AGENT_PREFIX}:top:{workspace_id}:{timeframe}:{limit}"

    @staticmethod
    def user_activity(user_id: str, date: str) -> str:
        """
        Key for user activity data.

        Args:
            user_id: User identifier
            date: Activity date (YYYY-MM-DD format)

        Returns:
            Cache key string
        """
        return f"{CacheKeys.USER_PREFIX}:activity:{user_id}:{date}"

    @staticmethod
    def user_metrics(user_id: str, timeframe: str) -> str:
        """
        Key for user metrics data.

        Args:
            user_id: User identifier
            timeframe: Time period

        Returns:
            Cache key string
        """
        return f"{CacheKeys.USER_PREFIX}:metrics:{user_id}:{timeframe}"

    @staticmethod
    def user_activity_analytics(workspace_id: str, timeframe: str, segment_id: str = None) -> str:
        """
        Key for user activity analytics data.

        Args:
            workspace_id: Workspace identifier
            timeframe: Time period (e.g., '7d', '30d', '90d')
            segment_id: Optional segment identifier

        Returns:
            Cache key string
        """
        segment_part = f":{segment_id}" if segment_id else ""
        return f"{CacheKeys.USER_PREFIX}:analytics:{workspace_id}:{timeframe}{segment_part}"

    @staticmethod
    def retention_curve(workspace_id: str, cohort_date: str, days: int) -> str:
        """
        Key for retention curve data.

        Args:
            workspace_id: Workspace identifier
            cohort_date: Cohort date in YYYY-MM-DD format
            days: Number of days for retention analysis

        Returns:
            Cache key string
        """
        return f"{CacheKeys.USER_PREFIX}:retention:curve:{workspace_id}:{cohort_date}:{days}"

    @staticmethod
    def cohort_analysis(workspace_id: str, cohort_type: str, start_date: str, end_date: str) -> str:
        """
        Key for cohort analysis data.

        Args:
            workspace_id: Workspace identifier
            cohort_type: Type of cohort (daily, weekly, monthly)
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            Cache key string
        """
        return f"{CacheKeys.USER_PREFIX}:cohort:{workspace_id}:{cohort_type}:{start_date}:{end_date}"

    @staticmethod
    def churn_analysis(workspace_id: str, timeframe: str) -> str:
        """
        Key for churn analysis data.

        Args:
            workspace_id: Workspace identifier
            timeframe: Time period

        Returns:
            Cache key string
        """
        return f"{CacheKeys.USER_PREFIX}:churn:{workspace_id}:{timeframe}"

    @staticmethod
    def workspace_metrics(workspace_id: str, metric_type: str, date: str) -> str:
        """
        Key for workspace metrics.

        Args:
            workspace_id: Workspace identifier
            metric_type: Type of metric (e.g., 'runs', 'users', 'credits')
            date: Date for metrics (YYYY-MM-DD format)

        Returns:
            Cache key string
        """
        return (
            f"{CacheKeys.WORKSPACE_PREFIX}:metrics:{workspace_id}:{metric_type}:{date}"
        )

    @staticmethod
    def workspace_overview(workspace_id: str) -> str:
        """
        Key for workspace overview data.

        Args:
            workspace_id: Workspace identifier

        Returns:
            Cache key string
        """
        return f"{CacheKeys.WORKSPACE_PREFIX}:overview:{workspace_id}"

    @staticmethod
    def query_result(query_hash: str) -> str:
        """
        Key for cached query results.

        Args:
            query_hash: MD5 hash of query and parameters

        Returns:
            Cache key string
        """
        return f"{CacheKeys.QUERY_PREFIX}:result:{query_hash}"

    @staticmethod
    def report_data(report_id: str, format: str = "json") -> str:
        """
        Key for cached report data.

        Args:
            report_id: Report identifier
            format: Report format (json, csv, pdf)

        Returns:
            Cache key string
        """
        return f"{CacheKeys.REPORT_PREFIX}:data:{report_id}:{format}"

    @staticmethod
    def metric_aggregation(metric_type: str, workspace_id: str, period: str) -> str:
        """
        Key for pre-aggregated metrics.

        Args:
            metric_type: Type of metric
            workspace_id: Workspace identifier
            period: Aggregation period (hourly, daily, weekly, monthly)

        Returns:
            Cache key string
        """
        return f"{CacheKeys.METRICS_PREFIX}:agg:{metric_type}:{workspace_id}:{period}"

    @staticmethod
    def generate_query_hash(query: str, params: Dict[str, Any]) -> str:
        """
        Generate MD5 hash for query caching.

        Args:
            query: SQL query string
            params: Query parameters dictionary

        Returns:
            MD5 hash string
        """
        # Sort params to ensure consistent hashing
        content = f"{query}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()

    @staticmethod
    def get_pattern(prefix: str, *parts: str) -> str:
        """
        Generate a pattern for batch operations (e.g., invalidation).

        Args:
            prefix: Key prefix
            *parts: Additional key parts (use '*' for wildcard)

        Returns:
            Pattern string for Redis SCAN operations

        Example:
            >>> CacheKeys.get_pattern(CacheKeys.AGENT_PREFIX, 'analytics', '*', '7d')
            'agent:analytics:*:7d'
        """
        key_parts = [prefix] + list(parts)
        return ":".join(key_parts)

    @staticmethod
    def get_workspace_pattern(workspace_id: str) -> List[str]:
        """
        Get all cache key patterns related to a workspace.

        Args:
            workspace_id: Workspace identifier

        Returns:
            List of patterns to invalidate
        """
        return [
            f"{CacheKeys.EXECUTIVE_PREFIX}:*:{workspace_id}:*",
            f"{CacheKeys.WORKSPACE_PREFIX}:*:{workspace_id}:*",
            f"{CacheKeys.METRICS_PREFIX}:*:{workspace_id}:*",
            f"{CacheKeys.AGENT_PREFIX}:top:{workspace_id}:*",
        ]

    @staticmethod
    def get_agent_pattern(agent_id: str) -> str:
        """
        Get cache key pattern for all agent-related data.

        Args:
            agent_id: Agent identifier

        Returns:
            Pattern string
        """
        return f"{CacheKeys.AGENT_PREFIX}:*:{agent_id}:*"

    @staticmethod
    def get_user_pattern(user_id: str) -> List[str]:
        """
        Get all cache key patterns related to a user.

        Args:
            user_id: User identifier

        Returns:
            List of patterns to invalidate
        """
        return [
            f"{CacheKeys.USER_PREFIX}:activity:{user_id}:*",
            f"{CacheKeys.USER_PREFIX}:metrics:{user_id}:*",
        ]

    @staticmethod
    def get_ttl_for_timeframe(timeframe: str) -> int:
        """
        Get appropriate TTL based on timeframe.

        Args:
            timeframe: Time period string (e.g., '24h', '7d', '30d')

        Returns:
            TTL in seconds
        """
        ttl_mapping = {
            "1h": CacheKeys.TTL_SHORT,
            "24h": CacheKeys.TTL_MEDIUM,
            "7d": CacheKeys.TTL_LONG,
            "30d": CacheKeys.TTL_HOUR,
            "90d": CacheKeys.TTL_HOUR,
        }
        return ttl_mapping.get(timeframe, CacheKeys.TTL_MEDIUM)
