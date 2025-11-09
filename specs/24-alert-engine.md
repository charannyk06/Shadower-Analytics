# Specification: Alert Engine System

## Overview
Implement comprehensive alerting system with configurable rules, multiple delivery channels, escalation policies, and alert fatigue prevention.

## Technical Requirements

### Backend Implementation

#### Service: `services/alert_engine.py`
```python
class AlertEngine:
    def __init__(self):
        self.rules = {}
        self.channels = {}
        self.cooldowns = {}
    
    async def evaluate_alert_rules(
        self,
        workspace_id: str,
        metric_data: dict
    ):
        """
        Evaluate all active alert rules for workspace
        Triggers alerts when conditions are met
        """
    
    async def send_alert(
        self,
        alert: Alert,
        channels: List[str],
        workspace_id: str
    ):
        """
        Send alert through specified channels
        Handles delivery confirmation and retry logic
        """
    
    async def check_escalation_needed(
        self,
        alert_id: str,
        workspace_id: str
    ):
        """
        Check if alert needs escalation
        Based on acknowledgment time and severity
        """
    
    def apply_alert_suppression(
        self,
        alert_type: str,
        workspace_id: str
    ):
        """
        Prevent alert fatigue with intelligent suppression
        Groups similar alerts and applies cooldowns
        """
    
    async def schedule_alert_check(
        self,
        rule_id: str,
        cron_expression: str
    ):
        """
        Schedule periodic alert rule evaluation
        Uses Celery beat for scheduling
        """
    
    async def validate_alert_condition(
        self,
        condition: str,
        test_data: dict = None
    ):
        """
        Validate alert condition syntax and logic
        Optionally test against sample data
        """

class AlertChannels:
    async def send_email(self, alert: Alert, recipients: List[str]):
        """Send alert via email with formatting"""
    
    async def send_slack(self, alert: Alert, webhook_url: str):
        """Send alert to Slack channel"""
    
    async def send_webhook(self, alert: Alert, endpoint: str):
        """Send alert to custom webhook"""
    
    async def send_sms(self, alert: Alert, phone_numbers: List[str]):
        """Send critical alerts via SMS"""
    
    async def send_pagerduty(self, alert: Alert, integration_key: str):
        """Create PagerDuty incident"""

#### Database Schema
```sql
-- Alert rules configuration
CREATE TABLE analytics.alert_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL,
    rule_name VARCHAR(255) NOT NULL,
    description TEXT,
    metric_type VARCHAR(100) NOT NULL,
    condition_type VARCHAR(50) NOT NULL, -- 'threshold', 'change', 'anomaly', 'pattern'
    condition_config JSONB NOT NULL,
    severity VARCHAR(20) NOT NULL, -- 'info', 'warning', 'critical', 'emergency'
    is_active BOOLEAN DEFAULT TRUE,
    check_interval_minutes INTEGER DEFAULT 5,
    cooldown_minutes INTEGER DEFAULT 60,
    notification_channels JSONB NOT NULL,
    escalation_policy_id UUID,
    created_by UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_alert_rules_workspace (workspace_id, is_active),
    UNIQUE(workspace_id, rule_name)
);

-- Alert instances
CREATE TABLE analytics.alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL,
    rule_id UUID NOT NULL REFERENCES analytics.alert_rules(id),
    alert_title VARCHAR(500) NOT NULL,
    alert_message TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL,
    metric_value DECIMAL,
    threshold_value DECIMAL,
    triggered_at TIMESTAMP NOT NULL,
    acknowledged_at TIMESTAMP,
    acknowledged_by UUID,
    resolved_at TIMESTAMP,
    resolved_by UUID,
    resolution_notes TEXT,
    alert_context JSONB,
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_channels JSONB,
    escalated BOOLEAN DEFAULT FALSE,
    escalation_level INTEGER DEFAULT 0,
    
    INDEX idx_alerts_workspace (workspace_id, triggered_at DESC),
    INDEX idx_alerts_unresolved (workspace_id, resolved_at NULLS FIRST),
    INDEX idx_alerts_severity (severity, acknowledged_at NULLS FIRST)
);

-- Notification history
CREATE TABLE analytics.notification_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id UUID NOT NULL REFERENCES analytics.alerts(id),
    channel VARCHAR(50) NOT NULL,
    recipient TEXT NOT NULL,
    sent_at TIMESTAMP NOT NULL,
    delivery_status VARCHAR(20) NOT NULL,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    response_data JSONB,
    
    INDEX idx_notifications_alert (alert_id),
    INDEX idx_notifications_status (delivery_status, sent_at DESC)
);

-- Escalation policies
CREATE TABLE analytics.escalation_policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL,
    policy_name VARCHAR(255) NOT NULL,
    escalation_levels JSONB NOT NULL, -- Array of levels with delays and contacts
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(workspace_id, policy_name)
);

