"""Comprehensive agent analytics service."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Constants for cost and threshold calculations
CREDIT_TO_DOLLAR_RATE = 0.01
MAX_ERROR_MESSAGE_LENGTH = 200
PERFORMANCE_THRESHOLD_SECONDS = 30
TOKEN_USAGE_THRESHOLD = 5000
ERROR_RATE_THRESHOLD_PERCENT = 5
SUCCESS_RATE_THRESHOLD_PERCENT = 90


def calculate_start_date(timeframe: str) -> datetime:
    """Calculate start date based on timeframe."""
    now = datetime.utcnow()

    timeframe_map = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
        "all": timedelta(days=365 * 10),
    }

    return now - timeframe_map.get(timeframe, timedelta(days=7))


def calculate_percentage_change(current: float, previous: float) -> float:
    """Calculate percentage change between two values."""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 2)


class AgentAnalyticsService:
    """Service for comprehensive agent analytics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_agent_analytics(
        self,
        agent_id: str,
        workspace_id: str,
        timeframe: str = "7d",
        skip_cache: bool = False,
    ) -> Dict[str, Any]:
        """Get comprehensive analytics for an agent."""

        end_date = datetime.utcnow()
        start_date = calculate_start_date(timeframe)

        # Parallel fetch all metrics
        results = await asyncio.gather(
            self._get_performance_metrics(agent_id, workspace_id, start_date, end_date),
            self._get_resource_usage(agent_id, workspace_id, start_date, end_date),
            self._get_error_analysis(agent_id, workspace_id, start_date, end_date),
            self._get_user_metrics(agent_id, workspace_id, start_date, end_date),
            self._get_comparison_metrics(agent_id, workspace_id, start_date, end_date),
            self._get_optimization_suggestions(agent_id, workspace_id),
            self._get_trend_data(agent_id, workspace_id, start_date, end_date),
            return_exceptions=True,
        )

        # Handle any errors in parallel execution
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error in analytics component {i}: {result}")
                results[i] = {}

        return {
            "agentId": agent_id,
            "workspaceId": workspace_id,
            "timeframe": timeframe,
            "generatedAt": datetime.utcnow().isoformat(),
            "performance": results[0],
            "resources": results[1],
            "errors": results[2],
            "userMetrics": results[3],
            "comparison": results[4],
            "optimizations": results[5],
            "trends": results[6],
        }

    async def _get_performance_metrics(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Calculate performance metrics."""

        query = text("""
            SELECT
                COUNT(*) as total_runs,
                COUNT(*) FILTER (WHERE status = 'completed') as successful_runs,
                COUNT(*) FILTER (WHERE status = 'failed') as failed_runs,
                COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled_runs,
                AVG(runtime_seconds) as avg_runtime,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY runtime_seconds) as median_runtime,
                MIN(runtime_seconds) as min_runtime,
                MAX(runtime_seconds) as max_runtime,
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY runtime_seconds) as p50,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY runtime_seconds) as p75,
                PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY runtime_seconds) as p90,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY runtime_seconds) as p95,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY runtime_seconds) as p99,
                STDDEV(runtime_seconds) as std_dev,
                MAX(concurrent_runs) as peak_concurrency,
                AVG(concurrent_runs) as avg_concurrency
            FROM analytics.agent_runs
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND started_at BETWEEN :start_date AND :end_date
        """)

        result = await self.db.execute(
            query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        row = result.fetchone()

        if not row or row.total_runs == 0:
            return self._get_empty_performance_metrics()

        success_rate = (row.successful_runs / row.total_runs * 100) if row.total_runs > 0 else 0
        availability_rate = (
            ((row.total_runs - row.failed_runs) / row.total_runs * 100)
            if row.total_runs > 0
            else 0
        )

        # Calculate throughput
        hours_in_period = (end_date - start_date).total_seconds() / 3600
        runs_per_hour = row.total_runs / hours_in_period if hours_in_period > 0 else 0

        return {
            "totalRuns": row.total_runs,
            "successfulRuns": row.successful_runs,
            "failedRuns": row.failed_runs,
            "cancelledRuns": row.cancelled_runs,
            "successRate": round(success_rate, 2),
            "availabilityRate": round(availability_rate, 2),
            "runtime": {
                "average": round(float(row.avg_runtime or 0), 2),
                "median": round(float(row.median_runtime or 0), 2),
                "min": round(float(row.min_runtime or 0), 2),
                "max": round(float(row.max_runtime or 0), 2),
                "p50": round(float(row.p50 or 0), 2),
                "p75": round(float(row.p75 or 0), 2),
                "p90": round(float(row.p90 or 0), 2),
                "p95": round(float(row.p95 or 0), 2),
                "p99": round(float(row.p99 or 0), 2),
                "standardDeviation": round(float(row.std_dev or 0), 2),
            },
            "throughput": {
                "runsPerHour": round(runs_per_hour, 2),
                "runsPerDay": round(runs_per_hour * 24, 2),
                "peakConcurrency": row.peak_concurrency or 0,
                "avgConcurrency": round(float(row.avg_concurrency or 0), 2),
            },
        }

    async def _get_resource_usage(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Calculate resource usage metrics."""

        # Main resource query
        query = text("""
            SELECT
                SUM(credits_consumed) as total_credits,
                AVG(credits_consumed) as avg_credits_per_run,
                SUM(tokens_used) as total_tokens,
                AVG(tokens_used) as avg_tokens_per_run,
                COUNT(*) as total_runs
            FROM analytics.agent_runs
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND started_at BETWEEN :start_date AND :end_date
        """)

        result = await self.db.execute(
            query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        row = result.fetchone()

        if not row or row.total_runs == 0:
            return self._get_empty_resource_metrics()

        # Model usage breakdown
        model_query = text("""
            SELECT
                model_name,
                COUNT(*) as calls,
                SUM(tokens_used) as tokens,
                SUM(credits_consumed) as credits
            FROM analytics.agent_runs
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND started_at BETWEEN :start_date AND :end_date
                AND model_name IS NOT NULL
            GROUP BY model_name
            ORDER BY credits DESC
        """)

        model_result = await self.db.execute(
            model_query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        model_usage = {}
        for model_row in model_result.fetchall():
            model_usage[model_row.model_name] = {
                "calls": model_row.calls,
                "tokens": model_row.tokens or 0,
                "credits": round(float(model_row.credits or 0), 2),
            }

        total_credits = float(row.total_credits or 0)
        avg_credits = float(row.avg_credits_per_run or 0)

        return {
            "totalCreditsConsumed": round(total_credits, 2),
            "avgCreditsPerRun": round(avg_credits, 2),
            "totalTokensUsed": row.total_tokens or 0,
            "avgTokensPerRun": round(float(row.avg_tokens_per_run or 0), 0),
            "costPerRun": round(avg_credits * CREDIT_TO_DOLLAR_RATE, 4),
            "totalCost": round(total_credits * CREDIT_TO_DOLLAR_RATE, 2),
            "modelUsage": model_usage,
        }

    async def _get_error_analysis(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Analyze error patterns and recovery."""

        # Get error breakdown
        error_query = text("""
            SELECT
                error_type,
                error_category,
                error_severity,
                COUNT(*) as count,
                MAX(error_message) as example_message,
                MAX(created_at) as last_occurred,
                AVG(recovery_time_seconds) as avg_recovery_time,
                COUNT(*) FILTER (WHERE auto_recovered = true) as auto_recovered_count
            FROM analytics.agent_errors
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND created_at BETWEEN :start_date AND :end_date
            GROUP BY error_type, error_category, error_severity
            ORDER BY count DESC
            LIMIT 20
        """)

        error_result = await self.db.execute(
            error_query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        errors = error_result.fetchall()
        total_errors = sum(e.count for e in errors)

        errors_by_type = {}
        for error in errors:
            errors_by_type[error.error_type] = {
                "count": error.count,
                "percentage": round((error.count / total_errors * 100) if total_errors > 0 else 0, 2),
                "category": error.error_category,
                "severity": error.error_severity,
                "lastOccurred": error.last_occurred.isoformat() if error.last_occurred else None,
                "exampleMessage": error.example_message[:MAX_ERROR_MESSAGE_LENGTH] if error.example_message else "",
                "avgRecoveryTime": round(float(error.avg_recovery_time or 0), 2),
                "autoRecoveryRate": round(
                    (error.auto_recovered_count / error.count * 100) if error.count > 0 else 0, 2
                ),
            }

        # Error patterns
        patterns = await self._analyze_error_patterns(agent_id, workspace_id, start_date, end_date)

        # Recovery metrics
        recovery_query = text("""
            SELECT
                AVG(recovery_time_seconds) as mttr,
                COUNT(*) FILTER (WHERE auto_recovered = true) as auto_recovered,
                COUNT(*) as total_errors
            FROM analytics.agent_errors
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND created_at BETWEEN :start_date AND :end_date
        """)

        recovery_result = await self.db.execute(
            recovery_query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        recovery = recovery_result.fetchone()

        # Calculate error rate
        total_runs_query = text("""
            SELECT COUNT(*) as total_runs
            FROM analytics.agent_runs
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND started_at BETWEEN :start_date AND :end_date
        """)
        runs_result = await self.db.execute(
            total_runs_query,
            {"agent_id": agent_id, "workspace_id": workspace_id, "start_date": start_date, "end_date": end_date},
        )
        total_runs = runs_result.fetchone().total_runs

        error_rate = (total_errors / total_runs * 100) if total_runs > 0 else 0

        return {
            "totalErrors": total_errors,
            "errorRate": round(error_rate, 2),
            "errorsByType": errors_by_type,
            "errorPatterns": patterns,
            "meanTimeToRecovery": round(float(recovery.mttr or 0), 2) if recovery else 0,
            "autoRecoveryRate": round(
                (recovery.auto_recovered / recovery.total_errors * 100)
                if recovery and recovery.total_errors > 0
                else 0,
                2,
            ),
        }

    async def _analyze_error_patterns(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Analyze error patterns and suggest fixes."""

        # Get common error patterns
        pattern_query = text("""
            SELECT
                error_category,
                error_severity,
                COUNT(*) as frequency,
                AVG(CASE WHEN business_impact = 'high' THEN 3
                         WHEN business_impact = 'medium' THEN 2
                         ELSE 1 END) as avg_impact
            FROM analytics.agent_errors
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND created_at BETWEEN :start_date AND :end_date
            GROUP BY error_category, error_severity
            HAVING COUNT(*) >= 3
            ORDER BY frequency DESC
            LIMIT 5
        """)

        result = await self.db.execute(
            pattern_query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        patterns = []
        impact_map = {1: "low", 2: "medium", 3: "high"}

        for row in result.fetchall():
            suggested_fix = self._get_error_fix_suggestion(row.error_category)
            patterns.append(
                {
                    "pattern": f"{row.error_category} ({row.error_severity} severity)",
                    "frequency": row.frequency,
                    "impact": impact_map.get(round(row.avg_impact), "medium"),
                    "suggestedFix": suggested_fix,
                }
            )

        return patterns

    def _get_error_fix_suggestion(self, error_category: str) -> str:
        """Get suggested fix for error category."""
        suggestions = {
            "timeout": "Increase timeout threshold or optimize agent processing logic",
            "rate_limit": "Implement exponential backoff or request queuing",
            "validation": "Add input validation and sanitization",
            "model_error": "Add fallback models or retry logic",
            "network": "Implement connection pooling and retry with backoff",
            "auth": "Refresh authentication tokens automatically",
            "resource": "Scale resources or implement rate limiting",
            "user_error": "Improve error messages and user documentation",
        }
        return suggestions.get(error_category, "Review error logs and implement appropriate error handling")

    async def _get_user_metrics(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Calculate user interaction metrics."""

        # User interaction query
        user_query = text("""
            SELECT
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(*) as total_interactions,
                COUNT(user_rating) as total_ratings,
                AVG(user_rating) as avg_rating,
                COUNT(*) FILTER (WHERE user_rating = 5) as rating_5,
                COUNT(*) FILTER (WHERE user_rating = 4) as rating_4,
                COUNT(*) FILTER (WHERE user_rating = 3) as rating_3,
                COUNT(*) FILTER (WHERE user_rating = 2) as rating_2,
                COUNT(*) FILTER (WHERE user_rating = 1) as rating_1
            FROM analytics.agent_runs
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND started_at BETWEEN :start_date AND :end_date
        """)

        result = await self.db.execute(
            user_query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        row = result.fetchone()

        if not row:
            return self._get_empty_user_metrics()

        # Usage by hour
        usage_by_hour = await self._get_usage_by_hour(agent_id, workspace_id, start_date, end_date)

        # Usage by day of week
        usage_by_day = await self._get_usage_by_day_of_week(agent_id, workspace_id, start_date, end_date)

        # Top users
        top_users = await self._get_top_users(agent_id, workspace_id, start_date, end_date)

        # Recent feedback
        feedback = await self._get_recent_feedback(agent_id, workspace_id, 10)

        avg_interactions_per_user = (
            row.total_interactions / row.unique_users if row.unique_users > 0 else 0
        )

        return {
            "uniqueUsers": row.unique_users or 0,
            "totalInteractions": row.total_interactions or 0,
            "avgInteractionsPerUser": round(avg_interactions_per_user, 2),
            "userRatings": {
                "average": round(float(row.avg_rating or 0), 2),
                "total": row.total_ratings or 0,
                "distribution": {
                    "5": row.rating_5 or 0,
                    "4": row.rating_4 or 0,
                    "3": row.rating_3 or 0,
                    "2": row.rating_2 or 0,
                    "1": row.rating_1 or 0,
                },
            },
            "feedback": feedback,
            "usageByHour": usage_by_hour,
            "usageByDayOfWeek": usage_by_day,
            "topUsers": top_users,
        }

    async def _get_usage_by_hour(
        self, agent_id: str, workspace_id: str, start_date: datetime, end_date: datetime
    ) -> List[int]:
        """Get usage distribution by hour of day."""
        query = text("""
            SELECT
                EXTRACT(HOUR FROM started_at) as hour,
                COUNT(*) as count
            FROM analytics.agent_runs
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND started_at BETWEEN :start_date AND :end_date
            GROUP BY EXTRACT(HOUR FROM started_at)
            ORDER BY hour
        """)

        result = await self.db.execute(
            query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        usage = [0] * 24
        for row in result.fetchall():
            usage[int(row.hour)] = row.count

        return usage

    async def _get_usage_by_day_of_week(
        self, agent_id: str, workspace_id: str, start_date: datetime, end_date: datetime
    ) -> List[int]:
        """Get usage distribution by day of week."""
        query = text("""
            SELECT
                EXTRACT(DOW FROM started_at) as dow,
                COUNT(*) as count
            FROM analytics.agent_runs
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND started_at BETWEEN :start_date AND :end_date
            GROUP BY EXTRACT(DOW FROM started_at)
            ORDER BY dow
        """)

        result = await self.db.execute(
            query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        usage = [0] * 7
        for row in result.fetchall():
            usage[int(row.dow)] = row.count

        return usage

    async def _get_top_users(
        self, agent_id: str, workspace_id: str, start_date: datetime, end_date: datetime, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top users by run count."""
        query = text("""
            SELECT
                user_id,
                COUNT(*) as run_count,
                COUNT(*) FILTER (WHERE status = 'completed') as successful_runs,
                ROUND(COUNT(*) FILTER (WHERE status = 'completed')::NUMERIC / COUNT(*) * 100, 2) as success_rate
            FROM analytics.agent_runs
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND started_at BETWEEN :start_date AND :end_date
            GROUP BY user_id
            ORDER BY run_count DESC
            LIMIT :limit
        """)

        result = await self.db.execute(
            query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit,
            },
        )

        return [
            {
                "userId": str(row.user_id),
                "runCount": row.run_count,
                "successRate": float(row.success_rate or 0),
            }
            for row in result.fetchall()
        ]

    async def _get_recent_feedback(
        self, agent_id: str, workspace_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent user feedback."""
        query = text("""
            SELECT
                user_id,
                rating,
                comment,
                created_at
            FROM analytics.agent_user_feedback
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND comment IS NOT NULL
            ORDER BY created_at DESC
            LIMIT :limit
        """)

        result = await self.db.execute(
            query,
            {"agent_id": agent_id, "workspace_id": workspace_id, "limit": limit},
        )

        return [
            {
                "userId": str(row.user_id),
                "rating": row.rating,
                "comment": row.comment,
                "timestamp": row.created_at.isoformat(),
            }
            for row in result.fetchall()
        ]

    async def _get_comparison_metrics(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Get comparative analysis metrics."""

        # Get workspace average
        workspace_avg_query = text("""
            SELECT
                AVG(success_rate) as avg_success_rate,
                AVG(avg_runtime) as avg_runtime,
                AVG(total_credits / NULLIF(total_runs, 0)) as avg_credits_per_run
            FROM analytics.agent_analytics_summary
            WHERE workspace_id = :workspace_id
                AND metric_date BETWEEN :start_date AND :end_date
        """)

        workspace_result = await self.db.execute(
            workspace_avg_query,
            {"workspace_id": workspace_id, "start_date": start_date.date(), "end_date": end_date.date()},
        )
        workspace_avg = workspace_result.fetchone()

        # Get current agent metrics for comparison
        agent_query = text("""
            SELECT
                AVG(success_rate) as success_rate,
                AVG(avg_runtime) as avg_runtime,
                AVG(total_credits / NULLIF(total_runs, 0)) as credits_per_run
            FROM analytics.agent_analytics_summary
            WHERE agent_id = :agent_id
                AND metric_date BETWEEN :start_date AND :end_date
        """)

        agent_result = await self.db.execute(
            agent_query,
            {"agent_id": agent_id, "start_date": start_date.date(), "end_date": end_date.date()},
        )
        agent_metrics = agent_result.fetchone()

        # Calculate vs workspace average
        vs_workspace = {}
        if workspace_avg and agent_metrics:
            vs_workspace = {
                "successRate": calculate_percentage_change(
                    float(agent_metrics.success_rate or 0),
                    float(workspace_avg.avg_success_rate or 0),
                ),
                "runtime": calculate_percentage_change(
                    float(agent_metrics.avg_runtime or 0),
                    float(workspace_avg.avg_runtime or 0),
                ),
                "creditEfficiency": calculate_percentage_change(
                    float(agent_metrics.credits_per_run or 0),
                    float(workspace_avg.avg_credits_per_run or 0),
                ),
            }

        # Get ranking
        rank_query = text("""
            WITH agent_ranks AS (
                SELECT
                    agent_id,
                    AVG(success_rate) as avg_success_rate,
                    RANK() OVER (ORDER BY AVG(success_rate) DESC) as rank,
                    COUNT(*) OVER () as total_agents
                FROM analytics.agent_analytics_summary
                WHERE workspace_id = :workspace_id
                    AND metric_date BETWEEN :start_date AND :end_date
                GROUP BY agent_id
            )
            SELECT rank, total_agents
            FROM agent_ranks
            WHERE agent_id = :agent_id
        """)

        rank_result = await self.db.execute(
            rank_query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date.date(),
                "end_date": end_date.date(),
            },
        )
        rank_row = rank_result.fetchone()

        vs_all_agents = {}
        if rank_row:
            vs_all_agents = {
                "rank": rank_row.rank,
                "percentile": round(
                    ((rank_row.total_agents - rank_row.rank + 1) / rank_row.total_agents * 100)
                    if rank_row.total_agents > 0
                    else 0,
                    2,
                ),
            }

        # Get previous period comparison
        period_length = end_date - start_date
        prev_start = start_date - period_length
        prev_end = start_date

        prev_query = text("""
            SELECT
                SUM(total_runs) as total_runs,
                AVG(success_rate) as success_rate,
                AVG(avg_runtime) as avg_runtime,
                SUM(total_credits) as total_credits
            FROM analytics.agent_analytics_summary
            WHERE agent_id = :agent_id
                AND metric_date BETWEEN :prev_start AND :prev_end
        """)

        prev_result = await self.db.execute(
            prev_query,
            {"agent_id": agent_id, "prev_start": prev_start.date(), "prev_end": prev_end.date()},
        )
        prev_metrics = prev_result.fetchone()

        curr_query = text("""
            SELECT
                SUM(total_runs) as total_runs,
                AVG(success_rate) as success_rate,
                AVG(avg_runtime) as avg_runtime,
                SUM(total_credits) as total_credits
            FROM analytics.agent_analytics_summary
            WHERE agent_id = :agent_id
                AND metric_date BETWEEN :start_date AND :end_date
        """)

        curr_result = await self.db.execute(
            curr_query,
            {"agent_id": agent_id, "start_date": start_date.date(), "end_date": end_date.date()},
        )
        curr_metrics = curr_result.fetchone()

        vs_previous = {}
        if prev_metrics and curr_metrics:
            vs_previous = {
                "runsChange": calculate_percentage_change(
                    curr_metrics.total_runs or 0,
                    prev_metrics.total_runs or 0,
                ),
                "successRateChange": calculate_percentage_change(
                    float(curr_metrics.success_rate or 0),
                    float(prev_metrics.success_rate or 0),
                ),
                "runtimeChange": calculate_percentage_change(
                    float(curr_metrics.avg_runtime or 0),
                    float(prev_metrics.avg_runtime or 0),
                ),
                "costChange": calculate_percentage_change(
                    float(curr_metrics.total_credits or 0),
                    float(prev_metrics.total_credits or 0),
                ),
            }

        return {
            "vsWorkspaceAverage": vs_workspace,
            "vsAllAgents": vs_all_agents,
            "vsPreviousPeriod": vs_previous,
        }

    async def _get_optimization_suggestions(
        self, agent_id: str, workspace_id: str
    ) -> List[Dict[str, Any]]:
        """Get optimization suggestions for the agent."""

        # Get active suggestions from database
        query = text("""
            SELECT
                suggestion_type,
                title,
                description,
                estimated_impact,
                effort_level,
                priority
            FROM analytics.agent_optimization_suggestions
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND status = 'active'
            ORDER BY priority DESC
            LIMIT 10
        """)

        result = await self.db.execute(
            query,
            {"agent_id": agent_id, "workspace_id": workspace_id},
        )

        suggestions = [
            {
                "type": row.suggestion_type,
                "title": row.title,
                "description": row.description,
                "estimatedImpact": row.estimated_impact,
                "effort": row.effort_level,
            }
            for row in result.fetchall()
        ]

        # If no stored suggestions, generate some based on metrics
        if not suggestions:
            suggestions = await self._generate_optimization_suggestions(agent_id, workspace_id)

        return suggestions

    async def _generate_optimization_suggestions(
        self, agent_id: str, workspace_id: str
    ) -> List[Dict[str, Any]]:
        """Generate optimization suggestions based on current metrics."""

        # Get recent stats
        stats_query = text("""
            SELECT
                AVG(avg_runtime) as avg_runtime,
                AVG(success_rate) as success_rate,
                AVG(total_credits / NULLIF(total_runs, 0)) as avg_credits_per_run,
                AVG(avg_tokens_per_run) as avg_tokens_per_run,
                SUM(total_errors) as total_errors,
                SUM(total_runs) as total_runs
            FROM analytics.agent_analytics_summary
            WHERE agent_id = :agent_id
                AND metric_date >= CURRENT_DATE - INTERVAL '7 days'
        """)

        result = await self.db.execute(
            stats_query,
            {"agent_id": agent_id},
        )
        stats = result.fetchone()

        suggestions = []

        if stats:
            # Performance suggestions
            if float(stats.avg_runtime or 0) > PERFORMANCE_THRESHOLD_SECONDS:
                suggestions.append(
                    {
                        "type": "performance",
                        "title": "Reduce execution time",
                        "description": f"Average runtime exceeds {PERFORMANCE_THRESHOLD_SECONDS} seconds. Consider optimizing prompts, caching results, or breaking into smaller tasks.",
                        "estimatedImpact": "20-30% runtime reduction",
                        "effort": "medium",
                    }
                )

            # Cost suggestions
            if float(stats.avg_tokens_per_run or 0) > TOKEN_USAGE_THRESHOLD:
                suggestions.append(
                    {
                        "type": "cost",
                        "title": "Optimize token usage",
                        "description": f"High token consumption detected (>{TOKEN_USAGE_THRESHOLD} tokens). Use more concise prompts, implement response caching, or switch to a more efficient model.",
                        "estimatedImpact": "15-25% cost reduction",
                        "effort": "low",
                    }
                )

            # Reliability suggestions
            error_rate = (
                (stats.total_errors / stats.total_runs * 100) if stats.total_runs > 0 else 0
            )
            if error_rate > ERROR_RATE_THRESHOLD_PERCENT:
                suggestions.append(
                    {
                        "type": "reliability",
                        "title": "Improve error handling",
                        "description": f"Error rate is {error_rate:.1f}%. Implement retry logic, add input validation, and improve error recovery mechanisms.",
                        "estimatedImpact": "50% error reduction",
                        "effort": "low",
                    }
                )

            # Success rate suggestions
            if float(stats.success_rate or 0) < SUCCESS_RATE_THRESHOLD_PERCENT:
                suggestions.append(
                    {
                        "type": "reliability",
                        "title": "Increase success rate",
                        "description": "Success rate below 90%. Review failed executions, add better error handling, and validate inputs.",
                        "estimatedImpact": "10-15% success rate improvement",
                        "effort": "medium",
                    }
                )

        return suggestions

    async def _get_trend_data(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Get time series trend data."""

        # Daily trends
        daily_query = text("""
            SELECT
                metric_date as timestamp,
                total_runs as runs,
                success_rate,
                avg_runtime,
                total_credits as credits,
                total_errors as errors
            FROM analytics.agent_analytics_summary
            WHERE agent_id = :agent_id
                AND metric_date BETWEEN :start_date AND :end_date
            ORDER BY metric_date
        """)

        daily_result = await self.db.execute(
            daily_query,
            {"agent_id": agent_id, "start_date": start_date.date(), "end_date": end_date.date()},
        )

        daily_trends = [
            {
                "timestamp": row.timestamp.isoformat(),
                "runs": row.runs or 0,
                "successRate": round(float(row.success_rate or 0), 2),
                "avgRuntime": round(float(row.avg_runtime or 0), 2),
                "credits": round(float(row.credits or 0), 2),
                "errors": row.errors or 0,
            }
            for row in daily_result.fetchall()
        ]

        # Hourly trends (last 48 hours only for performance)
        hourly_start = end_date - timedelta(hours=48)
        hourly_query = text("""
            SELECT
                metric_hour as timestamp,
                total_runs as runs,
                ROUND(successful_runs::NUMERIC / NULLIF(total_runs, 0) * 100, 2) as success_rate,
                avg_runtime_seconds as avg_runtime,
                total_credits as credits,
                total_errors as errors
            FROM analytics.agent_performance_hourly
            WHERE agent_id = :agent_id
                AND metric_hour >= :hourly_start
            ORDER BY metric_hour
        """)

        hourly_result = await self.db.execute(
            hourly_query,
            {"agent_id": agent_id, "hourly_start": hourly_start},
        )

        hourly_trends = [
            {
                "timestamp": row.timestamp.isoformat(),
                "runs": row.runs or 0,
                "successRate": float(row.success_rate or 0),
                "avgRuntime": round(float(row.avg_runtime or 0), 2),
                "credits": round(float(row.credits or 0), 2),
                "errors": row.errors or 0,
            }
            for row in hourly_result.fetchall()
        ]

        return {
            "daily": daily_trends,
            "hourly": hourly_trends,
        }

    # Helper methods for empty metrics
    def _get_empty_performance_metrics(self) -> Dict[str, Any]:
        """Return empty performance metrics structure."""
        return {
            "totalRuns": 0,
            "successfulRuns": 0,
            "failedRuns": 0,
            "cancelledRuns": 0,
            "successRate": 0.0,
            "availabilityRate": 0.0,
            "runtime": {
                "average": 0.0,
                "median": 0.0,
                "min": 0.0,
                "max": 0.0,
                "p50": 0.0,
                "p75": 0.0,
                "p90": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "standardDeviation": 0.0,
            },
            "throughput": {
                "runsPerHour": 0.0,
                "runsPerDay": 0.0,
                "peakConcurrency": 0,
                "avgConcurrency": 0.0,
            },
        }

    def _get_empty_resource_metrics(self) -> Dict[str, Any]:
        """Return empty resource metrics structure."""
        return {
            "totalCreditsConsumed": 0.0,
            "avgCreditsPerRun": 0.0,
            "totalTokensUsed": 0,
            "avgTokensPerRun": 0.0,
            "costPerRun": 0.0,
            "totalCost": 0.0,
            "modelUsage": {},
        }

    def _get_empty_user_metrics(self) -> Dict[str, Any]:
        """Return empty user metrics structure."""
        return {
            "uniqueUsers": 0,
            "totalInteractions": 0,
            "avgInteractionsPerUser": 0.0,
            "userRatings": {
                "average": 0.0,
                "total": 0,
                "distribution": {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0},
            },
            "feedback": [],
            "usageByHour": [0] * 24,
            "usageByDayOfWeek": [0] * 7,
            "topUsers": [],
        }
