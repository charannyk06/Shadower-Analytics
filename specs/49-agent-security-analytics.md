# Agent Security Analytics Specification

## Overview
Comprehensive security monitoring, threat detection, and compliance analytics for agent operations within the Shadower platform.

## Core Components

### 1. Security Event Monitoring

#### 1.1 Security Event Model
```typescript
interface SecurityEvent {
  event_id: string;
  agent_id: string;
  workspace_id: string;
  event_details: {
    type: 'authentication' | 'authorization' | 'data_access' | 'api_call' | 'injection' | 'anomaly';
    severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
    category: string;
    description: string;
    source_ip?: string;
    user_agent?: string;
    request_details?: any;
  };
  threat_indicators: {
    threat_score: number;
    threat_type?: string;
    ioc_matches?: string[]; // Indicators of Compromise
    behavior_anomaly_score?: number;
    known_threat_pattern?: boolean;
  };
  response_actions: {
    action_taken: 'blocked' | 'allowed' | 'flagged' | 'quarantined';
    automated_response: boolean;
    manual_review_required: boolean;
    remediation_steps?: string[];
  };
  context: {
    session_id?: string;
    execution_id?: string;
    related_events?: string[];
    affected_resources?: string[];
  };
  timestamp: string;
}
```

#### 1.2 Security Event Database
```sql
CREATE TABLE security_events (
    id UUID PRIMARY KEY,
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    
    -- Event details
    event_data JSONB NOT NULL,
    source_ip INET,
    user_id UUID,
    session_id UUID,
    
    -- Threat assessment
    threat_score FLOAT,
    threat_category VARCHAR(100),
    attack_vector VARCHAR(100),
    
    -- Response
    action_taken VARCHAR(50),
    blocked BOOLEAN DEFAULT FALSE,
    
    -- Compliance
    compliance_violation BOOLEAN DEFAULT FALSE,
    regulation_violated VARCHAR(50),
    
    -- Forensics
    request_payload TEXT,
    response_payload TEXT,
    stack_trace TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE INDEX idx_security_events_agent ON security_events(agent_id, created_at);
CREATE INDEX idx_security_events_severity ON security_events(severity, created_at);
CREATE INDEX idx_security_events_threat ON security_events(threat_score DESC);
```

### 2. Threat Detection System

#### 2.1 Anomaly Detection Engine
```python
class ThreatDetectionEngine:
    def detect_threats(self, agent_id: str, window_minutes: int = 60):
        events = self.get_recent_events(agent_id, window_minutes)
        
        threats = {
            "behavioral_anomalies": self.detect_behavioral_anomalies(events),
            "pattern_matches": self.match_threat_patterns(events),
            "statistical_outliers": self.find_statistical_outliers(events),
            "ml_predictions": self.predict_threats_ml(events),
            "correlation_threats": self.correlate_threat_indicators(events)
        }
        
        # Calculate overall threat level
        threat_level = self.calculate_threat_level(threats)
        
        # Generate alerts if necessary
        if threat_level > self.alert_threshold:
            self.generate_security_alert(agent_id, threats, threat_level)
        
        return {
            "threat_level": threat_level,
            "active_threats": self.filter_active_threats(threats),
            "risk_score": self.calculate_risk_score(threats),
            "recommended_actions": self.generate_recommendations(threats)
        }
    
    def detect_behavioral_anomalies(self, events):
        # Build behavior baseline
        baseline = self.get_behavior_baseline(events[0].agent_id)
        
        anomalies = []
        for event in events:
            # Extract behavioral features
            features = self.extract_behavioral_features(event)
            
            # Calculate deviation from baseline
            deviation = self.calculate_deviation(features, baseline)
            
            if deviation > self.anomaly_threshold:
                anomalies.append({
                    "event_id": event.id,
                    "anomaly_type": self.classify_anomaly(features, baseline),
                    "deviation_score": deviation,
                    "features_affected": self.identify_anomalous_features(features, baseline)
                })
        
        return anomalies
```

