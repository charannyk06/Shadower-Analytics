# Integration API Endpoints Documentation

## Overview

The Integration API provides comprehensive endpoints for connecting third-party services to Shadower Analytics. This includes messaging platforms (Slack, Teams), webhooks, email providers, external databases, and custom APIs.

## Base URL

All integration endpoints are prefixed with `/api/v1/integrations`

## Authentication

Most endpoints require authentication via JWT bearer token. Admin-level operations require the `admin` or `owner` role.

```
Authorization: Bearer <your-jwt-token>
```

## Endpoints Overview

### Slack Integration

#### 1. Install Slack Integration
**POST** `/api/v1/integrations/slack/install`

Install and configure Slack workspace integration.

**Required Role:** Admin

**Request:**
```json
{
  "workspace_id": "ws_123",
  "slack_workspace": "company.slack.com",
  "oauth_code": "slack_oauth_code_here",
  "redirect_uri": "https://analytics.shadower.ai/slack/callback"
}
```

**Response:**
```json
{
  "integration_id": "slack_ws_123_1234567890",
  "slack_team_id": "T123456",
  "slack_team_name": "company",
  "installed_channels": ["#general", "#analytics"],
  "bot_user_id": "U123456"
}
```

#### 2. Send Slack Message
**POST** `/api/v1/integrations/slack/send`

Send formatted messages to Slack channels.

**Required Role:** User

**Request:**
```json
{
  "channel": "#analytics",
  "message": "Daily analytics report ready",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Daily Analytics Summary*"
      }
    },
    {
      "type": "section",
      "fields": [
        {"type": "mrkdwn", "text": "*Active Users:* 3,421"},
        {"type": "mrkdwn", "text": "*Credits Used:* 125,000"}
      ]
    }
  ],
  "attachments": [
    {
      "title": "View Full Report",
      "title_link": "https://analytics.shadower.ai/reports/123"
    }
  ]
}
```

**Response:**
```json
{
  "sent": true,
  "message_ts": "1234567890.000000",
  "channel": "#analytics"
}
```

#### 3. Handle Slash Commands
**POST** `/api/v1/integrations/slack/slash-command`

Process Slack slash commands.

**Supported Commands:**
- `/analytics summary` - Get today's summary
- `/analytics agent [agent_id]` - Get agent performance
- `/analytics report [type]` - Generate report

**Request:** Form-encoded data from Slack

**Response:**
```json
{
  "response_type": "in_channel",
  "text": "Command response",
  "blocks": [...]
}
```

---

### Microsoft Teams Integration

#### 1. Install Teams Integration
**POST** `/api/v1/integrations/teams/install`

Configure Microsoft Teams integration.

**Required Role:** Admin

**Request:**
```json
{
  "workspace_id": "ws_123",
  "tenant_id": "microsoft_tenant_id",
  "client_id": "app_client_id",
  "client_secret": "app_client_secret",
  "webhook_url": "https://outlook.office.com/webhook/..."
}
```

**Response:**
```json
{
  "integration_id": "teams_ws_123_1234567890",
  "tenant_id": "microsoft_tenant_id",
  "configured_channels": ["General", "Analytics"]
}
```

#### 2. Send Adaptive Card
**POST** `/api/v1/integrations/teams/card`

Send adaptive cards to Teams channels.

**Required Role:** User

**Request:**
```json
{
  "channel": "General",
  "card": {
    "type": "AdaptiveCard",
    "version": "1.4",
    "body": [
      {
        "type": "TextBlock",
        "text": "Analytics Alert",
        "size": "Large",
        "weight": "Bolder"
      },
      {
        "type": "FactSet",
        "facts": [
          {"title": "Metric", "value": "Error Rate"},
          {"title": "Value", "value": "5.2%"},
          {"title": "Threshold", "value": "5.0%"}
        ]
      }
    ],
    "actions": [
      {
        "type": "Action.OpenUrl",
        "title": "View Dashboard",
        "url": "https://analytics.shadower.ai"
      }
    ]
  }
}
```

**Response:**
```json
{
  "sent": true,
  "message_id": "msg_1234567890"
}
```

---

### Webhook Management

#### 1. Create Webhook
**POST** `/api/v1/integrations/webhooks`

Register a webhook endpoint to receive analytics events.

**Required Role:** Admin

**Request:**
```json
{
  "name": "Alert Webhook",
  "url": "https://api.company.com/analytics/webhook",
  "events": [
    "alert.triggered",
    "report.completed",
    "threshold.exceeded"
  ],
  "headers": {
    "Authorization": "Bearer token123",
    "X-Custom-Header": "value"
  },
  "secret": "webhook_secret_for_signature",
  "retry_config": {
    "max_attempts": 3,
    "backoff_seconds": 60
  },
  "is_active": true
}
```

