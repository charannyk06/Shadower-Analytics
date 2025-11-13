-- =====================================================================
-- Migration: 028_create_security_analytics_tables.sql
-- Description: Create security analytics tables for threat detection,
--              compliance monitoring, and incident response
-- Created: 2025-11-13
-- =====================================================================

-- Set search path to include both analytics and public schemas
SET search_path TO analytics, public;

-- =====================================================================
-- 1. Security Events Table
-- =====================================================================
CREATE TABLE IF NOT EXISTS security_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),

    -- Event details
    event_data JSONB NOT NULL,
    category VARCHAR(100),
    description TEXT,
    source_ip INET,
    user_agent TEXT,
    user_id UUID,
    session_id UUID,
    execution_id UUID,

    -- Threat assessment
    threat_score FLOAT CHECK (threat_score >= 0 AND threat_score <= 100),
    threat_category VARCHAR(100),
    threat_type VARCHAR(100),
    attack_vector VARCHAR(100),
    ioc_matches TEXT[], -- Indicators of Compromise
    behavior_anomaly_score FLOAT,
    known_threat_pattern BOOLEAN DEFAULT FALSE,

    -- Response and actions
    action_taken VARCHAR(50) CHECK (action_taken IN ('blocked', 'allowed', 'flagged', 'quarantined', 'none')),
    blocked BOOLEAN DEFAULT FALSE,
    automated_response BOOLEAN DEFAULT FALSE,
    manual_review_required BOOLEAN DEFAULT FALSE,
    remediation_steps TEXT[],

    -- Compliance
    compliance_violation BOOLEAN DEFAULT FALSE,
    regulation_violated VARCHAR(50),

    -- Forensics
    request_payload TEXT,
    response_payload TEXT,
    stack_trace TEXT,
    related_events UUID[],
    affected_resources TEXT[],

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolved_by UUID,
    resolution_notes TEXT
);

CREATE INDEX idx_security_events_agent ON security_events(agent_id, created_at DESC);
CREATE INDEX idx_security_events_workspace ON security_events(workspace_id, created_at DESC);
CREATE INDEX idx_security_events_severity ON security_events(severity, created_at DESC);
CREATE INDEX idx_security_events_type ON security_events(event_type, created_at DESC);
CREATE INDEX idx_security_events_threat_score ON security_events(threat_score DESC NULLS LAST);
CREATE INDEX idx_security_events_unresolved ON security_events(created_at DESC) WHERE resolved_at IS NULL;
CREATE INDEX idx_security_events_compliance ON security_events(compliance_violation, created_at DESC) WHERE compliance_violation = TRUE;
CREATE INDEX idx_security_events_data ON security_events USING GIN (event_data);

COMMENT ON TABLE security_events IS 'Security events tracking authentication, authorization, data access, API calls, injections, and anomalies';

-- =====================================================================
-- 2. Data Access Events Table
-- =====================================================================
CREATE TABLE IF NOT EXISTS data_access_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    user_id UUID,

    -- Access details
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(255) NOT NULL,
    operation VARCHAR(20) NOT NULL CHECK (operation IN ('read', 'write', 'delete', 'modify', 'list', 'export')),

    -- Data classification
    data_sensitivity VARCHAR(20) CHECK (data_sensitivity IN ('public', 'internal', 'confidential', 'restricted')),
    contains_pii BOOLEAN DEFAULT FALSE,
    contains_phi BOOLEAN DEFAULT FALSE,

    -- Volume and scope
    records_accessed INTEGER DEFAULT 0,
    data_size_bytes BIGINT DEFAULT 0,

    -- Security context
    encryption_used BOOLEAN DEFAULT FALSE,
    access_justified BOOLEAN DEFAULT TRUE,
    business_justification TEXT,

    -- Anomaly detection
    anomaly_score FLOAT CHECK (anomaly_score >= 0 AND anomaly_score <= 100),
    baseline_deviation FLOAT,
    unusual_volume BOOLEAN DEFAULT FALSE,
    unusual_timing BOOLEAN DEFAULT FALSE,
    unusual_destination BOOLEAN DEFAULT FALSE,

    -- Request context
    source_ip INET,
    session_id UUID,
    request_id UUID,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_data_access_agent ON data_access_events(agent_id, created_at DESC);
