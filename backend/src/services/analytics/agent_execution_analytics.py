"""Agent execution analytics service."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, text
from ..cache import cached, CacheKeys
from ...utils.calculations import calculate_percentage_change
from ...utils.datetime import calculate_start_date

logger = logging.getLogger(__name__)

# Constants
QUERY_TIMEOUT_SECONDS = 30
MAX_RECENT_EXECUTIONS = 20
MAX_BOTTLENECKS = 10
MAX_EXECUTION_PATHS = 10


class AgentExecutionAnalyticsService:
    """Service for agent execution analytics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _execute_with_timeout(self, query, params: dict = None):
        """Execute query with timeout protection."""
        try:
            timeout_query = text(f"SET LOCAL statement_timeout = '{QUERY_TIMEOUT_SECONDS}s'")
            await self.db.execute(timeout_query)
            if params:
                result = await self.db.execute(query, params)
            else:
                result = await self.db.execute(query)
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}", exc_info=True)
            raise

    async def get_execution_analytics(
        self,
        agent_id: str,
        workspace_id: str,
        timeframe: str = "7d",
        skip_cache: bool = False,
    ) -> Dict[str, Any]:
        """Get comprehensive execution analytics for an agent."""

        # Validate UUID format
        try:
            uuid.UUID(agent_id)
            uuid.UUID(workspace_id)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid UUID format: {str(e)}")

        end_date = datetime.utcnow()
        start_date = calculate_start_date(timeframe)

        # Parallel fetch all metrics
        try:
            results = await asyncio.gather(
                self._get_execution_summary(agent_id, workspace_id, start_date, end_date),
                self._get_execution_trends(agent_id, workspace_id, start_date, end_date, timeframe),
                self._get_performance_metrics(agent_id, workspace_id, start_date, end_date),
                self._get_failure_analysis(agent_id, workspace_id, start_date, end_date),
                self._get_pattern_analysis(agent_id, workspace_id, start_date, end_date),
                self._get_recent_executions(agent_id, workspace_id, start_date, end_date),
                return_exceptions=True,
            )
        except Exception as e:
            logger.error(f"Critical error fetching execution analytics: {str(e)}", exc_info=True)
            raise

        # Handle errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error in execution analytics component {i}: {result}", exc_info=True)
                if i < 4:  # First 4 components are critical
                    raise result
                results[i] = {} if i == 4 else []

        return {
            "agentId": agent_id,
            "workspaceId": workspace_id,
            "timeframe": timeframe,
            "generatedAt": datetime.utcnow().isoformat(),
            "summary": results[0],
            "trends": results[1],
            "performance": results[2],
            "failureAnalysis": results[3],
            "patterns": results[4],
            "recentExecutions": results[5],
        }

    async def _get_execution_summary(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Get execution summary statistics."""

        query = text("""
            SELECT
                COUNT(*) as total_executions,
                COUNT(*) FILTER (WHERE status = 'success') as successful_executions,
                COUNT(*) FILTER (WHERE status = 'failed') as failed_executions,
                COUNT(*) FILTER (WHERE status = 'timeout') as timeout_executions,
                AVG(duration_ms) as avg_duration_ms,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as median_duration_ms,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_duration_ms,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) as p99_duration_ms,
                SUM(credits_consumed) as total_credits_consumed,
                AVG(credits_consumed) as avg_credits_per_execution
            FROM analytics.agent_executions
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND start_time >= :start_date
                AND start_time < :end_date
        """)

        result = await self._execute_with_timeout(
            query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        row = result.fetchone()

        if not row or row.total_executions == 0:
            return {
                "totalExecutions": 0,
                "successfulExecutions": 0,
                "failedExecutions": 0,
                "timeoutExecutions": 0,
                "successRate": 0.0,
                "avgDurationMs": 0.0,
                "medianDurationMs": 0.0,
                "p95DurationMs": 0.0,
                "p99DurationMs": 0.0,
                "totalCreditsConsumed": 0,
                "avgCreditsPerExecution": 0.0,
            }

        success_rate = (row.successful_executions / row.total_executions * 100) if row.total_executions > 0 else 0.0

        return {
            "totalExecutions": row.total_executions or 0,
            "successfulExecutions": row.successful_executions or 0,
            "failedExecutions": row.failed_executions or 0,
            "timeoutExecutions": row.timeout_executions or 0,
            "successRate": round(success_rate, 2),
            "avgDurationMs": round(row.avg_duration_ms or 0.0, 2),
            "medianDurationMs": round(row.median_duration_ms or 0.0, 2),
            "p95DurationMs": round(row.p95_duration_ms or 0.0, 2),
            "p99DurationMs": round(row.p99_duration_ms or 0.0, 2),
            "totalCreditsConsumed": row.total_credits_consumed or 0,
            "avgCreditsPerExecution": round(row.avg_credits_per_execution or 0.0, 2),
        }

    async def _get_execution_trends(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str,
    ) -> List[Dict[str, Any]]:
        """Get execution trends over time."""

        # Determine aggregation interval based on timeframe
        if timeframe == "24h":
            interval = "1 hour"
            date_trunc = "hour"
        elif timeframe in ["7d", "30d"]:
            interval = "1 day"
            date_trunc = "day"
        else:
            interval = "1 week"
            date_trunc = "week"

        query = text(f"""
            SELECT
                DATE_TRUNC(:date_trunc, start_time) as timestamp,
                COUNT(*) as execution_count,
                COUNT(*) FILTER (WHERE status = 'success') as success_count,
                COUNT(*) FILTER (WHERE status = 'failed') as failure_count,
                AVG(duration_ms) as avg_duration,
                SUM(credits_consumed) as credits_used
            FROM analytics.agent_executions
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND start_time >= :start_date
                AND start_time < :end_date
            GROUP BY DATE_TRUNC(:date_trunc, start_time)
            ORDER BY timestamp
        """)

        result = await self._execute_with_timeout(
            query,
            {
                "date_trunc": date_trunc,
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        trends = []
        for row in result:
            success_rate = (row.success_count / row.execution_count * 100) if row.execution_count > 0 else 0.0
            trends.append({
                "timestamp": row.timestamp.isoformat(),
                "executionCount": row.execution_count or 0,
                "successRate": round(success_rate, 2),
                "avgDuration": round(row.avg_duration or 0.0, 2),
                "failureCount": row.failure_count or 0,
                "creditsUsed": row.credits_used or 0,
            })

        return trends

    async def _get_performance_metrics(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Get detailed performance metrics."""

        query = text("""
            SELECT
                AVG(duration_ms) as avg_duration_ms,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as median_duration_ms,
                MIN(duration_ms) as min_duration_ms,
                MAX(duration_ms) as max_duration_ms,
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY duration_ms) as p50_duration_ms,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY duration_ms) as p75_duration_ms,
                PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY duration_ms) as p90_duration_ms,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_duration_ms,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) as p99_duration_ms,
                STDDEV(duration_ms) as std_deviation
            FROM analytics.agent_executions
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND start_time >= :start_date
                AND start_time < :end_date
                AND duration_ms IS NOT NULL
        """)

        result = await self._execute_with_timeout(
            query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        row = result.fetchone()

        if not row:
            return {
                "avgDurationMs": 0.0,
                "medianDurationMs": 0.0,
                "minDurationMs": 0.0,
                "maxDurationMs": 0.0,
                "p50DurationMs": 0.0,
                "p75DurationMs": 0.0,
                "p90DurationMs": 0.0,
                "p95DurationMs": 0.0,
                "p99DurationMs": 0.0,
                "stdDeviation": 0.0,
            }

        return {
            "avgDurationMs": round(row.avg_duration_ms or 0.0, 2),
            "medianDurationMs": round(row.median_duration_ms or 0.0, 2),
            "minDurationMs": round(row.min_duration_ms or 0.0, 2),
            "maxDurationMs": round(row.max_duration_ms or 0.0, 2),
            "p50DurationMs": round(row.p50_duration_ms or 0.0, 2),
            "p75DurationMs": round(row.p75_duration_ms or 0.0, 2),
            "p90DurationMs": round(row.p90_duration_ms or 0.0, 2),
            "p95DurationMs": round(row.p95_duration_ms or 0.0, 2),
            "p99DurationMs": round(row.p99_duration_ms or 0.0, 2),
            "stdDeviation": round(row.std_deviation or 0.0, 2),
        }

    async def _get_failure_analysis(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Get failure analysis metrics."""

        # Get failure statistics by type
        query = text("""
            SELECT
                error_type,
                COUNT(*) as count,
                AVG(duration_ms) as avg_duration_before_failure,
                MAX(start_time) as last_occurred,
                (SELECT error_message
                 FROM analytics.agent_executions
                 WHERE agent_id = :agent_id
                     AND error_type = ae.error_type
                     AND error_message IS NOT NULL
                 LIMIT 1) as example_message
            FROM analytics.agent_executions ae
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND start_time >= :start_date
                AND start_time < :end_date
                AND status = 'failed'
            GROUP BY error_type
            ORDER BY count DESC
            LIMIT 10
        """)

        result = await self._execute_with_timeout(
            query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        # Get total failures
        total_query = text("""
            SELECT COUNT(*) as total_failures,
                   COUNT(*) as total_executions
            FROM analytics.agent_executions
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND start_time >= :start_date
                AND start_time < :end_date
        """)

        total_result = await self._execute_with_timeout(
            total_query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        total_row = total_result.fetchone()
        total_failures = total_row.total_failures if total_row else 0
        total_executions = total_row.total_executions if total_row else 1

        failures_by_type = []
        for row in result:
            percentage = (row.count / total_failures * 100) if total_failures > 0 else 0.0
            failures_by_type.append({
                "errorType": row.error_type or "Unknown",
                "count": row.count,
                "percentage": round(percentage, 2),
                "avgDurationBeforeFailure": round(row.avg_duration_before_failure or 0.0, 2),
                "lastOccurred": row.last_occurred.isoformat() if row.last_occurred else None,
                "exampleMessage": row.example_message[:200] if row.example_message else None,
            })

        failure_rate = (total_failures / total_executions * 100) if total_executions > 0 else 0.0

        return {
            "totalFailures": total_failures,
            "failureRate": round(failure_rate, 2),
            "failuresByType": failures_by_type,
            "commonPatterns": [],  # Can be enhanced with ML pattern detection
        }

    async def _get_pattern_analysis(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Get execution pattern analysis."""

        # Hourly patterns
        hourly_query = text("""
            SELECT
                EXTRACT(HOUR FROM start_time) as hour,
                COUNT(*) as execution_count,
                AVG(duration_ms) as avg_duration_ms,
                AVG(CASE WHEN status = 'success' THEN 1 ELSE 0 END) * 100 as success_rate
            FROM analytics.agent_executions
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND start_time >= :start_date
                AND start_time < :end_date
            GROUP BY EXTRACT(HOUR FROM start_time)
            ORDER BY hour
        """)

        hourly_result = await self._execute_with_timeout(
            hourly_query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        hourly_patterns = []
        for row in hourly_result:
            hourly_patterns.append({
                "hour": int(row.hour),
                "executionCount": row.execution_count,
                "avgDurationMs": round(row.avg_duration_ms or 0.0, 2),
                "successRate": round(row.success_rate or 0.0, 2),
            })

        # Get bottlenecks from execution_steps
        bottlenecks_query = text("""
            SELECT
                s.step_name,
                AVG(s.duration_ms) as avg_duration_ms,
                STDDEV(s.duration_ms) as duration_variance,
                COUNT(*) as execution_count,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY s.duration_ms) as p95_duration_ms,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY s.duration_ms) as p99_duration_ms
            FROM analytics.execution_steps s
            JOIN analytics.agent_executions e ON s.execution_id = e.execution_id
            WHERE e.agent_id = :agent_id
                AND e.workspace_id = :workspace_id
                AND e.start_time >= :start_date
                AND e.start_time < :end_date
            GROUP BY s.step_name
            HAVING AVG(s.duration_ms) > 1000
            ORDER BY avg_duration_ms DESC
            LIMIT :limit
        """)

        bottlenecks_result = await self._execute_with_timeout(
            bottlenecks_query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
                "limit": MAX_BOTTLENECKS,
            },
        )

        bottlenecks = []
        for row in bottlenecks_result:
            # Calculate impact score (0-100) based on avg duration and frequency
            impact_score = min(100, (row.avg_duration_ms / 1000) * (row.execution_count / 10))

            # Determine priority
            if impact_score > 75:
                priority = "critical"
            elif impact_score > 50:
                priority = "high"
            elif impact_score > 25:
                priority = "medium"
            else:
                priority = "low"

            bottlenecks.append({
                "stepName": row.step_name,
                "avgDurationMs": int(row.avg_duration_ms or 0),
                "durationVariance": round(row.duration_variance or 0.0, 2),
                "executionCount": row.execution_count,
                "p95DurationMs": int(row.p95_duration_ms or 0),
                "p99DurationMs": int(row.p99_duration_ms or 0),
                "impactScore": round(impact_score, 2),
                "optimizationPriority": priority,
            })

        # Generate optimization suggestions
        suggestions = self._generate_optimization_suggestions(hourly_patterns, bottlenecks)

        return {
            "hourlyPatterns": hourly_patterns,
            "executionPaths": [],  # Can be enhanced with path tracking
            "bottlenecks": bottlenecks,
            "optimizationSuggestions": suggestions,
        }

    def _generate_optimization_suggestions(
        self,
        hourly_patterns: List[Dict],
        bottlenecks: List[Dict],
    ) -> List[str]:
        """Generate optimization suggestions based on patterns."""
        suggestions = []

        # Check for peak hour optimization
        if hourly_patterns:
            max_executions = max(p["executionCount"] for p in hourly_patterns)
            peak_hours = [p for p in hourly_patterns if p["executionCount"] > max_executions * 0.8]
            if peak_hours:
                hours_str = ", ".join(f"{p['hour']:02d}:00" for p in peak_hours)
                suggestions.append(
                    f"Consider scaling resources during peak hours: {hours_str}"
                )

        # Check for bottlenecks
        critical_bottlenecks = [b for b in bottlenecks if b["optimizationPriority"] in ["critical", "high"]]
        if critical_bottlenecks:
            for bottleneck in critical_bottlenecks[:3]:
                suggestions.append(
                    f"Optimize step '{bottleneck['stepName']}' - "
                    f"averaging {bottleneck['avgDurationMs']}ms ({bottleneck['optimizationPriority']} priority)"
                )

        # Check for high variance
        high_variance = [b for b in bottlenecks if b["durationVariance"] > b["avgDurationMs"] * 0.5]
        if high_variance:
            suggestions.append(
                "Investigate high duration variance in execution steps for consistency improvements"
            )

        return suggestions

    async def _get_recent_executions(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Get recent execution details."""

        query = text("""
            SELECT
                execution_id,
                agent_id,
                workspace_id,
                user_id,
                trigger_type,
                status,
                start_time,
                end_time,
                duration_ms,
                credits_consumed,
                error_message,
                error_type,
                steps_total,
                steps_completed
            FROM analytics.agent_executions
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND start_time >= :start_date
                AND start_time < :end_date
            ORDER BY start_time DESC
            LIMIT :limit
        """)

        result = await self._execute_with_timeout(
            query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
                "limit": MAX_RECENT_EXECUTIONS,
            },
        )

        executions = []
        for row in result:
            executions.append({
                "executionId": row.execution_id,
                "agentId": row.agent_id,
                "workspaceId": row.workspace_id,
                "userId": row.user_id,
                "triggerType": row.trigger_type,
                "status": row.status,
                "startTime": row.start_time.isoformat() if row.start_time else None,
                "endTime": row.end_time.isoformat() if row.end_time else None,
                "durationMs": row.duration_ms,
                "creditsConsumed": row.credits_consumed,
                "errorMessage": row.error_message,
                "errorType": row.error_type,
                "stepsTotal": row.steps_total,
                "stepsCompleted": row.steps_completed,
            })

        return executions

    async def get_workspace_execution_analytics(
        self,
        workspace_id: str,
        timeframe: str = "7d",
    ) -> Dict[str, Any]:
        """Get workspace-level execution analytics."""

        try:
            uuid.UUID(workspace_id)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid UUID format: {str(e)}")

        end_date = datetime.utcnow()
        start_date = calculate_start_date(timeframe)

        # Get workspace summary
        summary_query = text("""
            SELECT
                COUNT(*) as total_executions,
                AVG(CASE WHEN status = 'success' THEN 1 ELSE 0 END) * 100 as success_rate,
                AVG(duration_ms) as avg_duration_ms,
                SUM(credits_consumed) as total_credits,
                COUNT(DISTINCT agent_id) as active_agents
            FROM analytics.agent_executions
            WHERE workspace_id = :workspace_id
                AND start_time >= :start_date
                AND start_time < :end_date
        """)

        summary_result = await self._execute_with_timeout(
            summary_query,
            {
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        summary_row = summary_result.fetchone()

        # Get top agents
        top_agents_query = text("""
            SELECT
                agent_id,
                COUNT(*) as execution_count,
                AVG(CASE WHEN status = 'success' THEN 1 ELSE 0 END) * 100 as success_rate,
                AVG(duration_ms) as avg_duration_ms
            FROM analytics.agent_executions
            WHERE workspace_id = :workspace_id
                AND start_time >= :start_date
                AND start_time < :end_date
            GROUP BY agent_id
            ORDER BY execution_count DESC
            LIMIT 10
        """)

        top_agents_result = await self._execute_with_timeout(
            top_agents_query,
            {
                "workspace_id": workspace_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        top_agents = []
        for row in top_agents_result:
            top_agents.append({
                "agentId": row.agent_id,
                "executionCount": row.execution_count,
                "successRate": round(row.success_rate or 0.0, 2),
                "avgDurationMs": round(row.avg_duration_ms or 0.0, 2),
            })

        return {
            "workspaceId": workspace_id,
            "timeframe": timeframe,
            "totalExecutions": summary_row.total_executions if summary_row else 0,
            "successRate": round(summary_row.success_rate or 0.0, 2) if summary_row else 0.0,
            "avgDurationMs": round(summary_row.avg_duration_ms or 0.0, 2) if summary_row else 0.0,
            "totalCredits": summary_row.total_credits if summary_row else 0,
            "activeAgents": summary_row.active_agents if summary_row else 0,
            "trends": [],  # Can add trend calculation similar to agent-level
            "topAgents": top_agents,
        }