**Response:**
```json
{
  "webhook_id": "wh_1234567890",
  "url": "https://api.company.com/analytics/webhook",
  "events": ["alert.triggered", "report.completed", "threshold.exceeded"],
  "created_at": "2024-01-15T14:00:00Z",
  "test_endpoint": "/api/v1/integrations/webhooks/wh_1234567890/test"
}
```

#### 2. Test Webhook
**POST** `/api/v1/integrations/webhooks/{webhook_id}/test`

Send a test event to verify webhook configuration.

**Required Role:** Admin

**Request:** Optional custom payload

**Response:**
```json
{
  "webhook_id": "wh_1234567890",
  "test_sent": true,
  "response_status": 200,
  "response_time_ms": 145.5,
  "response_body": "{\"status\": \"ok\"}"
}
```

---

### Email Integration

#### Configure Email Provider
**POST** `/api/v1/integrations/email/configure`

Set up email provider for sending reports and alerts.

**Required Role:** Admin

**Request:**
```json
{
  "provider": "sendgrid",
  "settings": {
    "api_key": "sendgrid_api_key",
    "from_email": "analytics@company.com",
    "from_name": "Shadower Analytics"
  },
  "templates": {
    "alert": "template_id_123",
    "report": "template_id_456",
    "digest": "template_id_789"
  }
}
```

**Response:**
```json
{
  "integration_id": "email_sendgrid_1234567890",
  "provider": "sendgrid",
  "configured": true
}
```

---

### Database Integration

#### Connect External Database
**POST** `/api/v1/integrations/database`

Connect an external database for data synchronization.

**Required Role:** Admin

**Request:**
```json
{
  "name": "Production Database",
  "type": "postgresql",
  "connection": {
    "host": "db.company.com",
    "port": 5432,
    "database": "production",
    "username": "analytics_user",
    "password": "encrypted_password",
    "ssl": true
  },
  "sync_config": {
    "tables": ["users", "events", "transactions"],
    "schedule": "0 2 * * *",
    "incremental": true,
    "id_column": "updated_at"
  }
}
```

**Response:**
```json
{
  "integration_id": "db_postgresql_1234567890",
  "name": "Production Database",
  "status": "connected",
  "next_sync": "2024-01-16T02:00:00Z"
}
```

**Supported Database Types:**
- `postgresql`
- `mysql`
- `mongodb`
- `bigquery`
- `snowflake`

---

### API Integration

#### Connect External API
**POST** `/api/v1/integrations/api`

Integrate with external APIs for data synchronization.

**Required Role:** Admin

**Request:**
```json
{
  "name": "CRM API",
  "base_url": "https://api.crm.com/v2",
  "auth": {
    "type": "oauth2",
    "client_id": "client_123",
    "client_secret": "secret_456",
    "token_url": "https://api.crm.com/oauth/token"
  },
  "endpoints": [
    {
      "name": "users",
      "path": "/users",
      "method": "GET",
      "sync_interval": 3600
    }
  ],
  "rate_limit": {
    "requests_per_second": 10,
    "concurrent_requests": 5
  }
}
```

**Response:**
```json
{
  "integration_id": "api_1234567890",
  "name": "CRM API",
  "endpoints_configured": 1,
  "status": "active"
}
```

**Supported Auth Types:**
- `oauth2` - OAuth 2.0
- `api_key` - API Key authentication
- `basic` - HTTP Basic Auth
- `bearer` - Bearer token

---

### Integration Management

#### 1. List Integrations
**GET** `/api/v1/integrations`

Retrieve all configured integrations.

**Required Role:** User

**Query Parameters:**
- `workspace_id` (required): Workspace identifier
- `integration_type` (optional): Filter by type

**Response:**
```json
{
  "integrations": [
    {
      "id": "int_slack_123",
      "type": "slack",
      "name": "Slack Integration",
      "status": "active",
      "last_sync": "2024-01-15T14:00:00Z",
      "error_count": 0,
      "config": {
        "channels": ["#analytics", "#alerts"],
        "notifications_enabled": true
      },
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-15T14:00:00Z"
    }
  ]
}
```

#### 2. Update Integration Status
**PUT** `/api/v1/integrations/{integration_id}/status`

Enable or disable an integration.

**Required Role:** Admin

**Request:**
```json
{
  "is_active": false,
  "reason": "Temporary maintenance"
}
```

