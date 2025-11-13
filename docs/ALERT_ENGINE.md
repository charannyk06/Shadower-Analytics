# Alert Engine System Documentation

## Overview

The Shadower Analytics Alert Engine provides comprehensive alerting capabilities with configurable rules, multiple delivery channels, escalation policies, and alert fatigue prevention. This system allows you to proactively monitor your metrics and get notified when conditions require attention.

## Features

- **Multiple Alert Conditions**: Threshold, change detection, anomaly detection, and pattern recognition
- **Multi-Channel Notifications**: Email, Slack, webhooks, SMS, and PagerDuty
- **Escalation Policies**: Automatic alert escalation based on acknowledgment delays
- **Alert Management**: Acknowledge and resolve workflows
- **Alert Suppression**: Prevent alert fatigue with intelligent suppression rules
- **Scheduled Evaluation**: Automatic periodic rule evaluation via Celery

## Quick Start

### 1. Create an Alert Rule

```bash
POST /api/v1/alerts/rules
Content-Type: application/json

{
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "rule_name": "High Error Rate Alert",
  "description": "Alert when error rate exceeds 5%",
  "metric_type": "error_rate",
  "condition_type": "threshold",
  "condition_config": {
    "metric": "error_rate",
    "operator": ">",
    "value": 0.05,
    "duration_minutes": 5
  },
  "severity": "critical",
  "is_active": true,
  "check_interval_minutes": 5,
  "cooldown_minutes": 60,
  "notification_channels": [
    {
      "type": "email",
      "recipients": ["ops-team@company.com"]
    },
    {
      "type": "slack",
      "recipients": ["https://hooks.slack.com/services/YOUR/WEBHOOK/URL"]
    }
  ]
}
```

### 2. View Active Alerts

```bash
GET /api/v1/alerts/active?workspace_id=550e8400-e29b-41d4-a716-446655440000
```

### 3. Acknowledge an Alert

```bash
PUT /api/v1/alerts/{alert_id}/acknowledge
Content-Type: application/json

{
  "acknowledged_by": "550e8400-e29b-41d4-a716-446655440000",
  "notes": "Investigating the issue"
}
```

### 4. Resolve an Alert

```bash
PUT /api/v1/alerts/{alert_id}/resolve
Content-Type: application/json

{
  "resolved_by": "550e8400-e29b-41d4-a716-446655440000",
  "resolution_notes": "Fixed by deploying patch v1.2.3",
  "permanent_fix": true
}
```

## Alert Condition Types

### 1. Threshold Alerts

Trigger when a metric crosses a defined threshold.

```json
{
  "condition_type": "threshold",
  "condition_config": {
    "metric": "cpu_usage",
    "operator": ">",  // Options: ">", "<", ">=", "<=", "==", "!="
    "value": 80,
    "duration_minutes": 5
  }
}
```

**Use Cases:**
- CPU/Memory usage exceeds limit
- Error rate above acceptable level
- Response time threshold breach

### 2. Change Detection Alerts

Trigger when a metric changes significantly compared to a baseline.

```json
{
  "condition_type": "change",
  "condition_config": {
    "metric": "credit_consumption",
    "change_type": "percent",  // Options: "percent", "absolute"
    "threshold": 50,
    "comparison_period": "previous_hour"  // Options: "previous_hour", "previous_day", "previous_week"
  }
}
```

**Use Cases:**
- Sudden spike in credit consumption
- Traffic drop compared to previous period
- Unusual increase in API calls

### 3. Anomaly Detection Alerts

Trigger when statistical anomalies are detected using z-score analysis.

```json
{
  "condition_type": "anomaly",
  "condition_config": {
    "metric": "api_latency",
    "sensitivity": 2.5,  // Standard deviations (1.0 to 5.0)
    "min_deviation_duration": 10
  }
}
```

**Use Cases:**
- Detecting unusual patterns in metrics
- Performance degradation
- Unexpected behavior

### 4. Pattern Recognition Alerts

Trigger when specific patterns are detected in metric trends.

