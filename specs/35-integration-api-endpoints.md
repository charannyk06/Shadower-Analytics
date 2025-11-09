# Specification: Integration API Endpoints

## Overview
Define API endpoints for third-party integrations including Slack, Teams, webhooks, and external data sources.

## Technical Requirements

### Slack Integration Endpoints

#### POST `/api/v1/integrations/slack/install`
```python
@router.post("/integrations/slack/install")
async def install_slack_integration(
    slack_config: SlackInstallConfig,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Install Slack integration for workspace
    
    Request body:
    {
        "workspace_id": "ws_123",
        "slack_workspace": "company.slack.com",
        "oauth_code": "slack_oauth_code",
        "redirect_uri": "https://analytics.shadower.ai/slack/callback"
    }
    """
    # Exchange OAuth code for access token
    slack_tokens = await exchange_slack_oauth_code(
        code=slack_config.oauth_code,
        redirect_uri=slack_config.redirect_uri
    )
    
    # Store Slack integration
    integration = await create_slack_integration(
        workspace_id=slack_config.workspace_id,
        slack_tokens=slack_tokens
    )
    
    return {
        "integration_id": integration.id,
        "slack_team_id": integration.slack_team_id,
        "slack_team_name": integration.slack_team_name,
        "installed_channels": integration.channels,
        "bot_user_id": integration.bot_user_id
    }
```

#### POST `/api/v1/integrations/slack/send`
```python
@router.post("/integrations/slack/send")
async def send_slack_message(
    message_config: SlackMessageConfig,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Send message to Slack channel
    
    Request body:
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
    """
    result = await send_to_slack(
        workspace_id=user.workspace_id,
        config=message_config
    )
    
    return {
        "sent": True,
        "message_ts": result.timestamp,
        "channel": result.channel
    }
```

#### POST `/api/v1/integrations/slack/slash-command`
```python
@router.post("/integrations/slack/slash-command")
async def handle_slack_slash_command(
    command: SlackSlashCommand = Form()
) -> dict:
    """
    Handle Slack slash commands
    
    Slash commands:
    - /analytics summary - Get today's summary
    - /analytics agent [agent_id] - Get agent performance
    - /analytics report [type] - Generate report
    """
    # Verify Slack signature
    if not verify_slack_signature(command):
        raise HTTPException(401, "Invalid signature")
    
    # Parse command
    action, params = parse_slack_command(command.text)
    
    # Execute action
    response = await execute_slack_action(
        action=action,
        params=params,
        user_id=command.user_id,
        channel_id=command.channel_id
    )
    
    return {
        "response_type": "in_channel",
        "text": response.text,
        "blocks": response.blocks
    }
```

### Microsoft Teams Integration

#### POST `/api/v1/integrations/teams/install`
```python
@router.post("/integrations/teams/install")
async def install_teams_integration(
    teams_config: TeamsInstallConfig,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Install Microsoft Teams integration
    
    Request body:
    {
        "workspace_id": "ws_123",
        "tenant_id": "microsoft_tenant_id",
        "client_id": "app_client_id",
        "client_secret": "app_client_secret",
        "webhook_url": "https://outlook.office.com/webhook/..."
    }
    """
    integration = await create_teams_integration(
        workspace_id=teams_config.workspace_id,
        config=teams_config
    )
    
    return {
        "integration_id": integration.id,
        "tenant_id": integration.tenant_id,
        "configured_channels": integration.channels
    }
```

#### POST `/api/v1/integrations/teams/card`
```python
@router.post("/integrations/teams/card")
async def send_teams_adaptive_card(
    card_config: TeamsCardConfig,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Send adaptive card to Teams channel
    
    Request body:
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
    """
    result = await send_teams_message(
        workspace_id=user.workspace_id,
        config=card_config
    )
    
    return {
        "sent": True,
        "message_id": result.message_id
    }
```

### Webhook Management

#### POST `/api/v1/integrations/webhooks`
```python
@router.post("/integrations/webhooks")
async def create_webhook(
    webhook_config: WebhookConfig,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Create webhook endpoint
    
    Request body:
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
    """
    webhook = await create_webhook_endpoint(
        workspace_id=user.workspace_id,
        config=webhook_config
    )
    
    return {
        "webhook_id": webhook.id,
        "url": webhook.url,
        "events": webhook.events,
        "created_at": webhook.created_at,
        "test_endpoint": f"/api/v1/integrations/webhooks/{webhook.id}/test"
    }
```