**Response:**
```json
{
  "integration_id": "int_slack_123",
  "is_active": false,
  "reason": "Temporary maintenance",
  "updated_at": "2024-01-15T14:30:00Z"
}
```

#### 3. Get Integration Logs
**GET** `/api/v1/integrations/{integration_id}/logs`

Retrieve activity logs for an integration.

**Required Role:** Admin

**Query Parameters:**
- `start_date` (optional): Filter from date
- `end_date` (optional): Filter to date
- `log_status` (optional): Filter by status (success, failure, pending)
- `skip` (optional): Pagination offset (default: 0)
- `limit` (optional): Max results (default: 100, max: 1000)

**Response:**
```json
{
  "logs": [
    {
      "id": "log_123",
      "timestamp": "2024-01-15T14:30:00Z",
      "event_type": "webhook_sent",
      "status": "success",
      "details": {
        "url": "https://api.company.com/webhook",
        "response_code": 200,
        "response_time_ms": 145
      }
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

#### 4. Delete Integration
**DELETE** `/api/v1/integrations/{integration_id}`

Remove an integration and its configuration.

**Required Role:** Admin

**Response:**
```json
{
  "integration_id": "int_slack_123",
  "deleted": true,
  "deleted_at": "2024-01-15T15:00:00Z"
}
```

---

## Webhook Event Payloads

### Alert Triggered
```json
{
  "event": "alert.triggered",
  "timestamp": "2024-01-15T14:30:00Z",
  "workspace_id": "ws_123",
  "data": {
    "alert_id": "alert_456",
    "title": "High Error Rate",
    "severity": "critical",
    "metric": "error_rate",
    "value": 0.08,
    "threshold": 0.05
  }
}
```

### Report Completed
```json
{
  "event": "report.completed",
  "timestamp": "2024-01-15T15:00:00Z",
  "workspace_id": "ws_123",
  "data": {
    "report_id": "report_789",
    "name": "Daily Analytics Report",
    "format": "pdf",
    "size_mb": 4.5,
    "download_url": "https://analytics.shadower.ai/reports/download/report_789"
  }
}
```

### Threshold Exceeded
```json
{
  "event": "threshold.exceeded",
  "timestamp": "2024-01-15T15:30:00Z",
  "workspace_id": "ws_123",
  "data": {
    "metric": "active_users",
    "value": 5000,
    "threshold": 4500,
    "percentage": 111.1
  }
}
```

---

## Error Responses

All endpoints follow a consistent error format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common HTTP Status Codes:**
- `400` - Bad Request (invalid input)
- `401` - Unauthorized (missing or invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (resource doesn't exist)
- `500` - Internal Server Error

---

## Implementation Status

All endpoints are currently implemented with mock responses. The following items require implementation:

### Slack Integration
- [ ] OAuth code exchange with Slack API
- [ ] Slack token storage and management
- [ ] Message sending via Slack Web API
- [ ] Slash command parsing and execution
- [ ] Slack signature verification

### Teams Integration
- [ ] Teams webhook configuration
- [ ] Adaptive card rendering and sending
- [ ] Teams API integration

### Webhook Management
- [ ] Webhook database storage
- [ ] Event subscription system
- [ ] Webhook delivery with retry logic
- [ ] Signature generation for security

### Email Integration
- [ ] SendGrid integration
- [ ] AWS SES integration
- [ ] SMTP integration
- [ ] Template management

### Database Integration
- [ ] Database connection testing
- [ ] Sync scheduling (cron)
- [ ] Incremental data sync
- [ ] Connection pool management

### API Integration
- [ ] OAuth 2.0 flow implementation
- [ ] API key management
- [ ] Rate limiting
- [ ] Endpoint synchronization

### Common Features
- [ ] Integration database models
- [ ] Activity logging
- [ ] Error tracking and reporting
- [ ] Metrics and monitoring

---

## Success Metrics

Target metrics for integration endpoints:

- **Integration setup time:** < 5 minutes
- **Webhook delivery success rate:** > 99%
- **Message delivery latency:** < 1 second
- **Integration uptime:** > 99.9%

---

## Next Steps

1. Implement database models for integrations
2. Add service layer for each integration type
3. Implement OAuth flows for Slack and Teams
4. Add webhook delivery system with queuing
5. Implement comprehensive error handling
6. Add integration health monitoring
7. Create admin dashboard for managing integrations
8. Add comprehensive test coverage

---

## Support

For questions or issues with the Integration API, please contact the development team or file an issue in the project repository.
