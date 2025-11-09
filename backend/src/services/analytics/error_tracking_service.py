"""Comprehensive error tracking service."""

import asyncio
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ...utils.datetime import calculate_start_date

logger = logging.getLogger(__name__)


class ErrorTrackingService:
    """Service for comprehensive error tracking and analysis."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def track_error(
        self,
        workspace_id: str,
        error_data: Dict[str, Any]
    ) -> str:
        """Track a new error occurrence.

        Args:
            workspace_id: Workspace ID
            error_data: Error details including type, message, stack_trace, etc.

        Returns:
            error_id: ID of the tracked error
        """
        # Generate error fingerprint for grouping
        fingerprint = self._generate_fingerprint(error_data)

        # Check if error already exists
        existing = await self._get_error_by_fingerprint(fingerprint, workspace_id)

        if existing:
            # Update existing error
            error_id = existing['error_id']
            await self._update_error_occurrence(error_id, error_data)
        else:
            # Create new error entry
            error_id = await self._create_new_error(fingerprint, workspace_id, error_data)

        # Create occurrence record
        await self._create_occurrence(error_id, error_data)

        # Update timeline
        await self._update_timeline(workspace_id, error_data)

        return error_id

    async def get_error_tracking(
        self,
        workspace_id: str,
        timeframe: str,
        severity_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive error tracking data.

        Args:
            workspace_id: Workspace ID
            timeframe: Time range (24h, 7d, 30d, 90d)
            severity_filter: Optional severity filter

        Returns:
            Comprehensive error tracking data
        """
        end_time = datetime.utcnow()
        start_time = calculate_start_date(timeframe)

        # Build filter conditions
        filters = {
            'workspace_id': workspace_id,
            'start_time': start_time,
            'end_time': end_time
        }

        if severity_filter and severity_filter != 'all':
            filters['severity'] = severity_filter

        # Parallel fetch all data
        results = await asyncio.gather(
            self._get_error_overview(filters),
            self._get_error_categories(filters),
            self._get_error_timeline(filters),
            self._get_error_list(filters),
            self._get_top_errors(filters),
            self._get_error_correlations(filters),
            self._get_recovery_analysis(filters),
            return_exceptions=True
        )

        # Handle any errors in parallel execution
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error in component {i}: {result}", exc_info=True)
                results[i] = {}

        return {
            "workspaceId": workspace_id,
            "timeframe": timeframe,
            "overview": results[0],
            "categories": results[1],
            "timeline": results[2],
            "errors": results[3],
            "topErrors": results[4],
            "correlations": results[5],
            "recovery": results[6]
        }

    async def resolve_error(
        self,
        error_id: str,
        resolution_data: Dict[str, Any]
    ):
        """Mark an error as resolved.

        Args:
            error_id: Error ID
            resolution_data: Resolution details
        """
        query = text("""
            UPDATE analytics.errors
            SET
                status = 'resolved',
                resolved_at = NOW(),
                resolved_by = :resolved_by,
                resolution = :resolution,
                root_cause = :root_cause,
                preventive_measures = :preventive_measures,
                updated_at = NOW()
            WHERE error_id = :error_id
        """)

        await self.db.execute(
            query,
            {
                'error_id': error_id,
                'resolved_by': resolution_data.get('resolved_by'),
                'resolution': resolution_data.get('resolution'),
                'root_cause': resolution_data.get('root_cause'),
                'preventive_measures': resolution_data.get('preventive_measures', [])
            }
        )
        await self.db.commit()

    async def ignore_error(self, error_id: str):
        """Mark an error as ignored.

        Args:
            error_id: Error ID
        """
        query = text("""
            UPDATE analytics.errors
            SET
                status = 'ignored',
                updated_at = NOW()
            WHERE error_id = :error_id
        """)

        await self.db.execute(query, {'error_id': error_id})
        await self.db.commit()

    def _generate_fingerprint(self, error_data: Dict[str, Any]) -> str:
        """Generate unique fingerprint for error grouping.

        Args:
            error_data: Error details

        Returns:
            MD5 fingerprint
        """
        error_type = error_data.get('type', '')

        # Normalize stack trace (remove line numbers and specific values)
        stack_trace = error_data.get('stack_trace', '')
        normalized_stack = re.sub(r':\d+:\d+', '', stack_trace)
        normalized_stack = re.sub(r'"[^"]*"', '""', normalized_stack)
        normalized_stack = re.sub(r'\d+', 'N', normalized_stack)

        # Create fingerprint
        fingerprint_data = f"{error_type}:{normalized_stack[:500]}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()

    async def _get_error_by_fingerprint(
        self,
        fingerprint: str,
        workspace_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get existing error by fingerprint.

        Args:
            fingerprint: Error fingerprint
            workspace_id: Workspace ID

        Returns:
            Error data if exists
        """
        query = text("""
            SELECT error_id, occurrence_count
            FROM analytics.errors
            WHERE fingerprint = :fingerprint
                AND workspace_id = :workspace_id
        """)

        result = await self.db.execute(
            query,
            {'fingerprint': fingerprint, 'workspace_id': workspace_id}
        )
        row = result.fetchone()

        if row:
            return {
                'error_id': str(row.error_id),
                'occurrence_count': row.occurrence_count
            }
        return None

    async def _create_new_error(
        self,
        fingerprint: str,
        workspace_id: str,
        error_data: Dict[str, Any]
    ) -> str:
        """Create a new error entry.

        Args:
            fingerprint: Error fingerprint
            workspace_id: Workspace ID
            error_data: Error details

        Returns:
            error_id: New error ID
        """
        query = text("""
            INSERT INTO analytics.errors (
                fingerprint,
                workspace_id,
                error_type,
                message,
                severity,
                status,
                stack_trace,
                context,
                first_seen,
                last_seen,
                occurrence_count
            ) VALUES (
                :fingerprint,
                :workspace_id,
                :error_type,
                :message,
                :severity,
                'new',
                :stack_trace,
                :context::jsonb,
                NOW(),
                NOW(),
                1
            )
            RETURNING error_id
        """)

        result = await self.db.execute(
            query,
            {
                'fingerprint': fingerprint,
                'workspace_id': workspace_id,
                'error_type': error_data.get('type', 'Unknown'),
                'message': error_data.get('message', ''),
                'severity': error_data.get('severity', 'medium'),
                'stack_trace': error_data.get('stack_trace', ''),
                'context': error_data.get('context', '{}')
            }
        )
        await self.db.commit()

        row = result.fetchone()
        return str(row.error_id)

    async def _update_error_occurrence(
        self,
        error_id: str,
        error_data: Dict[str, Any]
    ):
        """Update existing error with new occurrence.

        Args:
            error_id: Error ID
            error_data: Error details
        """
        query = text("""
            UPDATE analytics.errors
            SET
                last_seen = NOW(),
                occurrence_count = occurrence_count + 1,
                updated_at = NOW()
            WHERE error_id = :error_id
        """)

        await self.db.execute(query, {'error_id': error_id})
        await self.db.commit()

    async def _create_occurrence(
        self,
        error_id: str,
        error_data: Dict[str, Any]
    ):
        """Create occurrence record.

        Args:
            error_id: Error ID
            error_data: Error details
        """
        query = text("""
            INSERT INTO analytics.error_occurrences (
                error_id,
                occurred_at,
                user_id,
                agent_id,
                run_id,
                metadata,
                environment,
                version
            ) VALUES (
                :error_id,
                NOW(),
                :user_id,
                :agent_id,
                :run_id,
                :metadata::jsonb,
                :environment,
                :version
            )
        """)

        context = error_data.get('context', {})

        await self.db.execute(
            query,
            {
                'error_id': error_id,
                'user_id': context.get('userId'),
                'agent_id': context.get('agentId'),
                'run_id': context.get('runId'),
                'metadata': error_data.get('metadata', '{}'),
                'environment': context.get('environment'),
                'version': context.get('version')
            }
        )
        await self.db.commit()

    async def _update_timeline(
        self,
        workspace_id: str,
        error_data: Dict[str, Any]
    ):
        """Update error timeline.

        Args:
            workspace_id: Workspace ID
            error_data: Error details
        """
        query = text("""
            SELECT analytics.update_error_timeline(
                :workspace_id::uuid,
                NOW(),
                :severity,
                NULL::uuid
            )
        """)

        await self.db.execute(
            query,
            {
                'workspace_id': workspace_id,
                'severity': error_data.get('severity', 'medium')
            }
        )
        await self.db.commit()

    async def _get_error_overview(
        self,
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get error overview metrics.

        Args:
            filters: Filter conditions

        Returns:
            Overview metrics
        """
        query = text("""
            WITH error_stats AS (
                SELECT
                    COUNT(DISTINCT e.error_id) as unique_errors,
                    SUM(e.occurrence_count) as total_errors,
                    COUNT(DISTINCT UNNEST(e.users_affected)) as affected_users,
                    COUNT(DISTINCT UNNEST(e.agents_affected)) as affected_agents,
                    SUM(e.executions_affected) as executions_affected,
                    SUM(e.credits_lost) as credits_lost,
                    COUNT(*) FILTER (WHERE e.severity = 'critical') as critical_errors,
                    AVG(
                        CASE WHEN e.resolved_at IS NOT NULL
                        THEN EXTRACT(EPOCH FROM (e.resolved_at - e.first_seen))
                        ELSE NULL END
                    ) as avg_recovery_time
                FROM analytics.errors e
                WHERE e.workspace_id = :workspace_id
                    AND e.last_seen BETWEEN :start_time AND :end_time
            ),
            prev_stats AS (
                SELECT
                    SUM(e.occurrence_count) as prev_total_errors
                FROM analytics.errors e
                WHERE e.workspace_id = :workspace_id
                    AND e.last_seen BETWEEN
                        :start_time - (:end_time - :start_time)
                        AND :start_time
            )
            SELECT
                COALESCE(es.total_errors, 0) as total_errors,
                COALESCE(es.unique_errors, 0) as unique_errors,
                COALESCE(es.affected_users, 0) as affected_users,
                COALESCE(es.affected_agents, 0) as affected_agents,
                COALESCE(es.executions_affected, 0) as executions_affected,
                COALESCE(es.credits_lost, 0) as credits_lost,
                COALESCE(es.critical_errors, 0) as critical_errors,
                COALESCE(es.avg_recovery_time, 0) as avg_recovery_time,
                COALESCE(ps.prev_total_errors, 0) as prev_total_errors
            FROM error_stats es
            CROSS JOIN prev_stats ps
        """)

        result = await self.db.execute(query, filters)
        row = result.fetchone()

        if not row:
            return self._get_empty_overview()

        # Calculate error rate and change
        total_errors = row.total_errors or 0
        prev_errors = row.prev_total_errors or 0
        error_rate_change = 0.0
        if prev_errors > 0:
            error_rate_change = ((total_errors - prev_errors) / prev_errors) * 100

        return {
            "totalErrors": total_errors,
            "uniqueErrors": row.unique_errors or 0,
            "affectedUsers": row.affected_users or 0,
            "affectedAgents": row.affected_agents or 0,
            "errorRate": 0.0,  # Would need total runs to calculate
            "errorRateChange": round(error_rate_change, 2),
            "criticalErrorRate": round(
                (row.critical_errors / total_errors * 100) if total_errors > 0 else 0, 2
            ),
            "userImpact": 0.0,  # Would need total users to calculate
            "systemImpact": self._calculate_system_impact(row.critical_errors, total_errors),
            "estimatedRevenueLoss": round(float(row.credits_lost or 0) * 0.01, 2),
            "avgRecoveryTime": round(float(row.avg_recovery_time or 0), 2),
            "autoRecoveryRate": 0.0,  # Would need recovery attempt data
            "manualInterventions": 0
        }

    def _calculate_system_impact(self, critical_errors: int, total_errors: int) -> str:
        """Calculate system impact level.

        Args:
            critical_errors: Number of critical errors
            total_errors: Total errors

        Returns:
            Impact level
        """
        if critical_errors > 10:
            return 'critical'
        elif critical_errors > 5:
            return 'high'
        elif total_errors > 50:
            return 'medium'
        else:
            return 'low'

    async def _get_error_categories(
        self,
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get error categorization data.

        Args:
            filters: Filter conditions

        Returns:
            Category data
        """
        # Get errors by type
        query = text("""
            SELECT
                e.error_type,
                e.severity,
                SUM(e.occurrence_count) as count,
                ARRAY_AGG(
                    JSON_BUILD_OBJECT(
                        'errorId', e.error_id,
                        'message', e.message,
                        'stackTrace', COALESCE(SUBSTRING(e.stack_trace, 1, 500), ''),
                        'occurredAt', e.last_seen
                    )
                    ORDER BY e.last_seen DESC
                    LIMIT 3
                ) as samples
            FROM analytics.errors e
            WHERE e.workspace_id = :workspace_id
                AND e.last_seen BETWEEN :start_time AND :end_time
            GROUP BY e.error_type, e.severity
            ORDER BY count DESC
            LIMIT 20
        """)

        result = await self.db.execute(query, filters)
        rows = result.fetchall()

        total_count = sum(row.count for row in rows)

        by_type = []
        for row in rows:
            by_type.append({
                "type": row.error_type,
                "category": self._categorize_error(row.error_type),
                "count": row.count,
                "percentage": round((row.count / total_count * 100) if total_count > 0 else 0, 2),
                "trend": "stable",  # Would need historical data
                "severity": row.severity,
                "samples": row.samples[:3] if row.samples else []
            })

        # Get severity breakdown
        severity_query = text("""
            SELECT
                e.severity,
                SUM(e.occurrence_count) as count
            FROM analytics.errors e
            WHERE e.workspace_id = :workspace_id
                AND e.last_seen BETWEEN :start_time AND :end_time
            GROUP BY e.severity
        """)

        severity_result = await self.db.execute(severity_query, filters)
        severity_rows = severity_result.fetchall()

        by_severity = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }

        for row in severity_rows:
            by_severity[row.severity] = row.count

        return {
            "byType": by_type,
            "bySeverity": by_severity,
            "bySource": {
                "agent": 0,
                "api": 0,
                "database": 0,
                "integration": 0,
                "system": 0
            }
        }

    def _categorize_error(self, error_type: str) -> str:
        """Categorize error type.

        Args:
            error_type: Error type name

        Returns:
            Category
        """
        error_type_lower = error_type.lower()

        if 'timeout' in error_type_lower:
            return 'timeout'
        elif 'validation' in error_type_lower or 'invalid' in error_type_lower:
            return 'validation'
        elif 'auth' in error_type_lower or 'permission' in error_type_lower:
            return 'auth'
        elif 'rate' in error_type_lower or 'limit' in error_type_lower:
            return 'api'
        elif 'network' in error_type_lower or 'connection' in error_type_lower:
            return 'api'
        else:
            return 'system'

    async def _get_error_timeline(
        self,
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get error timeline data.

        Args:
            filters: Filter conditions

        Returns:
            Timeline data
        """
        query = text("""
            SELECT
                time_bucket as timestamp,
                error_count as count,
                critical_count,
                unique_errors
            FROM analytics.error_timeline
            WHERE workspace_id = :workspace_id
                AND time_bucket BETWEEN :start_time AND :end_time
                AND bucket_size = 'hourly'
            ORDER BY time_bucket
        """)

        result = await self.db.execute(query, filters)
        rows = result.fetchall()

        errors_by_time = [
            {
                "timestamp": row.timestamp.isoformat(),
                "count": row.count,
                "criticalCount": row.critical_count,
                "uniqueErrors": row.unique_errors
            }
            for row in rows
        ]

        # Get spikes
        spikes_query = text("""
            SELECT
                start_time,
                end_time,
                peak_errors,
                total_errors,
                primary_cause,
                resolved
            FROM analytics.error_spikes
            WHERE workspace_id = :workspace_id
                AND start_time BETWEEN :start_time AND :end_time
            ORDER BY start_time DESC
            LIMIT 10
        """)

        spikes_result = await self.db.execute(spikes_query, filters)
        spikes_rows = spikes_result.fetchall()

        spikes = [
            {
                "startTime": row.start_time.isoformat(),
                "endTime": row.end_time.isoformat() if row.end_time else None,
                "peakErrors": row.peak_errors,
                "totalErrors": row.total_errors,
                "primaryCause": row.primary_cause or "Unknown",
                "resolved": row.resolved
            }
            for row in spikes_rows
        ]

        return {
            "errorsByTime": errors_by_time,
            "spikes": spikes,
            "patterns": []
        }

    async def _get_error_list(
        self,
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get list of errors.

        Args:
            filters: Filter conditions

        Returns:
            List of errors
        """
        query = text("""
            SELECT
                error_id,
                fingerprint,
                error_type,
                message,
                severity,
                status,
                first_seen,
                last_seen,
                occurrence_count,
                stack_trace,
                context,
                users_affected,
                agents_affected,
                executions_affected,
                credits_lost,
                cascading_failures,
                resolved_at,
                resolved_by,
                resolution,
                root_cause,
                preventive_measures
            FROM analytics.errors
            WHERE workspace_id = :workspace_id
                AND last_seen BETWEEN :start_time AND :end_time
            ORDER BY last_seen DESC
            LIMIT 100
        """)

        result = await self.db.execute(query, filters)
        rows = result.fetchall()

        errors = []
        for row in rows:
            error_dict = {
                "errorId": str(row.error_id),
                "fingerprint": row.fingerprint,
                "type": row.error_type,
                "message": row.message,
                "severity": row.severity,
                "status": row.status,
                "firstSeen": row.first_seen.isoformat(),
                "lastSeen": row.last_seen.isoformat(),
                "occurrences": row.occurrence_count,
                "affectedUsers": row.users_affected or [],
                "affectedAgents": row.agents_affected or [],
                "stackTrace": row.stack_trace or "",
                "context": row.context or {},
                "impact": {
                    "usersAffected": len(row.users_affected or []),
                    "executionsAffected": row.executions_affected or 0,
                    "creditsLost": float(row.credits_lost or 0),
                    "cascadingFailures": row.cascading_failures or 0
                }
            }

            if row.resolved_at:
                error_dict["resolution"] = {
                    "resolvedAt": row.resolved_at.isoformat(),
                    "resolvedBy": str(row.resolved_by) if row.resolved_by else None,
                    "resolution": row.resolution,
                    "rootCause": row.root_cause,
                    "preventiveMeasures": row.preventive_measures or []
                }

            errors.append(error_dict)

        return errors

    async def _get_top_errors(
        self,
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get top errors.

        Args:
            filters: Filter conditions

        Returns:
            Top errors by various metrics
        """
        by_occurrence_query = text("""
            SELECT
                error_id,
                error_type,
                occurrence_count as count,
                last_seen
            FROM analytics.errors
            WHERE workspace_id = :workspace_id
                AND last_seen BETWEEN :start_time AND :end_time
            ORDER BY occurrence_count DESC
            LIMIT 10
        """)

        by_occurrence_result = await self.db.execute(by_occurrence_query, filters)
        by_occurrence_rows = by_occurrence_result.fetchall()

        by_occurrence = [
            {
                "errorId": str(row.error_id),
                "type": row.error_type,
                "count": row.count,
                "lastSeen": row.last_seen.isoformat()
            }
            for row in by_occurrence_rows
        ]

        by_impact_query = text("""
            SELECT
                error_id,
                error_type,
                COALESCE(ARRAY_LENGTH(users_affected, 1), 0) as users_affected,
                credits_lost
            FROM analytics.errors
            WHERE workspace_id = :workspace_id
                AND last_seen BETWEEN :start_time AND :end_time
            ORDER BY credits_lost DESC
            LIMIT 10
        """)

        by_impact_result = await self.db.execute(by_impact_query, filters)
        by_impact_rows = by_impact_result.fetchall()

        by_impact = [
            {
                "errorId": str(row.error_id),
                "type": row.error_type,
                "usersAffected": row.users_affected,
                "creditsLost": float(row.credits_lost or 0)
            }
            for row in by_impact_rows
        ]

        unresolved_query = text("""
            SELECT
                error_id,
                error_type,
                EXTRACT(EPOCH FROM (NOW() - first_seen)) / 3600 as age,
                CASE
                    WHEN severity = 'critical' THEN 10
                    WHEN severity = 'high' THEN 7
                    WHEN severity = 'medium' THEN 4
                    ELSE 1
                END as priority
            FROM analytics.errors
            WHERE workspace_id = :workspace_id
                AND status NOT IN ('resolved', 'ignored')
                AND last_seen BETWEEN :start_time AND :end_time
            ORDER BY priority DESC, age DESC
            LIMIT 10
        """)

        unresolved_result = await self.db.execute(unresolved_query, filters)
        unresolved_rows = unresolved_result.fetchall()

        unresolved = [
            {
                "errorId": str(row.error_id),
                "type": row.error_type,
                "age": round(float(row.age), 2),
                "priority": row.priority
            }
            for row in unresolved_rows
        ]

        return {
            "byOccurrence": by_occurrence,
            "byImpact": by_impact,
            "unresolved": unresolved
        }

    async def _get_error_correlations(
        self,
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get error correlations.

        Args:
            filters: Filter conditions

        Returns:
            Correlation data
        """
        return {
            "agentCorrelation": [],
            "userCorrelation": [],
            "errorChains": []
        }

    async def _get_recovery_analysis(
        self,
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get recovery analysis data.

        Args:
            filters: Filter conditions

        Returns:
            Recovery analysis data
        """
        return {
            "recoveryTimes": {
                "automatic": {
                    "avg": 0,
                    "median": 0,
                    "p95": 0
                },
                "manual": {
                    "avg": 0,
                    "median": 0,
                    "p95": 0
                }
            },
            "recoveryMethods": [],
            "failedRecoveries": []
        }

    def _get_empty_overview(self) -> Dict[str, Any]:
        """Return empty overview structure."""
        return {
            "totalErrors": 0,
            "uniqueErrors": 0,
            "affectedUsers": 0,
            "affectedAgents": 0,
            "errorRate": 0.0,
            "errorRateChange": 0.0,
            "criticalErrorRate": 0.0,
            "userImpact": 0.0,
            "systemImpact": "low",
            "estimatedRevenueLoss": 0.0,
            "avgRecoveryTime": 0.0,
            "autoRecoveryRate": 0.0,
            "manualInterventions": 0
        }
