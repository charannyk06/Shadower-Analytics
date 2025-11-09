"""
Comparison Service
Business logic for comparison views
"""

import logging
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import stats
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.datetime import utc_now
from src.models.database.tables import (
    ExecutionLog,
    AgentMetric as AgentMetricDB,
    WorkspaceMetric as WorkspaceMetricDB,
)

# Configure logging
logger = logging.getLogger(__name__)
from src.models.comparison_views import (
    AgentComparison,
    AgentComparisonItem,
    AgentMetrics,
    BenchmarkMetrics,
    ChangeDetail,
    ChangeMetrics,
    ComparisonError,
    ComparisonFilters,
    ComparisonInsight,
    ComparisonOptions,
    ComparisonResponse,
    ComparisonType,
    ComparisonViews,
    CorrelationDirection,
    CorrelationStrength,
    DistributionBucket,
    InsightSeverity,
    InsightType,
    MetricComparison,
    MetricCorrelation,
    MetricDifference,
    MetricDistribution,
    MetricEntity,
    MetricOutlier,
    MetricStatistics,
    OutlierSeverity,
    OutlierType,
    PeriodComparison,
    PeriodMetrics,
    RankingMetrics,
    Recommendation,
    RecommendationPriority,
    RecommendationType,
    TimeSeriesComparison,
    TimeSeriesPoint,
    TopPerformer,
    TrendDirection,
    ChangeDirection,
    VisualDiff,
    VisualDiffItem,
    WorkspaceComparison,
    WorkspaceMetrics,
    WorkspaceRanking,
    ComparisonMetadata,
    DiffColor,
)

# ============================================================================
# Constants
# ============================================================================

# Comparison limits
MIN_AGENTS_FOR_COMPARISON = 2
MAX_AGENTS_FOR_COMPARISON = 10
MIN_WORKSPACES_FOR_COMPARISON = 2
MAX_WORKSPACES_FOR_COMPARISON = 20
MIN_ENTITIES_FOR_METRIC_COMPARISON = 2

# Performance thresholds
ERROR_RATE_HIGH_THRESHOLD = 10.0
COST_VARIANCE_THRESHOLD = 50.0
RUNTIME_VARIANCE_THRESHOLD = 100.0

# Statistical thresholds
OUTLIER_ZSCORE_THRESHOLD = 2.0
MODERATE_OUTLIER_ZSCORE_THRESHOLD = 2.5
EXTREME_OUTLIER_ZSCORE_THRESHOLD = 3.0
SIGNIFICANT_CHANGE_THRESHOLD = 10.0
STABLE_CHANGE_THRESHOLD = 5.0

# Scoring weights
DEFAULT_SCORING_WEIGHTS = {
    "success_rate": 0.3,
    "error_rate": 0.2,
    "throughput": 0.2,
    "user_satisfaction": 0.15,
    "cost": 0.15,
}

# Pagination
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000
MAX_TIME_SERIES_POINTS = 1000


