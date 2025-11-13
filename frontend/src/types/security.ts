/**
 * Security analytics types for the Shadower platform
 */

export type SecurityEventType =
  | 'authentication'
  | 'authorization'
  | 'data_access'
  | 'api_call'
  | 'injection'
  | 'anomaly';

export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export type ActionTaken = 'blocked' | 'allowed' | 'flagged' | 'quarantined' | 'none';

export type IncidentStatus =
  | 'detected'
  | 'investigating'
  | 'contained'
  | 'eradicated'
  | 'recovered'
  | 'closed';

export type DataSensitivity = 'public' | 'internal' | 'confidential' | 'restricted';

export type ComplianceFramework = 'GDPR' | 'HIPAA' | 'SOC2' | 'ISO27001' | 'PCI-DSS' | 'CCPA';

export interface ThreatIndicators {
  threat_score?: number;
  threat_type?: string;
  ioc_matches?: string[];
  behavior_anomaly_score?: number;
  known_threat_pattern: boolean;
}

export interface ResponseActions {
  action_taken: ActionTaken;
  automated_response: boolean;
  manual_review_required: boolean;
  remediation_steps?: string[];
}

export interface SecurityEventContext {
  session_id?: string;
  execution_id?: string;
  related_events?: string[];
  affected_resources?: string[];
}

export interface SecurityEventDetails {
  type: SecurityEventType;
  severity: Severity;
  category: string;
  description: string;
  source_ip?: string;
  user_agent?: string;
  request_details?: any;
}

export interface SecurityEvent {
  event_id: string;
  agent_id: string;
  workspace_id: string;
  event_details: SecurityEventDetails;
  threat_indicators: ThreatIndicators;
  response_actions: ResponseActions;
  context: SecurityEventContext;
  timestamp: string;
  resolved_at?: string;
}

export interface BehavioralAnomaly {
  event_id: string;
  anomaly_type: string;
  deviation_score: number;
  features_affected: string[];
}

export interface ThreatDetectionResult {
  agent_id: string;
  threat_level: number;
  behavioral_anomalies: BehavioralAnomaly[];
  pattern_matches: any[];
  statistical_outliers: any[];
  risk_score: number;
  recommended_actions: string[];
  timestamp: string;
}

export interface VulnerabilitySummary {
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
}

export interface VulnerabilityDetails {
  vulnerability_id: string;
  title: string;
  description: string;
  severity: Severity;
  cvss_score?: number;
  exploitability?: string;
  affected_component: string;
  remediation?: string;
}

export interface VulnerabilityScan {
  scan_id: string;
  agent_id?: string;
  workspace_id: string;
  scan_type: string;
  status: string;
  vulnerability_summary: VulnerabilitySummary;
  overall_risk_score?: number;
  exploitable_vulnerabilities: number;
  started_at: string;
  completed_at?: string;
  duration_seconds?: number;
}

export interface VulnerabilityScanResult {
  scan: VulnerabilityScan;
  vulnerabilities: VulnerabilityDetails[];
  remediation_plan?: any;
}

export interface ImpactAssessment {
  users_affected: number;
  data_records_exposed: number;
  financial_impact_usd?: number;
  reputation_impact?: string;
}

export interface IncidentTimeline {
  detected_at: string;
  investigated_at?: string;
  contained_at?: string;
  resolved_at?: string;
  total_duration_hours?: number;
}

export interface ResponseMetrics {
  time_to_detect?: number;
  time_to_respond?: number;
  time_to_contain?: number;
  time_to_resolve?: number;
}

export interface SecurityIncident {
  incident_id: string;
  incident_number: string;
  agent_id?: string;
  workspace_id: string;
  incident_type: string;
  severity: Severity;
  status: IncidentStatus;
  attack_vector?: string;
  affected_systems: string[];
  description: string;
  timeline: IncidentTimeline;
  impact_assessment: ImpactAssessment;
  response_metrics: ResponseMetrics;
  actions_taken: string[];
  created_at: string;
}

export interface SecurityDashboardSummary {
  workspace_id: string;
  security_events_24h: number;
  security_events_7d: number;
  critical_events: number;
  high_events: number;
  avg_threat_score: number;
  max_threat_score: number;
  open_incidents: number;
  critical_incidents: number;
  avg_resolution_time_minutes: number;
  critical_vulnerabilities: number;
  high_vulnerabilities: number;
  avg_vulnerability_risk_score: number;
  avg_compliance_score: number;
  last_updated: string;
}

export interface PermissionUsage {
  granted_permissions: string[];
  used_permissions: string[];
  unused_permissions: string[];
  permission_utilization_rate: number;
}

export interface AccessPattern {
  resource_access_frequency: Record<string, number>;
  unusual_access_times: string[];
  unusual_locations: string[];
}

export interface PrivilegeAnalysis {
  privilege_level: string;
  over_privileged: boolean;
  privilege_escalation_attempts: number;
  least_privilege_score: number;
}

export interface AccessControlMetrics {
  agent_id: string;
  permission_usage: PermissionUsage;
  access_patterns: AccessPattern;
  privilege_analysis: PrivilegeAnalysis;
  compliance_status: any;
}

export interface DataAccessAnalytics {
  total_access_events: number;
  pii_access_count: number;
  phi_access_count: number;
  high_risk_access_count: number;
  anomalous_access_count: number;
  avg_anomaly_score: number;
  data_exfiltration_risk: number;
  top_accessed_resources: any[];
}

export interface ComplianceViolation {
  requirement_id: string;
  description: string;
  severity: Severity;
  remediation_deadline?: string;
}

export interface ComplianceMetrics {
  framework: ComplianceFramework;
  compliance_score: number;
  requirements_met: number;
  requirements_total: number;
  violations: ComplianceViolation[];
  last_audit: string;
}

export interface ThreatAnalysis {
  agent_id: string;
  timeframe: string;
  threat_detection: ThreatDetectionResult;
  recent_events: SecurityEvent[];
  vulnerability_status?: VulnerabilityScan;
  access_control_metrics?: AccessControlMetrics;
}

export interface SecurityAnalyticsResponse {
  summary: SecurityDashboardSummary;
  threat_analysis?: ThreatAnalysis;
  compliance_status?: ComplianceMetrics[];
  recent_incidents: SecurityIncident[];
}
