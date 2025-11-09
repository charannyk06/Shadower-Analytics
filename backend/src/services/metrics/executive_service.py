"""Executive dashboard aggregation service with caching support."""

import asyncio
from datetime import datetime, timedelta, date
from typing import Dict, List, Any
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from ...models.schemas.metrics import (
    ExecutiveDashboardResponse,
    Period,
    UserMetrics,
    ExecutionMetrics,
    BusinessMetrics,
    AgentMetrics,
    TopAgent,
    TopUser,
    Alert,
    TrendData,
    TimeSeriesData,
)
from ..cache import cached, CacheKeys

logger = logging.getLogger(__name__)


def calculate_start_date(timeframe: str) -> datetime:
    """Calculate start date based on timeframe."""
    now = datetime.utcnow()

    if timeframe == "24h":
        return now - timedelta(hours=24)
    elif timeframe == "7d":
        return now - timedelta(days=7)
    elif timeframe == "30d":
        return now - timedelta(days=30)
    elif timeframe == "90d":
        return now - timedelta(days=90)
    else:  # 'all'
        return now - timedelta(days=365 * 10)  # 10 years back


def calculate_percentage_change(current: float, previous: float) -> float:
    """Calculate percentage change between two values.

    Args:
        current: The current value.
        previous: The previous value to compare against.

    Returns:
        The percentage change from previous to current.
        - If previous is 0 and current > 0, returns 100.0.
        - If both current and previous are 0, returns 0.0.
        - Otherwise, returns ((current - previous) / previous) * 100.
    """
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return ((current - previous) / previous) * 100


async def get_user_metrics(
    db: AsyncSession,
    workspace_id: str,
    start_date: datetime,
    end_date: datetime
) -> UserMetrics:
    """Get user engagement metrics with trend data."""

    # For now, return mock data with realistic values
    # In production, these would be actual database queries

    # Current period metrics (mock data)
    dau = 1247
    wau = 3892
    mau = 12450
    new_users = 342
    churned_users = 28

    # Previous period metrics (mock data for comparison)
    prev_dau = 1180
    prev_wau = 3650
    prev_mau = 11800

    # Calculate changes
    dau_change = calculate_percentage_change(dau, prev_dau)
    wau_change = calculate_percentage_change(wau, prev_wau)
    mau_change = calculate_percentage_change(mau, prev_mau)
    active_rate = (wau / mau * 100) if mau > 0 else 0.0

    return UserMetrics(
        dau=dau,
        dau_change=dau_change,
        wau=wau,
        wau_change=wau_change,
        mau=mau,
        mau_change=mau_change,
        new_users=new_users,
        churned_users=churned_users,
        active_rate=active_rate,
    )


async def get_execution_metrics(
    db: AsyncSession,
    workspace_id: str,
    start_date: datetime,
    end_date: datetime,
) -> ExecutionMetrics:
    """Get execution performance metrics with trends."""

    # Mock data - replace with actual queries
    total_runs = 45678
    successful_runs = 43201
    failed_runs = 2477
    success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0.0

    # Previous period comparison
    prev_total_runs = 42300
    prev_success_rate = 93.5

    total_runs_change = calculate_percentage_change(total_runs, prev_total_runs)
    success_rate_change = calculate_percentage_change(success_rate, prev_success_rate)

    # Credits
    total_credits = 2_345_678
    prev_credits = 2_100_000
    credits_change = calculate_percentage_change(total_credits, prev_credits)

    return ExecutionMetrics(
        total_runs=total_runs,
        total_runs_change=total_runs_change,
        successful_runs=successful_runs,
        failed_runs=failed_runs,
        success_rate=success_rate,
        success_rate_change=success_rate_change,
        avg_runtime=2.34,  # seconds
        p95_runtime=8.92,  # seconds
        total_credits_used=total_credits,
        credits_change=credits_change,
    )