CREATE INDEX idx_data_access_workspace ON data_access_events(workspace_id, created_at DESC);
CREATE INDEX idx_data_access_sensitivity ON data_access_events(data_sensitivity, created_at DESC);
CREATE INDEX idx_data_access_anomaly ON data_access_events(anomaly_score DESC NULLS LAST);
CREATE INDEX idx_data_access_pii ON data_access_events(created_at DESC) WHERE contains_pii = TRUE OR contains_phi = TRUE;
CREATE INDEX idx_data_access_unusual ON data_access_events(created_at DESC) WHERE unusual_volume = TRUE OR unusual_timing = TRUE OR unusual_destination = TRUE;

COMMENT ON TABLE data_access_events IS 'Tracks all data access events for security monitoring and compliance';

-- =====================================================================
-- 3. Security Incidents Table
-- =====================================================================
CREATE TABLE IF NOT EXISTS security_incidents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_number VARCHAR(50) UNIQUE NOT NULL,
    agent_id UUID,
    workspace_id UUID NOT NULL,

    -- Incident classification
    incident_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    status VARCHAR(50) NOT NULL CHECK (status IN ('detected', 'investigating', 'contained', 'eradicated', 'recovered', 'closed')),
    attack_vector VARCHAR(100),

    -- Impact assessment
    affected_systems TEXT[],
    affected_agents UUID[],
    users_affected INTEGER DEFAULT 0,
    data_records_exposed INTEGER DEFAULT 0,
    data_compromised BOOLEAN DEFAULT FALSE,
    financial_impact_usd NUMERIC(12, 2),
    reputation_impact VARCHAR(20) CHECK (reputation_impact IN ('high', 'medium', 'low', 'none')),

    -- Timeline
    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    investigated_at TIMESTAMP,
    contained_at TIMESTAMP,
    eradicated_at TIMESTAMP,
    recovered_at TIMESTAMP,
    closed_at TIMESTAMP,

    -- Response metrics
    time_to_detect_minutes INTEGER,
    time_to_respond_minutes INTEGER,
    time_to_contain_minutes INTEGER,
    time_to_resolve_minutes INTEGER,

    -- Investigation details
    description TEXT NOT NULL,
    root_cause TEXT,
    investigation_notes TEXT,
    evidence_collected TEXT[],

    -- Response and remediation
    actions_taken TEXT[],
    patches_applied TEXT[],
    configurations_changed TEXT[],
    lessons_learned TEXT[],

    -- Assignment
    assigned_to UUID,
    assigned_at TIMESTAMP,

    -- Related data
    related_events UUID[],
    related_incidents UUID[],

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

CREATE INDEX idx_security_incidents_workspace ON security_incidents(workspace_id, detected_at DESC);
CREATE INDEX idx_security_incidents_agent ON security_incidents(agent_id, detected_at DESC) WHERE agent_id IS NOT NULL;
CREATE INDEX idx_security_incidents_status ON security_incidents(status, detected_at DESC);
CREATE INDEX idx_security_incidents_severity ON security_incidents(severity, detected_at DESC);
CREATE INDEX idx_security_incidents_open ON security_incidents(detected_at DESC) WHERE status NOT IN ('closed', 'recovered');
CREATE INDEX idx_security_incidents_number ON security_incidents(incident_number);

COMMENT ON TABLE security_incidents IS 'Security incident management and tracking';

