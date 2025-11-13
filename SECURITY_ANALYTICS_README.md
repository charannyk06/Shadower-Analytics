# Agent Security Analytics

Comprehensive security monitoring, threat detection, and compliance analytics for agent operations within the Shadower platform.

## Overview

The Agent Security Analytics system provides real-time security monitoring and threat detection capabilities for AI agents. It includes:

- **Security Event Monitoring**: Track authentication, authorization, data access, API calls, injections, and anomalies
- **Threat Detection**: Behavioral anomaly detection, attack pattern matching, and ML-based threat predictions
- **Vulnerability Scanning**: Automated security scans for code, dependencies, configurations, and APIs
- **Access Control Analytics**: Permission usage tracking and privilege escalation detection
- **Data Security**: Data access monitoring and exfiltration risk detection
- **Compliance Monitoring**: GDPR, HIPAA, SOC2, ISO27001, PCI-DSS, and CCPA compliance tracking
- **Incident Response**: Security incident management and forensic analysis

## Architecture

### Database Schema

The security analytics system uses PostgreSQL with the following main tables:

- `security_events`: All security-related events with threat indicators
- `data_access_events`: Data access tracking with PII/PHI detection
- `security_incidents`: Security incident management and tracking
- `vulnerability_scans`: Vulnerability scan results and assessments
- `compliance_audits`: Compliance audit results and findings
- `access_control_logs`: Access control decisions and privilege tracking
- `attack_patterns`: Known attack patterns for detection
- `threat_intelligence`: Threat intelligence data
- `security_baselines`: Behavioral baselines for anomaly detection

### Backend Services

Located in `/backend/src/services/security/`:

1. **ThreatDetectionEngine** (`threat_detection_service.py`)
   - Behavioral anomaly detection
   - Attack pattern matching
   - Statistical outlier detection
   - Risk assessment and scoring
   - Automated alert generation

2. **VulnerabilityScanner** (`vulnerability_scanner_service.py`)
   - Code vulnerability scanning
   - Dependency vulnerability checks
   - Configuration security audits
   - API security testing
   - Injection risk detection

3. **SecurityAnalyticsService** (`security_analytics_service.py`)
   - Main orchestrator for security features
   - Dashboard metrics aggregation
   - Data access analytics
   - Access control metrics
   - Compliance status tracking

### API Endpoints

Base path: `/api/v1/security`

#### Dashboard
- `GET /dashboard/{workspace_id}` - Get security dashboard summary

#### Threat Detection
- `GET /threats/{agent_id}` - Get threat analysis for an agent
- `GET /analytics/{agent_id}` - Get comprehensive threat analysis

#### Vulnerability Scanning
- `POST /vulnerabilities/scan` - Perform vulnerability scan
- `GET /vulnerabilities/{scan_id}` - Get scan results

#### Incidents
- `GET /incidents/{workspace_id}` - Get security incidents

#### Events
- `POST /events` - Create security event
- `GET /events/{agent_id}` - Get security events

#### Access Control
- `GET /access-control/{agent_id}` - Get access control metrics

#### Data Access
- `GET /data-access/{workspace_id}` - Get data access analytics

#### Utilities
- `POST /refresh-views` - Refresh security materialized views

## Frontend Components

Located in `/frontend/src/components/security/`:

### SecurityDashboard Component

Real-time security dashboard displaying:
- Current threat level indicator
- Security events (24h/7d)
- Open incidents count
- Critical vulnerabilities
- Compliance score
- Recent incident timeline
- Quick action buttons

```tsx
import { SecurityDashboard } from '@/components/security';

function SecurityPage() {
  return <SecurityDashboard workspaceId="workspace-123" />;
}
```

## Database Migration

Run the security analytics migration:

```bash
psql -U your_user -d your_database -f database/migrations/028_create_security_analytics_tables.sql
```

This creates:
- All security tables with proper indexes
- Materialized views for dashboard metrics
- Attack pattern detection view
- Security baseline tables
- Compliance audit tables

## Usage Examples

### 1. Get Security Dashboard

```python
from services.security.security_analytics_service import SecurityAnalyticsService

service = SecurityAnalyticsService(db)
dashboard = await service.get_security_dashboard("workspace-id")

print(f"Threat Level: {dashboard.max_threat_score}")
print(f"Open Incidents: {dashboard.open_incidents}")
print(f"Critical Vulnerabilities: {dashboard.critical_vulnerabilities}")
```

### 2. Run Threat Detection

```python
from services.security.threat_detection_service import ThreatDetectionEngine

engine = ThreatDetectionEngine(db)
threats = await engine.detect_threats("agent-id", window_minutes=60)

print(f"Threat Level: {threats.threat_level}")
print(f"Risk Score: {threats.risk_score}")
print(f"Anomalies: {len(threats.behavioral_anomalies)}")
print(f"Recommendations: {threats.recommended_actions}")
```

### 3. Perform Vulnerability Scan