async def get_business_metrics(
    db: AsyncSession,
    workspace_id: str,
    start_date: datetime,
    end_date: datetime,
) -> BusinessMetrics:
    """Get business and financial metrics."""

    # Mock data - replace with actual queries
    mrr = 124500.0
    prev_mrr = 118200.0
    mrr_change = calculate_percentage_change(mrr, prev_mrr)

    arr = mrr * 12
    ltv = 15000.0
    cac = 1200.0
    ltv_cac_ratio = ltv / cac if cac > 0 else 0.0

    return BusinessMetrics(
        mrr=mrr,
        mrr_change=mrr_change,
        arr=arr,
        ltv=ltv,
        cac=cac,
        ltv_cac_ratio=ltv_cac_ratio,
        active_workspaces=847,
        paid_workspaces=623,
        trial_workspaces=224,
        churn_rate=2.3,
    )


async def get_agent_metrics(
    db: AsyncSession,
    workspace_id: str,
    start_date: datetime,
    end_date: datetime,
) -> AgentMetrics:
    """Get agent performance metrics and top agents."""

    # Mock data for top agents
    top_agents = [
        TopAgent(
            id="agent-001",
            name="Data Analyzer Pro",
            runs=5678,
            success_rate=98.5,
            avg_runtime=1.87,
        ),
        TopAgent(
            id="agent-002",
            name="Report Generator",
            runs=4532,
            success_rate=99.2,
            avg_runtime=2.34,
        ),
        TopAgent(
            id="agent-003",
            name="Email Campaign Manager",
            runs=3891,
            success_rate=97.8,
            avg_runtime=3.12,
        ),
        TopAgent(
            id="agent-004",
            name="API Integration Bot",
            runs=3456,
            success_rate=96.4,
            avg_runtime=4.56,
        ),
        TopAgent(
            id="agent-005",
            name="Social Media Monitor",
            runs=2987,
            success_rate=98.1,
            avg_runtime=1.92,
        ),
    ]

    return AgentMetrics(
        total_agents=234,
        active_agents=187,
        top_agents=top_agents,
    )


async def get_trend_data(
    db: AsyncSession,
    workspace_id: str,
    start_date: datetime,
    end_date: datetime,
    timeframe: str,
) -> TrendData:
    """Get time-series trend data for charts."""

    # Generate mock time series data
    # In production, this would query actual data

    # Determine granularity based on timeframe
    if timeframe == "24h":
        intervals = 24
        delta = timedelta(hours=1)
    elif timeframe == "7d":
        intervals = 7
        delta = timedelta(days=1)
    elif timeframe == "30d":
        intervals = 30
        delta = timedelta(days=1)
    elif timeframe == "90d":
        intervals = 90
        delta = timedelta(days=1)
    else:  # all
        intervals = 52
        delta = timedelta(weeks=1)

    # Generate execution trends
    execution_trend = []
    users_trend = []
    revenue_trend = []
    errors_trend = []

    import random
    random.seed(42)  # For consistent mock data

    current_time = start_date
    for i in range(intervals):
        timestamp = (current_time + (delta * i)).isoformat()

        # Execution data with some variance
        base_executions = 1500 + (i * 10)
        total = base_executions + random.randint(-100, 200)
        successful = int(total * (0.94 + random.random() * 0.05))
        failed = total - successful

        execution_trend.append(
            TimeSeriesData(
                timestamp=timestamp,
                value=total,
                total=total,
                successful=successful,
                failed=failed,
            )
        )

        # User activity trend
        users_trend.append(
            TimeSeriesData(
                timestamp=timestamp,
                value=800 + i * 5 + random.randint(-50, 100),
            )
        )

        # Revenue trend
        revenue_trend.append(
            TimeSeriesData(
                timestamp=timestamp,
                value=50000 + i * 500 + random.randint(-2000, 3000),
            )
        )

        # Error rate trend
        errors_trend.append(
            TimeSeriesData(
                timestamp=timestamp,
                value=2.5 + random.random() * 2,
            )
        )

    return TrendData(
        execution=execution_trend,
        users=users_trend,
        revenue=revenue_trend,
        errors=errors_trend,
    )