-- =====================================================================
-- 4. Attack Patterns Table
-- =====================================================================
CREATE TABLE IF NOT EXISTS attack_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pattern_name VARCHAR(255) NOT NULL,
    pattern_signature TEXT NOT NULL,
    attack_type VARCHAR(100) NOT NULL,
    threat_level VARCHAR(20) NOT NULL CHECK (threat_level IN ('critical', 'high', 'medium', 'low')),

    -- Pattern details
    description TEXT,
    indicators TEXT[],
    typical_sequence TEXT[],
    mitre_attack_ids TEXT[], -- MITRE ATT&CK framework IDs

    -- Detection
    min_match_score FLOAT DEFAULT 0.7,
    enabled BOOLEAN DEFAULT TRUE,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_detected_at TIMESTAMP,
    detection_count INTEGER DEFAULT 0
);

CREATE INDEX idx_attack_patterns_type ON attack_patterns(attack_type, enabled);
CREATE INDEX idx_attack_patterns_threat ON attack_patterns(threat_level, enabled);
CREATE INDEX idx_attack_patterns_enabled ON attack_patterns(enabled) WHERE enabled = TRUE;

COMMENT ON TABLE attack_patterns IS 'Known attack patterns for threat detection';

-- =====================================================================
-- 5. Vulnerability Scans Table
-- =====================================================================
CREATE TABLE IF NOT EXISTS vulnerability_scans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_id VARCHAR(100) UNIQUE NOT NULL,
    agent_id UUID,
    workspace_id UUID NOT NULL,

    -- Scan configuration
    scan_type VARCHAR(50) NOT NULL CHECK (scan_type IN ('comprehensive', 'quick', 'targeted', 'code', 'dependencies', 'configuration')),
    scan_scope TEXT[],

    -- Results summary
    status VARCHAR(50) NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    critical_vulnerabilities INTEGER DEFAULT 0,
    high_vulnerabilities INTEGER DEFAULT 0,
    medium_vulnerabilities INTEGER DEFAULT 0,
    low_vulnerabilities INTEGER DEFAULT 0,
    info_vulnerabilities INTEGER DEFAULT 0,

    -- Risk assessment
    overall_risk_score FLOAT CHECK (overall_risk_score >= 0 AND overall_risk_score <= 100),
    exploitable_vulnerabilities INTEGER DEFAULT 0,

    -- Timing
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,

    -- Results
    vulnerabilities JSONB,
    remediation_plan JSONB,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID
);

CREATE INDEX idx_vulnerability_scans_agent ON vulnerability_scans(agent_id, started_at DESC) WHERE agent_id IS NOT NULL;
CREATE INDEX idx_vulnerability_scans_workspace ON vulnerability_scans(workspace_id, started_at DESC);
CREATE INDEX idx_vulnerability_scans_status ON vulnerability_scans(status, started_at DESC);
CREATE INDEX idx_vulnerability_scans_risk ON vulnerability_scans(overall_risk_score DESC NULLS LAST);

COMMENT ON TABLE vulnerability_scans IS 'Vulnerability scan results and assessments';

-- =====================================================================
-- 6. Compliance Audits Table
-- =====================================================================
CREATE TABLE IF NOT EXISTS compliance_audits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    audit_id VARCHAR(100) UNIQUE NOT NULL,
    workspace_id UUID NOT NULL,

    -- Audit details
    framework VARCHAR(50) NOT NULL CHECK (framework IN ('GDPR', 'HIPAA', 'SOC2', 'ISO27001', 'PCI-DSS', 'CCPA')),
    audit_type VARCHAR(50) NOT NULL CHECK (audit_type IN ('scheduled', 'manual', 'triggered')),
    status VARCHAR(50) NOT NULL CHECK (status IN ('pending', 'in_progress', 'completed', 'failed')),

    -- Scope
    scope_agents UUID[],
    scope_description TEXT,

    -- Results
    compliance_score FLOAT CHECK (compliance_score >= 0 AND compliance_score <= 100),
    requirements_total INTEGER NOT NULL,
    requirements_met INTEGER DEFAULT 0,
    requirements_failed INTEGER DEFAULT 0,
    violations JSONB,

    -- Findings
    critical_findings INTEGER DEFAULT 0,
    high_findings INTEGER DEFAULT 0,
    medium_findings INTEGER DEFAULT 0,
    low_findings INTEGER DEFAULT 0,

    -- Timing
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    next_audit_due TIMESTAMP,

    -- Audit trail
    auditor_id UUID,
    audit_notes TEXT,
    findings_detail JSONB,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_compliance_audits_workspace ON compliance_audits(workspace_id, started_at DESC);