-- Alert suppression rules
CREATE TABLE analytics.alert_suppressions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL,
    suppression_type VARCHAR(50) NOT NULL,
    pattern JSONB NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    reason TEXT,
    created_by UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_suppression_active (workspace_id, start_time, end_time)
);
```

### Frontend Components

#### Component: `components/analytics/AlertManagementDashboard.tsx`
```typescript
interface AlertManagementDashboardProps {
    workspaceId: string;
    userId: string;
}

export function AlertManagementDashboard({
    workspaceId,
    userId
}: AlertManagementDashboardProps) {
    // Active alerts view
    // Alert rules configuration
    // Notification settings
    // Alert history
    
    return (
        <div className="alert-dashboard">
            <ActiveAlertsFeed />
            <AlertRulesManager />
            <NotificationChannels />
            <EscalationPolicies />
            <AlertHistory />
        </div>
    );
}

interface AlertRulesManagerProps {
    rules: AlertRule[];
    onRuleUpdate: (rule: AlertRule) => void;
}

export function AlertRulesManager({
    rules,
    onRuleUpdate
}: AlertRulesManagerProps) {
    // Create/edit alert rules
    // Test rules against historical data
    // Enable/disable rules
    // Set thresholds and conditions
}

interface ActiveAlertsFeedProps {
    alerts: Alert[];
    onAcknowledge: (alertId: string) => void;
    onResolve: (alertId: string, notes: string) => void;
}

export function ActiveAlertsFeed({
    alerts,
    onAcknowledge,
    onResolve
}: ActiveAlertsFeedProps) {
    // Real-time alert feed
    // Severity indicators
    // Quick actions
    // Alert grouping
}

interface NotificationChannelsProps {
    channels: NotificationChannel[];
    onChannelUpdate: (channel: NotificationChannel) => void;
}

export function NotificationChannels({
    channels,
    onChannelUpdate
}: NotificationChannelsProps) {
    // Configure email, Slack, webhooks
    // Test notification delivery
    // Set channel preferences by severity
    // Manage recipient lists
}
```

### API Endpoints

#### GET `/api/analytics/alerts/active`
- Query parameters: workspace_id, severity, acknowledged
- Returns list of active alerts
- Includes context and suggested actions

#### POST `/api/analytics/alerts/rules`
- Creates new alert rule
- Request body: { rule_name, metric_type, condition, severity, channels }
- Validates condition before saving

#### PUT `/api/analytics/alerts/{alert_id}/acknowledge`
- Acknowledges alert receipt
- Stops escalation timer
- Records acknowledgment metadata

#### PUT `/api/analytics/alerts/{alert_id}/resolve`
- Marks alert as resolved
- Request body: { resolution_notes, permanent_fix }
- Updates related metrics

#### POST `/api/analytics/alerts/test`
- Tests alert rule against historical data
- Request body: { rule_config, test_period }
- Returns would-have-triggered alerts

#### GET `/api/analytics/alerts/history`
- Query parameters: workspace_id, date_from, date_to, rule_id
- Returns historical alerts with outcomes
- Includes delivery status

### Alert Conditions

1. **Threshold Alerts**
```python
{
    "condition_type": "threshold",
    "metric": "error_rate",
    "operator": ">",
    "value": 0.05,
    "duration_minutes": 5
}
```

2. **Change Alerts**
```python
{
    "condition_type": "change",
    "metric": "credit_consumption",
    "change_type": "percent",
    "threshold": 50,
    "comparison_period": "previous_hour"
}
```

3. **Anomaly Alerts**
```python
{
    "condition_type": "anomaly",
    "metric": "api_latency",
    "sensitivity": 2.5,
    "min_deviation_duration": 10
}
```

4. **Pattern Alerts**
```python
{
    "condition_type": "pattern",
    "pattern": "increasing_errors",
    "window_minutes": 30,
    "min_occurrences": 3
}
```

### Escalation Example

```python
escalation_policy = {
    "levels": [
        {
            "level": 1,
            "delay_minutes": 0,
            "channels": ["email"],
            "recipients": ["on-call@company.com"]
        },
        {
            "level": 2,
            "delay_minutes": 15,
            "channels": ["slack", "sms"],
            "recipients": ["team-lead@company.com"]
        },
        {
            "level": 3,
            "delay_minutes": 30,
            "channels": ["pagerduty"],
            "recipients": ["emergency-escalation"]
        }
    ]
}
```

## Implementation Priority
1. Basic threshold alerts
2. Email and Slack channels
3. Alert acknowledgment flow
4. Escalation policies
5. Advanced pattern detection

## Success Metrics
- Alert delivery success rate > 99%
- Mean time to acknowledge < 5 minutes
- False positive rate < 10%
- Alert configuration time < 3 minutes