#### POST `/api/v1/integrations/webhooks/{webhook_id}/test`
```python
@router.post("/integrations/webhooks/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    test_payload: Optional[dict] = None,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Test webhook with sample payload
    """
    webhook = await get_webhook(webhook_id)
    
    # Send test payload
    result = await send_webhook_test(
        webhook=webhook,
        payload=test_payload or generate_sample_payload(webhook.events[0])
    )
    
    return {
        "webhook_id": webhook_id,
        "test_sent": True,
        "response_status": result.status_code,
        "response_time_ms": result.response_time,
        "response_body": result.body[:500]  # First 500 chars
    }
```

### Email Integration

#### POST `/api/v1/integrations/email/configure`
```python
@router.post("/integrations/email/configure")
async def configure_email_integration(
    email_config: EmailConfig,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Configure email integration settings
    
    Request body:
    {
        "provider": "sendgrid",  # sendgrid, ses, smtp
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
    """
    integration = await configure_email_provider(
        workspace_id=user.workspace_id,
        config=email_config
    )
    
    return {
        "integration_id": integration.id,
        "provider": integration.provider,
        "configured": True
    }
```

### Database Integration

#### POST `/api/v1/integrations/database`
```python
@router.post("/integrations/database")
async def create_database_integration(
    db_config: DatabaseIntegrationConfig,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Connect external database for data import
    
    Request body:
    {
        "name": "Production Database",
        "type": "postgresql",  # postgresql, mysql, mongodb, bigquery
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
            "schedule": "0 2 * * *",  # Daily at 2 AM
            "incremental": true,
            "id_column": "updated_at"
        }
    }
    """
    # Test connection
    connection_valid = await test_database_connection(db_config.connection)
    
    if not connection_valid:
        raise HTTPException(400, "Cannot connect to database")
    
    # Create integration
    integration = await create_db_integration(
        workspace_id=user.workspace_id,
        config=db_config
    )
    
    return {
        "integration_id": integration.id,
        "name": integration.name,
        "status": "connected",
        "next_sync": integration.next_sync_time
    }
```

### API Integration

#### POST `/api/v1/integrations/api`
```python
@router.post("/integrations/api")
async def create_api_integration(
    api_config: APIIntegrationConfig,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Connect external API for data sync
    
    Request body:
    {
        "name": "CRM API",
        "base_url": "https://api.crm.com/v2",
        "auth": {
            "type": "oauth2",  # oauth2, api_key, basic
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
    """
    integration = await create_api_integration(
        workspace_id=user.workspace_id,
        config=api_config
    )
    
    return {
        "integration_id": integration.id,
        "name": integration.name,
        "endpoints_configured": len(integration.endpoints),
        "status": "active"
    }
```

### Integration Status

#### GET `/api/v1/integrations`
```python
@router.get("/integrations")
async def list_integrations(
    workspace_id: str,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    List all integrations for workspace
    """
    integrations = await get_workspace_integrations(workspace_id)
    
    return {
        "integrations": [
            {
                "id": "int_123",
                "type": "slack",
                "name": "Slack Integration",
                "status": "active",
                "last_sync": "2024-01-15T14:00:00Z",
                "error_count": 0,
                "config": {
                    "channels": ["#analytics", "#alerts"],
                    "notifications_enabled": True
                }
            }
        ]
    }
```

#### PUT `/api/v1/integrations/{integration_id}/status`
```python
@router.put("/integrations/{integration_id}/status")
async def update_integration_status(
    integration_id: str,
    status_update: IntegrationStatusUpdate,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Enable/disable integration
    
    Request body:
    {
        "is_active": false,
        "reason": "Temporary maintenance"
    }
    """
    await update_integration_status_db(
        integration_id=integration_id,
        status_update=status_update
    )
    
    return {
        "integration_id": integration_id,
        "is_active": status_update.is_active,
        "updated_at": datetime.utcnow().isoformat()
    }
```

### Integration Logs

#### GET `/api/v1/integrations/{integration_id}/logs`
```python
@router.get("/integrations/{integration_id}/logs")
async def get_integration_logs(
    integration_id: str,
    date_range: Optional[DateRange] = None,
    status: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    user: User = Depends(require_admin)
) -> PaginatedResponse:
    """
    Get integration activity logs
    """
    logs = await get_integration_activity_logs(
        integration_id=integration_id,
        date_range=date_range,
        status=status,
        pagination=pagination
    )
    
    return {
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
        **pagination.dict()
    }
```

## Webhook Payload Examples

```python
# Alert Triggered
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

# Report Completed
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

## Implementation Priority
1. Slack integration
2. Webhook management
3. Email configuration
4. Teams integration
5. External database connections

## Success Metrics
- Integration setup time < 5 minutes
- Webhook delivery success rate > 99%
- Message delivery latency < 1 second
- Integration uptime > 99.9%