CREATE INDEX idx_compliance_audits_framework ON compliance_audits(framework, started_at DESC);
CREATE INDEX idx_compliance_audits_status ON compliance_audits(status, started_at DESC);
CREATE INDEX idx_compliance_audits_score ON compliance_audits(compliance_score ASC NULLS LAST);

COMMENT ON TABLE compliance_audits IS 'Compliance audit results and tracking';

-- =====================================================================
-- 7. Access Control Logs Table
-- =====================================================================
CREATE TABLE IF NOT EXISTS access_control_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    user_id UUID,

    -- Access details
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    permission_required VARCHAR(100),

    -- Result
    access_granted BOOLEAN NOT NULL,
    denial_reason TEXT,

    -- Context
    privilege_level VARCHAR(50),
    effective_permissions TEXT[],
    requested_permissions TEXT[],

    -- Anomaly detection
    privilege_escalation_attempt BOOLEAN DEFAULT FALSE,
    unusual_access_time BOOLEAN DEFAULT FALSE,
    unusual_location BOOLEAN DEFAULT FALSE,
    anomaly_score FLOAT,

    -- Request context
    source_ip INET,
    user_agent TEXT,
    session_id UUID,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_access_control_agent ON access_control_logs(agent_id, created_at DESC);
CREATE INDEX idx_access_control_workspace ON access_control_logs(workspace_id, created_at DESC);
CREATE INDEX idx_access_control_user ON access_control_logs(user_id, created_at DESC) WHERE user_id IS NOT NULL;
CREATE INDEX idx_access_control_denied ON access_control_logs(created_at DESC) WHERE access_granted = FALSE;
CREATE INDEX idx_access_control_escalation ON access_control_logs(created_at DESC) WHERE privilege_escalation_attempt = TRUE;

COMMENT ON TABLE access_control_logs IS 'Access control decisions and privilege usage tracking';

-- =====================================================================
-- 8. Threat Intelligence Table
-- =====================================================================
CREATE TABLE IF NOT EXISTS threat_intelligence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Threat identification
    threat_id VARCHAR(100) UNIQUE NOT NULL,
    threat_name VARCHAR(255) NOT NULL,
    threat_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low')),

    -- Intelligence data
    description TEXT,
    indicators_of_compromise JSONB,
    attack_patterns TEXT[],
    affected_systems TEXT[],

    -- MITRE ATT&CK mapping
    mitre_tactics TEXT[],
    mitre_techniques TEXT[],

    -- Source and confidence
    source VARCHAR(255),
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 100),

    -- Status
    active BOOLEAN DEFAULT TRUE,
    last_seen TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_threat_intelligence_type ON threat_intelligence(threat_type, active);
CREATE INDEX idx_threat_intelligence_severity ON threat_intelligence(severity, active);
CREATE INDEX idx_threat_intelligence_active ON threat_intelligence(active, created_at DESC);

COMMENT ON TABLE threat_intelligence IS 'Threat intelligence data for proactive security monitoring';