#### 2.2 Attack Pattern Recognition
```sql
CREATE MATERIALIZED VIEW attack_pattern_detection AS
WITH event_sequences AS (
    SELECT 
        agent_id,
        session_id,
        ARRAY_AGG(
            event_type ORDER BY created_at
        ) as event_sequence,
        ARRAY_AGG(
            created_at ORDER BY created_at
        ) as timestamps,
        MIN(created_at) as sequence_start,
        MAX(created_at) as sequence_end
    FROM security_events
    WHERE created_at > NOW() - INTERVAL '24 hours'
    GROUP BY agent_id, session_id
),
pattern_matches AS (
    SELECT 
        es.*,
        ap.pattern_name,
        ap.threat_level,
        ap.attack_type,
        similarity(
            array_to_string(es.event_sequence, ','),
            ap.pattern_signature
        ) as match_score
    FROM event_sequences es
    CROSS JOIN attack_patterns ap
    WHERE similarity(
        array_to_string(es.event_sequence, ','),
        ap.pattern_signature
    ) > 0.7
)
SELECT 
    agent_id,
    session_id,
    pattern_name,
    threat_level,
    attack_type,
    match_score,
    sequence_start,
    sequence_end,
    EXTRACT(EPOCH FROM (sequence_end - sequence_start)) as attack_duration_seconds
FROM pattern_matches
ORDER BY match_score DESC, threat_level DESC;
```

### 3. Access Control Analytics

#### 3.1 Permission Usage Analysis
```typescript
interface AccessControlMetrics {
  agent_id: string;
  permission_usage: {
    granted_permissions: string[];
    used_permissions: string[];
    unused_permissions: string[];
    permission_utilization_rate: number;
  };
  access_patterns: {
    resource_access_frequency: Map<string, number>;
    time_based_patterns: {
      hour_distribution: number[];
      day_distribution: number[];
      unusual_access_times: string[];
    };
    geographic_patterns: {
      common_locations: string[];
      unusual_locations: string[];
      vpn_usage: number;
    };
  };
  privilege_analysis: {
    privilege_level: 'minimal' | 'standard' | 'elevated' | 'admin';
    over_privileged: boolean;
    privilege_escalation_attempts: number;
    least_privilege_score: number;
  };
  compliance_status: {
    rbac_compliant: boolean;
    policy_violations: string[];
    audit_findings: string[];
  };
}
```

#### 3.2 Privilege Escalation Detection
```python
class PrivilegeEscalationDetector:
    def detect_privilege_escalation(self, agent_id: str):
        access_logs = self.get_access_logs(agent_id)
        
        escalation_indicators = {
            "direct_attempts": self.find_direct_escalation_attempts(access_logs),
            "lateral_movement": self.detect_lateral_movement(access_logs),
            "permission_creep": self.identify_permission_creep(access_logs),
            "unusual_elevation": self.find_unusual_elevations(access_logs)
        }
        
        risk_assessment = {
            "escalation_risk_score": self.calculate_escalation_risk(escalation_indicators),
            "affected_resources": self.identify_affected_resources(escalation_indicators),
            "potential_impact": self.assess_potential_impact(escalation_indicators),
            "recommended_mitigations": self.generate_mitigations(escalation_indicators)
        }
        
        return {
            "escalation_indicators": escalation_indicators,
            "risk_assessment": risk_assessment,
            "requires_immediate_action": risk_assessment["escalation_risk_score"] > 0.7
        }
```

### 4. Data Security Analytics

#### 4.1 Data Access Monitoring
```sql
CREATE TABLE data_access_events (
    id UUID PRIMARY KEY,
    agent_id UUID NOT NULL,
    user_id UUID,
    
    -- Access details
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    operation VARCHAR(20), -- 'read', 'write', 'delete', 'modify'
    
    -- Data classification
    data_sensitivity VARCHAR(20), -- 'public', 'internal', 'confidential', 'restricted'
    contains_pii BOOLEAN,
    contains_phi BOOLEAN,
    
    -- Volume and scope
    records_accessed INTEGER,
    data_size_bytes BIGINT,
    
    -- Security context
    encryption_used BOOLEAN,
    access_justified BOOLEAN,
    business_justification TEXT,
    
    -- Anomaly detection
    anomaly_score FLOAT,
    baseline_deviation FLOAT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_data_access_agent ON data_access_events(agent_id, created_at);
CREATE INDEX idx_data_access_sensitivity ON data_access_events(data_sensitivity);
CREATE INDEX idx_data_access_anomaly ON data_access_events(anomaly_score DESC);
```