class ComparisonService:
    """Service for handling comparison operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Main Comparison Method
    # ========================================================================

    async def generate_comparison(
        self,
        comparison_type: ComparisonType,
        filters: ComparisonFilters,
        options: Optional[ComparisonOptions] = None,
    ) -> ComparisonResponse:
        """
        Generate comparison based on type

        Args:
            comparison_type: Type of comparison
            filters: Filters to apply
            options: Additional options

        Returns:
            ComparisonResponse with results
        """
        start_time = utc_now()

        try:
            # Use default options if not provided
            if options is None:
                options = ComparisonOptions()

            # Generate comparison based on type
            if comparison_type == ComparisonType.AGENTS:
                comparison_data = await self._compare_agents(filters, options)
            elif comparison_type == ComparisonType.PERIODS:
                comparison_data = await self._compare_periods(filters, options)
            elif comparison_type == ComparisonType.WORKSPACES:
                comparison_data = await self._compare_workspaces(filters, options)
            elif comparison_type == ComparisonType.METRICS:
                comparison_data = await self._compare_metrics(filters, options)
            else:
                raise ValueError(f"Unknown comparison type: {comparison_type}")

            # Calculate processing time
            processing_time = (utc_now() - start_time).total_seconds()

            # Count entities and data points
            entity_count = self._count_entities(comparison_data)
            data_points = self._count_data_points(comparison_data)

            return ComparisonResponse(
                success=True,
                data=comparison_data,
                metadata=ComparisonMetadata(
                    generated_at=utc_now(),
                    processing_time=processing_time,
                    entity_count=entity_count,
                    data_points=data_points,
                ),
            )

        except Exception as e:
            processing_time = (utc_now() - start_time).total_seconds()
            return ComparisonResponse(
                success=False,
                metadata=ComparisonMetadata(
                    generated_at=utc_now(),
                    processing_time=processing_time,
                    entity_count=0,
                    data_points=0,
                ),
                error=ComparisonError(code="COMPARISON_ERROR", message=str(e)),
            )

    # ========================================================================
    # Agent Comparison
    # ========================================================================

    async def _compare_agents(
        self, filters: ComparisonFilters, options: ComparisonOptions
    ) -> ComparisonViews:
        """Compare multiple agents"""

        # Get agent data
        agents_data = await self._fetch_agent_metrics(filters)

        if len(agents_data) < 2:
            raise ValueError("Need at least 2 agents for comparison")

        # Calculate differences
        differences = self._calculate_agent_differences(agents_data)

        # Determine winner
        winner, winner_score = self._determine_agent_winner(agents_data)

        # Generate recommendations
        recommendations = []
        if options.include_recommendations:
            recommendations = self._generate_agent_recommendations(agents_data, differences)

        agent_comparison = AgentComparison(
            agents=agents_data,
            differences=differences,
            winner=winner,
            winner_score=winner_score,
            recommendations=recommendations,
        )

        return ComparisonViews(
            type=ComparisonType.AGENTS,
            timestamp=utc_now(),
            agent_comparison=agent_comparison,
        )

    async def _fetch_agent_metrics(
        self, filters: ComparisonFilters
    ) -> List[AgentComparisonItem]:
        """Fetch metrics for agents from database

        Args:
            filters: Comparison filters with agent IDs and date range

        Returns:
            List of agent comparison items with metrics

        Raises:
            ValueError: If no valid agent data found
        """
        try:
            agent_ids = filters.agent_ids or []
            if not agent_ids:
                raise ValueError("No agent IDs provided")

            # Limit to max 10 agents as per constraints
            agent_ids = agent_ids[:MAX_AGENTS_FOR_COMPARISON]

            logger.info(f"Fetching metrics for {len(agent_ids)} agents")

            agents = []

            for agent_id in agent_ids:
                # Build base query for execution logs
                query = select(ExecutionLog).where(ExecutionLog.agent_id == agent_id)

                # Apply date filters
                if filters.start_date:
                    query = query.where(ExecutionLog.started_at >= filters.start_date)
                if filters.end_date:
                    query = query.where(ExecutionLog.started_at <= filters.end_date)

                # Apply workspace filter if provided
                if filters.workspace_ids:
                    query = query.where(ExecutionLog.workspace_id.in_(filters.workspace_ids))

                result = await self.db.execute(query)
                executions = result.scalars().all()

                if not executions:
                    logger.warning(f"No execution data found for agent {agent_id}")
                    continue

                # Calculate metrics from execution data
                total_runs = len(executions)
                successful_runs = len([e for e in executions if e.status == "success"])
                failed_runs = len([e for e in executions if e.status in ["failed", "error"]])

                success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0
                error_rate = (failed_runs / total_runs * 100) if total_runs > 0 else 0

                # Calculate runtime metrics (in milliseconds)
                durations = [e.duration for e in executions if e.duration is not None]
                avg_runtime = np.mean(durations) if durations else 0
                p50_runtime = np.percentile(durations, 50) if durations else 0
                p95_runtime = np.percentile(durations, 95) if durations else 0
                p99_runtime = np.percentile(durations, 99) if durations else 0

                # Calculate cost metrics
                credits_used = [e.credits_used for e in executions if e.credits_used is not None]
                total_credits = sum(credits_used) if credits_used else 0
                credits_per_run = total_credits / total_runs if total_runs > 0 else 0

                # Estimate cost (assuming $0.01 per credit as placeholder)
                cost_per_run = credits_per_run * 0.01
                total_cost = total_credits * 0.01

                # Calculate throughput (runs per day)
                if filters.start_date and filters.end_date:
                    days = (filters.end_date - filters.start_date).days or 1
                    throughput = total_runs / days
                else:
                    # Default to last 30 days
                    throughput = total_runs / 30

                # Get agent name from first execution metadata or use ID
                agent_name = f"Agent {agent_id}"
                if executions and executions[0].metadata:
                    agent_name = executions[0].metadata.get("agent_name", agent_name)

                # Get last run timestamp
                last_run_at = max([e.completed_at or e.started_at for e in executions])

                metrics = AgentMetrics(
                    success_rate=float(success_rate),
                    average_runtime=float(avg_runtime),
                    total_runs=total_runs,
                    error_rate=float(error_rate),
                    cost_per_run=float(cost_per_run),
                    total_cost=float(total_cost),
                    p50_runtime=float(p50_runtime),
                    p95_runtime=float(p95_runtime),
                    p99_runtime=float(p99_runtime),
                    throughput=float(throughput),
                    user_satisfaction=None,  # Not available in current schema
                    credits_per_run=float(credits_per_run),
                )

                agents.append(
                    AgentComparisonItem(
                        id=agent_id,
                        name=agent_name,
                        metrics=metrics,
                        last_run_at=last_run_at,
                    )
                )

            if not agents:
                raise ValueError("No valid agent data found for provided IDs")

            logger.info(f"Successfully fetched metrics for {len(agents)} agents")
            return agents

        except Exception as e:
            logger.error(f"Error fetching agent metrics: {str(e)}", exc_info=True)
            raise

    def _calculate_agent_differences(
        self, agents: List[AgentComparisonItem]
    ) -> Dict[str, MetricDifference]:
        """Calculate differences between agents"""

        # Extract metric values
        success_rates = {a.id: a.metrics.success_rate for a in agents}
        runtimes = {a.id: a.metrics.average_runtime for a in agents}
        costs = {a.id: a.metrics.cost_per_run for a in agents}
        throughputs = {a.id: a.metrics.throughput for a in agents}
        error_rates = {a.id: a.metrics.error_rate for a in agents}

        differences = {
            "successRate": self._create_metric_difference(
                success_rates, higher_is_better=True
            ),
            "runtime": self._create_metric_difference(
                runtimes, higher_is_better=False
            ),
            "cost": self._create_metric_difference(
                costs, higher_is_better=False
            ),
            "throughput": self._create_metric_difference(
                throughputs, higher_is_better=True
            ),
            "errorRate": self._create_metric_difference(
                error_rates, higher_is_better=False
            ),
        }

        return differences

    def _create_metric_difference(
        self, values: Dict[str, float], higher_is_better: bool
    ) -> MetricDifference:
        """Create metric difference object"""

        if higher_is_better:
            best_id = max(values, key=values.get)
            worst_id = min(values, key=values.get)
        else:
            best_id = min(values, key=values.get)
            worst_id = max(values, key=values.get)

        best_value = values[best_id]
        worst_value = values[worst_id]
        delta = abs(best_value - worst_value)
        delta_percent = (delta / worst_value * 100) if worst_value != 0 else 0

        return MetricDifference(
            best=best_id,
            worst=worst_id,
            delta=delta,
            delta_percent=delta_percent,
            values=values,
        )

    def _determine_agent_winner(
        self, agents: List[AgentComparisonItem]
    ) -> Tuple[str, float]:
        """Determine overall winner based on composite score"""

        scores = {}
        for agent in agents:
            # Weighted composite score using default weights
            score = (
                agent.metrics.success_rate * DEFAULT_SCORING_WEIGHTS["success_rate"]
                + (100 - min(agent.metrics.error_rate, 100)) * DEFAULT_SCORING_WEIGHTS["error_rate"]
                + min(agent.metrics.throughput / 10, 100) * DEFAULT_SCORING_WEIGHTS["throughput"]
                + (agent.metrics.user_satisfaction or 0) * 20 * DEFAULT_SCORING_WEIGHTS["user_satisfaction"]
                + max(100 - agent.metrics.cost_per_run * 100, 0) * DEFAULT_SCORING_WEIGHTS["cost"]
            )
            scores[agent.id] = score

        winner_id = max(scores, key=scores.get)
        winner_score = scores[winner_id]

        return winner_id, winner_score

    def _generate_agent_recommendations(
        self,
        agents: List[AgentComparisonItem],
        differences: Dict[str, MetricDifference],
    ) -> List[Recommendation]:
        """Generate recommendations based on comparison"""

        recommendations = []

        # Check error rates
        high_error_agents = [
            a for a in agents if a.metrics.error_rate > ERROR_RATE_HIGH_THRESHOLD
        ]
        if high_error_agents:
            recommendations.append(
                Recommendation(
                    type=RecommendationType.RELIABILITY,
                    priority=RecommendationPriority.HIGH,
                    title="High Error Rates Detected",
                    description=f"{len(high_error_agents)} agent(s) have error rates above {ERROR_RATE_HIGH_THRESHOLD}%. Consider reviewing error logs and implementing retry logic.",
                    affected_agents=[a.id for a in high_error_agents],
                )
            )

        # Check costs
        if differences["cost"].delta_percent > COST_VARIANCE_THRESHOLD:
            recommendations.append(
                Recommendation(
                    type=RecommendationType.COST,
                    priority=RecommendationPriority.MEDIUM,
                    title="Significant Cost Variance",
                    description=f"Cost per run varies by {differences['cost'].delta_percent:.1f}%. Review agent {differences['cost'].best} configuration for cost optimization opportunities.",
                    affected_agents=[differences["cost"].worst],
                    potential_impact={
                        "metric": "cost_per_run",
                        "estimated_improvement": differences["cost"].delta_percent,
                    },
                )
            )

        # Check performance
        if differences["runtime"].delta_percent > RUNTIME_VARIANCE_THRESHOLD:
            recommendations.append(
                Recommendation(
                    type=RecommendationType.PERFORMANCE,
                    priority=RecommendationPriority.HIGH,
                    title="Runtime Optimization Opportunity",
                    description=f"Runtime varies by {differences['runtime'].delta_percent:.1f}%. Agent {differences['runtime'].best} demonstrates superior performance.",
                    affected_agents=[differences["runtime"].worst],
                )
            )

        return recommendations

    # ========================================================================
    # Period Comparison
    # ========================================================================

    async def _compare_periods(
        self, filters: ComparisonFilters, options: ComparisonOptions
    ) -> ComparisonViews:
        """Compare two time periods"""

        # Calculate period boundaries
        if not filters.end_date:
            filters.end_date = utc_now()
        if not filters.start_date:
            filters.start_date = filters.end_date - timedelta(days=7)

        period_length = filters.end_date - filters.start_date
        previous_start = filters.start_date - period_length
        previous_end = filters.start_date

        # Fetch metrics for both periods
        current = await self._fetch_period_metrics(
            filters.start_date, filters.end_date, "Current Period"
        )
        previous = await self._fetch_period_metrics(
            previous_start, previous_end, "Previous Period"
        )

        # Calculate changes
        change = self._calculate_period_changes(current, previous)

        # Generate insights
        improvements, regressions = self._identify_period_changes(change)

        # Generate summary
        summary = self._generate_period_summary(current, previous, change)

        # Time series comparison if requested
        time_series = None
        if options.include_time_series:
            time_series = await self._generate_time_series_comparison(
                filters.start_date, filters.end_date, previous_start, previous_end
            )

        period_comparison = PeriodComparison(
            current=current,
            previous=previous,
            change=change,
            improvements=improvements,
            regressions=regressions,
            summary=summary,
            time_series_comparison=time_series,
        )

        return ComparisonViews(
            type=ComparisonType.PERIODS,
            timestamp=utc_now(),
            period_comparison=period_comparison,
        )

    async def _fetch_period_metrics(
        self, start: datetime, end: datetime, period_name: str
    ) -> PeriodMetrics:
        """Fetch metrics for a time period from database

        Args:
            start: Period start date
            end: Period end date
            period_name: Name of the period

        Returns:
            PeriodMetrics with aggregated data

        Raises:
            ValueError: If no data found for the period
        """
        try:
            logger.info(f"Fetching metrics for period {period_name} ({start} to {end})")

            # Query execution logs for the period
            query = select(ExecutionLog).where(
                and_(
                    ExecutionLog.started_at >= start,
                    ExecutionLog.started_at <= end
                )
            )

            result = await self.db.execute(query)
            executions = result.scalars().all()

            if not executions:
                logger.warning(f"No execution data found for period {period_name}")
                # Return zero metrics instead of failing
                return PeriodMetrics(
                    period=period_name,
                    start_date=start,
                    end_date=end,
                    total_runs=0,
                    success_rate=0.0,
                    average_runtime=0.0,
                    total_cost=0.0,
                    error_count=0,
                    active_agents=0,
                    active_users=0,
                    throughput=0.0,
                    p95_runtime=0.0,
                    credit_consumption=0.0,
                )

            # Calculate aggregated metrics
            total_runs = len(executions)
            successful_runs = len([e for e in executions if e.status == "success"])
            failed_runs = len([e for e in executions if e.status in ["failed", "error"]])

            success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0

            # Runtime metrics
            durations = [e.duration for e in executions if e.duration is not None]
            avg_runtime = float(np.mean(durations)) if durations else 0.0
            p95_runtime = float(np.percentile(durations, 95)) if durations else 0.0

            # Cost and credit metrics
            credits = [e.credits_used for e in executions if e.credits_used is not None]
            total_credits = sum(credits) if credits else 0
            total_cost = total_credits * 0.01  # $0.01 per credit

            # Active entities
            active_agents = len(set(e.agent_id for e in executions))
            active_users = len(set(e.user_id for e in executions))

            # Throughput (runs per day)
            days = (end - start).days or 1
            throughput = total_runs / days

            logger.info(f"Successfully fetched metrics for period {period_name}: {total_runs} runs")

            return PeriodMetrics(
                period=period_name,
                start_date=start,
                end_date=end,
                total_runs=total_runs,
                success_rate=float(success_rate),
                average_runtime=avg_runtime,
                total_cost=float(total_cost),
                error_count=failed_runs,
                active_agents=active_agents,
                active_users=active_users,
                throughput=float(throughput),
                p95_runtime=p95_runtime,
                credit_consumption=float(total_credits),
            )

        except Exception as e:
            logger.error(f"Error fetching period metrics: {str(e)}", exc_info=True)
            raise

    def _calculate_period_changes(
        self, current: PeriodMetrics, previous: PeriodMetrics
    ) -> ChangeMetrics:
        """Calculate changes between periods"""

        def create_change(curr_val: float, prev_val: float, higher_is_better: bool) -> ChangeDetail:
            absolute = curr_val - prev_val
            percent = (absolute / prev_val * 100) if prev_val != 0 else 0

            if abs(percent) < STABLE_CHANGE_THRESHOLD:
                trend = TrendDirection.STABLE
            elif absolute > 0:
                trend = TrendDirection.UP
            else:
                trend = TrendDirection.DOWN

            significant = abs(percent) > SIGNIFICANT_CHANGE_THRESHOLD

            if higher_is_better:
                direction = (
                    ChangeDirection.POSITIVE if absolute > 0
                    else ChangeDirection.NEGATIVE if absolute < 0
                    else ChangeDirection.NEUTRAL
                )
            else:
                direction = (
                    ChangeDirection.NEGATIVE if absolute > 0
                    else ChangeDirection.POSITIVE if absolute < 0
                    else ChangeDirection.NEUTRAL
                )

            return ChangeDetail(
                absolute=absolute,
                percent=percent,
                trend=trend,
                significant=significant,
                direction=direction,
            )

        return ChangeMetrics(
            total_runs=create_change(current.total_runs, previous.total_runs, True),
            success_rate=create_change(current.success_rate, previous.success_rate, True),
            average_runtime=create_change(current.average_runtime, previous.average_runtime, False),
            total_cost=create_change(current.total_cost, previous.total_cost, False),
            error_count=create_change(current.error_count, previous.error_count, False),
            active_agents=create_change(current.active_agents, previous.active_agents, True),
            active_users=create_change(current.active_users, previous.active_users, True),
            throughput=create_change(current.throughput, previous.throughput, True),
            p95_runtime=create_change(current.p95_runtime, previous.p95_runtime, False),
            credit_consumption=create_change(current.credit_consumption, previous.credit_consumption, False),
        )

    def _identify_period_changes(
        self, change: ChangeMetrics
    ) -> Tuple[List[str], List[str]]:
        """Identify improvements and regressions"""

        improvements = []
        regressions = []

        for field_name, change_detail in change.model_dump().items():
            if not isinstance(change_detail, dict):
                continue

            direction = change_detail.get("direction")
            significant = change_detail.get("significant")
            percent = change_detail.get("percent", 0)

            if not significant:
                continue

            metric_label = field_name.replace("_", " ").title()

            if direction == "positive":
                improvements.append(
                    f"{metric_label} improved by {abs(percent):.1f}%"
                )
            elif direction == "negative":
                regressions.append(
                    f"{metric_label} declined by {abs(percent):.1f}%"
                )

        return improvements, regressions

    def _generate_period_summary(
        self, current: PeriodMetrics, previous: PeriodMetrics, change: ChangeMetrics
    ) -> str:
        """Generate summary of period comparison"""

        positive_changes = sum(
            1 for field_name, value in change.model_dump().items()
            if isinstance(value, dict) and value.get("direction") == "positive"
        )

        negative_changes = sum(
            1 for field_name, value in change.model_dump().items()
            if isinstance(value, dict) and value.get("direction") == "negative"
        )

        if positive_changes > negative_changes:
            overall = "improved"
        elif negative_changes > positive_changes:
            overall = "declined"
        else:
            overall = "remained stable"

        return f"Overall performance has {overall} compared to the previous period, with {positive_changes} improvements and {negative_changes} regressions."

    async def _generate_time_series_comparison(
        self,
        current_start: datetime,
        current_end: datetime,
        previous_start: datetime,
        previous_end: datetime,
    ) -> TimeSeriesComparison:
        """Generate time series comparison data"""

        # Mock time series data
        current_data = [
            TimeSeriesPoint(
                timestamp=current_start + timedelta(days=i),
                value=np.random.uniform(80, 99),
            )
            for i in range((current_end - current_start).days + 1)
        ]

        previous_data = [
            TimeSeriesPoint(
                timestamp=previous_start + timedelta(days=i),
                value=np.random.uniform(75, 95),
            )
            for i in range((previous_end - previous_start).days + 1)
        ]

        return TimeSeriesComparison(
            current_period_data=current_data,
            previous_period_data=previous_data,
            metric="success_rate",
            unit="%",
        )

    # ========================================================================
    # Workspace Comparison
    # ========================================================================

    async def _compare_workspaces(
        self, filters: ComparisonFilters, options: ComparisonOptions
    ) -> ComparisonViews:
        """Compare multiple workspaces"""

        # Fetch workspace metrics
        workspaces = await self._fetch_workspace_metrics(filters)

        if len(workspaces) < 2:
            raise ValueError("Need at least 2 workspaces for comparison")

        # Calculate benchmarks
        benchmarks = self._calculate_workspace_benchmarks(workspaces)

        # Generate rankings
        rankings = self._generate_workspace_rankings(workspaces)

        # Generate insights
        insights = self._generate_workspace_insights(workspaces, benchmarks)

        workspace_comparison = WorkspaceComparison(
            workspaces=workspaces,
            benchmarks=benchmarks,
            rankings=rankings,
            insights=insights,
        )

        return ComparisonViews(
            type=ComparisonType.WORKSPACES,
            timestamp=utc_now(),
            workspace_comparison=workspace_comparison,
        )

    async def _fetch_workspace_metrics(
        self, filters: ComparisonFilters
    ) -> List[WorkspaceMetrics]:
        """Fetch metrics for workspaces from database

        Args:
            filters: Comparison filters with workspace IDs and date range

        Returns:
            List of workspace metrics

        Raises:
            ValueError: If no valid workspace data found
        """
        try:
            workspace_ids = filters.workspace_ids or []
            if not workspace_ids:
                raise ValueError("No workspace IDs provided")

            # Limit to max 20 workspaces as per constraints
            workspace_ids = workspace_ids[:MAX_WORKSPACES_FOR_COMPARISON]

            logger.info(f"Fetching metrics for {len(workspace_ids)} workspaces")

            workspaces = []

            for workspace_id in workspace_ids:
                # Build base query for execution logs
                query = select(ExecutionLog).where(ExecutionLog.workspace_id == workspace_id)

                # Apply date filters
                if filters.start_date:
                    query = query.where(ExecutionLog.started_at >= filters.start_date)
                if filters.end_date:
                    query = query.where(ExecutionLog.started_at <= filters.end_date)

                result = await self.db.execute(query)
                executions = result.scalars().all()

                if not executions:
                    logger.warning(f"No execution data found for workspace {workspace_id}")
                    continue

                # Calculate metrics from execution data
                total_runs = len(executions)
                successful_runs = len([e for e in executions if e.status == "success"])
                failed_runs = len([e for e in executions if e.status in ["failed", "error"]])

                success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0
                error_rate = (failed_runs / total_runs * 100) if total_runs > 0 else 0

                # Calculate runtime metrics
                durations = [e.duration for e in executions if e.duration is not None]
                avg_runtime = float(np.mean(durations)) if durations else 0.0

                # Calculate cost metrics
                credits = [e.credits_used for e in executions if e.credits_used is not None]
                total_credits = sum(credits) if credits else 0
                total_cost = total_credits * 0.01  # $0.01 per credit

                # Active entities
                active_agents = len(set(e.agent_id for e in executions))
                active_users = len(set(e.user_id for e in executions))

                # Calculate throughput (runs per day)
                if filters.start_date and filters.end_date:
                    days = (filters.end_date - filters.start_date).days or 1
                    throughput = total_runs / days
                else:
                    throughput = total_runs / 30  # Default to 30 days

                workspaces.append(
                    WorkspaceMetrics(
                        workspace_id=workspace_id,
                        workspace_name=f"Workspace {workspace_id}",
                        total_runs=total_runs,
                        success_rate=float(success_rate),
                        average_runtime=avg_runtime,
                        total_cost=float(total_cost),
                        active_agents=active_agents,
                        active_users=active_users,
                        credit_usage=float(total_credits),
                        error_rate=float(error_rate),
                        throughput=float(throughput),
                        user_satisfaction=None,  # Not available in current schema
                    )
                )

            if not workspaces:
                raise ValueError("No valid workspace data found for provided IDs")

            logger.info(f"Successfully fetched metrics for {len(workspaces)} workspaces")
            return workspaces

        except Exception as e:
            logger.error(f"Error fetching workspace metrics: {str(e)}", exc_info=True)
            raise

    def _calculate_workspace_benchmarks(
        self, workspaces: List[WorkspaceMetrics]
    ) -> BenchmarkMetrics:
        """Calculate benchmark metrics"""

        avg_success_rate = np.mean([w.success_rate for w in workspaces])
        avg_runtime = np.mean([w.average_runtime for w in workspaces])
        avg_cost = np.mean([w.total_cost for w in workspaces])
        avg_throughput = np.mean([w.throughput for w in workspaces])

        # Calculate composite scores using default weights
        scores = {}
        for ws in workspaces:
            score = (
                ws.success_rate * DEFAULT_SCORING_WEIGHTS["success_rate"]
                + (100 - min(ws.error_rate, 100)) * DEFAULT_SCORING_WEIGHTS["error_rate"]
                + min(ws.throughput / 10, 100) * DEFAULT_SCORING_WEIGHTS["throughput"]
                + (ws.user_satisfaction or 0) * 20 * DEFAULT_SCORING_WEIGHTS["user_satisfaction"]
                + max(100 - ws.total_cost / 100, 0) * DEFAULT_SCORING_WEIGHTS["cost"]
            )
            scores[ws.workspace_id] = (score, ws.workspace_name)

        top_id = max(scores, key=lambda k: scores[k][0])
        bottom_id = min(scores, key=lambda k: scores[k][0])

        return BenchmarkMetrics(
            average_success_rate=avg_success_rate,
            average_runtime=avg_runtime,
            average_cost=avg_cost,
            average_throughput=avg_throughput,
            top_performer=TopPerformer(
                workspace_id=top_id,
                workspace_name=scores[top_id][1],
                score=scores[top_id][0],
            ),
            bottom_performer=TopPerformer(
                workspace_id=bottom_id,
                workspace_name=scores[bottom_id][1],
                score=scores[bottom_id][0],
            ),
        )

    def _generate_workspace_rankings(
        self, workspaces: List[WorkspaceMetrics]
    ) -> RankingMetrics:
        """Generate workspace rankings"""

        # Calculate scores using default weights
        scores = []
        for ws in workspaces:
            score = (
                ws.success_rate * DEFAULT_SCORING_WEIGHTS["success_rate"]
                + (100 - min(ws.error_rate, 100)) * DEFAULT_SCORING_WEIGHTS["error_rate"]
                + min(ws.throughput / 10, 100) * DEFAULT_SCORING_WEIGHTS["throughput"]
                + (ws.user_satisfaction or 0) * 20 * DEFAULT_SCORING_WEIGHTS["user_satisfaction"]
                + max(100 - ws.total_cost / 100, 0) * DEFAULT_SCORING_WEIGHTS["cost"]
            )
            scores.append((ws, score))

        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)

        # Create rankings
        rankings = []
        for rank, (ws, score) in enumerate(scores, 1):
            percentile = (len(scores) - rank + 1) / len(scores) * 100

            # Identify strengths and weaknesses
            strengths = []
            weaknesses = []

            if ws.success_rate > 95:
                strengths.append("High success rate")
            elif ws.success_rate < 85:
                weaknesses.append("Low success rate")

            if ws.error_rate < 5:
                strengths.append("Low error rate")
            elif ws.error_rate > 15:
                weaknesses.append("High error rate")

            if ws.throughput > 80:
                strengths.append("High throughput")
            elif ws.throughput < 30:
                weaknesses.append("Low throughput")

            rankings.append(
                WorkspaceRanking(
                    rank=rank,
                    workspace_id=ws.workspace_id,
                    workspace_name=ws.workspace_name,
                    score=score,
                    percentile=percentile,
                    strengths=strengths or ["Stable performance"],
                    weaknesses=weaknesses or ["No significant issues"],
                )
            )

        return RankingMetrics(
            rankings=rankings,
            score_method="weighted",
            weights=DEFAULT_SCORING_WEIGHTS,
        )

    def _generate_workspace_insights(
        self, workspaces: List[WorkspaceMetrics], benchmarks: BenchmarkMetrics
    ) -> List[ComparisonInsight]:
        """Generate insights from workspace comparison"""

        insights = []

        # Check for underperforming workspaces
        underperforming = [
            w for w in workspaces
            if w.success_rate < benchmarks.average_success_rate - 10
        ]

        if underperforming:
            insights.append(
                ComparisonInsight(
                    type=InsightType.WARNING,
                    severity=InsightSeverity.HIGH,
                    title="Underperforming Workspaces",
                    description=f"{len(underperforming)} workspace(s) performing significantly below average",
                    affected_workspaces=[w.workspace_id for w in underperforming],
                )
            )

        # Check for cost anomalies
        cost_values = [w.total_cost for w in workspaces]
        cost_mean = np.mean(cost_values)
        cost_std = np.std(cost_values)

        high_cost = [
            w for w in workspaces
            if w.total_cost > cost_mean + 2 * cost_std
        ]

        if high_cost:
            insights.append(
                ComparisonInsight(
                    type=InsightType.ANOMALY,
                    severity=InsightSeverity.MEDIUM,
                    title="Unusual Cost Pattern",
                    description=f"{len(high_cost)} workspace(s) with costs significantly above average",
                    affected_workspaces=[w.workspace_id for w in high_cost],
                )
            )

        return insights

    # ========================================================================
    # Metric Comparison
    # ========================================================================

    async def _compare_metrics(
        self, filters: ComparisonFilters, options: ComparisonOptions
    ) -> ComparisonViews:
        """Compare a specific metric across entities"""

        # Use first metric name or default
        metric_name = (
            filters.metric_names[0] if filters.metric_names else "success_rate"
        )

        # Fetch metric data
        entities = await self._fetch_metric_entities(metric_name, filters)

        if len(entities) < 2:
            raise ValueError("Need at least 2 entities for metric comparison")

        # Calculate statistics
        values = [e.value for e in entities]
        statistics = self._calculate_metric_statistics(values)

        # Calculate distribution
        distribution = self._calculate_metric_distribution(values)

        # Identify outliers
        outliers = self._identify_metric_outliers(entities, statistics)

        # Calculate correlations if requested
        correlations = None
        if options.include_correlations:
            correlations = await self._calculate_metric_correlations(
                metric_name, filters
            )

        metric_comparison = MetricComparison(
            metric_name=metric_name,
            metric_type="performance",
            entities=entities,
            statistics=statistics,
            distribution=distribution,
            outliers=outliers,
            correlations=correlations,
        )

        return ComparisonViews(
            type=ComparisonType.METRICS,
            timestamp=utc_now(),
            metric_comparison=metric_comparison,
        )

    async def _fetch_metric_entities(
        self, metric_name: str, filters: ComparisonFilters
    ) -> List[MetricEntity]:
        """Fetch metric values for entities from database

        Args:
            metric_name: Name of the metric to fetch
            filters: Comparison filters

        Returns:
            List of metric entities

        Raises:
            ValueError: If no valid entity data found
        """
        try:
            logger.info(f"Fetching metric entities for {metric_name}")

            # Map metric names to database fields
            metric_mapping = {
                "success_rate": lambda e: (len([x for x in e if x.status == "success"]) / len(e) * 100) if e else 0,
                "error_rate": lambda e: (len([x for x in e if x.status in ["failed", "error"]]) / len(e) * 100) if e else 0,
                "average_runtime": lambda e: float(np.mean([x.duration for x in e if x.duration])) if any(x.duration for x in e) else 0,
                "throughput": lambda e: len(e),
                "cost_per_run": lambda e: (sum(x.credits_used for x in e if x.credits_used) / len(e) * 0.01) if e else 0,
            }

            if metric_name not in metric_mapping:
                raise ValueError(f"Unsupported metric: {metric_name}")

            # Determine entity type (agents or workspaces)
            entity_ids = []
            entity_type = "agent"

            if filters.agent_ids:
                entity_ids = filters.agent_ids
                entity_type = "agent"
            elif filters.workspace_ids:
                entity_ids = filters.workspace_ids
                entity_type = "workspace"
            else:
                # Fetch all distinct entities from execution logs
                if filters.start_date and filters.end_date:
                    query = select(ExecutionLog.agent_id).distinct().where(
                        and_(
                            ExecutionLog.started_at >= filters.start_date,
                            ExecutionLog.started_at <= filters.end_date
                        )
                    ).limit(50)
                else:
                    query = select(ExecutionLog.agent_id).distinct().limit(50)

                result = await self.db.execute(query)
                entity_ids = [row[0] for row in result.all()]

            if not entity_ids:
                raise ValueError("No entities found for metric comparison")

            entities = []
            values = []

            for entity_id in entity_ids:
                # Build query for entity executions
                if entity_type == "agent":
                    query = select(ExecutionLog).where(ExecutionLog.agent_id == entity_id)
                else:
                    query = select(ExecutionLog).where(ExecutionLog.workspace_id == entity_id)

                # Apply date filters
                if filters.start_date:
                    query = query.where(ExecutionLog.started_at >= filters.start_date)
                if filters.end_date:
                    query = query.where(ExecutionLog.started_at <= filters.end_date)

                result = await self.db.execute(query)
                executions = result.scalars().all()

                if not executions:
                    continue

                # Calculate metric value using mapping function
                value = metric_mapping[metric_name](executions)
                values.append(value)

                entities.append({
                    "id": entity_id,
                    "executions": executions,
                    "value": value
                })

            if not entities:
                raise ValueError("No valid entity data found")

            # Calculate statistics for percentiles and deviations
            values_array = np.array(values)
            mean_value = np.mean(values_array)

            # Build final entity list with statistics
            result_entities = []
            for entity_data in entities:
                entity_id = entity_data["id"]
                value = entity_data["value"]
                executions = entity_data["executions"]

                percentile = stats.percentileofscore(values, value)
                deviation = value - mean_value

                # Calculate trend (simple: compare first half vs second half)
                if len(executions) >= 4:
                    mid = len(executions) // 2
                    first_half = metric_mapping[metric_name](executions[:mid])
                    second_half = metric_mapping[metric_name](executions[mid:])

                    if second_half > first_half * 1.1:
                        trend = "increasing"
                    elif second_half < first_half * 0.9:
                        trend = "decreasing"
                    else:
                        trend = "stable"
                else:
                    trend = "stable"

                # Generate sparkline data (last 7 data points)
                sparkline_data = []
                if len(executions) >= 7:
                    chunk_size = max(1, len(executions) // 7)
                    for i in range(7):
                        start_idx = i * chunk_size
                        end_idx = min((i + 1) * chunk_size, len(executions))
                        chunk = executions[start_idx:end_idx]
                        if chunk:
                            sparkline_data.append(metric_mapping[metric_name](chunk))

                result_entities.append(
                    MetricEntity(
                        id=entity_id,
                        name=f"{entity_type.capitalize()} {entity_id}",
                        value=float(value),
                        percentile=float(percentile),
                        deviation_from_mean=float(deviation),
                        trend=trend,
                        sparkline_data=sparkline_data if sparkline_data else None,
                    )
                )

            logger.info(f"Successfully fetched {len(result_entities)} metric entities")
            return result_entities

        except Exception as e:
            logger.error(f"Error fetching metric entities: {str(e)}", exc_info=True)
            raise

    def _calculate_metric_statistics(
        self, values: List[float]
    ) -> MetricStatistics:
        """Calculate statistical measures"""

        arr = np.array(values)

        return MetricStatistics(
            mean=float(np.mean(arr)),
            median=float(np.median(arr)),
            standard_deviation=float(np.std(arr)),
            min=float(np.min(arr)),
            max=float(np.max(arr)),
            p25=float(np.percentile(arr, 25)),
            p75=float(np.percentile(arr, 75)),
            p90=float(np.percentile(arr, 90)),
            p95=float(np.percentile(arr, 95)),
            p99=float(np.percentile(arr, 99)),
            variance=float(np.var(arr)),
            coefficient_of_variation=float(np.std(arr) / np.mean(arr))
            if np.mean(arr) != 0
            else 0,
        )

    def _calculate_metric_distribution(
        self, values: List[float]
    ) -> MetricDistribution:
        """Calculate distribution of metric values"""

        arr = np.array(values)

        # Create buckets
        num_buckets = min(10, len(values) // 2)
        counts, bin_edges = np.histogram(arr, bins=num_buckets)

        buckets = []
        for i, count in enumerate(counts):
            buckets.append(
                DistributionBucket(
                    min=float(bin_edges[i]),
                    max=float(bin_edges[i + 1]),
                    count=int(count),
                    percentage=float(count / len(values) * 100),
                    label=f"{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}",
                )
            )

        # Calculate skewness and kurtosis
        skewness = float(stats.skew(arr))
        kurtosis = float(stats.kurtosis(arr))

        # Test for normality (Shapiro-Wilk test)
        _, p_value = stats.shapiro(arr) if len(arr) >= 3 else (0, 0)
        is_normal = p_value > 0.05

        return MetricDistribution(
            buckets=buckets,
            skewness=skewness,
            kurtosis=kurtosis,
            is_normal=is_normal,
        )

    def _identify_metric_outliers(
        self, entities: List[MetricEntity], statistics: MetricStatistics
    ) -> List[MetricOutlier]:
        """Identify outliers in metric data"""

        outliers = []

        for entity in entities:
            # Calculate z-score
            z_score = (
                (entity.value - statistics.mean) / statistics.standard_deviation
                if statistics.standard_deviation != 0
                else 0
            )

            # Determine if outlier
            if abs(z_score) > OUTLIER_ZSCORE_THRESHOLD:
                outlier_type = OutlierType.HIGH if z_score > 0 else OutlierType.LOW

                if abs(z_score) > EXTREME_OUTLIER_ZSCORE_THRESHOLD:
                    severity = OutlierSeverity.EXTREME
                elif abs(z_score) > MODERATE_OUTLIER_ZSCORE_THRESHOLD:
                    severity = OutlierSeverity.MODERATE
                else:
                    severity = OutlierSeverity.MILD

                outliers.append(
                    MetricOutlier(
                        entity_id=entity.id,
                        entity_name=entity.name,
                        value=entity.value,
                        z_score=float(z_score),
                        type=outlier_type,
                        severity=severity,
                    )
                )

        return outliers

    async def _calculate_metric_correlations(
        self, metric_name: str, filters: ComparisonFilters
    ) -> List[MetricCorrelation]:
        """Calculate correlations with other metrics using real data

        Args:
            metric_name: Primary metric name
            filters: Comparison filters

        Returns:
            List of metric correlations

        Raises:
            ValueError: If insufficient data for correlation calculation
        """
        try:
            logger.info(f"Calculating correlations for {metric_name}")

            # Define metrics to correlate with
            other_metrics = [
                "success_rate",
                "error_rate",
                "average_runtime",
                "throughput",
                "cost_per_run",
            ]

            # Remove the primary metric from the list
            other_metrics = [m for m in other_metrics if m != metric_name]

            # Fetch entities for primary metric
            primary_entities = await self._fetch_metric_entities(metric_name, filters)

            if len(primary_entities) < 3:
                raise ValueError("Need at least 3 entities for correlation calculation")

            primary_values = [e.value for e in primary_entities]
            entity_ids = [e.id for e in primary_entities]

            correlations = []

            for other_metric in other_metrics:
                try:
                    # Fetch entities for other metric
                    # Create a new filter with the same entity IDs
                    correlation_filters = ComparisonFilters(
                        agent_ids=entity_ids if filters.agent_ids else None,
                        workspace_ids=entity_ids if filters.workspace_ids else None,
                        start_date=filters.start_date,
                        end_date=filters.end_date,
                    )

                    other_entities = await self._fetch_metric_entities(
                        other_metric, correlation_filters
                    )

                    # Match entities by ID and create paired values
                    other_values_dict = {e.id: e.value for e in other_entities}

                    # Build paired arrays
                    paired_primary = []
                    paired_other = []

                    for entity_id, primary_val in zip(entity_ids, primary_values):
                        if entity_id in other_values_dict:
                            paired_primary.append(primary_val)
                            paired_other.append(other_values_dict[entity_id])

                    if len(paired_primary) < 3:
                        logger.warning(
                            f"Insufficient paired data for {metric_name} vs {other_metric}"
                        )
                        continue

                    # Calculate Pearson correlation coefficient
                    coefficient, p_value = stats.pearsonr(paired_primary, paired_other)

                    # Handle NaN results
                    if np.isnan(coefficient) or np.isnan(p_value):
                        logger.warning(
                            f"NaN correlation result for {metric_name} vs {other_metric}"
                        )
                        continue

                    # Determine strength
                    abs_coef = abs(coefficient)
                    if abs_coef > 0.7:
                        strength = CorrelationStrength.STRONG
                    elif abs_coef > 0.4:
                        strength = CorrelationStrength.MODERATE
                    else:
                        strength = CorrelationStrength.WEAK

                    # Determine direction
                    direction = (
                        CorrelationDirection.POSITIVE
                        if coefficient > 0
                        else CorrelationDirection.NEGATIVE
                    )

                    correlations.append(
                        MetricCorrelation(
                            metric1=metric_name,
                            metric2=other_metric,
                            coefficient=float(coefficient),
                            strength=strength,
                            direction=direction,
                            p_value=float(p_value),
                            significant=p_value < 0.05,
                        )
                    )

                except Exception as e:
                    logger.warning(
                        f"Failed to calculate correlation for {other_metric}: {str(e)}"
                    )
                    continue

            logger.info(f"Calculated {len(correlations)} correlations for {metric_name}")
            return correlations

        except Exception as e:
            logger.error(f"Error calculating metric correlations: {str(e)}", exc_info=True)
            # Return empty list instead of failing
            return []

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _count_entities(self, comparison: ComparisonViews) -> int:
        """Count entities in comparison"""

        if comparison.agent_comparison:
            return len(comparison.agent_comparison.agents)
        elif comparison.period_comparison:
            return 2  # Current and previous
        elif comparison.workspace_comparison:
            return len(comparison.workspace_comparison.workspaces)
        elif comparison.metric_comparison:
            return len(comparison.metric_comparison.entities)

        return 0

    def _count_data_points(self, comparison: ComparisonViews) -> int:
        """Count data points in comparison"""

        count = 0

        if comparison.agent_comparison:
            count = len(comparison.agent_comparison.agents) * 12  # 12 metrics per agent
        elif comparison.period_comparison:
            count = 20  # 10 metrics * 2 periods
            if comparison.period_comparison.time_series_comparison:
                count += len(
                    comparison.period_comparison.time_series_comparison.current_period_data
                )
                count += len(
                    comparison.period_comparison.time_series_comparison.previous_period_data
                )
        elif comparison.workspace_comparison:
            count = len(comparison.workspace_comparison.workspaces) * 11
        elif comparison.metric_comparison:
            count = len(comparison.metric_comparison.entities)

        return count