-- =====================================================================
-- 9. Security Baselines Table
-- =====================================================================
CREATE TABLE IF NOT EXISTS security_baselines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,

    -- Baseline type
    baseline_type VARCHAR(50) NOT NULL CHECK (baseline_type IN ('behavioral', 'performance', 'access_pattern', 'data_flow')),

    -- Baseline data
    baseline_data JSONB NOT NULL,
    statistical_model JSONB,

    -- Thresholds
    anomaly_threshold FLOAT DEFAULT 0.7,
    alert_threshold FLOAT DEFAULT 0.8,

    -- Validity
    valid_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP,
    active BOOLEAN DEFAULT TRUE,

    -- Learning period
    learning_period_days INTEGER DEFAULT 30,
    samples_count INTEGER DEFAULT 0,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated_by VARCHAR(50)
);

CREATE INDEX idx_security_baselines_agent ON security_baselines(agent_id, baseline_type, active);
CREATE INDEX idx_security_baselines_workspace ON security_baselines(workspace_id, baseline_type, active);
CREATE INDEX idx_security_baselines_active ON security_baselines(active, valid_until) WHERE active = TRUE;

COMMENT ON TABLE security_baselines IS 'Security baselines for anomaly detection';

-- =====================================================================
-- 10. Materialized View: Security Dashboard Summary
-- =====================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS security_dashboard_summary AS
WITH recent_events AS (
    SELECT
        workspace_id,
        COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as events_24h,
        COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') as events_7d,
        COUNT(*) FILTER (WHERE severity = 'critical') as critical_events,
        COUNT(*) FILTER (WHERE severity = 'high') as high_events,
        AVG(threat_score) as avg_threat_score,
        MAX(threat_score) as max_threat_score
    FROM security_events
    WHERE created_at > NOW() - INTERVAL '30 days'
    GROUP BY workspace_id
),
open_incidents AS (
    SELECT
        workspace_id,
        COUNT(*) as open_incidents_count,
        COUNT(*) FILTER (WHERE severity = 'critical') as critical_incidents,
        AVG(EXTRACT(EPOCH FROM (COALESCE(closed_at, NOW()) - detected_at)) / 60) as avg_resolution_time_minutes
    FROM security_incidents
    WHERE status NOT IN ('closed', 'recovered')
    GROUP BY workspace_id
),
recent_scans AS (
    SELECT
        workspace_id,
        COUNT(*) as total_scans,
        SUM(critical_vulnerabilities) as total_critical_vulns,
        SUM(high_vulnerabilities) as total_high_vulns,
        AVG(overall_risk_score) as avg_risk_score
    FROM vulnerability_scans
    WHERE started_at > NOW() - INTERVAL '30 days'
        AND status = 'completed'
    GROUP BY workspace_id
),
compliance_status AS (
    SELECT
        workspace_id,
        AVG(compliance_score) as avg_compliance_score,
        COUNT(*) FILTER (WHERE status = 'completed') as completed_audits
    FROM compliance_audits
    WHERE started_at > NOW() - INTERVAL '90 days'
    GROUP BY workspace_id
)
SELECT
    COALESCE(re.workspace_id, oi.workspace_id, rs.workspace_id, cs.workspace_id) as workspace_id,
    COALESCE(re.events_24h, 0) as security_events_24h,
    COALESCE(re.events_7d, 0) as security_events_7d,
    COALESCE(re.critical_events, 0) as critical_events,
    COALESCE(re.high_events, 0) as high_events,
    COALESCE(re.avg_threat_score, 0) as avg_threat_score,
    COALESCE(re.max_threat_score, 0) as max_threat_score,
    COALESCE(oi.open_incidents_count, 0) as open_incidents,
    COALESCE(oi.critical_incidents, 0) as critical_incidents,
    COALESCE(oi.avg_resolution_time_minutes, 0) as avg_resolution_time_minutes,
    COALESCE(rs.total_critical_vulns, 0) as critical_vulnerabilities,
    COALESCE(rs.total_high_vulns, 0) as high_vulnerabilities,
    COALESCE(rs.avg_risk_score, 0) as avg_vulnerability_risk_score,
    COALESCE(cs.avg_compliance_score, 0) as avg_compliance_score,
    NOW() as last_updated