#### 4.2 Data Exfiltration Detection
```python
class DataExfiltrationDetector:
    def detect_exfiltration(self, workspace_id: str):
        data_flows = self.analyze_data_flows(workspace_id)
        
        exfiltration_indicators = {
            "volume_anomalies": self.detect_volume_anomalies(data_flows),
            "destination_anomalies": self.detect_destination_anomalies(data_flows),
            "timing_anomalies": self.detect_timing_anomalies(data_flows),
            "encoding_anomalies": self.detect_encoding_anomalies(data_flows)
        }
        
        # Machine learning based detection
        ml_predictions = self.ml_exfiltration_detection(data_flows)
        
        # Combine indicators
        risk_score = self.calculate_exfiltration_risk(
            exfiltration_indicators,
            ml_predictions
        )
        
        if risk_score > 0.8:
            return {
                "high_risk_detected": True,
                "risk_score": risk_score,
                "indicators": exfiltration_indicators,
                "affected_agents": self.identify_affected_agents(data_flows),
                "data_at_risk": self.estimate_data_at_risk(data_flows),
                "immediate_actions": self.generate_immediate_actions(risk_score)
            }
        
        return {
            "high_risk_detected": False,
            "risk_score": risk_score,
            "monitoring_recommendations": self.generate_monitoring_recommendations(risk_score)
        }
```

### 5. Compliance Monitoring

#### 5.1 Regulatory Compliance Tracking
```typescript
interface ComplianceMetrics {
  workspace_id: string;
  compliance_frameworks: {
    framework: 'GDPR' | 'HIPAA' | 'SOC2' | 'ISO27001' | 'PCI-DSS';
    compliance_score: number;
    requirements_met: number;
    requirements_total: number;
    violations: {
      requirement_id: string;
      description: string;
      severity: string;
      remediation_deadline: string;
    }[];
    last_audit: string;
  }[];
  data_governance: {
    data_classification_coverage: number;
    encryption_compliance: number;
    retention_policy_adherence: number;
    deletion_compliance: number;
  };
  audit_trail: {
    completeness: number;
    integrity_verified: boolean;
    tampering_detected: boolean;
    retention_compliant: boolean;
  };
}
```

#### 5.2 Audit Trail Analytics
```sql
CREATE MATERIALIZED VIEW audit_trail_analytics AS
WITH audit_completeness AS (
    SELECT 
        agent_id,
        COUNT(DISTINCT operation_type) as operation_types_logged,
        COUNT(*) as total_events,
        COUNT(DISTINCT user_id) as unique_users,
        COUNT(DISTINCT session_id) as unique_sessions,
        MIN(created_at) as earliest_log,
        MAX(created_at) as latest_log
    FROM audit_logs
    GROUP BY agent_id
),
audit_gaps AS (
    SELECT 
        agent_id,
        COUNT(*) as gap_count,
        AVG(gap_duration_minutes) as avg_gap_duration,
        MAX(gap_duration_minutes) as max_gap_duration
    FROM (
        SELECT 
            agent_id,
            created_at,
            LAG(created_at) OVER (PARTITION BY agent_id ORDER BY created_at) as prev_event,
            EXTRACT(EPOCH FROM (created_at - LAG(created_at) OVER (PARTITION BY agent_id ORDER BY created_at)))/60 as gap_duration_minutes
        FROM audit_logs
    ) t
    WHERE gap_duration_minutes > 60  -- Gaps longer than 1 hour
    GROUP BY agent_id
)
SELECT 
    ac.agent_id,
    ac.operation_types_logged,
    ac.total_events,
    ag.gap_count,
    ag.avg_gap_duration,
    ag.max_gap_duration,
    CASE 
        WHEN ag.gap_count = 0 THEN 'complete'
        WHEN ag.gap_count < 5 THEN 'mostly_complete'
        WHEN ag.gap_count < 20 THEN 'gaps_detected'
        ELSE 'significant_gaps'
    END as audit_quality,
    (ac.operation_types_logged::float / 10) * -- Assuming 10 operation types
    (1 - LEAST(ag.gap_count::float / 100, 1)) as completeness_score
FROM audit_completeness ac
LEFT JOIN audit_gaps ag ON ac.agent_id = ag.agent_id;
```

### 6. Vulnerability Assessment

#### 6.1 Security Vulnerability Scanner
```python
class VulnerabilityScanner:
    def scan_agent_vulnerabilities(self, agent_id: str):
        scan_results = {
            "code_vulnerabilities": self.scan_code_vulnerabilities(agent_id),
            "dependency_vulnerabilities": self.scan_dependencies(agent_id),
            "configuration_issues": self.scan_configurations(agent_id),
            "api_vulnerabilities": self.scan_api_endpoints(agent_id),
            "injection_risks": self.scan_injection_risks(agent_id)
        }
        
        # Calculate CVSS scores
        for vuln_type, vulnerabilities in scan_results.items():
            for vuln in vulnerabilities:
                vuln["cvss_score"] = self.calculate_cvss_score(vuln)
                vuln["exploitability"] = self.assess_exploitability(vuln)
        
        # Generate remediation plan
        remediation_plan = self.create_remediation_plan(scan_results)
        
        return {
            "scan_results": scan_results,
            "critical_vulnerabilities": self.filter_critical(scan_results),
            "risk_score": self.calculate_overall_risk(scan_results),
            "remediation_plan": remediation_plan,
            "estimated_fix_time": self.estimate_fix_time(remediation_plan)
        }
    
    def scan_injection_risks(self, agent_id: str):
        agent_code = self.get_agent_code(agent_id)
        prompts = self.get_agent_prompts(agent_id)
        
        injection_risks = []
        
        # Check for SQL injection
        sql_risks = self.detect_sql_injection_risks(agent_code)
        injection_risks.extend(sql_risks)
        
        # Check for prompt injection
        prompt_risks = self.detect_prompt_injection_risks(prompts)
        injection_risks.extend(prompt_risks)
        
        # Check for command injection
        command_risks = self.detect_command_injection_risks(agent_code)
        injection_risks.extend(command_risks)
        
        return injection_risks
```

