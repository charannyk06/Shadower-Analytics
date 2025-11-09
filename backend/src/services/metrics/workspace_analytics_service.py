"""Workspace analytics service with comprehensive metrics calculation."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ...models.schemas.workspaces import (
    WorkspaceAnalytics,
    WorkspaceOverview,
    HealthFactors,
    MemberAnalytics,
    MembersByRole,
    MemberActivityItem,
    TopContributor,
    InactiveMember,
    AgentUsage,
    AgentPerformance,
    AgentEfficiency,
    ResourceUtilization,
    Credits,
    DailyConsumption,
    Storage,
    APIUsage,
    Billing,
    UsageLimit,
    BillingHistory,
    BillingRecommendation,
    WorkspaceComparison,
    WorkspaceRanking,
    Benchmarks,
    SimilarWorkspace,
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


def determine_workspace_status(
    last_activity_at: Optional[datetime],
    active_members: int,
    health_score: int
) -> str:
    """Determine workspace status based on activity and health."""
    if not last_activity_at:
        return "churned"

    days_since_activity = (datetime.utcnow() - last_activity_at).days

    if days_since_activity > 30:
        return "churned"
    elif days_since_activity > 14 or health_score < 40:
        return "at_risk"
    elif active_members == 0 or days_since_activity > 7:
        return "idle"
    else:
        return "active"


def determine_activity_trend(
    current_activity: int,
    previous_activity: int
) -> str:
    """Determine activity trend based on current vs previous period."""
    if previous_activity == 0:
        return "increasing" if current_activity > 0 else "stable"

    change_pct = ((current_activity - previous_activity) / previous_activity) * 100

    if change_pct > 10:
        return "increasing"
    elif change_pct < -10:
        return "decreasing"
    else:
        return "stable"


async def get_workspace_overview(
    db: AsyncSession,
    workspace_id: str,
    start_date: datetime,
    end_date: datetime
) -> WorkspaceOverview:
    """Get workspace overview metrics."""

    # Get workspace basic info and member counts
    workspace_query = text("""
        SELECT
            w.id,
            w.name,
            w.created_at,
            COUNT(DISTINCT wm.user_id) as total_members,
            COUNT(DISTINCT wm.user_id) FILTER (
                WHERE wm.last_active_at > NOW() - INTERVAL '7 days'
            ) as active_members,
            COUNT(DISTINCT wi.id) FILTER (
                WHERE wi.status = 'pending'
            ) as pending_invites,
            EXTRACT(DAY FROM NOW() - w.created_at) as days_active
        FROM public.workspaces w
        LEFT JOIN public.workspace_members wm ON w.id = wm.workspace_id
        LEFT JOIN public.workspace_invites wi ON w.id = wi.workspace_id
        WHERE w.id = :workspace_id
        GROUP BY w.id, w.name, w.created_at
    """)

    result = await db.execute(workspace_query, {"workspace_id": workspace_id})
    workspace_data = result.fetchone()

    if not workspace_data:
        raise ValueError(f"Workspace {workspace_id} not found")

    # Get activity metrics for current period
    activity_query = text("""
        SELECT
            COUNT(*) as total_activity,
            MAX(created_at) as last_activity_at
        FROM analytics.user_activity
        WHERE workspace_id = :workspace_id
            AND created_at BETWEEN :start_date AND :end_date
    """)

    result = await db.execute(activity_query, {
        "workspace_id": workspace_id,
        "start_date": start_date,
        "end_date": end_date
    })
    activity_data = result.fetchone()

    # Get previous period activity for trend calculation
    prev_start = start_date - (end_date - start_date)
    prev_activity_query = text("""
        SELECT COUNT(*) as prev_activity
        FROM analytics.user_activity
        WHERE workspace_id = :workspace_id
            AND created_at BETWEEN :prev_start AND :start_date
    """)

    result = await db.execute(prev_activity_query, {
        "workspace_id": workspace_id,
        "prev_start": prev_start,
        "start_date": start_date
    })
    prev_activity_data = result.fetchone()

    # Calculate health score
    health_factors = await calculate_health_score(db, workspace_id, start_date, end_date)

    total_members = workspace_data.total_members or 0
    active_members = workspace_data.active_members or 0
    total_activity = activity_data.total_activity or 0
    prev_activity = prev_activity_data.prev_activity if prev_activity_data else 0

    # Determine status and trend
    status = determine_workspace_status(
        activity_data.last_activity_at,
        active_members,
        health_factors.activity
    )

    activity_trend = determine_activity_trend(total_activity, prev_activity)

    # Calculate member growth (comparing to 30 days ago)
    member_growth_query = text("""
        SELECT COUNT(DISTINCT user_id) as members_30d_ago
        FROM public.workspace_members
        WHERE workspace_id = :workspace_id
            AND joined_at < NOW() - INTERVAL '30 days'
    """)

    result = await db.execute(member_growth_query, {"workspace_id": workspace_id})
    growth_data = result.fetchone()
    members_30d_ago = growth_data.members_30d_ago if growth_data else total_members

    member_growth = 0.0
    if members_30d_ago > 0:
        member_growth = ((total_members - members_30d_ago) / members_30d_ago) * 100

    return WorkspaceOverview(
        total_members=total_members,
        active_members=active_members,
        pending_invites=workspace_data.pending_invites or 0,
        member_growth=round(member_growth, 2),
        total_activity=total_activity,
        avg_activity_per_member=round(total_activity / total_members, 2) if total_members > 0 else 0,
        last_activity_at=activity_data.last_activity_at.isoformat() if activity_data.last_activity_at else None,
        activity_trend=activity_trend,
        health_score=health_factors.activity,
        health_factors=health_factors,
        status=status,
        days_active=int(workspace_data.days_active or 0),
        created_at=workspace_data.created_at.isoformat()
    )


async def calculate_health_score(
    db: AsyncSession,
    workspace_id: str,
    start_date: datetime,
    end_date: datetime
) -> HealthFactors:
    """Calculate workspace health score factors."""

    # Activity Score (based on active member percentage)
    activity_query = text("""
        SELECT
            COUNT(DISTINCT user_id) as total_members,
            COUNT(DISTINCT user_id) FILTER (
                WHERE last_active_at > NOW() - INTERVAL '7 days'
            ) as active_members
        FROM public.workspace_members
        WHERE workspace_id = :workspace_id
    """)

    result = await db.execute(activity_query, {"workspace_id": workspace_id})
    activity_data = result.fetchone()

    total_members = activity_data.total_members or 0
    active_members = activity_data.active_members or 0

    activity_score = min(100, int((active_members / total_members * 100)) if total_members > 0 else 0)

    # Engagement Score (based on average activity per user)
    engagement_query = text("""
        SELECT COUNT(*) as total_activity
        FROM analytics.user_activity
        WHERE workspace_id = :workspace_id
            AND created_at >= NOW() - INTERVAL '7 days'
    """)

    result = await db.execute(engagement_query, {"workspace_id": workspace_id})
    engagement_data = result.fetchone()

    total_activity = engagement_data.total_activity or 0
    avg_activity_per_user = (total_activity / total_members) if total_members > 0 else 0
    engagement_score = min(100, int(avg_activity_per_user * 10))  # Normalize to 0-100

    # Efficiency Score (based on agent success rate)
    efficiency_query = text("""
        SELECT
            COUNT(*) as total_runs,
            COUNT(*) FILTER (WHERE status = 'success') as successful_runs
        FROM public.agent_runs
        WHERE workspace_id = :workspace_id
            AND started_at BETWEEN :start_date AND :end_date
    """)

    result = await db.execute(efficiency_query, {
        "workspace_id": workspace_id,
        "start_date": start_date,
        "end_date": end_date
    })
    efficiency_data = result.fetchone()

    total_runs = efficiency_data.total_runs or 0
    successful_runs = efficiency_data.successful_runs or 0
    efficiency_score = int((successful_runs / total_runs * 100)) if total_runs > 0 else 100

    # Reliability Score (inverse of error rate)
    reliability_score = efficiency_score  # For now, use same as efficiency

    return HealthFactors(
        activity=activity_score,
        engagement=engagement_score,
        efficiency=efficiency_score,
        reliability=reliability_score
    )


async def get_member_analytics(
    db: AsyncSession,
    workspace_id: str,
    start_date: datetime,
    end_date: datetime
) -> MemberAnalytics:
    """Get detailed member analytics."""

    # Get members by role
    role_query = text("""
        SELECT
            role,
            COUNT(*) as count
        FROM public.workspace_members
        WHERE workspace_id = :workspace_id
        GROUP BY role
    """)

    result = await db.execute(role_query, {"workspace_id": workspace_id})
    role_data = result.fetchall()

    members_by_role = MembersByRole()
    for row in role_data:
        setattr(members_by_role, row.role.lower(), row.count)

    # Get activity distribution
    activity_query = text("""
        SELECT
            wm.user_id,
            u.name as user_name,
            wm.role,
            COUNT(ua.id) as activity_count,
            MAX(ua.created_at) as last_active_at,
            CASE
                WHEN COUNT(ua.id) > 50 THEN 'high'
                WHEN COUNT(ua.id) > 20 THEN 'medium'
                WHEN COUNT(ua.id) > 0 THEN 'low'
                ELSE 'inactive'
            END as engagement_level
        FROM public.workspace_members wm
        LEFT JOIN public.users u ON wm.user_id = u.id
        LEFT JOIN analytics.user_activity ua ON wm.user_id = ua.user_id
            AND ua.workspace_id = :workspace_id
            AND ua.created_at BETWEEN :start_date AND :end_date
        WHERE wm.workspace_id = :workspace_id
        GROUP BY wm.user_id, u.name, wm.role
        ORDER BY activity_count DESC
        LIMIT 100
    """)

    result = await db.execute(activity_query, {
        "workspace_id": workspace_id,
        "start_date": start_date,
        "end_date": end_date
    })
    activity_data = result.fetchall()

    activity_distribution = [
        MemberActivityItem(
            user_id=str(row.user_id),
            user_name=row.user_name or "Unknown",
            role=row.role,
            activity_count=row.activity_count,
            last_active_at=row.last_active_at.isoformat() if row.last_active_at else None,
            engagement_level=row.engagement_level
        )
        for row in activity_data
    ]

    # Get top contributors
    contributor_query = text("""
        SELECT
            wm.user_id,
            u.name as user_name,
            COUNT(ar.id) as agent_runs,
            ROUND(AVG(CASE WHEN ar.status = 'success' THEN 100.0 ELSE 0.0 END), 2) as success_rate,
            SUM(ar.credits_consumed) as credits_used
        FROM public.workspace_members wm
        LEFT JOIN public.users u ON wm.user_id = u.id
        LEFT JOIN public.agent_runs ar ON wm.user_id = ar.user_id
            AND ar.workspace_id = :workspace_id
            AND ar.started_at BETWEEN :start_date AND :end_date
        WHERE wm.workspace_id = :workspace_id
        GROUP BY wm.user_id, u.name
        HAVING COUNT(ar.id) > 0
        ORDER BY agent_runs DESC
        LIMIT 10
    """)

    result = await db.execute(contributor_query, {
        "workspace_id": workspace_id,
        "start_date": start_date,
        "end_date": end_date
    })
    contributor_data = result.fetchall()

    top_contributors = [
        TopContributor(
            user_id=str(row.user_id),
            user_name=row.user_name or "Unknown",
            contribution={
                "agentRuns": row.agent_runs,
                "successRate": float(row.success_rate or 0),
                "creditsUsed": float(row.credits_used or 0)
            }
        )
        for row in contributor_data
    ]

    # Get inactive members (no activity in last 30 days)
    inactive_query = text("""
        SELECT
            wm.user_id,
            u.name as user_name,
            wm.last_active_at,
            EXTRACT(DAY FROM NOW() - wm.last_active_at) as days_since_active
        FROM public.workspace_members wm
        LEFT JOIN public.users u ON wm.user_id = u.id
        WHERE wm.workspace_id = :workspace_id
            AND (wm.last_active_at IS NULL OR wm.last_active_at < NOW() - INTERVAL '30 days')
        ORDER BY days_since_active DESC
        LIMIT 20
    """)

    result = await db.execute(inactive_query, {"workspace_id": workspace_id})
    inactive_data = result.fetchall()

    inactive_members = [
        InactiveMember(
            user_id=str(row.user_id),
            user_name=row.user_name or "Unknown",
            last_active_at=row.last_active_at.isoformat() if row.last_active_at else "Never",
            days_since_active=int(row.days_since_active or 9999)
        )
        for row in inactive_data
    ]

    return MemberAnalytics(
        members_by_role=members_by_role,
        activity_distribution=activity_distribution,
        top_contributors=top_contributors,
        inactive_members=inactive_members
    )


async def get_agent_usage(
    db: AsyncSession,
    workspace_id: str,
    start_date: datetime,
    end_date: datetime
) -> AgentUsage:
    """Get agent usage analytics."""

    # Get agent counts
    agent_count_query = text("""
        SELECT
            COUNT(DISTINCT id) as total_agents,
            COUNT(DISTINCT id) FILTER (
                WHERE last_run_at > NOW() - INTERVAL '7 days'
            ) as active_agents
        FROM public.agents
        WHERE workspace_id = :workspace_id
    """)

    result = await db.execute(agent_count_query, {"workspace_id": workspace_id})
    count_data = result.fetchone()

    # Get agent performance
    agent_query = text("""
        SELECT
            a.id as agent_id,
            a.name as agent_name,
            COUNT(ar.id) as runs,
            ROUND(AVG(CASE WHEN ar.status = 'success' THEN 100.0 ELSE 0.0 END), 2) as success_rate,
            ROUND(AVG(EXTRACT(EPOCH FROM (ar.ended_at - ar.started_at))), 2) as avg_runtime,
            SUM(ar.credits_consumed) as credits_consumed,
            MAX(ar.started_at) as last_run_at
        FROM public.agents a
        LEFT JOIN public.agent_runs ar ON a.id = ar.agent_id
            AND ar.started_at BETWEEN :start_date AND :end_date
        WHERE a.workspace_id = :workspace_id
        GROUP BY a.id, a.name
        ORDER BY runs DESC
        LIMIT 50
    """)

    result = await db.execute(agent_query, {
        "workspace_id": workspace_id,
        "start_date": start_date,
        "end_date": end_date
    })
    agent_data = result.fetchall()

    agents = [
        AgentPerformance(
            agent_id=str(row.agent_id),
            agent_name=row.agent_name,
            runs=row.runs or 0,
            success_rate=float(row.success_rate or 0),
            avg_runtime=float(row.avg_runtime or 0),
            credits_consumed=float(row.credits_consumed or 0),
            last_run_at=row.last_run_at.isoformat() if row.last_run_at else None
        )
        for row in agent_data
    ]

    # Calculate efficiency metrics
    most_efficient = None
    least_efficient = None
    if agents:
        # Sort by success rate
        efficient_agents = sorted(agents, key=lambda x: x.success_rate, reverse=True)
        most_efficient = efficient_agents[0].agent_name if efficient_agents else None
        least_efficient = efficient_agents[-1].agent_name if len(efficient_agents) > 1 else None

    avg_success = sum(a.success_rate for a in agents) / len(agents) if agents else 0
    avg_runtime = sum(a.avg_runtime for a in agents) / len(agents) if agents else 0

    agent_efficiency = AgentEfficiency(
        most_efficient=most_efficient,
        least_efficient=least_efficient,
        avg_success_rate=round(avg_success, 2),
        avg_runtime=round(avg_runtime, 2)
    )

    return AgentUsage(
        total_agents=count_data.total_agents or 0,
        active_agents=count_data.active_agents or 0,
        agents=agents,
        usage_by_agent={},  # Can be populated with time-series data if needed
        agent_efficiency=agent_efficiency
    )


async def get_resource_utilization(
    db: AsyncSession,
    workspace_id: str,
    start_date: datetime,
    end_date: datetime
) -> ResourceUtilization:
    """Get resource utilization metrics."""

    # Get credit usage
    credit_query = text("""
        SELECT
            wc.allocated_credits,
            wc.consumed_credits,
            wc.allocated_credits - wc.consumed_credits as remaining_credits
        FROM public.workspace_credits wc
        WHERE wc.workspace_id = :workspace_id
    """)

    result = await db.execute(credit_query, {"workspace_id": workspace_id})
    credit_data = result.fetchone()

    allocated = float(credit_data.allocated_credits or 0) if credit_data else 0
    consumed = float(credit_data.consumed_credits or 0) if credit_data else 0
    remaining = float(credit_data.remaining_credits or 0) if credit_data else 0

    utilization_rate = (consumed / allocated * 100) if allocated > 0 else 0

    # Get daily consumption for last 30 days
    daily_query = text("""
        SELECT
            DATE(ar.started_at) as date,
            SUM(ar.credits_consumed) as credits
        FROM public.agent_runs ar
        WHERE ar.workspace_id = :workspace_id
            AND ar.started_at >= NOW() - INTERVAL '30 days'
        GROUP BY DATE(ar.started_at)
        ORDER BY date DESC
    """)

    result = await db.execute(daily_query, {"workspace_id": workspace_id})
    daily_data = result.fetchall()

    daily_consumption = [
        DailyConsumption(
            date=row.date.isoformat(),
            credits=float(row.credits or 0)
        )
        for row in daily_data
    ]

    # Calculate projected exhaustion
    projected_exhaustion = None
    if len(daily_consumption) > 0:
        avg_daily = sum(d.credits for d in daily_consumption) / len(daily_consumption)
        if avg_daily > 0 and remaining > 0:
            days_remaining = remaining / avg_daily
            exhaustion_date = datetime.utcnow() + timedelta(days=days_remaining)
            projected_exhaustion = exhaustion_date.isoformat()

    credits = Credits(
        allocated=allocated,
        consumed=consumed,
        remaining=remaining,
        utilization_rate=round(utilization_rate, 2),
        projected_exhaustion=projected_exhaustion,
        consumption_by_model={},  # Can be populated from agent_runs model column
        daily_consumption=daily_consumption
    )

    # Storage metrics (placeholder - would need actual file tracking)
    storage = Storage(
        used=0,
        limit=10737418240,  # 10GB
        utilization_rate=0,
        breakdown={}
    )

    # API usage (placeholder - would need actual API tracking)
    api_usage = APIUsage(
        total_calls=0,
        rate_limit=10000,
        utilization_rate=0,
        by_endpoint={}
    )

    return ResourceUtilization(
        credits=credits,
        storage=storage,
        api_usage=api_usage
    )


async def get_billing_info(
    db: AsyncSession,
    workspace_id: str,
    start_date: datetime,
    end_date: datetime
) -> Billing:
    """Get billing and subscription information."""

    # Get workspace subscription info
    sub_query = text("""
        SELECT
            w.plan,
            w.billing_status,
            ws.current_month_cost,
            ws.projected_month_cost,
            ws.last_month_cost
        FROM public.workspaces w
        LEFT JOIN public.workspace_subscriptions ws ON w.id = ws.workspace_id
        WHERE w.id = :workspace_id
    """)

    result = await db.execute(sub_query, {"workspace_id": workspace_id})
    sub_data = result.fetchone()

    plan = sub_data.plan if sub_data else "free"
    status = sub_data.billing_status if sub_data else "active"

    # Get usage limits
    limits = {
        "members": UsageLimit(used=0, limit=10),
        "agents": UsageLimit(used=0, limit=50),
        "credits": UsageLimit(used=0, limit=1000),
        "storage": UsageLimit(used=0, limit=10737418240)
    }

    # Billing history (placeholder)
    history = []

    # Recommendations (placeholder)
    recommendations = []

    return Billing(
        plan=plan,
        status=status,
        current_month_cost=float(sub_data.current_month_cost or 0) if sub_data else 0,
        projected_month_cost=float(sub_data.projected_month_cost or 0) if sub_data else 0,
        last_month_cost=float(sub_data.last_month_cost or 0) if sub_data else 0,
        limits=limits,
        history=history,
        recommendations=recommendations
    )


async def get_workspace_comparison(
    db: AsyncSession,
    workspace_id: str
) -> WorkspaceComparison:
    """Get workspace comparison data (admin only)."""

    # Query the materialized view for comparison data
    comparison_query = text("""
        SELECT
            health_rank as overall,
            total_workspaces,
            health_percentile as percentile,
            activity_vs_avg_pct,
            efficiency_vs_avg_pct,
            cost_vs_avg_pct
        FROM analytics.mv_workspace_comparison
        WHERE workspace_id = :workspace_id
    """)

    result = await db.execute(comparison_query, {"workspace_id": workspace_id})
    comp_data = result.fetchone()

    if not comp_data:
        # Return default values if no comparison data
        return WorkspaceComparison(
            ranking=WorkspaceRanking(
                overall=1,
                total_workspaces=1,
                percentile=100.0
            ),
            benchmarks=Benchmarks(
                activity_vs_avg=0.0,
                efficiency_vs_avg=0.0,
                cost_vs_avg=0.0
            ),
            similar_workspaces=[]
        )

    ranking = WorkspaceRanking(
        overall=comp_data.overall,
        total_workspaces=comp_data.total_workspaces,
        percentile=float(comp_data.percentile)
    )

    benchmarks = Benchmarks(
        activity_vs_avg=float(comp_data.activity_vs_avg_pct or 0),
        efficiency_vs_avg=float(comp_data.efficiency_vs_avg_pct or 0),
        cost_vs_avg=float(comp_data.cost_vs_avg_pct or 0)
    )

    # Find similar workspaces (placeholder - would need similarity algorithm)
    similar_workspaces = []

    return WorkspaceComparison(
        ranking=ranking,
        benchmarks=benchmarks,
        similar_workspaces=similar_workspaces
    )


@cached(
    key_func=lambda workspace_id, timeframe, include_comparison:
        f"{CacheKeys.WORKSPACE_PREFIX}:analytics:{workspace_id}:{timeframe}:{include_comparison}",
    ttl=CacheKeys.TTL_LONG
)
async def get_workspace_analytics(
    db: AsyncSession,
    workspace_id: str,
    timeframe: str = "30d",
    include_comparison: bool = False
) -> WorkspaceAnalytics:
    """Get comprehensive workspace analytics.

    Args:
        db: Database session
        workspace_id: Workspace ID
        timeframe: Time period (24h, 7d, 30d, 90d, all)
        include_comparison: Include comparison data (admin only)

    Returns:
        Complete workspace analytics data
    """

    end_date = datetime.utcnow()
    start_date = calculate_start_date(timeframe)

    # Get workspace basic info
    workspace_query = text("""
        SELECT name, plan FROM public.workspaces WHERE id = :workspace_id
    """)
    result = await db.execute(workspace_query, {"workspace_id": workspace_id})
    workspace = result.fetchone()

    if not workspace:
        raise ValueError(f"Workspace {workspace_id} not found")

    # Fetch all metrics in parallel
    tasks = [
        get_workspace_overview(db, workspace_id, start_date, end_date),
        get_member_analytics(db, workspace_id, start_date, end_date),
        get_agent_usage(db, workspace_id, start_date, end_date),
        get_resource_utilization(db, workspace_id, start_date, end_date),
        get_billing_info(db, workspace_id, start_date, end_date),
    ]

    if include_comparison:
        tasks.append(get_workspace_comparison(db, workspace_id))

    results = await asyncio.gather(*tasks)

    return WorkspaceAnalytics(
        workspace_id=workspace_id,
        workspace_name=workspace.name,
        plan=workspace.plan or "free",
        timeframe=timeframe,
        overview=results[0],
        member_analytics=results[1],
        agent_usage=results[2],
        resource_utilization=results[3],
        billing=results[4],
        comparison=results[5] if include_comparison else None
    )
