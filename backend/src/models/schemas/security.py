"""Security analytics schemas."""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# =====================================================================
# Enums
# =====================================================================

class SecurityEventType(str, Enum):
    """Security event types."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    API_CALL = "api_call"
    INJECTION = "injection"
    ANOMALY = "anomaly"


class Severity(str, Enum):
    """Severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ActionTaken(str, Enum):
    """Response actions."""
    BLOCKED = "blocked"
    ALLOWED = "allowed"
    FLAGGED = "flagged"
    QUARANTINED = "quarantined"
    NONE = "none"


class IncidentStatus(str, Enum):
    """Incident status."""
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    ERADICATED = "eradicated"
    RECOVERED = "recovered"
    CLOSED = "closed"


class DataSensitivity(str, Enum):
    """Data sensitivity levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class ComplianceFramework(str, Enum):
    """Compliance frameworks."""
    GDPR = "GDPR"
    HIPAA = "HIPAA"
    SOC2 = "SOC2"
    ISO27001 = "ISO27001"
    PCI_DSS = "PCI-DSS"
    CCPA = "CCPA"


# =====================================================================
# Security Event Schemas
# =====================================================================

class ThreatIndicators(BaseModel):
    """Threat indicators for security events."""
    threat_score: Optional[float] = Field(None, ge=0, le=100)
    threat_type: Optional[str] = None
    ioc_matches: Optional[List[str]] = Field(default_factory=list)
    behavior_anomaly_score: Optional[float] = Field(None, ge=0, le=100)
    known_threat_pattern: bool = False


class ResponseActions(BaseModel):
    """Response actions taken for security events."""
    action_taken: ActionTaken = ActionTaken.NONE
    automated_response: bool = False
    manual_review_required: bool = False
    remediation_steps: Optional[List[str]] = Field(default_factory=list)


class SecurityEventContext(BaseModel):
    """Context information for security events."""
    session_id: Optional[str] = None
    execution_id: Optional[str] = None
    related_events: Optional[List[str]] = Field(default_factory=list)
    affected_resources: Optional[List[str]] = Field(default_factory=list)


class SecurityEventDetails(BaseModel):
    """Detailed information about a security event."""
    type: SecurityEventType
    severity: Severity
    category: str
    description: str
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    request_details: Optional[Dict[str, Any]] = None


class SecurityEvent(BaseModel):
    """Security event model."""
    event_id: str = Field(..., alias="id")
    agent_id: str
    workspace_id: str
    event_details: SecurityEventDetails
    threat_indicators: ThreatIndicators
    response_actions: ResponseActions
    context: SecurityEventContext
    timestamp: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        populate_by_name = True


class SecurityEventCreate(BaseModel):
    """Create security event request."""
    agent_id: str
    workspace_id: str
    event_type: SecurityEventType
    severity: Severity
    category: str
    description: str
    event_data: Dict[str, Any]
    threat_score: Optional[float] = Field(None, ge=0, le=100)
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None


# =====================================================================
# Data Access Schemas
# =====================================================================

class DataAccessEvent(BaseModel):
    """Data access event model."""
    id: str
    agent_id: str
    workspace_id: str
    user_id: Optional[str] = None
    resource_type: str
    resource_id: str
    operation: str
    data_sensitivity: Optional[DataSensitivity] = None
    contains_pii: bool = False
    contains_phi: bool = False
    records_accessed: int = 0
    data_size_bytes: int = 0
    encryption_used: bool = False
    anomaly_score: Optional[float] = Field(None, ge=0, le=100)
    unusual_volume: bool = False
    unusual_timing: bool = False
    unusual_destination: bool = False
    created_at: datetime


class DataAccessAnalytics(BaseModel):
    """Data access analytics."""
    total_access_events: int
    pii_access_count: int
    phi_access_count: int
    high_risk_access_count: int
    anomalous_access_count: int
    avg_anomaly_score: float
    data_exfiltration_risk: float
    top_accessed_resources: List[Dict[str, Any]]


# =====================================================================
# Security Incident Schemas
# =====================================================================

class ImpactAssessment(BaseModel):
    """Impact assessment for security incidents."""
    users_affected: int = 0
    data_records_exposed: int = 0
    financial_impact_usd: Optional[float] = None
    reputation_impact: Optional[str] = None


class IncidentTimeline(BaseModel):
    """Timeline for security incidents."""
    detected_at: datetime
    investigated_at: Optional[datetime] = None
    contained_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    total_duration_hours: Optional[float] = None


class ResponseMetrics(BaseModel):
    """Response metrics for security incidents."""
    time_to_detect: Optional[int] = None
    time_to_respond: Optional[int] = None
    time_to_contain: Optional[int] = None
    time_to_resolve: Optional[int] = None


class SecurityIncident(BaseModel):
    """Security incident model."""
    incident_id: str
    incident_number: str
    agent_id: Optional[str] = None
    workspace_id: str
    incident_type: str
    severity: Severity
    status: IncidentStatus
    attack_vector: Optional[str] = None
    affected_systems: List[str] = Field(default_factory=list)
    description: str
    timeline: IncidentTimeline
    impact_assessment: ImpactAssessment
    response_metrics: ResponseMetrics
    actions_taken: List[str] = Field(default_factory=list)
    created_at: datetime


class SecurityIncidentCreate(BaseModel):
    """Create security incident request."""
    agent_id: Optional[str] = None
    workspace_id: str
    incident_type: str
    severity: Severity
    description: str
    attack_vector: Optional[str] = None
    affected_systems: Optional[List[str]] = Field(default_factory=list)


# =====================================================================
# Vulnerability Scan Schemas
# =====================================================================

class VulnerabilitySummary(BaseModel):
    """Summary of vulnerabilities found."""
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0


class VulnerabilityDetails(BaseModel):
    """Detailed vulnerability information."""
    vulnerability_id: str
    title: str
    description: str
    severity: Severity
    cvss_score: Optional[float] = Field(None, ge=0, le=10)
    exploitability: Optional[str] = None
    affected_component: str
    remediation: Optional[str] = None


class VulnerabilityScan(BaseModel):
    """Vulnerability scan model."""
    scan_id: str
    agent_id: Optional[str] = None
    workspace_id: str
    scan_type: str
    status: str
    vulnerability_summary: VulnerabilitySummary
    overall_risk_score: Optional[float] = Field(None, ge=0, le=100)
    exploitable_vulnerabilities: int = 0
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None


class VulnerabilityScanCreate(BaseModel):
    """Create vulnerability scan request."""
    agent_id: Optional[str] = None
    workspace_id: str
    scan_type: str = "comprehensive"
    scan_scope: Optional[List[str]] = Field(default_factory=list)


class VulnerabilityScanResult(BaseModel):
    """Vulnerability scan result."""
    scan: VulnerabilityScan
    vulnerabilities: List[VulnerabilityDetails]
    remediation_plan: Optional[Dict[str, Any]] = None


# =====================================================================
# Compliance Schemas
# =====================================================================

class ComplianceViolation(BaseModel):
    """Compliance violation details."""
    requirement_id: str
    description: str
    severity: Severity
    remediation_deadline: Optional[datetime] = None


class ComplianceMetrics(BaseModel):
    """Compliance metrics."""
    framework: ComplianceFramework
    compliance_score: float = Field(..., ge=0, le=100)
    requirements_met: int
    requirements_total: int
    violations: List[ComplianceViolation] = Field(default_factory=list)
    last_audit: datetime


class ComplianceAudit(BaseModel):
    """Compliance audit model."""
    audit_id: str
    workspace_id: str
    framework: ComplianceFramework
    status: str
    compliance_score: Optional[float] = Field(None, ge=0, le=100)
    requirements_total: int
    requirements_met: int = 0
    requirements_failed: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    medium_findings: int = 0
    low_findings: int = 0
    started_at: datetime
    completed_at: Optional[datetime] = None


class ComplianceAuditCreate(BaseModel):
    """Create compliance audit request."""
    workspace_id: str
    framework: ComplianceFramework
    scope_agents: Optional[List[str]] = Field(default_factory=list)
    scope_description: Optional[str] = None


# =====================================================================
# Threat Detection Schemas
# =====================================================================

class BehavioralAnomaly(BaseModel):
    """Behavioral anomaly detection result."""
    event_id: str
    anomaly_type: str
    deviation_score: float
    features_affected: List[str]


class ThreatDetectionResult(BaseModel):
    """Threat detection analysis result."""
    agent_id: str
    threat_level: float = Field(..., ge=0, le=100)
    behavioral_anomalies: List[BehavioralAnomaly] = Field(default_factory=list)
    pattern_matches: List[Dict[str, Any]] = Field(default_factory=list)
    statistical_outliers: List[Dict[str, Any]] = Field(default_factory=list)
    risk_score: float = Field(..., ge=0, le=100)
    recommended_actions: List[str] = Field(default_factory=list)
    timestamp: datetime


class AttackPattern(BaseModel):
    """Attack pattern model."""
    pattern_id: str
    pattern_name: str
    attack_type: str
    threat_level: Severity
    description: Optional[str] = None
    indicators: List[str] = Field(default_factory=list)
    mitre_attack_ids: List[str] = Field(default_factory=list)
    detection_count: int = 0
    last_detected_at: Optional[datetime] = None


# =====================================================================
# Access Control Schemas
# =====================================================================

class PermissionUsage(BaseModel):
    """Permission usage analysis."""
    granted_permissions: List[str]
    used_permissions: List[str]
    unused_permissions: List[str]
    permission_utilization_rate: float = Field(..., ge=0, le=100)


class AccessPattern(BaseModel):
    """Access pattern analysis."""
    resource_access_frequency: Dict[str, int]
    unusual_access_times: List[str] = Field(default_factory=list)
    unusual_locations: List[str] = Field(default_factory=list)


class PrivilegeAnalysis(BaseModel):
    """Privilege analysis."""
    privilege_level: str
    over_privileged: bool
    privilege_escalation_attempts: int = 0
    least_privilege_score: float = Field(..., ge=0, le=100)


class AccessControlMetrics(BaseModel):
    """Access control metrics."""
    agent_id: str
    permission_usage: PermissionUsage
    access_patterns: AccessPattern
    privilege_analysis: PrivilegeAnalysis
    compliance_status: Dict[str, Any]


# =====================================================================
# Security Dashboard Schemas
# =====================================================================

class SecurityDashboardSummary(BaseModel):
    """Security dashboard summary."""
    workspace_id: str
    security_events_24h: int
    security_events_7d: int
    critical_events: int
    high_events: int
    avg_threat_score: float
    max_threat_score: float
    open_incidents: int
    critical_incidents: int
    avg_resolution_time_minutes: float
    critical_vulnerabilities: int
    high_vulnerabilities: int
    avg_vulnerability_risk_score: float
    avg_compliance_score: float
    last_updated: datetime


class ThreatAnalysis(BaseModel):
    """Comprehensive threat analysis."""
    agent_id: str
    timeframe: str
    threat_detection: ThreatDetectionResult
    recent_events: List[SecurityEvent]
    vulnerability_status: Optional[VulnerabilityScan] = None
    access_control_metrics: Optional[AccessControlMetrics] = None


class SecurityAnalyticsResponse(BaseModel):
    """Security analytics response."""
    summary: SecurityDashboardSummary
    threat_analysis: Optional[ThreatAnalysis] = None
    compliance_status: Optional[List[ComplianceMetrics]] = None
    recent_incidents: List[SecurityIncident] = Field(default_factory=list)