```json
{
  "condition_type": "pattern",
  "condition_config": {
    "metric": "error_count",
    "pattern": "increasing_errors",  // Options: "increasing_errors", "decreasing_performance", "spike", "flat_line"
    "window_minutes": 30,
    "min_occurrences": 3
  }
}
```

**Use Cases:**
- Gradual performance degradation
- Cascading failures
- System stall detection

## Notification Channels

### Email

```json
{
  "type": "email",
  "recipients": ["team@company.com", "oncall@company.com"]
}
```

Sends formatted HTML emails with alert details, severity color-coding, and metric values.

### Slack

```json
{
  "type": "slack",
  "recipients": ["https://hooks.slack.com/services/YOUR/WEBHOOK/URL"]
}
```

Posts rich-formatted messages to Slack with color-coded severity blocks.

### Custom Webhook

```json
{
  "type": "webhook",
  "recipients": ["https://your-service.com/webhook/alerts"]
}
```

POSTs JSON payload with complete alert data to your custom endpoint.

### SMS (Critical Alerts)

```json
{
  "type": "sms",
  "recipients": ["+1234567890"]
}
```

Sends text messages for critical alerts (requires Twilio configuration).

### PagerDuty

```json
{
  "type": "pagerduty",
  "recipients": ["your-pagerduty-integration-key"]
}
```

Creates incidents in PagerDuty with proper severity mapping.

## Escalation Policies

Create escalation policies to automatically escalate unacknowledged alerts.

```bash
POST /api/v1/alerts/escalation-policies
Content-Type: application/json

{
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "policy_name": "Standard Escalation",
  "escalation_levels": [
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
      "recipients": ["emergency-escalation-key"]
    }
  ],
  "is_active": true
}
```

Then reference it in your alert rule:

```json
{
  "escalation_policy_id": "policy-uuid-here",
  ...
}
```

## Alert Suppression

Suppress alerts during maintenance windows or to prevent alert fatigue.

```bash
POST /api/v1/alerts/suppressions
Content-Type: application/json

{
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "suppression_type": "maintenance",
  "pattern": {
    "severity": "info",
    "metric_type": "api_latency"
  },
  "start_time": "2025-01-15T02:00:00Z",
  "end_time": "2025-01-15T04:00:00Z",
  "reason": "Scheduled maintenance window"
}
```

**Suppression Types:**
- **rule**: Suppress specific alert rules
- **pattern**: Suppress by metric type or severity
- **maintenance**: Time-based maintenance windows

## Testing Alert Rules

Test your alert rules against historical data before activating them:

```bash
POST /api/v1/alerts/test
Content-Type: application/json

{
  "condition_type": "threshold",
  "condition_config": {
    "metric": "error_rate",
    "operator": ">",
    "value": 0.05
  }
}
```

Returns validation results and indicates if the condition syntax is correct.

## Alert Statistics

Get statistics about your alerts:

```bash
GET /api/v1/alerts/stats?workspace_id=550e8400-e29b-41d4-a716-446655440000
```

Response:
```json
{
  "total_alerts": 245,
  "active_alerts": 3,
  "acknowledged_alerts": 1,
  "resolved_alerts": 242,
  "critical_alerts": 1
}
```

## Background Processing

Alert evaluation runs automatically via Celery Beat:

- **Rule Evaluation**: Every 5 minutes
- **Escalation Check**: Every 10 minutes
- **Alert Cleanup**: Daily at 4:00 AM UTC

### Manual Evaluation

Trigger manual evaluation via Celery:

```python
from src.tasks.alerts import evaluate_alert_rules_task

# Evaluate all workspaces
evaluate_alert_rules_task.delay()

# Evaluate specific workspace
evaluate_alert_rules_task.delay(workspace_id="your-workspace-id")
```

## Configuration

### Email Configuration

Set environment variables or update `config.py`:

```python
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "alerts@company.com"
SMTP_PASSWORD = "your-password"
FROM_EMAIL = "noreply@company.com"
```

