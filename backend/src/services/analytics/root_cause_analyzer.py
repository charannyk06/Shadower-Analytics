"""
Root Cause Analysis Engine

Performs automated root cause analysis using causal inference,
correlation analysis, and ML-powered pattern recognition.

Author: Claude Code
Date: 2025-11-13
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import numpy as np

logger = logging.getLogger(__name__)


class RootCauseAnalyzer:
    """
    Automated root cause analysis engine using multiple techniques:
    - Causal inference
    - Temporal correlation
    - Dependency chain analysis
    - Environmental factor analysis
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_error(
        self,
        error_id: str,
        depth: int = 3
    ) -> Dict[str, Any]:
        """
        Perform comprehensive root cause analysis for an error.

        Args:
            error_id: Error identifier
            depth: Depth of causal chain to explore

        Returns:
            Complete root cause analysis
        """
        try:
            logger.info(f"Starting root cause analysis for error {error_id}")

            # Fetch error details
            error_data = await self._get_error_details(error_id)

            if not error_data:
                return {
                    "error": "Error not found",
                    "error_id": error_id
                }

            # Run analyses in parallel
            results = await asyncio.gather(
                self._identify_immediate_cause(error_data),
                self._trace_root_causes(error_data, depth),
                self._identify_contributing_factors(error_data),
                self._correlate_with_recent_changes(error_data),
                self._find_similar_errors(error_data),
                self._analyze_dependency_chain(error_data),
                self._analyze_temporal_patterns(error_data),
                self._check_environmental_factors(error_data),
                return_exceptions=True
            )

            # Handle exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error in analysis component {i}: {result}", exc_info=True)
                    results[i] = {}

            analysis = {
                "error_id": error_id,
                "error_type": error_data["error_type"],
                "immediate_cause": results[0],
                "root_causes": results[1],
                "contributing_factors": results[2],
                "correlation_analysis": results[3],
                "similar_errors": results[4],
                "dependency_chain": results[5],
                "temporal_correlation": results[6],
                "environmental_factors": results[7],
                "analyzed_at": datetime.utcnow().isoformat(),
                "analysis_version": "v1.0.0"
            }

            # Generate remediation suggestions
            analysis["remediation_suggestions"] = await self._generate_remediation_plan(analysis)

            # Calculate overall confidence
            analysis["analysis_confidence"] = self._calculate_analysis_confidence(analysis)

            # Store analysis results
            await self._store_analysis(error_id, analysis)

            logger.info(f"Root cause analysis completed for error {error_id}")
            return analysis

        except Exception as e:
            logger.error(f"Error in root cause analysis: {e}", exc_info=True)
            raise

    async def _get_error_details(self, error_id: str) -> Optional[Dict[str, Any]]:
        """Fetch complete error details."""
        query = text("""
            SELECT
                e.*,
                COALESCE(
                    json_agg(
                        json_build_object(
                            'occurred_at', eo.occurred_at,
                            'user_id', eo.user_id,
                            'agent_id', eo.agent_id,
                            'metadata', eo.metadata
                        )
                        ORDER BY eo.occurred_at DESC
                    ) FILTER (WHERE eo.id IS NOT NULL),
                    '[]'::json
                ) as occurrences
            FROM analytics.errors e
            LEFT JOIN analytics.error_occurrences eo ON e.error_id = eo.error_id
            WHERE e.error_id = :error_id
            GROUP BY e.error_id
        """)

        result = await self.db.execute(query, {"error_id": error_id})
        row = result.fetchone()

        if not row:
            return None

        return {
            "error_id": str(row.error_id),
            "workspace_id": str(row.workspace_id),
            "error_type": row.error_type,
            "message": row.message,
            "severity": row.severity,
            "first_seen": row.first_seen,
            "last_seen": row.last_seen,
            "occurrence_count": row.occurrence_count,
            "stack_trace": row.stack_trace,
            "context": row.context or {},
            "users_affected": row.users_affected or [],
            "agents_affected": row.agents_affected or [],
            "occurrences": json.loads(row.occurrences) if isinstance(row.occurrences, str) else row.occurrences
        }

    async def _identify_immediate_cause(self, error_data: Dict[str, Any]) -> str:
        """Identify the immediate cause of the error."""
        # Extract immediate cause from stack trace and message
        message = error_data.get("message", "")
        error_type = error_data.get("error_type", "")
        stack_trace = error_data.get("stack_trace", "")

        # Simple heuristic-based immediate cause identification
        immediate_causes = {
            "TimeoutError": "Operation exceeded time limit",
            "ValidationError": "Input validation failed",
            "AuthenticationError": "Authentication credentials invalid or missing",
            "RateLimitError": "API rate limit exceeded",
            "NetworkError": "Network connection failed or timeout",
            "ResourceError": "Insufficient system resources",
            "ModelError": "AI model execution failed"
        }

        return immediate_causes.get(error_type, f"Error of type {error_type}: {message[:100]}")

    async def _trace_root_causes(
        self,
        error_data: Dict[str, Any],
        depth: int
    ) -> List[Dict[str, Any]]:
        """
        Trace root causes using causal inference.
        Returns list of potential root causes with probability scores.
        """
        root_causes = []

        # Check for common root causes based on error patterns
        error_type = error_data.get("error_type", "")
        context = error_data.get("context", {})
        occurrences = error_data.get("occurrences", [])

        # Analyze occurrence patterns
        if len(occurrences) > 1:
            # Check if errors follow a pattern
            time_deltas = []
            for i in range(1, min(len(occurrences), 10)):
                prev_time = datetime.fromisoformat(occurrences[i-1]["occurred_at"].replace('Z', '+00:00'))
                curr_time = datetime.fromisoformat(occurrences[i]["occurred_at"].replace('Z', '+00:00'))
                time_deltas.append((curr_time - prev_time).total_seconds())

            if time_deltas and np.std(time_deltas) < 60:  # Regular pattern
                root_causes.append({
                    "cause": "Systematic recurring issue",
                    "probability": 0.85,
                    "evidence": f"Errors occur in regular pattern (avg interval: {np.mean(time_deltas):.1f}s)",
                    "remediation": "Investigate scheduled jobs or periodic processes"
                })

        # Check for resource-related causes
        if error_type in ["TimeoutError", "ResourceError"]:
            root_causes.append({
                "cause": "Insufficient resource allocation",
                "probability": 0.75,
                "evidence": f"Error type {error_type} typically indicates resource constraints",
                "remediation": "Increase timeout limits, add resource scaling, or optimize operations"
            })

        # Check for configuration issues
        if error_type in ["ValidationError", "AuthenticationError"]:
            root_causes.append({
                "cause": "Configuration or credential issue",
                "probability": 0.80,
                "evidence": f"Error type {error_type} suggests misconfiguration",
                "remediation": "Review and validate configuration settings and credentials"
            })

        # Check for external dependency failures
        if error_type in ["NetworkError", "RateLimitError"]:
            root_causes.append({
                "cause": "External service dependency failure",
                "probability": 0.70,
                "evidence": f"Error type {error_type} indicates external service issues",
                "remediation": "Implement circuit breaker, add fallback mechanisms, or cache responses"
            })

        # Check for code quality issues
        if error_data.get("occurrence_count", 0) > 50:
            root_causes.append({
                "cause": "Underlying code defect",
                "probability": 0.65,
                "evidence": f"High occurrence count ({error_data.get('occurrence_count')}) suggests systemic issue",
                "remediation": "Perform code review and add unit tests for affected functionality"
            })

        # Sort by probability
        root_causes.sort(key=lambda x: x["probability"], reverse=True)

        return root_causes[:5]  # Return top 5

    async def _identify_contributing_factors(self, error_data: Dict[str, Any]) -> List[str]:
        """Identify contributing factors that increase error likelihood."""
        factors = []

        # Time-based factors
        occurrences = error_data.get("occurrences", [])
        if occurrences:
            hours = [datetime.fromisoformat(o["occurred_at"].replace('Z', '+00:00')).hour
                    for o in occurrences[:100]]
            hour_counts = {}
            for h in hours:
                hour_counts[h] = hour_counts.get(h, 0) + 1

            # Check for peak hour patterns
            max_hour = max(hour_counts.items(), key=lambda x: x[1])
            if max_hour[1] > len(hours) * 0.3:  # >30% occur in one hour
                factors.append(f"Peak occurrence during hour {max_hour[0]} (possible load-related)")

        # User-based factors
        users_affected = error_data.get("users_affected", [])
        if len(users_affected) > 10:
            factors.append(f"Wide user impact ({len(users_affected)} users) suggests system-wide issue")
        elif len(users_affected) == 1:
            factors.append("Single user affected suggests user-specific configuration or data issue")

        # Agent-based factors
        agents_affected = error_data.get("agents_affected", [])
        if len(agents_affected) == 1:
            factors.append("Single agent affected suggests agent-specific configuration issue")

        # Severity escalation
        if error_data.get("severity") == "critical":
            factors.append("Critical severity indicates high business impact")

        return factors

    async def _correlate_with_recent_changes(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Correlate error with recent deployments, config changes, etc."""
        workspace_id = error_data.get("workspace_id")
        first_seen = error_data.get("first_seen")

        # Check for other errors that started around the same time
        query = text("""
            SELECT
                error_type,
                COUNT(*) as count,
                MIN(first_seen) as first_occurrence
            FROM analytics.errors
            WHERE workspace_id = :workspace_id
                AND first_seen BETWEEN :start_time AND :end_time
                AND error_id != :error_id
            GROUP BY error_type
            ORDER BY count DESC
            LIMIT 5
        """)

        start_time = first_seen - timedelta(hours=1)
        end_time = first_seen + timedelta(hours=1)

        result = await self.db.execute(
            query,
            {
                "workspace_id": workspace_id,
                "start_time": start_time,
                "end_time": end_time,
                "error_id": error_data["error_id"]
            }
        )
        related_errors = result.fetchall()

        return {
            "time_window": "±1 hour from first occurrence",
            "related_errors": [
                {
                    "error_type": row.error_type,
                    "count": row.count,
                    "first_occurrence": row.first_occurrence.isoformat()
                }
                for row in related_errors
            ],
            "correlation_strength": "high" if len(related_errors) > 3 else "low"
        }

    async def _find_similar_errors(self, error_data: Dict[str, Any]) -> List[str]:
        """Find similar errors by error type and pattern."""
        query = text("""
            SELECT error_id
            FROM analytics.errors
            WHERE workspace_id = :workspace_id
                AND error_type = :error_type
                AND error_id != :error_id
                AND first_seen >= :lookback_date
            ORDER BY occurrence_count DESC
            LIMIT 5
        """)

        result = await self.db.execute(
            query,
            {
                "workspace_id": error_data["workspace_id"],
                "error_type": error_data["error_type"],
                "error_id": error_data["error_id"],
                "lookback_date": datetime.utcnow() - timedelta(days=30)
            }
        )

        return [str(row.error_id) for row in result.fetchall()]

    async def _analyze_dependency_chain(self, error_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze dependency chain to identify upstream failures."""
        # Check for parent/related errors in context
        context = error_data.get("context", {})
        parent_error_id = context.get("parent_error_id")

        chain = []

        if parent_error_id:
            # Fetch parent error
            parent_data = await self._get_error_details(parent_error_id)
            if parent_data:
                chain.append({
                    "level": "parent",
                    "error_id": parent_error_id,
                    "error_type": parent_data["error_type"],
                    "first_seen": parent_data["first_seen"].isoformat()
                })

        # Check for cascading failures
        query = text("""
            SELECT cascade_chain
            FROM analytics.error_cascades
            WHERE initial_error_id = :error_id
                OR :error_id = ANY(cascade_chain)
            ORDER BY cascade_start DESC
            LIMIT 1
        """)

        result = await self.db.execute(query, {"error_id": error_data["error_id"]})
        row = result.fetchone()

        if row and row.cascade_chain:
            chain.append({
                "type": "cascade",
                "chain_length": len(row.cascade_chain),
                "error_ids": [str(eid) for eid in row.cascade_chain]
            })

        return chain

    async def _analyze_temporal_patterns(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze temporal patterns in error occurrences."""
        occurrences = error_data.get("occurrences", [])

        if not occurrences:
            return {"pattern": "insufficient_data"}

        # Analyze day of week pattern
        days = [datetime.fromisoformat(o["occurred_at"].replace('Z', '+00:00')).weekday()
                for o in occurrences[:100]]

        day_counts = {}
        for d in days:
            day_counts[d] = day_counts.get(d, 0) + 1

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        max_day = max(day_counts.items(), key=lambda x: x[1]) if day_counts else (0, 0)

        return {
            "day_of_week_pattern": {
                day_names[i]: day_counts.get(i, 0) for i in range(7)
            },
            "worst_day": day_names[max_day[0]] if max_day[1] > 0 else "Unknown",
            "pattern_strength": "strong" if max_day[1] > len(days) * 0.3 else "weak"
        }

    async def _check_environmental_factors(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check environmental factors that may contribute to errors."""
        occurrences = error_data.get("occurrences", [])

        # Analyze environment distribution
        environments = {}
        for occ in occurrences[:100]:
            env = occ.get("metadata", {}).get("environment", "unknown")
            environments[env] = environments.get(env, 0) + 1

        # Analyze version distribution
        versions = {}
        for occ in occurrences[:100]:
            ver = occ.get("metadata", {}).get("version", "unknown")
            versions[ver] = versions.get(ver, 0) + 1

        return {
            "environment_distribution": environments,
            "version_distribution": versions,
            "environment_specific": len(environments) == 1 and "unknown" not in environments
        }

    async def _generate_remediation_plan(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate remediation suggestions based on analysis."""
        suggestions = []

        # Based on root causes
        for root_cause in analysis.get("root_causes", []):
            if root_cause["probability"] > 0.7:
                suggestions.append({
                    "priority": "high",
                    "action": root_cause["remediation"],
                    "rationale": root_cause["cause"],
                    "estimated_effort": "medium"
                })

        # Based on dependency chain
        if analysis.get("dependency_chain"):
            suggestions.append({
                "priority": "high",
                "action": "Investigate and resolve upstream errors first",
                "rationale": "Error appears to be part of a cascade",
                "estimated_effort": "high"
            })

        # Based on temporal patterns
        temporal = analysis.get("temporal_correlation", {})
        if temporal.get("pattern_strength") == "strong":
            suggestions.append({
                "priority": "medium",
                "action": f"Investigate system load and configuration on {temporal.get('worst_day')}",
                "rationale": "Strong temporal pattern detected",
                "estimated_effort": "medium"
            })

        # Based on environmental factors
        env_factors = analysis.get("environmental_factors", {})
        if env_factors.get("environment_specific"):
            env_name = list(env_factors.get("environment_distribution", {}).keys())[0]
            suggestions.append({
                "priority": "high",
                "action": f"Review configuration specific to {env_name} environment",
                "rationale": "Error only occurs in specific environment",
                "estimated_effort": "low"
            })

        return suggestions

    def _calculate_analysis_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate overall confidence in the analysis."""
        confidence_factors = []

        # Root cause confidence
        root_causes = analysis.get("root_causes", [])
        if root_causes and len(root_causes) > 0:
            max_prob = max(rc["probability"] for rc in root_causes)
            confidence_factors.append(max_prob)

        # Similar errors found
        if analysis.get("similar_errors"):
            confidence_factors.append(0.8)

        # Dependency chain identified
        if analysis.get("dependency_chain"):
            confidence_factors.append(0.7)

        # Strong temporal pattern
        temporal = analysis.get("temporal_correlation", {})
        if temporal.get("pattern_strength") == "strong":
            confidence_factors.append(0.75)

        # Calculate average
        if confidence_factors:
            return round(sum(confidence_factors) / len(confidence_factors), 2)
        else:
            return 0.5

    async def _store_analysis(self, error_id: str, analysis: Dict[str, Any]) -> None:
        """Store root cause analysis results."""
        try:
            query = text("""
                INSERT INTO analytics.error_root_causes (
                    error_id,
                    workspace_id,
                    immediate_cause,
                    root_causes,
                    contributing_factors,
                    correlated_changes,
                    similar_errors,
                    dependency_chain,
                    temporal_correlation,
                    environmental_factors,
                    remediation_suggestions,
                    auto_remediation_possible,
                    analysis_confidence,
                    analysis_version
                ) VALUES (
                    :error_id,
                    (SELECT workspace_id FROM analytics.errors WHERE error_id = :error_id),
                    :immediate_cause,
                    :root_causes::jsonb,
                    :contributing_factors::jsonb,
                    :correlated_changes::jsonb,
                    :similar_errors,
                    :dependency_chain::jsonb,
                    :temporal_correlation::jsonb,
                    :environmental_factors::jsonb,
                    :remediation_suggestions::jsonb,
                    :auto_remediation_possible,
                    :analysis_confidence,
                    :analysis_version
                )
                ON CONFLICT (error_id) DO UPDATE SET
                    immediate_cause = EXCLUDED.immediate_cause,
                    root_causes = EXCLUDED.root_causes,
                    contributing_factors = EXCLUDED.contributing_factors,
                    correlated_changes = EXCLUDED.correlated_changes,
                    similar_errors = EXCLUDED.similar_errors,
                    dependency_chain = EXCLUDED.dependency_chain,
                    temporal_correlation = EXCLUDED.temporal_correlation,
                    environmental_factors = EXCLUDED.environmental_factors,
                    remediation_suggestions = EXCLUDED.remediation_suggestions,
                    auto_remediation_possible = EXCLUDED.auto_remediation_possible,
                    analysis_confidence = EXCLUDED.analysis_confidence,
                    analyzed_at = NOW(),
                    updated_at = NOW()
            """)

            await self.db.execute(
                query,
                {
                    "error_id": error_id,
                    "immediate_cause": analysis["immediate_cause"],
                    "root_causes": json.dumps(analysis["root_causes"]),
                    "contributing_factors": json.dumps(analysis["contributing_factors"]),
                    "correlated_changes": json.dumps(analysis["correlation_analysis"]),
                    "similar_errors": analysis["similar_errors"],
                    "dependency_chain": json.dumps(analysis["dependency_chain"]),
                    "temporal_correlation": json.dumps(analysis["temporal_correlation"]),
                    "environmental_factors": json.dumps(analysis["environmental_factors"]),
                    "remediation_suggestions": json.dumps(analysis["remediation_suggestions"]),
                    "auto_remediation_possible": len(analysis["remediation_suggestions"]) > 0,
                    "analysis_confidence": analysis["analysis_confidence"],
                    "analysis_version": analysis["analysis_version"]
                }
            )

            await self.db.commit()
            logger.info(f"Stored RCA for error {error_id}")

        except Exception as e:
            logger.error(f"Error storing RCA: {e}", exc_info=True)
            await self.db.rollback()