async def get_active_alerts(
    db: AsyncSession,
    workspace_id: str,
) -> List[Alert]:
    """Get active system alerts."""

    # Mock alerts - replace with actual query
    now = datetime.utcnow()

    return [
        Alert(
            id="alert-001",
            type="performance",
            message="API response time increased by 15% in the last hour",
            severity="medium",
            triggered_at=(now - timedelta(minutes=25)).isoformat(),
        ),
        Alert(
            id="alert-002",
            type="quota",
            message="Workspace approaching 80% of monthly credit limit",
            severity="high",
            triggered_at=(now - timedelta(hours=2)).isoformat(),
        ),
        Alert(
            id="alert-003",
            type="error_rate",
            message="Agent 'Data Processor' error rate above threshold (8.5%)",
            severity="critical",
            triggered_at=(now - timedelta(minutes=45)).isoformat(),
        ),
    ]


async def get_top_users(
    db: AsyncSession,
    workspace_id: str,
    start_date: datetime,
    end_date: datetime,
    limit: int = 10,
) -> List[TopUser]:
    """Get top users by activity."""

    # Mock data - replace with actual query
    now = datetime.utcnow()

    return [
        TopUser(
            id="user-001",
            name="Alice Johnson",
            email="alice.johnson@company.com",
            total_runs=1234,
            credits_used=45678,
            last_active=(now - timedelta(hours=2)).isoformat(),
        ),
        TopUser(
            id="user-002",
            name="Bob Smith",
            email="bob.smith@company.com",
            total_runs=987,
            credits_used=38901,
            last_active=(now - timedelta(minutes=30)).isoformat(),
        ),
        TopUser(
            id="user-003",
            name="Carol White",
            email="carol.white@company.com",
            total_runs=856,
            credits_used=32145,
            last_active=(now - timedelta(hours=5)).isoformat(),
        ),
        TopUser(
            id="user-004",
            name="David Brown",
            email="david.brown@company.com",
            total_runs=745,
            credits_used=28934,
            last_active=(now - timedelta(hours=1)).isoformat(),
        ),
        TopUser(
            id="user-005",
            name="Eve Davis",
            email="eve.davis@company.com",
            total_runs=678,
            credits_used=25123,
            last_active=(now - timedelta(hours=8)).isoformat(),
        ),
    ]


async def get_executive_dashboard_data(
    db: AsyncSession,
    workspace_id: str,
    timeframe: str = "7d",
) -> ExecutiveDashboardResponse:
    """Get comprehensive executive dashboard data.

    Aggregates all metrics, trends, and alerts in parallel for performance.
    """

    end_date = datetime.utcnow()
    start_date = calculate_start_date(timeframe)

    # Fetch all data in parallel for better performance
    (
        user_metrics,
        execution_metrics,
        business_metrics,
        agent_metrics,
        trends,
        alerts,
        top_users,
    ) = await asyncio.gather(
        get_user_metrics(db, workspace_id, start_date, end_date),
        get_execution_metrics(db, workspace_id, start_date, end_date),
        get_business_metrics(db, workspace_id, start_date, end_date),
        get_agent_metrics(db, workspace_id, start_date, end_date),
        get_trend_data(db, workspace_id, start_date, end_date, timeframe),
        get_active_alerts(db, workspace_id),
        get_top_users(db, workspace_id, start_date, end_date),
        return_exceptions=True,
    )

    # Handle any errors in parallel execution
    def handle_error(result, default):
        if isinstance(result, Exception):
            logger.error(f"Error fetching metric data: {result}", exc_info=True)
            return default
        return result

    return ExecutiveDashboardResponse(
        timeframe=timeframe,
        period=Period(
            start=start_date.isoformat(),
            end=end_date.isoformat(),
        ),
        user_metrics=handle_error(user_metrics, UserMetrics(
            dau=0, dau_change=0, wau=0, wau_change=0, mau=0, mau_change=0,
            new_users=0, churned_users=0, active_rate=0
        )),
        execution_metrics=handle_error(execution_metrics, ExecutionMetrics(
            total_runs=0, total_runs_change=0, successful_runs=0, failed_runs=0,
            success_rate=0, success_rate_change=0, avg_runtime=0, p95_runtime=0,
            total_credits_used=0, credits_change=0
        )),
        business_metrics=handle_error(business_metrics, BusinessMetrics(
            mrr=0, mrr_change=0, arr=0, ltv=0, cac=0, ltv_cac_ratio=0,
            active_workspaces=0, paid_workspaces=0, trial_workspaces=0, churn_rate=0
        )),
        agent_metrics=handle_error(agent_metrics, AgentMetrics(
            total_agents=0, active_agents=0, top_agents=[]
        )),
        trends=handle_error(trends, TrendData(
            execution=[], users=[], revenue=[], errors=[]
        )),
        active_alerts=handle_error(alerts, []),
        top_users=handle_error(top_users, []),
    )


