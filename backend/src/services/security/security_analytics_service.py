"""Security analytics service - main orchestrator for security features."""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.schemas.security import (
    SecurityDashboardSummary,
    SecurityAnalyticsResponse,
    ThreatAnalysis,
    ComplianceMetrics,
    SecurityIncident,
    SecurityEvent,
    AccessControlMetrics,
    PermissionUsage,
    AccessPattern,
    PrivilegeAnalysis,
    DataAccessAnalytics,
)
from .threat_detection_service import ThreatDetectionEngine
from .vulnerability_scanner_service import VulnerabilityScanner

logger = logging.getLogger(__name__)


class SecurityAnalyticsService:
    """Main service for security analytics operations."""

    def __init__(self, db: AsyncSession):
        """Initialize security analytics service."""
        self.db = db
        self.threat_detector = ThreatDetectionEngine(db)
        self.vuln_scanner = VulnerabilityScanner(db)

    async def get_security_dashboard(
        self, workspace_id: str
    ) -> SecurityDashboardSummary:
        """
        Get security dashboard summary for a workspace.

        Args:
            workspace_id: Workspace identifier

        Returns:
            SecurityDashboardSummary with key metrics
        """
        logger.info(f"Fetching security dashboard for workspace {workspace_id}")

        query = text("""
            SELECT
                workspace_id,
                security_events_24h,
                security_events_7d,
                critical_events,
                high_events,
                avg_threat_score,
                max_threat_score,
                open_incidents,
                critical_incidents,
                avg_resolution_time_minutes,
                critical_vulnerabilities,
                high_vulnerabilities,
                avg_vulnerability_risk_score,
                avg_compliance_score,
                last_updated
            FROM analytics.security_dashboard_summary
            WHERE workspace_id = :workspace_id
        """)

        result = await self.db.execute(query, {"workspace_id": workspace_id})
        row = result.fetchone()

        if row:
            return SecurityDashboardSummary(
                workspace_id=str(row.workspace_id),
                security_events_24h=row.security_events_24h,
                security_events_7d=row.security_events_7d,
                critical_events=row.critical_events,
                high_events=row.high_events,
                avg_threat_score=float(row.avg_threat_score),
                max_threat_score=float(row.max_threat_score),
                open_incidents=row.open_incidents,
                critical_incidents=row.critical_incidents,
                avg_resolution_time_minutes=float(row.avg_resolution_time_minutes),
                critical_vulnerabilities=row.critical_vulnerabilities,
                high_vulnerabilities=row.high_vulnerabilities,
                avg_vulnerability_risk_score=float(row.avg_vulnerability_risk_score),
                avg_compliance_score=float(row.avg_compliance_score),
                last_updated=row.last_updated,
            )

        # Return empty summary if no data
        return SecurityDashboardSummary(
            workspace_id=workspace_id,
            security_events_24h=0,
            security_events_7d=0,
            critical_events=0,
            high_events=0,
            avg_threat_score=0.0,
            max_threat_score=0.0,
            open_incidents=0,
            critical_incidents=0,
            avg_resolution_time_minutes=0.0,
            critical_vulnerabilities=0,
            high_vulnerabilities=0,
            avg_vulnerability_risk_score=0.0,
            avg_compliance_score=0.0,
            last_updated=datetime.utcnow(),
        )

    async def get_threat_analysis(
        self, agent_id: str, timeframe: str = "24h"
    ) -> ThreatAnalysis:
        """
        Get comprehensive threat analysis for an agent.

        Args:
            agent_id: Agent identifier
            timeframe: Time range (24h, 7d, 30d)

        Returns:
            ThreatAnalysis with detection results
        """
        logger.info(f"Fetching threat analysis for agent {agent_id}, timeframe {timeframe}")

        # Parse timeframe
        window_minutes = self._parse_timeframe(timeframe)

        # Run threat detection
        threat_detection = await self.threat_detector.detect_threats(agent_id, window_minutes)

        # Get recent security events
        recent_events = await self._get_recent_security_events(agent_id, window_minutes)

        # Get latest vulnerability scan
        vulnerability_status = await self._get_latest_vulnerability_scan(agent_id)

        # Get access control metrics
        access_control_metrics = await self._get_access_control_metrics(agent_id)

        return ThreatAnalysis(
            agent_id=agent_id,
            timeframe=timeframe,
            threat_detection=threat_detection,
            recent_events=recent_events,
            vulnerability_status=vulnerability_status,
            access_control_metrics=access_control_metrics,
        )

    async def get_access_control_metrics(
        self, agent_id: str
    ) -> AccessControlMetrics:
        """
        Get access control metrics for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            AccessControlMetrics with permission usage and patterns
        """
        logger.info(f"Fetching access control metrics for agent {agent_id}")

        # Get permission usage
        permission_usage = await self._analyze_permission_usage(agent_id)

        # Get access patterns
        access_patterns = await self._analyze_access_patterns(agent_id)

        # Get privilege analysis
        privilege_analysis = await self._analyze_privileges(agent_id)

        # Get compliance status
        compliance_status = await self._get_access_compliance_status(agent_id)

        return AccessControlMetrics(
            agent_id=agent_id,
            permission_usage=permission_usage,
            access_patterns=access_patterns,
            privilege_analysis=privilege_analysis,
            compliance_status=compliance_status,
        )

    async def get_data_access_analytics(
        self, workspace_id: str, timeframe: str = "7d"
    ) -> DataAccessAnalytics:
        """
        Get data access analytics for a workspace.

        Args:
            workspace_id: Workspace identifier
            timeframe: Time range

        Returns:
            DataAccessAnalytics with access patterns
        """
        window_minutes = self._parse_timeframe(timeframe)

        query = text("""
            SELECT
                COUNT(*) as total_access_events,
                COUNT(*) FILTER (WHERE contains_pii = TRUE) as pii_access_count,
                COUNT(*) FILTER (WHERE contains_phi = TRUE) as phi_access_count,
                COUNT(*) FILTER (WHERE anomaly_score > 70) as high_risk_access_count,
                COUNT(*) FILTER (WHERE unusual_volume OR unusual_timing OR unusual_destination) as anomalous_access_count,
                AVG(anomaly_score) as avg_anomaly_score,
                MAX(anomaly_score) as max_anomaly_score
            FROM analytics.data_access_events
            WHERE workspace_id = :workspace_id
                AND created_at > NOW() - INTERVAL ':window_minutes minutes'
        """)

        result = await self.db.execute(
            query, {"workspace_id": workspace_id, "window_minutes": window_minutes}
        )
        row = result.fetchone()

        # Get top accessed resources
        top_resources_query = text("""
            SELECT
                resource_type,
                resource_id,
                COUNT(*) as access_count,
                MAX(data_sensitivity) as max_sensitivity
            FROM analytics.data_access_events
            WHERE workspace_id = :workspace_id
                AND created_at > NOW() - INTERVAL ':window_minutes minutes'
            GROUP BY resource_type, resource_id
            ORDER BY access_count DESC
            LIMIT 10
        """)

        top_result = await self.db.execute(
            top_resources_query, {"workspace_id": workspace_id, "window_minutes": window_minutes}
        )
        top_resources = [
            {
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "access_count": r.access_count,
                "sensitivity": r.max_sensitivity,
            }
            for r in top_result.fetchall()
        ]

        if row:
            # Calculate exfiltration risk
            exfiltration_risk = self._calculate_exfiltration_risk(
                row.anomalous_access_count,
                row.total_access_events,
                float(row.max_anomaly_score or 0),
            )

            return DataAccessAnalytics(
                total_access_events=row.total_access_events,
                pii_access_count=row.pii_access_count,
                phi_access_count=row.phi_access_count,
                high_risk_access_count=row.high_risk_access_count,
                anomalous_access_count=row.anomalous_access_count,
                avg_anomaly_score=float(row.avg_anomaly_score or 0),
                data_exfiltration_risk=exfiltration_risk,
                top_accessed_resources=top_resources,
            )

        return DataAccessAnalytics(
            total_access_events=0,
            pii_access_count=0,
            phi_access_count=0,
            high_risk_access_count=0,
            anomalous_access_count=0,
            avg_anomaly_score=0.0,
            data_exfiltration_risk=0.0,
            top_accessed_resources=[],
        )

    async def get_recent_incidents(
        self, workspace_id: str, limit: int = 10
    ) -> List[SecurityIncident]:
        """Get recent security incidents for a workspace."""
        query = text("""
            SELECT
                id,
                incident_number,
                agent_id,
                workspace_id,
                incident_type,
                severity,
                status,
                attack_vector,
                affected_systems,
                description,
                detected_at,
                investigated_at,
                contained_at,
                resolved_at,
                users_affected,
                data_records_exposed,
                financial_impact_usd,
                reputation_impact,
                time_to_detect_minutes,
                time_to_respond_minutes,
                time_to_contain_minutes,
                time_to_resolve_minutes,
                actions_taken,
                created_at
            FROM analytics.security_incidents
            WHERE workspace_id = :workspace_id
            ORDER BY detected_at DESC
            LIMIT :limit
        """)

        result = await self.db.execute(
            query, {"workspace_id": workspace_id, "limit": limit}
        )
        rows = result.fetchall()

        incidents = []
        for row in rows:
            from ...models.schemas.security import (
                IncidentTimeline,
                ImpactAssessment,
                ResponseMetrics,
            )

            timeline = IncidentTimeline(
                detected_at=row.detected_at,
                investigated_at=row.investigated_at,
                contained_at=row.contained_at,
                resolved_at=row.resolved_at,
            )

            impact = ImpactAssessment(
                users_affected=row.users_affected or 0,
                data_records_exposed=row.data_records_exposed or 0,
                financial_impact_usd=float(row.financial_impact_usd) if row.financial_impact_usd else None,
                reputation_impact=row.reputation_impact,
            )

            response = ResponseMetrics(
                time_to_detect=row.time_to_detect_minutes,
                time_to_respond=row.time_to_respond_minutes,
                time_to_contain=row.time_to_contain_minutes,
                time_to_resolve=row.time_to_resolve_minutes,
            )

            incidents.append(
                SecurityIncident(
                    incident_id=str(row.id),
                    incident_number=row.incident_number,
                    agent_id=str(row.agent_id) if row.agent_id else None,
                    workspace_id=str(row.workspace_id),
                    incident_type=row.incident_type,
                    severity=row.severity,
                    status=row.status,
                    attack_vector=row.attack_vector,
                    affected_systems=row.affected_systems or [],
                    description=row.description,
                    timeline=timeline,
                    impact_assessment=impact,
                    response_metrics=response,
                    actions_taken=row.actions_taken or [],
                    created_at=row.created_at,
                )
            )

        return incidents

    # Helper methods

    def _parse_timeframe(self, timeframe: str) -> int:
        """Parse timeframe string to minutes."""
        timeframe_map = {
            "1h": 60,
            "24h": 1440,
            "7d": 10080,
            "30d": 43200,
            "90d": 129600,
        }
        return timeframe_map.get(timeframe, 1440)

    async def _get_recent_security_events(
        self, agent_id: str, window_minutes: int
    ) -> List[SecurityEvent]:
        """Get recent security events for an agent."""
        from ...models.schemas.security import (
            SecurityEventDetails,
            ThreatIndicators,
            ResponseActions,
            SecurityEventContext,
        )

        query = text("""
            SELECT
                id,
                agent_id,
                workspace_id,
                event_type,
                severity,
                category,
                description,
                event_data,
                source_ip,
                user_agent,
                threat_score,
                threat_type,
                ioc_matches,
                behavior_anomaly_score,
                known_threat_pattern,
                action_taken,
                automated_response,
                manual_review_required,
                remediation_steps,
                session_id,
                execution_id,
                related_events,
                affected_resources,
                created_at,
                resolved_at
            FROM analytics.security_events
            WHERE agent_id = :agent_id
                AND created_at > NOW() - INTERVAL ':window_minutes minutes'
            ORDER BY created_at DESC
            LIMIT 50
        """)

        result = await self.db.execute(
            query, {"agent_id": agent_id, "window_minutes": window_minutes}
        )
        rows = result.fetchall()

        events = []
        for row in rows:
            details = SecurityEventDetails(
                type=row.event_type,
                severity=row.severity,
                category=row.category or "unknown",
                description=row.description or "",
                source_ip=str(row.source_ip) if row.source_ip else None,
                user_agent=row.user_agent,
                request_details=row.event_data,
            )

            threat_indicators = ThreatIndicators(
                threat_score=row.threat_score,
                threat_type=row.threat_type,
                ioc_matches=row.ioc_matches or [],
                behavior_anomaly_score=row.behavior_anomaly_score,
                known_threat_pattern=row.known_threat_pattern or False,
            )

            response_actions = ResponseActions(
                action_taken=row.action_taken or "none",
                automated_response=row.automated_response or False,
                manual_review_required=row.manual_review_required or False,
                remediation_steps=row.remediation_steps or [],
            )

            context = SecurityEventContext(
                session_id=str(row.session_id) if row.session_id else None,
                execution_id=str(row.execution_id) if row.execution_id else None,
                related_events=[str(e) for e in (row.related_events or [])],
                affected_resources=row.affected_resources or [],
            )

            events.append(
                SecurityEvent(
                    event_id=str(row.id),
                    agent_id=str(row.agent_id),
                    workspace_id=str(row.workspace_id),
                    event_details=details,
                    threat_indicators=threat_indicators,
                    response_actions=response_actions,
                    context=context,
                    timestamp=row.created_at,
                    resolved_at=row.resolved_at,
                )
            )

        return events

    async def _get_latest_vulnerability_scan(self, agent_id: str):
        """Get latest vulnerability scan for an agent."""
        query = text("""
            SELECT
                scan_id,
                agent_id,
                workspace_id,
                scan_type,
                status,
                critical_vulnerabilities,
                high_vulnerabilities,
                medium_vulnerabilities,
                low_vulnerabilities,
                info_vulnerabilities,
                overall_risk_score,
                exploitable_vulnerabilities,
                started_at,
                completed_at,
                duration_seconds
            FROM analytics.vulnerability_scans
            WHERE agent_id = :agent_id
                AND status = 'completed'
            ORDER BY completed_at DESC
            LIMIT 1
        """)

        result = await self.db.execute(query, {"agent_id": agent_id})
        row = result.fetchone()

        if row:
            from ...models.schemas.security import VulnerabilitySummary, VulnerabilityScan

            summary = VulnerabilitySummary(
                critical=row.critical_vulnerabilities,
                high=row.high_vulnerabilities,
                medium=row.medium_vulnerabilities,
                low=row.low_vulnerabilities,
                info=row.info_vulnerabilities,
            )

            return VulnerabilityScan(
                scan_id=row.scan_id,
                agent_id=str(row.agent_id),
                workspace_id=str(row.workspace_id),
                scan_type=row.scan_type,
                status=row.status,
                vulnerability_summary=summary,
                overall_risk_score=row.overall_risk_score,
                exploitable_vulnerabilities=row.exploitable_vulnerabilities,
                started_at=row.started_at,
                completed_at=row.completed_at,
                duration_seconds=row.duration_seconds,
            )

        return None

    async def _get_access_control_metrics(self, agent_id: str) -> Optional[AccessControlMetrics]:
        """Get access control metrics for an agent."""
        # This would require additional data - simplified version
        return None

    async def _analyze_permission_usage(self, agent_id: str) -> PermissionUsage:
        """Analyze permission usage for an agent."""
        # Simplified implementation
        return PermissionUsage(
            granted_permissions=["read", "write", "execute"],
            used_permissions=["read", "write"],
            unused_permissions=["execute"],
            permission_utilization_rate=66.7,
        )

    async def _analyze_access_patterns(self, agent_id: str) -> AccessPattern:
        """Analyze access patterns for an agent."""
        # Simplified implementation
        return AccessPattern(
            resource_access_frequency={},
            unusual_access_times=[],
            unusual_locations=[],
        )

    async def _analyze_privileges(self, agent_id: str) -> PrivilegeAnalysis:
        """Analyze privilege levels for an agent."""
        query = text("""
            SELECT
                COUNT(*) FILTER (WHERE privilege_escalation_attempt = TRUE) as escalation_attempts
            FROM analytics.access_control_logs
            WHERE agent_id = :agent_id
                AND created_at > NOW() - INTERVAL '30 days'
        """)

        result = await self.db.execute(query, {"agent_id": agent_id})
        row = result.fetchone()

        escalation_attempts = row.escalation_attempts if row else 0

        return PrivilegeAnalysis(
            privilege_level="standard",
            over_privileged=False,
            privilege_escalation_attempts=escalation_attempts,
            least_privilege_score=85.0,
        )

    async def _get_access_compliance_status(self, agent_id: str) -> Dict[str, Any]:
        """Get access compliance status for an agent."""
        return {
            "rbac_compliant": True,
            "policy_violations": [],
            "audit_findings": [],
        }

    def _calculate_exfiltration_risk(
        self, anomalous_count: int, total_count: int, max_anomaly_score: float
    ) -> float:
        """Calculate data exfiltration risk score."""
        if total_count == 0:
            return 0.0

        anomaly_rate = anomalous_count / total_count
        risk = (anomaly_rate * 0.6 + (max_anomaly_score / 100) * 0.4) * 100

        return min(risk, 100.0)

    async def refresh_security_views(self):
        """Refresh security materialized views."""
        logger.info("Refreshing security materialized views")

        query = text("SELECT analytics.refresh_security_materialized_views()")
        await self.db.execute(query)
        await self.db.commit()

        logger.info("Security materialized views refreshed successfully")