### Alert Engine Configuration

```python
# Enable/disable features
ENABLE_ALERTS = True
ALERT_EVALUATION_INTERVAL = 300  # 5 minutes
ALERT_RETENTION_DAYS = 90

# Channel-specific config
SLACK_DEFAULT_WEBHOOK = "https://hooks.slack.com/..."
TWILIO_ACCOUNT_SID = "your-sid"
TWILIO_AUTH_TOKEN = "your-token"
TWILIO_FROM_NUMBER = "+1234567890"
PAGERDUTY_API_KEY = "your-api-key"
```

## Best Practices

### 1. Alert Rule Design

- **Be Specific**: Create focused rules for specific conditions
- **Use Appropriate Severity**: Reserve "critical" and "emergency" for real emergencies
- **Set Reasonable Thresholds**: Avoid alert fatigue with appropriate thresholds
- **Test First**: Use the test endpoint before activating rules

### 2. Notification Management

- **Multiple Channels**: Use different channels for different severity levels
- **Team Distribution**: Route alerts to the right teams
- **Escalation**: Configure escalation for critical alerts
- **Acknowledgment**: Always acknowledge alerts to stop escalation

### 3. Alert Fatigue Prevention

- **Cooldown Periods**: Set appropriate cooldown periods (default: 60 minutes)
- **Grouping**: Use alert suppression to group similar alerts
- **Maintenance Windows**: Suppress alerts during planned maintenance
- **Regular Review**: Periodically review and tune alert rules

### 4. Monitoring

- **Delivery Rates**: Monitor `notification_history` table for delivery success
- **Response Times**: Track MTTA (mean time to acknowledge) and MTTR (mean time to resolve)
- **False Positives**: Review and adjust rules with high false positive rates

## Troubleshooting

### Alerts Not Triggering

1. Check rule is active: `is_active = true`
2. Verify check interval hasn't passed
3. Check cooldown period
4. Review alert suppression rules
5. Check Celery workers are running

### Notifications Not Delivered

1. Check `notification_history` table for delivery status
2. Verify channel configuration (SMTP, Slack webhook, etc.)
3. Check network connectivity
4. Review error messages in `notification_history.error_message`
5. Verify recipient addresses/URLs are correct

### High Alert Volume

1. Increase cooldown periods
2. Adjust thresholds
3. Implement alert suppression
4. Group similar alerts
5. Review and disable noisy rules

## API Reference

### Alert Rules

- `GET /api/v1/alerts/rules` - List all rules
- `POST /api/v1/alerts/rules` - Create rule
- `GET /api/v1/alerts/rules/{id}` - Get rule details
- `PUT /api/v1/alerts/rules/{id}` - Update rule
- `DELETE /api/v1/alerts/rules/{id}` - Delete rule

### Alerts

- `GET /api/v1/alerts/active` - List active alerts
- `GET /api/v1/alerts/history` - Alert history
- `PUT /api/v1/alerts/{id}/acknowledge` - Acknowledge alert
- `PUT /api/v1/alerts/{id}/resolve` - Resolve alert
- `GET /api/v1/alerts/stats` - Alert statistics

### Configuration

- `GET /api/v1/alerts/escalation-policies` - List escalation policies
- `POST /api/v1/alerts/escalation-policies` - Create policy
- `POST /api/v1/alerts/suppressions` - Create suppression
- `POST /api/v1/alerts/test` - Test alert condition

## Examples

See `/examples/alert-rules/` directory for common alert rule templates:

- `high-error-rate.json` - Error rate threshold alert
- `credit-spike.json` - Credit consumption change detection
- `latency-anomaly.json` - API latency anomaly detection
- `degrading-performance.json` - Performance degradation pattern
- `escalation-policy.json` - Multi-level escalation policy

## Support

For issues or questions:
- GitHub Issues: https://github.com/charannyk06/Shadower-Analytics/issues
- Documentation: `/docs/ALERT_ENGINE.md`
- API Docs: `/docs/api/alerts`