class ExecutiveMetricsService:
    """Service for executive dashboard metrics with automatic caching."""

    @cached(
        key_func=lambda self, workspace_id, timeframe, **_: CacheKeys.executive_dashboard(
            workspace_id, timeframe
        ),
        ttl=CacheKeys.TTL_LONG,
    )
    async def get_executive_overview(
        self, workspace_id: str, timeframe: str = "30d", skip_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Get executive dashboard overview with caching.

        Args:
            workspace_id: Workspace identifier
            timeframe: Time period (7d, 30d, 90d)
            skip_cache: Bypass cache if True

        Returns:
            Dictionary with executive metrics
        """
        logger.info(
            f"Fetching executive overview for workspace {workspace_id}, timeframe {timeframe}"
        )

        # Parse timeframe
        days = self._parse_timeframe(timeframe)
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # This would call actual metrics services
        # For now, returning placeholder data
        return {
            "workspace_id": workspace_id,
            "timeframe": timeframe,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "mrr": 0,
            "churn_rate": 0.0,
            "ltv": 0,
            "dau": 0,
            "wau": 0,
            "mau": 0,
            "total_executions": 0,
            "success_rate": 0.0,
            "cached_at": None,  # Will be populated by caching layer
        }

    @cached(
        key_func=lambda self, workspace_id, timeframe, **_: CacheKeys.workspace_metrics(
            workspace_id, "revenue", timeframe
        ),
        ttl=CacheKeys.TTL_LONG,
    )
    async def get_revenue_metrics(
        self, workspace_id: str, timeframe: str = "30d", skip_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Get revenue metrics with caching.

        Args:
            workspace_id: Workspace identifier
            timeframe: Time period
            skip_cache: Bypass cache if True

        Returns:
            Revenue metrics and trends
        """
        logger.info(
            f"Fetching revenue metrics for workspace {workspace_id}, timeframe {timeframe}"
        )

        # Placeholder implementation
        return {
            "workspace_id": workspace_id,
            "timeframe": timeframe,
            "total_revenue": 0,
            "mrr": 0,
            "arr": 0,
            "trend": [],
            "growth_rate": 0.0,
        }

    @cached(
        key_func=lambda self, workspace_id, **_: CacheKeys.workspace_metrics(
            workspace_id, "kpis", "current"
        ),
        ttl=CacheKeys.TTL_MEDIUM,
    )
    async def get_key_performance_indicators(
        self, workspace_id: str, skip_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Get key performance indicators with caching.

        Args:
            workspace_id: Workspace identifier
            skip_cache: Bypass cache if True

        Returns:
            Key performance indicators
        """
        logger.info(f"Fetching KPIs for workspace {workspace_id}")

        # Placeholder implementation
        return {
            "workspace_id": workspace_id,
            "total_users": 0,
            "active_agents": 0,
            "total_executions": 0,
            "success_rate": 0.0,
            "avg_execution_time": 0.0,
            "total_credits_used": 0,
        }

    def _parse_timeframe(self, timeframe: str) -> int:
        """
        Parse timeframe string to number of days.

        Args:
            timeframe: Timeframe string (e.g., '7d', '30d', '90d')

        Returns:
            Number of days
        """
        timeframe_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365, "24h": 1}

        return timeframe_map.get(timeframe, 30)


# Singleton instance
executive_metrics_service = ExecutiveMetricsService()