FROM recent_events re
FULL OUTER JOIN open_incidents oi ON re.workspace_id = oi.workspace_id
FULL OUTER JOIN recent_scans rs ON COALESCE(re.workspace_id, oi.workspace_id) = rs.workspace_id
FULL OUTER JOIN compliance_status cs ON COALESCE(re.workspace_id, oi.workspace_id, rs.workspace_id) = cs.workspace_id;

CREATE UNIQUE INDEX idx_security_dashboard_summary_workspace ON security_dashboard_summary(workspace_id);

COMMENT ON MATERIALIZED VIEW security_dashboard_summary IS 'Real-time security dashboard metrics aggregated by workspace';

-- =====================================================================
-- 11. Materialized View: Attack Pattern Detection
-- =====================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS attack_pattern_detection AS
WITH event_sequences AS (
    SELECT
        agent_id,
        workspace_id,
        session_id,
        ARRAY_AGG(event_type ORDER BY created_at) as event_sequence,
        ARRAY_AGG(created_at ORDER BY created_at) as timestamps,
        MIN(created_at) as sequence_start,
        MAX(created_at) as sequence_end,
        COUNT(*) as event_count
    FROM security_events
    WHERE created_at > NOW() - INTERVAL '24 hours'
        AND session_id IS NOT NULL
    GROUP BY agent_id, workspace_id, session_id
),
pattern_matches AS (
    SELECT
        es.agent_id,
        es.workspace_id,
        es.session_id,
        ap.pattern_name,
        ap.threat_level,
        ap.attack_type,
        es.event_sequence,
        es.sequence_start,
        es.sequence_end,
        es.event_count,
        -- Calculate similarity between event sequence and pattern
        (
            SELECT COUNT(*)::FLOAT / GREATEST(array_length(es.event_sequence, 1), array_length(ap.typical_sequence, 1))
            FROM unnest(es.event_sequence) e
            WHERE e = ANY(ap.typical_sequence)
        ) as match_score
    FROM event_sequences es
    CROSS JOIN attack_patterns ap
    WHERE ap.enabled = TRUE
)
SELECT
    agent_id,
    workspace_id,
    session_id,
    pattern_name,
    threat_level,
    attack_type,
    match_score,
    event_count,
    sequence_start,
    sequence_end,
    EXTRACT(EPOCH FROM (sequence_end - sequence_start)) as attack_duration_seconds,
    NOW() as detected_at
FROM pattern_matches
WHERE match_score >= 0.6
ORDER BY match_score DESC, threat_level DESC;

CREATE INDEX idx_attack_pattern_detection_agent ON attack_pattern_detection(agent_id, detected_at DESC);
CREATE INDEX idx_attack_pattern_detection_workspace ON attack_pattern_detection(workspace_id, detected_at DESC);
CREATE INDEX idx_attack_pattern_detection_threat ON attack_pattern_detection(threat_level, match_score DESC);

COMMENT ON MATERIALIZED VIEW attack_pattern_detection IS 'Real-time attack pattern detection based on event sequences';

-- =====================================================================
-- 12. Refresh Function for Materialized Views
-- =====================================================================
CREATE OR REPLACE FUNCTION refresh_security_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY security_dashboard_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY attack_pattern_detection;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_security_materialized_views IS 'Refresh all security analytics materialized views';

-- =====================================================================
-- 13. Grant Permissions
-- =====================================================================
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO authenticated;
GRANT INSERT, UPDATE ON security_events, data_access_events, access_control_logs TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA analytics TO service_role;

-- Grant usage on sequences
GRANT USAGE ON ALL SEQUENCES IN SCHEMA analytics TO authenticated;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA analytics TO service_role;

-- =====================================================================
-- End of Migration
-- =====================================================================
