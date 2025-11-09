"""
Comparison Service
Business logic for comparison views
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np
from scipy import stats
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.comparison_views import (
    AgentComparison,
    AgentComparisonItem,
    AgentMetrics,
    BenchmarkMetrics,
    ChangeDetail,
    ChangeMetrics,
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
        start_time = datetime.utcnow()

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
            processing_time = (datetime.utcnow() - start_time).total_seconds()

            # Count entities and data points
            entity_count = self._count_entities(comparison_data)
            data_points = self._count_data_points(comparison_data)

            return ComparisonResponse(
                success=True,
                data=comparison_data,
                metadata=ComparisonMetadata(
                    generated_at=datetime.utcnow(),
                    processing_time=processing_time,
                    entity_count=entity_count,
                    data_points=data_points,
                ),
            )

        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            return ComparisonResponse(
                success=False,
                metadata=ComparisonMetadata(
                    generated_at=datetime.utcnow(),
                    processing_time=processing_time,
                    entity_count=0,
                    data_points=0,
                ),
                error={"code": "COMPARISON_ERROR", "message": str(e)},
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
            timestamp=datetime.utcnow(),
            agent_comparison=agent_comparison,
        )

    async def _fetch_agent_metrics(
        self, filters: ComparisonFilters
    ) -> List[AgentComparisonItem]:
        """Fetch metrics for agents"""

        # This is a mock implementation
        # In production, this would query the database
        agents = []
        agent_ids = filters.agent_ids or []

        for agent_id in agent_ids[:5]:  # Limit to 5 agents
            metrics = AgentMetrics(
                success_rate=np.random.uniform(85, 99),
                average_runtime=np.random.uniform(100, 5000),
                total_runs=np.random.randint(100, 10000),
                error_rate=np.random.uniform(1, 15),
                cost_per_run=np.random.uniform(0.01, 0.5),
                total_cost=np.random.uniform(10, 1000),
                p50_runtime=np.random.uniform(50, 2000),
                p95_runtime=np.random.uniform(200, 8000),
                p99_runtime=np.random.uniform(500, 15000),
                throughput=np.random.uniform(10, 100),
                user_satisfaction=np.random.uniform(3.5, 5.0),
                credits_per_run=np.random.uniform(1, 50),
            )

            agents.append(
                AgentComparisonItem(
                    id=agent_id,
                    name=f"Agent {agent_id}",
                    metrics=metrics,
                )
            )

        return agents

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
            # Weighted composite score
            score = (
                agent.metrics.success_rate * 0.3
                + (100 - min(agent.metrics.error_rate, 100)) * 0.2
                + min(agent.metrics.throughput / 10, 100) * 0.2
                + (agent.metrics.user_satisfaction or 0) * 20 * 0.15
                + max(100 - agent.metrics.cost_per_run * 100, 0) * 0.15
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
            a for a in agents if a.metrics.error_rate > 10
        ]
        if high_error_agents:
            recommendations.append(
                Recommendation(
                    type=RecommendationType.RELIABILITY,
                    priority=RecommendationPriority.HIGH,
                    title="High Error Rates Detected",
                    description=f"{len(high_error_agents)} agent(s) have error rates above 10%. Consider reviewing error logs and implementing retry logic.",
                    affected_agents=[a.id for a in high_error_agents],
                )
            )

        # Check costs
        if differences["cost"].delta_percent > 50:
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
        if differences["runtime"].delta_percent > 100:
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
            filters.end_date = datetime.utcnow()
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
            timestamp=datetime.utcnow(),
            period_comparison=period_comparison,
        )

    async def _fetch_period_metrics(
        self, start: datetime, end: datetime, period_name: str
    ) -> PeriodMetrics:
        """Fetch metrics for a time period"""

        # Mock implementation
        return PeriodMetrics(
            period=period_name,
            start_date=start,
            end_date=end,
            total_runs=np.random.randint(1000, 10000),
            success_rate=np.random.uniform(85, 99),
            average_runtime=np.random.uniform(500, 3000),
            total_cost=np.random.uniform(100, 5000),
            error_count=np.random.randint(10, 500),
            active_agents=np.random.randint(5, 50),
            active_users=np.random.randint(10, 200),
            throughput=np.random.uniform(20, 100),
            p95_runtime=np.random.uniform(1000, 8000),
            credit_consumption=np.random.uniform(1000, 50000),
        )

    def _calculate_period_changes(
        self, current: PeriodMetrics, previous: PeriodMetrics
    ) -> ChangeMetrics:
        """Calculate changes between periods"""

        def create_change(curr_val: float, prev_val: float, higher_is_better: bool) -> ChangeDetail:
            absolute = curr_val - prev_val
            percent = (absolute / prev_val * 100) if prev_val != 0 else 0

            if abs(percent) < 5:
                trend = TrendDirection.STABLE
            elif absolute > 0:
                trend = TrendDirection.UP
            else:
                trend = TrendDirection.DOWN

            significant = abs(percent) > 10

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
            timestamp=datetime.utcnow(),
            workspace_comparison=workspace_comparison,
        )

    async def _fetch_workspace_metrics(
        self, filters: ComparisonFilters
    ) -> List[WorkspaceMetrics]:
        """Fetch metrics for workspaces"""

        # Mock implementation
        workspaces = []
        workspace_ids = filters.workspace_ids or []

        for ws_id in workspace_ids[:10]:  # Limit to 10 workspaces
            workspaces.append(
                WorkspaceMetrics(
                    workspace_id=ws_id,
                    workspace_name=f"Workspace {ws_id}",
                    total_runs=np.random.randint(500, 15000),
                    success_rate=np.random.uniform(80, 99),
                    average_runtime=np.random.uniform(300, 4000),
                    total_cost=np.random.uniform(50, 3000),
                    active_agents=np.random.randint(3, 30),
                    active_users=np.random.randint(5, 100),
                    credit_usage=np.random.uniform(500, 30000),
                    error_rate=np.random.uniform(1, 20),
                    throughput=np.random.uniform(15, 120),
                    user_satisfaction=np.random.uniform(3.0, 5.0),
                )
            )

        return workspaces

    def _calculate_workspace_benchmarks(
        self, workspaces: List[WorkspaceMetrics]
    ) -> BenchmarkMetrics:
        """Calculate benchmark metrics"""

        avg_success_rate = np.mean([w.success_rate for w in workspaces])
        avg_runtime = np.mean([w.average_runtime for w in workspaces])
        avg_cost = np.mean([w.total_cost for w in workspaces])
        avg_throughput = np.mean([w.throughput for w in workspaces])

        # Calculate composite scores
        scores = {}
        for ws in workspaces:
            score = (
                ws.success_rate * 0.3
                + (100 - min(ws.error_rate, 100)) * 0.2
                + min(ws.throughput / 10, 100) * 0.2
                + (ws.user_satisfaction or 0) * 20 * 0.15
                + max(100 - ws.total_cost / 100, 0) * 0.15
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

        # Calculate scores
        scores = []
        for ws in workspaces:
            score = (
                ws.success_rate * 0.3
                + (100 - min(ws.error_rate, 100)) * 0.2
                + min(ws.throughput / 10, 100) * 0.2
                + (ws.user_satisfaction or 0) * 20 * 0.15
                + max(100 - ws.total_cost / 100, 0) * 0.15
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
            weights={
                "success_rate": 0.3,
                "error_rate": 0.2,
                "throughput": 0.2,
                "user_satisfaction": 0.15,
                "cost": 0.15,
            },
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
            timestamp=datetime.utcnow(),
            metric_comparison=metric_comparison,
        )

    async def _fetch_metric_entities(
        self, metric_name: str, filters: ComparisonFilters
    ) -> List[MetricEntity]:
        """Fetch metric values for entities"""

        # Mock implementation
        entities = []
        entity_count = 20

        values = np.random.normal(75, 15, entity_count)
        values = np.clip(values, 0, 100)

        mean_value = np.mean(values)

        for i, value in enumerate(values):
            percentile = stats.percentileofscore(values, value)
            deviation = value - mean_value

            entities.append(
                MetricEntity(
                    id=f"entity-{i}",
                    name=f"Entity {i}",
                    value=float(value),
                    percentile=float(percentile),
                    deviation_from_mean=float(deviation),
                    trend=np.random.choice(["increasing", "decreasing", "stable"]),
                    sparkline_data=list(np.random.uniform(value - 10, value + 10, 7)),
                )
            )

        return entities

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
            if abs(z_score) > 2:
                outlier_type = OutlierType.HIGH if z_score > 0 else OutlierType.LOW

                if abs(z_score) > 3:
                    severity = OutlierSeverity.EXTREME
                elif abs(z_score) > 2.5:
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
        """Calculate correlations with other metrics"""

        # Mock implementation
        correlations = []

        other_metrics = [
            "average_runtime",
            "error_rate",
            "throughput",
            "cost_per_run",
        ]

        for other_metric in other_metrics:
            if other_metric == metric_name:
                continue

            # Generate mock correlation
            coefficient = np.random.uniform(-0.8, 0.8)
            p_value = np.random.uniform(0, 0.1)

            strength = (
                CorrelationStrength.STRONG
                if abs(coefficient) > 0.7
                else CorrelationStrength.MODERATE
                if abs(coefficient) > 0.4
                else CorrelationStrength.WEAK
            )

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

        return correlations

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
