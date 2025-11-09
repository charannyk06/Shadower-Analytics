"""Executive dashboard aggregation service with caching support."""

import asyncio
from datetime import datetime, timedelta, date, timezone
from typing import Dict, List, Any, Optional
import logging
from sqlalchemy import select, func, and_, distinct
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
from .constants import (
    TIMEFRAME_24H,
    TIMEFRAME_7D,
    TIMEFRAME_30D,
    TIMEFRAME_90D,
    TIMEFRAME_1Y,
    DEFAULT_TIMEFRAME_DAYS,
    PERCENTAGE_MULTIPLIER,
    ZERO_TO_POSITIVE_GROWTH,
)
from ...models.database.tables import (
    ExecutionLog,
    WorkspaceMetric,
    UserMetric,
    AgentMetric,
)
from ...utils.calculations import calculate_percentage_change
from ...utils.datetime import calculate_start_date

logger = logging.getLogger(__name__)


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
    now = datetime.now(timezone.utc)

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
    now = datetime.now(timezone.utc)

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

    end_date = datetime.now(timezone.utc)
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

    def __init__(self, db: Optional[AsyncSession] = None):
        """
        Initialize the service.

        Args:
            db: Database session (optional, can be passed per method call)
        """
        self.db = db

    @cached(
        key_func=lambda self, workspace_id, timeframe, **_: CacheKeys.executive_dashboard(
            workspace_id, timeframe
        ),
        ttl=CacheKeys.TTL_LONG,
    )
    async def get_executive_overview(
        self,
        workspace_id: str,
        timeframe: str = "30d",
        skip_cache: bool = False,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Get executive dashboard overview with caching.

        Args:
            workspace_id: Workspace identifier
            timeframe: Time period (7d, 30d, 90d)
            skip_cache: Bypass cache if True
            db: Database session

        Returns:
            Dictionary with executive metrics
        """
        session = db or self.db
        if not session:
            raise ValueError("Database session required")

        logger.info(
            f"Fetching executive overview for workspace {workspace_id}, timeframe {timeframe}"
        )

        try:
            # Parse timeframe
            days = self._parse_timeframe(timeframe)
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)

            # Calculate metrics in parallel for better performance
            dau = await self._calculate_daily_active_users(
                session, workspace_id, end_date
            )
            wau = await self._calculate_weekly_active_users(
                session, workspace_id, end_date
            )
            mau = await self._calculate_monthly_active_users(
                session, workspace_id, end_date
            )

            total_executions = await self._calculate_total_executions(
                session, workspace_id, start_date, end_date
            )
            success_rate = await self._calculate_success_rate(
                session, workspace_id, start_date, end_date
            )

            # Business metrics (currently returning 0 as revenue tracking not implemented)
            mrr = 0.0
            churn_rate = 0.0
            ltv = 0.0

            return {
                "workspace_id": workspace_id,
                "timeframe": timeframe,
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "mrr": mrr,
                "churn_rate": churn_rate,
                "ltv": ltv,
                "dau": dau,
                "wau": wau,
                "mau": mau,
                "total_executions": total_executions,
                "success_rate": success_rate,
                "cached_at": None,  # Will be populated by caching layer
            }

        except Exception as e:
            logger.error(
                f"Error fetching executive overview for workspace {workspace_id}: {e}",
                exc_info=True,
            )
            # Return safe defaults on error
            return self._get_default_overview(workspace_id, timeframe)

    @cached(
        key_func=lambda self, workspace_id, timeframe, **_: CacheKeys.workspace_metrics(
            workspace_id, "revenue", timeframe
        ),
        ttl=CacheKeys.TTL_LONG,
    )
    async def get_revenue_metrics(
        self,
        workspace_id: str,
        timeframe: str = "30d",
        skip_cache: bool = False,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Get revenue metrics with caching.

        Args:
            workspace_id: Workspace identifier
            timeframe: Time period
            skip_cache: Bypass cache if True
            db: Database session

        Returns:
            Revenue metrics and trends
        """
        logger.info(
            f"Fetching revenue metrics for workspace {workspace_id}, timeframe {timeframe}"
        )

        try:
            # Revenue tracking not yet implemented - return placeholders
            # TODO: Implement when billing/subscription tables are added
            return {
                "workspace_id": workspace_id,
                "timeframe": timeframe,
                "total_revenue": 0,
                "mrr": 0,
                "arr": 0,
                "trend": [],
                "growth_rate": 0.0,
            }
        except Exception as e:
            logger.error(
                f"Error fetching revenue metrics for workspace {workspace_id}: {e}",
                exc_info=True,
            )
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
        self, workspace_id: str, skip_cache: bool = False, db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Get key performance indicators with caching.

        Args:
            workspace_id: Workspace identifier
            skip_cache: Bypass cache if True
            db: Database session

        Returns:
            Key performance indicators
        """
        session = db or self.db
        if not session:
            raise ValueError("Database session required")

        logger.info(f"Fetching KPIs for workspace {workspace_id}")

        try:
            # Calculate KPIs from database
            total_users = await self._calculate_total_users(session, workspace_id)
            active_agents = await self._calculate_active_agents(session, workspace_id)

            # Use last 30 days for execution metrics
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)

            total_executions = await self._calculate_total_executions(
                session, workspace_id, start_date, end_date
            )
            success_rate = await self._calculate_success_rate(
                session, workspace_id, start_date, end_date
            )
            avg_execution_time = await self._calculate_avg_execution_time(
                session, workspace_id, start_date, end_date
            )
            total_credits_used = await self._calculate_total_credits(
                session, workspace_id, start_date, end_date
            )

            return {
                "workspace_id": workspace_id,
                "total_users": total_users,
                "active_agents": active_agents,
                "total_executions": total_executions,
                "success_rate": success_rate,
                "avg_execution_time": avg_execution_time,
                "total_credits_used": total_credits_used,
            }
        except Exception as e:
            logger.error(
                f"Error fetching KPIs for workspace {workspace_id}: {e}",
                exc_info=True,
            )
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
        timeframe_map = {
            "24h": TIMEFRAME_24H,
            "7d": TIMEFRAME_7D,
            "30d": TIMEFRAME_30D,
            "90d": TIMEFRAME_90D,
            "1y": TIMEFRAME_1Y,
        }

        return timeframe_map.get(timeframe, DEFAULT_TIMEFRAME_DAYS)

    async def _calculate_daily_active_users(
        self, db: AsyncSession, workspace_id: str, target_date: datetime
    ) -> int:
        """Calculate Daily Active Users (last 24 hours)."""
        try:
            start_time = target_date - timedelta(days=1)
            stmt = (
                select(func.count(distinct(ExecutionLog.user_id)))
                .where(
                    and_(
                        ExecutionLog.workspace_id == workspace_id,
                        ExecutionLog.started_at >= start_time,
                        ExecutionLog.started_at <= target_date,
                    )
                )
            )
            result = await db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error calculating DAU: {e}", exc_info=True)
            return 0

    async def _calculate_weekly_active_users(
        self, db: AsyncSession, workspace_id: str, target_date: datetime
    ) -> int:
        """Calculate Weekly Active Users (last 7 days)."""
        try:
            start_time = target_date - timedelta(days=7)
            stmt = (
                select(func.count(distinct(ExecutionLog.user_id)))
                .where(
                    and_(
                        ExecutionLog.workspace_id == workspace_id,
                        ExecutionLog.started_at >= start_time,
                        ExecutionLog.started_at <= target_date,
                    )
                )
            )
            result = await db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error calculating WAU: {e}", exc_info=True)
            return 0

    async def _calculate_monthly_active_users(
        self, db: AsyncSession, workspace_id: str, target_date: datetime
    ) -> int:
        """Calculate Monthly Active Users (last 30 days)."""
        try:
            start_time = target_date - timedelta(days=30)
            stmt = (
                select(func.count(distinct(ExecutionLog.user_id)))
                .where(
                    and_(
                        ExecutionLog.workspace_id == workspace_id,
                        ExecutionLog.started_at >= start_time,
                        ExecutionLog.started_at <= target_date,
                    )
                )
            )
            result = await db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error calculating MAU: {e}", exc_info=True)
            return 0

    async def _calculate_total_executions(
        self,
        db: AsyncSession,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> int:
        """Calculate total executions in time range."""
        try:
            stmt = (
                select(func.count(ExecutionLog.id))
                .where(
                    and_(
                        ExecutionLog.workspace_id == workspace_id,
                        ExecutionLog.started_at >= start_date,
                        ExecutionLog.started_at <= end_date,
                    )
                )
            )
            result = await db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error calculating total executions: {e}", exc_info=True)
            return 0

    async def _calculate_success_rate(
        self,
        db: AsyncSession,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> float:
        """Calculate success rate percentage."""
        try:
            # Count total executions
            total_stmt = (
                select(func.count(ExecutionLog.id))
                .where(
                    and_(
                        ExecutionLog.workspace_id == workspace_id,
                        ExecutionLog.started_at >= start_date,
                        ExecutionLog.started_at <= end_date,
                    )
                )
            )
            total_result = await db.execute(total_stmt)
            total = total_result.scalar() or 0

            if total == 0:
                return 0.0

            # Count successful executions
            success_stmt = (
                select(func.count(ExecutionLog.id))
                .where(
                    and_(
                        ExecutionLog.workspace_id == workspace_id,
                        ExecutionLog.started_at >= start_date,
                        ExecutionLog.started_at <= end_date,
                        ExecutionLog.status == "success",
                    )
                )
            )
            success_result = await db.execute(success_stmt)
            successful = success_result.scalar() or 0

            return round((successful / total) * PERCENTAGE_MULTIPLIER, 2)
        except Exception as e:
            logger.error(f"Error calculating success rate: {e}", exc_info=True)
            return 0.0

    async def _calculate_avg_execution_time(
        self,
        db: AsyncSession,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> float:
        """Calculate average execution time in seconds."""
        try:
            stmt = (
                select(func.avg(ExecutionLog.duration))
                .where(
                    and_(
                        ExecutionLog.workspace_id == workspace_id,
                        ExecutionLog.started_at >= start_date,
                        ExecutionLog.started_at <= end_date,
                        ExecutionLog.duration.isnot(None),
                    )
                )
            )
            result = await db.execute(stmt)
            avg_time = result.scalar()
            return round(avg_time, 2) if avg_time else 0.0
        except Exception as e:
            logger.error(f"Error calculating avg execution time: {e}", exc_info=True)
            return 0.0

    async def _calculate_total_credits(
        self,
        db: AsyncSession,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> int:
        """Calculate total credits used."""
        try:
            stmt = (
                select(func.sum(ExecutionLog.credits_used))
                .where(
                    and_(
                        ExecutionLog.workspace_id == workspace_id,
                        ExecutionLog.started_at >= start_date,
                        ExecutionLog.started_at <= end_date,
                    )
                )
            )
            result = await db.execute(stmt)
            total = result.scalar()
            return total if total else 0
        except Exception as e:
            logger.error(f"Error calculating total credits: {e}", exc_info=True)
            return 0

    async def _calculate_total_users(
        self, db: AsyncSession, workspace_id: str
    ) -> int:
        """Calculate total unique users in workspace."""
        try:
            stmt = (
                select(func.count(distinct(ExecutionLog.user_id)))
                .where(ExecutionLog.workspace_id == workspace_id)
            )
            result = await db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error calculating total users: {e}", exc_info=True)
            return 0

    async def _calculate_active_agents(
        self, db: AsyncSession, workspace_id: str
    ) -> int:
        """Calculate active agents (agents with executions in last 30 days)."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
            stmt = (
                select(func.count(distinct(ExecutionLog.agent_id)))
                .where(
                    and_(
                        ExecutionLog.workspace_id == workspace_id,
                        ExecutionLog.started_at >= cutoff_date,
                    )
                )
            )
            result = await db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error calculating active agents: {e}", exc_info=True)
            return 0

    def _get_default_overview(self, workspace_id: str, timeframe: str) -> Dict[str, Any]:
        """Return default overview when errors occur."""
        days = self._parse_timeframe(timeframe)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

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
            "cached_at": None,
        }


# Singleton instance
executive_metrics_service = ExecutiveMetricsService()
