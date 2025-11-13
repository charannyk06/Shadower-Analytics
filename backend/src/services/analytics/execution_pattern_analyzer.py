"""Execution pattern analysis service."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import uuid

logger = logging.getLogger(__name__)


class ExecutionPatternAnalyzer:
    """Service for analyzing execution patterns and detecting anomalies."""

    QUERY_TIMEOUT_SECONDS = 30

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _execute_with_timeout(self, query, params: dict = None):
        """Execute query with timeout protection."""
        try:
            timeout_query = text(f"SET LOCAL statement_timeout = '{self.QUERY_TIMEOUT_SECONDS}s'")
            await self.db.execute(timeout_query)
            if params:
                result = await self.db.execute(query, params)
            else:
                result = await self.db.execute(query)
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}", exc_info=True)
            raise

    async def analyze_patterns(
        self,
        agent_id: str,
        workspace_id: str,
        lookback_days: int = 30,
    ) -> Dict[str, Any]:
        """Analyze execution patterns for optimization."""

        try:
            uuid.UUID(agent_id)
            uuid.UUID(workspace_id)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid UUID format: {str(e)}")

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=lookback_days)

        # Analyze different pattern types
        hourly_patterns = await self._analyze_time_patterns(agent_id, workspace_id, start_date, end_date)
        input_patterns = await self._analyze_input_patterns(agent_id, workspace_id, start_date, end_date)
        path_patterns = await self._analyze_path_patterns(agent_id, workspace_id, start_date, end_date)
        bottlenecks = await self._detect_bottlenecks(agent_id, workspace_id, start_date, end_date)

        return {
            "hourlyPatterns": hourly_patterns,
            "inputPatterns": input_patterns,
            "executionPaths": path_patterns,
            "bottlenecks": bottlenecks,
            "optimizationSuggestions": self._generate_suggestions(
                hourly_patterns,
                bottlenecks,
                input_patterns
            ),
        }

    async def _analyze_time_patterns(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Analyze time-based execution patterns."""

        query = text("""
            SELECT
                EXTRACT(HOUR FROM start_time) as hour,
                COUNT(*) as execution_count,
                AVG(duration_ms) as avg_duration,
                AVG(CASE WHEN status = 'success' THEN 1 ELSE 0 END) * 100 as success_rate,
                AVG(credits_consumed) as avg_credits
            FROM analytics.agent_executions
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND start_time >= :start_date
                AND start_time < :end_date
            GROUP BY EXTRACT(HOUR FROM start_time)
            ORDER BY hour
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

        patterns = []
        for row in result:
            patterns.append({
                "hour": int(row.hour),
                "executionCount": row.execution_count,
                "avgDuration": round(row.avg_duration or 0.0, 2),
                "successRate": round(row.success_rate or 0.0, 2),
                "avgCredits": round(row.avg_credits or 0.0, 2),
            })

        return patterns

    async def _analyze_input_patterns(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Analyze input data patterns."""

        query = text("""
            SELECT
                jsonb_object_keys(input_data) as input_key,
                COUNT(*) as usage_count,
                AVG(CASE WHEN status = 'success' THEN 1 ELSE 0 END) * 100 as success_rate,
                AVG(duration_ms) as avg_duration
            FROM analytics.agent_executions
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND start_time >= :start_date
                AND start_time < :end_date
                AND input_data IS NOT NULL
            GROUP BY jsonb_object_keys(input_data)
            ORDER BY usage_count DESC
            LIMIT 20
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

        patterns = []
        for row in result:
            patterns.append({
                "inputKey": row.input_key,
                "usageCount": row.usage_count,
                "successRate": round(row.success_rate or 0.0, 2),
                "avgDuration": round(row.avg_duration or 0.0, 2),
            })

        return patterns

    async def _analyze_path_patterns(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Analyze execution path patterns."""

        query = text("""
            SELECT
                execution_graph->>'path' as execution_path,
                COUNT(*) as frequency,
                AVG(duration_ms) as avg_duration,
                AVG(credits_consumed) as avg_credits,
                AVG(CASE WHEN status = 'success' THEN 1 ELSE 0 END) * 100 as success_rate
            FROM analytics.agent_executions
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND start_time >= :start_date
                AND start_time < :end_date
                AND execution_graph IS NOT NULL
            GROUP BY execution_graph->>'path'
            ORDER BY frequency DESC
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

        patterns = []
        for row in result:
            if row.execution_path:
                patterns.append({
                    "executionPath": row.execution_path,
                    "frequency": row.frequency,
                    "avgDuration": round(row.avg_duration or 0.0, 2),
                    "avgCredits": round(row.avg_credits or 0.0, 2),
                    "successRate": round(row.success_rate or 0.0, 2),
                })

        return patterns

    async def _detect_bottlenecks(
        self,
        agent_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Detect performance bottlenecks."""

        query = text("""
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
                AND s.duration_ms IS NOT NULL
            GROUP BY s.step_name
            HAVING AVG(s.duration_ms) > 1000
            ORDER BY avg_duration_ms DESC
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

        bottlenecks = []
        for row in result:
            # Calculate impact score based on duration and frequency
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

            suggestions = []
            if row.duration_variance and row.avg_duration_ms:
                variance_ratio = row.duration_variance / row.avg_duration_ms
                if variance_ratio > 0.5:
                    suggestions.append("High variance detected - consider implementing caching or optimization")

            if row.avg_duration_ms > 5000:
                suggestions.append("Consider parallelization or asynchronous processing")

            bottlenecks.append({
                "stepName": row.step_name,
                "avgDurationMs": int(row.avg_duration_ms or 0),
                "durationVariance": round(row.duration_variance or 0.0, 2),
                "executionCount": row.execution_count,
                "p95DurationMs": int(row.p95_duration_ms or 0),
                "p99DurationMs": int(row.p99_duration_ms or 0),
                "impactScore": round(impact_score, 2),
                "optimizationPriority": priority,
                "suggestions": suggestions,
            })

        return bottlenecks

    def _generate_suggestions(
        self,
        hourly_patterns: List[Dict],
        bottlenecks: List[Dict],
        input_patterns: List[Dict],
    ) -> List[str]:
        """Generate optimization suggestions based on patterns."""
        suggestions = []

        # Analyze hourly patterns for peak times
        if hourly_patterns:
            max_executions = max(p["executionCount"] for p in hourly_patterns)
            peak_hours = [p for p in hourly_patterns if p["executionCount"] > max_executions * 0.8]

            if peak_hours:
                hours_str = ", ".join(f"{p['hour']:02d}:00" for p in peak_hours)
                suggestions.append(
                    f"Peak execution hours detected: {hours_str}. "
                    "Consider auto-scaling or resource pre-allocation during these times."
                )

            # Check for low-activity periods
            low_activity = [p for p in hourly_patterns if p["executionCount"] < max_executions * 0.2]
            if low_activity and len(low_activity) > 4:
                suggestions.append(
                    "Significant low-activity periods detected. "
                    "Consider scheduled maintenance or batch processing during these times."
                )

        # Analyze bottlenecks
        if bottlenecks:
            critical_bottlenecks = [b for b in bottlenecks if b["optimizationPriority"] in ["critical", "high"]]

            if critical_bottlenecks:
                for bottleneck in critical_bottlenecks[:3]:
                    suggestions.append(
                        f"Critical bottleneck: '{bottleneck['stepName']}' "
                        f"(avg: {bottleneck['avgDurationMs']}ms, {bottleneck['optimizationPriority']} priority). "
                        f"Impact score: {bottleneck['impactScore']:.1f}/100"
                    )

            # Check for high variance bottlenecks
            high_variance = [
                b for b in bottlenecks
                if b["durationVariance"] > b["avgDurationMs"] * 0.5
            ]
            if high_variance:
                suggestions.append(
                    f"High performance variance detected in {len(high_variance)} step(s). "
                    "Investigate for inconsistent resource availability or data dependencies."
                )

        # Analyze input patterns
        if input_patterns:
            low_success_inputs = [p for p in input_patterns if p["successRate"] < 80]
            if low_success_inputs:
                suggestions.append(
                    f"Input validation needed: {len(low_success_inputs)} input key(s) "
                    "show low success rates. Consider adding validation or preprocessing."
                )

        # General suggestions if we have data
        if hourly_patterns and bottlenecks:
            total_executions = sum(p["executionCount"] for p in hourly_patterns)
            if total_executions > 1000:
                suggestions.append(
                    "High execution volume detected. "
                    "Consider implementing result caching for frequently used input patterns."
                )

        if not suggestions:
            suggestions.append("No significant optimization opportunities detected at this time.")

        return suggestions

    async def save_pattern_analysis(
        self,
        agent_id: str,
        workspace_id: str,
        pattern_type: str,
        pattern_data: Dict[str, Any],
        metrics: Dict[str, Any],
    ) -> None:
        """Save pattern analysis results to database."""

        query = text("""
            INSERT INTO analytics.execution_patterns (
                agent_id,
                workspace_id,
                pattern_type,
                pattern_data,
                frequency,
                avg_duration_ms,
                avg_credits,
                success_rate,
                sample_size,
                confidence_score
            ) VALUES (
                :agent_id,
                :workspace_id,
                :pattern_type,
                :pattern_data,
                :frequency,
                :avg_duration_ms,
                :avg_credits,
                :success_rate,
                :sample_size,
                :confidence_score
            )
        """)

        await self.db.execute(
            query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "pattern_type": pattern_type,
                "pattern_data": pattern_data,
                "frequency": metrics.get("frequency"),
                "avg_duration_ms": metrics.get("avg_duration_ms"),
                "avg_credits": metrics.get("avg_credits"),
                "success_rate": metrics.get("success_rate"),
                "sample_size": metrics.get("sample_size"),
                "confidence_score": metrics.get("confidence_score", 0.95),
            },
        )
        await self.db.commit()

    async def detect_anomalies(
        self,
        agent_id: str,
        workspace_id: str,
        current_execution: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in current execution compared to historical patterns."""

        anomalies = []

        # Get historical averages
        query = text("""
            SELECT
                AVG(duration_ms) as avg_duration,
                STDDEV(duration_ms) as stddev_duration,
                AVG(credits_consumed) as avg_credits,
                STDDEV(credits_consumed) as stddev_credits
            FROM analytics.agent_executions
            WHERE agent_id = :agent_id
                AND workspace_id = :workspace_id
                AND status = 'success'
                AND start_time >= NOW() - INTERVAL '30 days'
        """)

        result = await self._execute_with_timeout(
            query,
            {"agent_id": agent_id, "workspace_id": workspace_id},
        )
        baseline = result.fetchone()

        if not baseline:
            return anomalies

        # Check duration anomaly (> 2 standard deviations)
        if baseline.avg_duration and baseline.stddev_duration:
            threshold = baseline.avg_duration + (2 * baseline.stddev_duration)
            if current_execution.get("duration_ms", 0) > threshold:
                anomalies.append({
                    "type": "duration",
                    "severity": "high",
                    "message": f"Execution duration ({current_execution['duration_ms']}ms) "
                               f"significantly exceeds normal range (avg: {baseline.avg_duration:.0f}ms)",
                    "threshold": threshold,
                    "value": current_execution.get("duration_ms"),
                })

        # Check credits anomaly
        if baseline.avg_credits and baseline.stddev_credits:
            threshold = baseline.avg_credits + (2 * baseline.stddev_credits)
            if current_execution.get("credits_consumed", 0) > threshold:
                anomalies.append({
                    "type": "credits",
                    "severity": "medium",
                    "message": f"Credit consumption ({current_execution['credits_consumed']}) "
                               f"exceeds normal range (avg: {baseline.avg_credits:.0f})",
                    "threshold": threshold,
                    "value": current_execution.get("credits_consumed"),
                })

        return anomalies