```python
from services.security.vulnerability_scanner_service import VulnerabilityScanner

scanner = VulnerabilityScanner(db)
result = await scanner.scan_agent_vulnerabilities(
    agent_id="agent-id",
    workspace_id="workspace-id",
    scan_type="comprehensive"
)

print(f"Critical: {result.scan.vulnerability_summary.critical}")
print(f"High: {result.scan.vulnerability_summary.high}")
print(f"Risk Score: {result.scan.overall_risk_score}")
```

### 4. Create Security Event

```bash
curl -X POST http://localhost:8000/api/v1/security/events \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-123",
    "workspace_id": "workspace-456",
    "event_type": "injection",
    "severity": "critical",
    "category": "sql_injection",
    "description": "SQL injection attempt detected",
    "event_data": {"query": "SELECT * FROM users WHERE id = 1 OR 1=1"},
    "threat_score": 95.0,
    "source_ip": "192.168.1.100"
  }'
```

## Security Features

### 1. Behavioral Anomaly Detection

The system builds behavioral baselines for each agent and detects deviations:
- Event type frequency patterns
- Timing patterns (hour of day, day of week)
- Access patterns
- Resource usage patterns
- Geographic patterns

Anomalies are scored (0-100) and classified by type:
- `high_severity_event`
- `unusual_timing`
- `injection_attempt`
- `privilege_escalation`
- `general_anomaly`

### 2. Attack Pattern Recognition

Known attack patterns are matched against event sequences:
- SQL injection patterns
- XSS attack patterns
- CSRF patterns
- Authentication bypass attempts
- Privilege escalation patterns
- Data exfiltration patterns

Patterns are mapped to MITRE ATT&CK framework.

### 3. Vulnerability Scanning

Multiple scan types available:
- **Comprehensive**: Full security scan (code, dependencies, config, APIs)
- **Quick**: Fast scan of critical areas
- **Code**: Code vulnerability scan (hardcoded secrets, insecure functions)
- **Dependencies**: Dependency vulnerability checks against CVE databases
- **Configuration**: Security configuration audit
- **Targeted**: Scan specific components

Each vulnerability includes:
- CVSS score
- Exploitability assessment
- Affected component
- Remediation steps

### 4. Compliance Monitoring

Automated compliance checks for:
- **GDPR**: Data protection and privacy requirements
- **HIPAA**: Healthcare data security
- **SOC2**: Security, availability, and confidentiality
- **ISO27001**: Information security management
- **PCI-DSS**: Payment card data security
- **CCPA**: California privacy requirements

Compliance audits track:
- Requirements met/failed
- Policy violations
- Audit findings by severity
- Remediation deadlines

### 5. Incident Response

Security incidents are automatically created for:
- High threat levels (>80)
- Critical vulnerabilities
- Multiple anomalies in short time
- Known attack pattern matches

Incident tracking includes:
- Timeline (detected → investigated → contained → resolved)
- Impact assessment (users affected, data exposed, financial impact)
- Response metrics (time to detect/respond/contain/resolve)
- Actions taken and lessons learned

## Performance Optimization

### Materialized Views

Security metrics are pre-aggregated in materialized views:
- `security_dashboard_summary`: Real-time dashboard metrics
- `attack_pattern_detection`: Pattern matching results

Refresh views periodically:
```sql
SELECT analytics.refresh_security_materialized_views();
```

### Indexes

Optimized indexes for common queries:
- Agent ID + timestamp
- Workspace ID + timestamp
- Severity + timestamp
- Threat score (descending)
- Unresolved incidents
- Compliance violations

### Caching

Dashboard metrics are cached for 1 minute.
Threat analysis results are cached for 5 minutes.

## Monitoring & Alerts

### Real-time Monitoring

WebSocket support for real-time security event streaming:
- Connect to `/ws/security/monitor`
- Receive real-time threat notifications
- Get instant incident alerts

### Alert Thresholds

Automatic alerts triggered for:
- Threat level > 80 (critical)
- 5+ anomalies in 1 hour
- Critical vulnerability detected
- Compliance violation
- Privilege escalation attempt

## Testing

Run integration tests:

```bash
cd backend
pytest tests/integration/test_security_routes.py -v
```

Test coverage includes:
- Security dashboard endpoints
- Threat detection
- Vulnerability scanning
- Incident management
- Security event creation
- Access control metrics
- Data access analytics

## Roadmap

### Phase 1 (Completed)
- ✅ Basic security event monitoring and logging
- ✅ Threat detection and anomaly identification
- ✅ Vulnerability scanning and assessment
- ✅ Security dashboard and visualization

### Phase 2 (In Progress)
- 🔄 Machine learning-based threat prediction
- 🔄 Advanced behavioral profiling
- 🔄 Integration with threat intelligence feeds
- 🔄 Automated incident response workflows

### Phase 3 (Planned)
- 📋 Compliance automation and reporting
- 📋 Advanced forensic analysis
- 📋 Security orchestration and automation (SOAR)
- 📋 Red team simulation and testing

## Support

For questions or issues:
- Create an issue in the GitHub repository
- Contact the security team: security@shadower.ai
- Documentation: https://docs.shadower.ai/security

## License

Copyright © 2025 Shadower Analytics. All rights reserved.