### 7. Incident Response Analytics

#### 7.1 Security Incident Management
```typescript
interface SecurityIncident {
  incident_id: string;
  agent_id: string;
  incident_details: {
    type: string;
    severity: 'critical' | 'high' | 'medium' | 'low';
    status: 'detected' | 'investigating' | 'contained' | 'eradicated' | 'recovered' | 'closed';
    attack_vector: string;
    affected_systems: string[];
    data_compromised: boolean;
  };
  timeline: {
    detected_at: string;
    investigated_at?: string;
    contained_at?: string;
    resolved_at?: string;
    total_duration_hours?: number;
  };
  response_metrics: {
    time_to_detect: number;
    time_to_respond: number;
    time_to_contain: number;
    time_to_resolve: number;
  };
  impact_assessment: {
    users_affected: number;
    data_records_exposed: number;
    financial_impact_usd: number;
    reputation_impact: 'high' | 'medium' | 'low' | 'none';
  };
  remediation: {
    actions_taken: string[];
    patches_applied: string[];
    configurations_changed: string[];
    lessons_learned: string[];
  };
}
```

### 8. API Endpoints

#### 8.1 Security Analytics Endpoints
```python
@router.get("/analytics/security/threats/{agent_id}")
async def get_threat_analysis(
    agent_id: str,
    timeframe: str = "24h",
    include_predictions: bool = True
):
    """Get threat analysis for an agent"""
    
@router.get("/analytics/security/vulnerabilities")
async def scan_vulnerabilities(
    workspace_id: str,
    scan_type: str = "comprehensive",
    severity_threshold: str = "medium"
):
    """Perform vulnerability scanning"""
    
@router.get("/analytics/security/compliance")
async def get_compliance_status(
    workspace_id: str,
    frameworks: List[str] = Query(default=["SOC2", "GDPR"])
):
    """Get compliance status for specified frameworks"""
    
@router.post("/analytics/security/incidents/{incident_id}/investigate")
async def investigate_incident(
    incident_id: str,
    investigation_depth: str = "standard"
):
    """Investigate a security incident"""
```

### 9. Security Dashboard

#### 9.1 Real-time Security Monitor
```typescript
const SecurityDashboard: React.FC = () => {
  const [threats, setThreats] = useState<ThreatData[]>([]);
  const [incidents, setIncidents] = useState<SecurityIncident[]>([]);
  
  useEffect(() => {
    const ws = new WebSocket('/ws/security/monitor');
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'threat_detected') {
        handleThreatDetection(data);
      }
      
      if (data.severity === 'critical') {
        triggerCriticalAlert(data);
      }
    };
  }, []);
  
  return (
    <div className="security-dashboard">
      <ThreatLevelIndicator level={currentThreatLevel} />
      <SecurityEventStream events={securityEvents} />
      <AttackPatternVisualizer patterns={attackPatterns} />
      <VulnerabilityHeatmap vulnerabilities={vulnData} />
      <ComplianceStatusMatrix frameworks={complianceData} />
      <IncidentTimeline incidents={incidents} />
      <AccessAnomalyChart anomalies={accessAnomalies} />
      <DataFlowSankey flows={dataFlows} />
    </div>
  );
};
```

## Implementation Priority
1. Phase 1: Basic security event monitoring and logging
2. Phase 2: Threat detection and anomaly identification
3. Phase 3: Vulnerability scanning and assessment
4. Phase 4: Compliance monitoring and reporting
5. Phase 5: Advanced incident response and forensics

## Success Metrics
- 99.9% security event capture rate
- < 5 minute mean time to detect threats
- 95% vulnerability detection accuracy
- 100% compliance audit trail completeness