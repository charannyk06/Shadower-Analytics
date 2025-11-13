"""
Agent Lifecycle Analytics Service.

Provides comprehensive lifecycle tracking and analysis for agents including:
- State transitions and lifecycle events
- Version management and performance comparison
- Deployment analytics and patterns
- Health score calculation
- Retirement risk assessment
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, text, case
from ...utils.datetime import calculate_start_date

logger = logging.getLogger(__name__)


# Constants
QUERY_TIMEOUT_SECONDS = 30
MAX_TRANSITIONS = 100
MAX_VERSIONS = 50
MAX_DEPLOYMENTS = 20
RETIREMENT_THRESHOLD_DAYS = 90


class AgentLifecycleService:
    """Service for agent lifecycle analytics and tracking."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _execute_with_timeout(self, query, params: dict):
        """Execute query with timeout protection."""
        try:
            timeout_query = text(f"SET LOCAL statement_timeout = '{QUERY_TIMEOUT_SECONDS}s'")
            await self.db.execute(timeout_query)
            result = await self.db.execute(query, params)
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}", exc_info=True)
            raise

    # ========================================================================
    # Main Analytics Method
    # ========================================================================

    async def get_lifecycle_analytics(
        self,
        agent_id: str,
        workspace_id: str,
        timeframe: str = "all",
        include_predictions: bool = False,
        include_versions: bool = True,
        include_deployments: bool = True,
        include_health: bool = True,
    ) -> Dict[str, Any]:
        """
        Get comprehensive lifecycle analytics for an agent.

        Args:
            agent_id: Agent UUID
            workspace_id: Workspace UUID
            timeframe: Time period (24h, 7d, 30d, 90d, all)
            include_predictions: Include predictive analytics
            include_versions: Include version comparison data
            include_deployments: Include deployment metrics
            include_health: Include health score data

        Returns:
            Dict containing comprehensive lifecycle analytics
        """
        # Validate UUIDs
        try:
            uuid.UUID(agent_id)
            uuid.UUID(workspace_id)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid UUID format: {str(e)}")

        start_date = calculate_start_date(timeframe)

        # Build list of tasks based on includes
        tasks = [
            self._get_current_state(agent_id),
            self._get_lifecycle_metrics(agent_id, workspace_id),
            self._get_state_transitions(agent_id, start_date),
            self._get_state_durations(agent_id),
            self._get_transition_matrix(agent_id),
            self._get_timeline(agent_id, start_date),
        ]

        if include_versions:
            tasks.extend([
                self._get_versions(agent_id),
                self._get_version_performance(agent_id),
            ])

        if include_deployments:
            tasks.append(self._get_deployment_metrics(agent_id))
            tasks.append(self._get_recent_deployments(agent_id, limit=MAX_DEPLOYMENTS))

        if include_health:
            tasks.append(self._get_current_health_score(agent_id))

        # Add retirement risk assessment
        tasks.append(self._assess_retirement_risk(agent_id, workspace_id))

        # Fetch all data in parallel
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Critical error fetching lifecycle analytics: {str(e)}", exc_info=True)
            raise

        # Parse results
        idx = 0
        current_state = results[idx] if not isinstance(results[idx], Exception) else {}
        idx += 1
        lifecycle_metrics = results[idx] if not isinstance(results[idx], Exception) else {}
        idx += 1
        transitions = results[idx] if not isinstance(results[idx], Exception) else []
        idx += 1
        state_durations = results[idx] if not isinstance(results[idx], Exception) else []
        idx += 1
        transition_matrix = results[idx] if not isinstance(results[idx], Exception) else []
        idx += 1
        timeline = results[idx] if not isinstance(results[idx], Exception) else []
        idx += 1

        versions = []
        version_comparison = []
        if include_versions:
            versions = results[idx] if not isinstance(results[idx], Exception) else []
            idx += 1
            version_comparison = results[idx] if not isinstance(results[idx], Exception) else []
            idx += 1

        deployment_metrics = None
        recent_deployments = []
        if include_deployments:
            deployment_metrics = results[idx] if not isinstance(results[idx], Exception) else None
            idx += 1
            recent_deployments = results[idx] if not isinstance(results[idx], Exception) else []
            idx += 1

        current_health_score = None
        health_trend = None
        if include_health:
            health_data = results[idx] if not isinstance(results[idx], Exception) else None
            if health_data:
                current_health_score = health_data
                health_trend = health_data.get("trend")
            idx += 1

        retirement_data = results[idx] if not isinstance(results[idx], Exception) else {}

        return {
            "agentId": agent_id,
            "workspaceId": workspace_id,
            "generatedAt": datetime.utcnow().isoformat(),
            "currentState": current_state.get("state") if current_state else None,
            "currentStateSince": current_state.get("transition_at").isoformat() if current_state and current_state.get("transition_at") else None,
            "lifecycleMetrics": lifecycle_metrics,
            "stateDurations": state_durations,
            "transitions": transitions,
            "transitionMatrix": transition_matrix,
            "timeline": timeline,
            "versions": versions,
            "versionComparison": version_comparison,
            "deploymentMetrics": deployment_metrics,
            "recentDeployments": recent_deployments,
            "currentHealthScore": current_health_score,
            "healthTrend": health_trend,
            "retirementRisk": retirement_data.get("retirement_risk"),
            "retirementScore": retirement_data.get("retirement_score"),
        }

    # ========================================================================
    # Current State Methods
    # ========================================================================

    async def _get_current_state(self, agent_id: str) -> Dict[str, Any]:
        """Get the current lifecycle state of the agent."""
        query = text("""
            SELECT
                new_state as state,
                timestamp as transition_at,
                EXTRACT(EPOCH FROM (NOW() - timestamp)) / 86400 as days_in_state,
                triggered_by,
                metadata
            FROM analytics.agent_lifecycle_events
            WHERE agent_id = :agent_id
              AND event_type = 'state_change'
            ORDER BY timestamp DESC
            LIMIT 1
        """)

        result = await self._execute_with_timeout(query, {"agent_id": agent_id})
        row = result.first()

        if not row:
            # Agent might not have lifecycle events yet, return default
            return {
                "state": "draft",
                "transition_at": datetime.utcnow(),
                "days_in_state": 0,
                "triggered_by": "system",
                "metadata": {}
            }

        return {
            "state": row.state,
            "transition_at": row.transition_at,
            "days_in_state": float(row.days_in_state) if row.days_in_state else 0,
            "triggered_by": row.triggered_by,
            "metadata": row.metadata or {}
        }

    # ========================================================================
    # Lifecycle Metrics Methods
    # ========================================================================

    async def _get_lifecycle_metrics(self, agent_id: str, workspace_id: str) -> Dict[str, Any]:
        """Get comprehensive lifecycle metrics from the summary view."""
        query = text("""
            SELECT
                current_state,
                days_in_current_state,
                total_transitions,
                lifecycle_started,
                last_state_change,
                total_lifecycle_days,
                total_versions,
                production_versions,
                latest_version_number,
                total_deployments,
                successful_deployments,
                deployment_success_rate,
                rollback_count
            FROM analytics.agent_lifecycle_summary
            WHERE agent_id = :agent_id
        """)

        result = await self._execute_with_timeout(query, {"agent_id": agent_id})
        row = result.first()

        if not row:
            # Return default metrics if no summary available
            return {
                "currentState": "draft",
                "daysInCurrentState": 0,
                "totalDaysSinceCreation": 0,
                "totalTransitions": 0,
                "totalVersions": 0,
                "productionVersions": 0,
                "latestVersionNumber": 0,
                "totalDeployments": 0,
                "successfulDeployments": 0,
                "deploymentSuccessRate": 0,
                "rollbackCount": 0,
            }

        return {
            "currentState": row.current_state,
            "daysInCurrentState": float(row.days_in_current_state) if row.days_in_current_state else 0,
            "totalDaysSinceCreation": float(row.total_lifecycle_days) if row.total_lifecycle_days else 0,
            "totalTransitions": row.total_transitions or 0,
            "totalVersions": row.total_versions or 0,
            "productionVersions": row.production_versions or 0,
            "latestVersionNumber": row.latest_version_number or 0,
            "totalDeployments": row.total_deployments or 0,
            "successfulDeployments": row.successful_deployments or 0,
            "deploymentSuccessRate": float(row.deployment_success_rate) if row.deployment_success_rate else 0,
            "rollbackCount": row.rollback_count or 0,
        }

    # ========================================================================
    # State Transition Methods
    # ========================================================================

    async def _get_state_transitions(self, agent_id: str, start_date: datetime) -> List[Dict[str, Any]]:
        """Get state transitions within timeframe."""
        query = text("""
            SELECT
                previous_state as from_state,
                new_state as to_state,
                timestamp as transition_at,
                EXTRACT(EPOCH FROM (
                    timestamp - LAG(timestamp) OVER (ORDER BY timestamp)
                )) as duration_in_state,
                triggered_by,
                metadata->>'reason' as transition_reason,
                metadata
            FROM analytics.agent_lifecycle_events
            WHERE agent_id = :agent_id
              AND event_type = 'state_change'
              AND timestamp >= :start_date
            ORDER BY timestamp DESC
            LIMIT :max_transitions
        """)

        result = await self._execute_with_timeout(
            query,
            {
                "agent_id": agent_id,
                "start_date": start_date,
                "max_transitions": MAX_TRANSITIONS
            }
        )

        transitions = []
        for row in result.fetchall():
            transitions.append({
                "fromState": row.from_state,
                "toState": row.to_state,
                "transitionAt": row.transition_at.isoformat() if row.transition_at else None,
                "durationInState": float(row.duration_in_state) if row.duration_in_state else None,
                "triggeredBy": row.triggered_by,
                "transitionReason": row.transition_reason,
                "metadata": row.metadata or {}
            })

        return transitions

    async def _get_state_durations(self, agent_id: str) -> List[Dict[str, Any]]:
        """Calculate average duration in each state."""
        query = text("""
            WITH state_periods AS (
                SELECT
                    new_state as state,
                    timestamp as entered_at,
                    LEAD(timestamp) OVER (ORDER BY timestamp) as exited_at
                FROM analytics.agent_lifecycle_events
                WHERE agent_id = :agent_id
                  AND event_type = 'state_change'
            ),
            durations AS (
                SELECT
                    state,
                    EXTRACT(EPOCH FROM (exited_at - entered_at)) as duration_seconds
                FROM state_periods
                WHERE exited_at IS NOT NULL
            ),
            total_time AS (
                SELECT SUM(duration_seconds) as total FROM durations
            )
            SELECT
                d.state,
                SUM(d.duration_seconds) as total_duration_seconds,
                AVG(d.duration_seconds) as average_duration_seconds,
                COUNT(*) as total_occurrences,
                CASE
                    WHEN t.total > 0
                    THEN (SUM(d.duration_seconds) / t.total) * 100
                    ELSE 0
                END as percentage_of_lifetime
            FROM durations d
            CROSS JOIN total_time t
            GROUP BY d.state, t.total
            ORDER BY total_duration_seconds DESC
        """)

        result = await self._execute_with_timeout(query, {"agent_id": agent_id})

        durations = []
        for row in result.fetchall():
            durations.append({
                "state": row.state,
                "totalDurationSeconds": float(row.total_duration_seconds) if row.total_duration_seconds else 0,
                "averageDurationSeconds": float(row.average_duration_seconds) if row.average_duration_seconds else 0,
                "totalOccurrences": row.total_occurrences,
                "percentageOfLifetime": float(row.percentage_of_lifetime) if row.percentage_of_lifetime else 0,
            })

        return durations

    async def _get_transition_matrix(self, agent_id: str) -> List[Dict[str, Any]]:
        """Build state transition probability matrix."""
        query = text("""
            WITH transitions AS (
                SELECT
                    previous_state as from_state,
                    new_state as to_state,
                    EXTRACT(EPOCH FROM (
                        timestamp - LAG(timestamp) OVER (ORDER BY timestamp)
                    )) as time_in_source_state
                FROM analytics.agent_lifecycle_events
                WHERE agent_id = :agent_id
                  AND event_type = 'state_change'
                  AND previous_state IS NOT NULL
            ),
            transition_counts AS (
                SELECT
                    from_state,
                    to_state,
                    COUNT(*) as transition_count,
                    AVG(time_in_source_state) as avg_time_in_source_state
                FROM transitions
                GROUP BY from_state, to_state
            ),
            from_state_totals AS (
                SELECT
                    from_state,
                    SUM(transition_count) as total_from_state
                FROM transition_counts
                GROUP BY from_state
            )
            SELECT
                tc.from_state,
                tc.to_state,
                tc.transition_count,
                CASE
                    WHEN fst.total_from_state > 0
                    THEN tc.transition_count::float / fst.total_from_state::float
                    ELSE 0
                END as transition_probability,
                tc.avg_time_in_source_state
            FROM transition_counts tc
            JOIN from_state_totals fst ON fst.from_state = tc.from_state
            ORDER BY tc.from_state, tc.transition_count DESC
        """)

        result = await self._execute_with_timeout(query, {"agent_id": agent_id})

        matrix = []
        for row in result.fetchall():
            matrix.append({
                "fromState": row.from_state,
                "toState": row.to_state,
                "transitionCount": row.transition_count,
                "transitionProbability": float(row.transition_probability) if row.transition_probability else 0,
                "avgTimeInSourceState": float(row.avg_time_in_source_state) if row.avg_time_in_source_state else 0,
            })

        return matrix

    async def _get_timeline(self, agent_id: str, start_date: datetime) -> List[Dict[str, Any]]:
        """Get timeline of all lifecycle events for visualization."""
        query = text("""
            SELECT
                timestamp,
                new_state as state,
                event_type as event,
                triggered_by,
                metadata
            FROM analytics.agent_lifecycle_events
            WHERE agent_id = :agent_id
              AND timestamp >= :start_date
            ORDER BY timestamp DESC
            LIMIT 100
        """)

        result = await self._execute_with_timeout(
            query,
            {"agent_id": agent_id, "start_date": start_date}
        )

        timeline = []
        for row in result.fetchall():
            timeline.append({
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "state": row.state or "N/A",
                "event": row.event,
                "triggeredBy": row.triggered_by,
                "metadata": row.metadata or {}
            })

        return timeline

    # ========================================================================
    # Version Methods
    # ========================================================================

    async def _get_versions(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all versions for the agent."""
        query = text("""
            SELECT
                id,
                agent_id,
                workspace_id,
                version,
                version_number,
                description,
                status,
                is_active,
                created_at,
                released_at,
                deprecated_at
            FROM analytics.agent_versions
            WHERE agent_id = :agent_id
            ORDER BY version_number DESC
            LIMIT :max_versions
        """)

        result = await self._execute_with_timeout(
            query,
            {"agent_id": agent_id, "max_versions": MAX_VERSIONS}
        )

        versions = []
        for row in result.fetchall():
            versions.append({
                "id": str(row.id),
                "agentId": str(row.agent_id),
                "workspaceId": str(row.workspace_id),
                "version": row.version,
                "versionNumber": row.version_number,
                "description": row.description,
                "status": row.status,
                "isActive": row.is_active,
                "createdAt": row.created_at.isoformat() if row.created_at else None,
                "releasedAt": row.released_at.isoformat() if row.released_at else None,
                "deprecatedAt": row.deprecated_at.isoformat() if row.deprecated_at else None,
            })

        return versions

    async def _get_version_performance(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get performance comparison across versions."""
        query = text("""
            SELECT
                version_id,
                agent_id,
                version,
                version_number,
                version_released,
                total_executions,
                avg_duration,
                p50_duration,
                p95_duration,
                success_rate,
                avg_credits,
                avg_rating,
                unique_users,
                error_count
            FROM analytics.agent_version_performance
            WHERE agent_id = :agent_id
            ORDER BY version_number DESC
            LIMIT :max_versions
        """)

        result = await self._execute_with_timeout(
            query,
            {"agent_id": agent_id, "max_versions": MAX_VERSIONS}
        )

        comparisons = []
        for row in result.fetchall():
            comparisons.append({
                "versionId": str(row.version_id),
                "agentId": str(row.agent_id),
                "version": row.version,
                "versionNumber": row.version_number,
                "versionReleased": row.version_released.isoformat() if row.version_released else None,
                "totalExecutions": row.total_executions or 0,
                "avgDuration": float(row.avg_duration) if row.avg_duration else 0,
                "p50Duration": float(row.p50_duration) if row.p50_duration else 0,
                "p95Duration": float(row.p95_duration) if row.p95_duration else 0,
                "successRate": float(row.success_rate) if row.success_rate else 0,
                "avgCredits": float(row.avg_credits) if row.avg_credits else 0,
                "avgRating": float(row.avg_rating) if row.avg_rating else None,
                "uniqueUsers": row.unique_users or 0,
                "errorCount": row.error_count or 0,
            })

        return comparisons

    # ========================================================================
    # Deployment Methods
    # ========================================================================

    async def _get_deployment_metrics(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get deployment success metrics."""
        query = text("""
            SELECT
                COUNT(*) as total_deployments,
                COUNT(*) FILTER (WHERE status = 'completed') as successful_deployments,
                COUNT(*) FILTER (WHERE status = 'failed') as failed_deployments,
                COUNT(*) FILTER (WHERE status = 'rolled_back') as rollback_count,
                AVG(duration_seconds) / 60 as avg_deployment_time_minutes,
                MAX(started_at) as last_deployment
            FROM analytics.agent_deployments
            WHERE agent_id = :agent_id
        """)

        result = await self._execute_with_timeout(query, {"agent_id": agent_id})
        row = result.first()

        if not row or row.total_deployments == 0:
            return None

        success_rate = 0
        if row.total_deployments > 0:
            success_rate = row.successful_deployments / row.total_deployments

        return {
            "totalDeployments": row.total_deployments,
            "successfulDeployments": row.successful_deployments,
            "failedDeployments": row.failed_deployments,
            "rollbackCount": row.rollback_count,
            "successRate": float(success_rate),
            "avgDeploymentTimeMinutes": float(row.avg_deployment_time_minutes) if row.avg_deployment_time_minutes else 0,
            "lastDeployment": row.last_deployment.isoformat() if row.last_deployment else None,
        }

    async def _get_recent_deployments(self, agent_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent deployment history."""
        query = text("""
            SELECT
                id,
                agent_id,
                workspace_id,
                version_id,
                deployment_type,
                environment,
                status,
                started_at,
                completed_at,
                duration_seconds,
                triggered_by
            FROM analytics.agent_deployments
            WHERE agent_id = :agent_id
            ORDER BY started_at DESC
            LIMIT :limit
        """)

        result = await self._execute_with_timeout(
            query,
            {"agent_id": agent_id, "limit": limit}
        )

        deployments = []
        for row in result.fetchall():
            deployments.append({
                "id": str(row.id),
                "agentId": str(row.agent_id),
                "workspaceId": str(row.workspace_id),
                "versionId": str(row.version_id) if row.version_id else None,
                "deploymentType": row.deployment_type,
                "environment": row.environment,
                "status": row.status,
                "startedAt": row.started_at.isoformat() if row.started_at else None,
                "completedAt": row.completed_at.isoformat() if row.completed_at else None,
                "durationSeconds": row.duration_seconds,
                "triggeredBy": row.triggered_by,
            })

        return deployments

    # ========================================================================
    # Health Score Methods
    # ========================================================================

    async def _get_current_health_score(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent health score."""
        query = text("""
            SELECT
                id,
                agent_id,
                workspace_id,
                overall_score,
                health_status,
                performance_score,
                reliability_score,
                usage_score,
                maintenance_score,
                cost_score,
                trend,
                previous_score,
                score_change,
                calculated_at
            FROM analytics.agent_health_scores
            WHERE agent_id = :agent_id
            ORDER BY calculated_at DESC
            LIMIT 1
        """)

        result = await self._execute_with_timeout(query, {"agent_id": agent_id})
        row = result.first()

        if not row:
            return None

        return {
            "id": str(row.id),
            "agentId": str(row.agent_id),
            "workspaceId": str(row.workspace_id),
            "overallScore": float(row.overall_score),
            "healthStatus": row.health_status,
            "performanceScore": float(row.performance_score) if row.performance_score else None,
            "reliabilityScore": float(row.reliability_score) if row.reliability_score else None,
            "usageScore": float(row.usage_score) if row.usage_score else None,
            "maintenanceScore": float(row.maintenance_score) if row.maintenance_score else None,
            "costScore": float(row.cost_score) if row.cost_score else None,
            "trend": row.trend,
            "previousScore": float(row.previous_score) if row.previous_score else None,
            "scoreChange": float(row.score_change) if row.score_change else None,
            "calculatedAt": row.calculated_at.isoformat() if row.calculated_at else None,
        }

    # ========================================================================
    # Retirement Risk Methods
    # ========================================================================

    async def _assess_retirement_risk(self, agent_id: str, workspace_id: str) -> Dict[str, Any]:
        """Assess retirement risk for the agent."""
        query = text("""
            SELECT
                days_since_last_use,
                total_executions_30d,
                recent_avg_rating,
                active_users_30d,
                dependent_agents_count,
                retirement_priority,
                retirement_score
            FROM analytics.agent_retirement_candidates
            WHERE agent_id = :agent_id
            ORDER BY identified_at DESC
            LIMIT 1
        """)

        result = await self._execute_with_timeout(
            query,
            {"agent_id": agent_id}
        )
        row = result.first()

        if not row:
            # Calculate basic retirement risk if not in candidates table
            return {
                "retirement_risk": "low",
                "retirement_score": 0,
            }

        return {
            "retirement_risk": row.retirement_priority,
            "retirement_score": float(row.retirement_score) if row.retirement_score else 0,
            "daysSinceLastUse": row.days_since_last_use,
            "totalExecutions30d": row.total_executions_30d,
            "recentAvgRating": float(row.recent_avg_rating) if row.recent_avg_rating else None,
            "activeUsers30d": row.active_users_30d,
            "dependentAgentsCount": row.dependent_agents_count,
        }

    # ========================================================================
    # Lifecycle Event Recording
    # ========================================================================

    async def record_lifecycle_event(
        self,
        agent_id: str,
        workspace_id: str,
        event_type: str,
        previous_state: Optional[str] = None,
        new_state: Optional[str] = None,
        triggered_by: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Record a lifecycle event for an agent.

        Args:
            agent_id: Agent UUID
            workspace_id: Workspace UUID
            event_type: Type of event (state_change, version_release, etc.)
            previous_state: Previous state (for state changes)
            new_state: New state (for state changes)
            triggered_by: Who/what triggered the event
            metadata: Additional metadata

        Returns:
            Event ID (UUID)
        """
        query = text("""
            SELECT analytics.record_lifecycle_event(
                :agent_id::uuid,
                :workspace_id::uuid,
                :event_type,
                :previous_state,
                :new_state,
                :triggered_by,
                :metadata::jsonb
            )
        """)

        result = await self.db.execute(
            query,
            {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "event_type": event_type,
                "previous_state": previous_state,
                "new_state": new_state,
                "triggered_by": triggered_by,
                "metadata": metadata or {},
            }
        )

        event_id = result.scalar()
        await self.db.commit()

        return str(event_id)
