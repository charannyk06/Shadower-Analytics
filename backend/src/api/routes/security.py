"""Security analytics API routes."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, HTTPException
from datetime import datetime

from ...core.database import get_db
from ...models.schemas.security import (
    SecurityDashboardSummary,
    SecurityAnalyticsResponse,
    ThreatAnalysis,
    ThreatDetectionResult,
    VulnerabilityScanCreate,
    VulnerabilityScanResult,
    SecurityIncident,
    SecurityEventCreate,
    SecurityEvent,
    AccessControlMetrics,
    DataAccessAnalytics,
    ComplianceMetrics,
    ComplianceFramework,
)
from ...services.security.security_analytics_service import SecurityAnalyticsService
from ...services.security.threat_detection_service import ThreatDetectionEngine
from ...services.security.vulnerability_scanner_service import VulnerabilityScanner
from ...middleware.auth import get_current_user
from ...middleware.workspace import validate_workspace_access

router = APIRouter(prefix="/api/v1/security", tags=["security"])
logger = logging.getLogger(__name__)


@router.get("/dashboard/{workspace_id}", response_model=SecurityDashboardSummary)
async def get_security_dashboard(
    workspace_id: str = Path(..., description="Workspace ID"),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get security dashboard summary for a workspace.

    Provides real-time security metrics including:
    - Recent security events
    - Open incidents
    - Vulnerability summary
    - Compliance status
    - Threat levels
    """
    try:
        service = SecurityAnalyticsService(db)
        dashboard = await service.get_security_dashboard(workspace_id)
        return dashboard
    except Exception as e:
        logger.error(f"Error fetching security dashboard: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch security dashboard: {str(e)}")


@router.get("/threats/{agent_id}", response_model=ThreatDetectionResult)
async def get_threat_analysis(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query("24h", description="Time range: 1h, 24h, 7d, 30d"),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get threat analysis for a specific agent.

    Performs real-time threat detection including:
    - Behavioral anomaly detection
    - Attack pattern matching
    - Statistical outlier detection
    - Risk assessment
    - Security recommendations
    """
    try:
        logger.info(f"Threat analysis requested for agent {agent_id}, timeframe {timeframe}")

        # Parse timeframe to minutes
        timeframe_map = {"1h": 60, "24h": 1440, "7d": 10080, "30d": 43200}
        window_minutes = timeframe_map.get(timeframe, 1440)

        engine = ThreatDetectionEngine(db)
        result = await engine.detect_threats(agent_id, window_minutes)

        return result
    except Exception as e:
        logger.error(f"Error in threat analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Threat analysis failed: {str(e)}")


@router.get("/analytics/{agent_id}", response_model=ThreatAnalysis)
async def get_comprehensive_threat_analysis(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query("24h", description="Time range: 1h, 24h, 7d, 30d"),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get comprehensive threat analysis for an agent.

    Includes:
    - Threat detection results
    - Recent security events
    - Latest vulnerability scan
    - Access control metrics
    """
    try:
        service = SecurityAnalyticsService(db)
        analysis = await service.get_threat_analysis(agent_id, timeframe)
        return analysis
    except Exception as e:
        logger.error(f"Error in comprehensive threat analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/vulnerabilities/scan", response_model=VulnerabilityScanResult)
async def scan_vulnerabilities(
    scan_request: VulnerabilityScanCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Perform vulnerability scan on an agent or workspace.

    Scan types:
    - comprehensive: Full security scan (code, dependencies, config, APIs)
    - quick: Fast scan of critical areas
    - targeted: Scan specific components
    - code: Code vulnerability scan
    - dependencies: Dependency vulnerability scan
    - configuration: Configuration security scan
    """
    try:
        logger.info(f"Starting vulnerability scan: {scan_request.dict()}")

        scanner = VulnerabilityScanner(db)
        result = await scanner.scan_agent_vulnerabilities(
            agent_id=scan_request.agent_id,
            workspace_id=scan_request.workspace_id,
            scan_type=scan_request.scan_type,
        )

        return result
    except Exception as e:
        logger.error(f"Vulnerability scan failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@router.get("/vulnerabilities/{scan_id}", response_model=VulnerabilityScanResult)
async def get_vulnerability_scan(
    scan_id: str = Path(..., description="Scan ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """Get details of a specific vulnerability scan."""
    try:
        # Query scan from database
        from sqlalchemy import text

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
                duration_seconds,
                vulnerabilities,
                remediation_plan
            FROM analytics.vulnerability_scans
            WHERE scan_id = :scan_id AND workspace_id = :workspace_id
        """)

        result = await db.execute(query, {"scan_id": scan_id, "workspace_id": workspace_id})
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Scan not found")

        from ...models.schemas.security import VulnerabilitySummary, VulnerabilityScan

        summary = VulnerabilitySummary(
            critical=row.critical_vulnerabilities,
            high=row.high_vulnerabilities,
            medium=row.medium_vulnerabilities,
            low=row.low_vulnerabilities,
            info=row.info_vulnerabilities,
        )

        scan = VulnerabilityScan(
            scan_id=row.scan_id,
            agent_id=str(row.agent_id) if row.agent_id else None,
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

        return VulnerabilityScanResult(
            scan=scan,
            vulnerabilities=row.vulnerabilities or [],
            remediation_plan=row.remediation_plan,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching vulnerability scan: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch scan: {str(e)}")


@router.get("/incidents/{workspace_id}", response_model=List[SecurityIncident])
async def get_security_incidents(
    workspace_id: str = Path(..., description="Workspace ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get security incidents for a workspace.

    Filters:
    - status: detected, investigating, contained, eradicated, recovered, closed
    - severity: critical, high, medium, low
    """
    try:
        service = SecurityAnalyticsService(db)
        incidents = await service.get_recent_incidents(workspace_id, limit)

        # Apply filters
        if status:
            incidents = [i for i in incidents if i.status == status]
        if severity:
            incidents = [i for i in incidents if i.severity == severity]

        return incidents
    except Exception as e:
        logger.error(f"Error fetching incidents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch incidents: {str(e)}")


@router.get("/access-control/{agent_id}", response_model=AccessControlMetrics)
async def get_access_control_metrics(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get access control metrics and privilege analysis for an agent.

    Includes:
    - Permission usage analysis
    - Access patterns
    - Privilege escalation detection
    - Compliance status
    """
    try:
        service = SecurityAnalyticsService(db)
        metrics = await service.get_access_control_metrics(agent_id)

        if not metrics:
            raise HTTPException(status_code=404, detail="No access control data found")

        return metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching access control metrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics: {str(e)}")


@router.get("/data-access/{workspace_id}", response_model=DataAccessAnalytics)
async def get_data_access_analytics(
    workspace_id: str = Path(..., description="Workspace ID"),
    timeframe: str = Query("7d", description="Time range: 1h, 24h, 7d, 30d"),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get data access analytics for a workspace.

    Monitors:
    - PII/PHI access
    - Data sensitivity levels
    - Anomalous access patterns
    - Data exfiltration risk
    - Top accessed resources
    """
    try:
        service = SecurityAnalyticsService(db)
        analytics = await service.get_data_access_analytics(workspace_id, timeframe)
        return analytics
    except Exception as e:
        logger.error(f"Error fetching data access analytics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {str(e)}")


@router.post("/events", response_model=dict)
async def create_security_event(
    event: SecurityEventCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create a new security event.

    Used for logging security-related events such as:
    - Authentication attempts
    - Authorization failures
    - Data access
    - API calls
    - Injection attempts
    - Anomalies
    """
    try:
        from sqlalchemy import text
        import uuid

        query = text("""
            INSERT INTO analytics.security_events (
                id,
                agent_id,
                workspace_id,
                event_type,
                severity,
                category,
                description,
                event_data,
                threat_score,
                source_ip,
                user_agent,
                created_at
            ) VALUES (
                :id,
                :agent_id,
                :workspace_id,
                :event_type,
                :severity,
                :category,
                :description,
                :event_data::jsonb,
                :threat_score,
                :source_ip,
                :user_agent,
                NOW()
            )
            RETURNING id
        """)

        event_id = uuid.uuid4()

        result = await db.execute(
            query,
            {
                "id": event_id,
                "agent_id": event.agent_id,
                "workspace_id": event.workspace_id,
                "event_type": event.event_type,
                "severity": event.severity,
                "category": event.category,
                "description": event.description,
                "event_data": str(event.event_data),
                "threat_score": event.threat_score,
                "source_ip": event.source_ip,
                "user_agent": event.user_agent,
            },
        )
        await db.commit()

        return {"event_id": str(event_id), "status": "created"}

    except Exception as e:
        logger.error(f"Error creating security event: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create event: {str(e)}")


@router.post("/refresh-views")
async def refresh_security_views(
    workspace_id: str = Query(..., description="Workspace ID"),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Refresh security materialized views.

    Triggers recalculation of:
    - Security dashboard summary
    - Attack pattern detection
    - Threat indicators
    """
    try:
        service = SecurityAnalyticsService(db)
        await service.refresh_security_views()

        return {"status": "success", "message": "Security views refreshed"}
    except Exception as e:
        logger.error(f"Error refreshing security views: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to refresh views: {str(e)}")


@router.get("/events/{agent_id}", response_model=List[SecurityEvent])
async def get_security_events(
    agent_id: str = Path(..., description="Agent ID"),
    workspace_id: str = Query(..., description="Workspace ID"),
    timeframe: str = Query("24h", description="Time range: 1h, 24h, 7d, 30d"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(100, ge=1, le=1000),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
):
    """
    Get security events for an agent.

    Filters:
    - timeframe: Time range for events
    - severity: Filter by severity level
    - event_type: Filter by event type
    """
    try:
        service = SecurityAnalyticsService(db)

        # Parse timeframe
        timeframe_map = {"1h": 60, "24h": 1440, "7d": 10080, "30d": 43200}
        window_minutes = timeframe_map.get(timeframe, 1440)

        events = await service._get_recent_security_events(agent_id, window_minutes)

        # Apply filters
        if severity:
            events = [e for e in events if e.event_details.severity == severity]
        if event_type:
            events = [e for e in events if e.event_details.type == event_type]

        return events[:limit]
    except Exception as e:
        logger.error(f"Error fetching security events: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch events: {str(e)}")
