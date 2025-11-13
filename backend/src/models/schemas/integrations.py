"""Integration schemas for third-party services."""

from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


class IntegrationType(str, Enum):
    """Integration type enumeration."""

    SLACK = "slack"
    TEAMS = "teams"
    WEBHOOK = "webhook"
    EMAIL = "email"
    DATABASE = "database"
    API = "api"


class IntegrationStatus(str, Enum):
    """Integration status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"


class EventType(str, Enum):
    """Webhook event types."""

    ALERT_TRIGGERED = "alert.triggered"
    REPORT_COMPLETED = "report.completed"
    THRESHOLD_EXCEEDED = "threshold.exceeded"
    AGENT_ERROR = "agent.error"
    WORKSPACE_CREATED = "workspace.created"
    USER_ADDED = "user.added"


# Slack Integration Schemas
class SlackInstallConfig(BaseModel):
    """Slack installation configuration."""

    workspace_id: str = Field(..., min_length=1, max_length=255)
    slack_workspace: str = Field(..., min_length=1)
    oauth_code: str = Field(..., min_length=1)
    redirect_uri: HttpUrl


class SlackBlock(BaseModel):
    """Slack block element."""

    type: str
    text: Optional[Dict[str, Any]] = None
    fields: Optional[List[Dict[str, Any]]] = None
    elements: Optional[List[Dict[str, Any]]] = None
    accessory: Optional[Dict[str, Any]] = None


class SlackAttachment(BaseModel):
    """Slack message attachment."""

    title: Optional[str] = None
    title_link: Optional[HttpUrl] = None
    text: Optional[str] = None
    color: Optional[str] = None
    fields: Optional[List[Dict[str, str]]] = None


class SlackMessageConfig(BaseModel):
    """Slack message configuration."""

    channel: str = Field(..., min_length=1)
    message: Optional[str] = None
    blocks: Optional[List[SlackBlock]] = None
    attachments: Optional[List[SlackAttachment]] = None
    thread_ts: Optional[str] = None


class SlackSlashCommand(BaseModel):
    """Slack slash command payload."""

    token: str
    team_id: str
    team_domain: str
    channel_id: str
    channel_name: str
    user_id: str
    user_name: str
    command: str
    text: str
    response_url: HttpUrl
    trigger_id: str


class SlackIntegrationResponse(BaseModel):
    """Slack integration response."""

    integration_id: str
    slack_team_id: str
    slack_team_name: str
    installed_channels: List[str]
    bot_user_id: str


class SlackMessageResponse(BaseModel):
    """Slack message send response."""

    sent: bool
    message_ts: str
    channel: str


# Microsoft Teams Schemas
class TeamsInstallConfig(BaseModel):
    """Teams installation configuration."""

    workspace_id: str = Field(..., min_length=1, max_length=255)
    tenant_id: str = Field(..., min_length=1)
    client_id: str = Field(..., min_length=1)
    client_secret: str = Field(..., min_length=1)
    webhook_url: HttpUrl


class TeamsAdaptiveCard(BaseModel):
    """Teams adaptive card."""

    type: str = "AdaptiveCard"
    version: str = "1.4"
    body: List[Dict[str, Any]]
    actions: Optional[List[Dict[str, Any]]] = None


class TeamsCardConfig(BaseModel):
    """Teams card configuration."""

    channel: str = Field(..., min_length=1)
    card: TeamsAdaptiveCard


class TeamsIntegrationResponse(BaseModel):
    """Teams integration response."""

    integration_id: str
    tenant_id: str
    configured_channels: List[str]


class TeamsMessageResponse(BaseModel):
    """Teams message send response."""

    sent: bool
    message_id: str


# Webhook Schemas
class RetryConfig(BaseModel):
    """Webhook retry configuration."""

    max_attempts: int = Field(3, ge=1, le=10)
    backoff_seconds: int = Field(60, ge=1, le=3600)


class WebhookConfig(BaseModel):
    """Webhook configuration."""

    name: str = Field(..., min_length=1, max_length=255)
    url: HttpUrl
    events: List[EventType]
    headers: Optional[Dict[str, str]] = None
    secret: Optional[str] = None
    retry_config: Optional[RetryConfig] = RetryConfig()
    is_active: bool = True


class WebhookResponse(BaseModel):
    """Webhook creation response."""

    webhook_id: str
    url: HttpUrl
    events: List[EventType]
    created_at: datetime
    test_endpoint: str


class WebhookTestResponse(BaseModel):
    """Webhook test response."""

    webhook_id: str
    test_sent: bool
    response_status: int
    response_time_ms: float
    response_body: str


# Email Integration Schemas
class EmailProvider(str, Enum):
    """Email provider types."""

    SENDGRID = "sendgrid"
    SES = "ses"
    SMTP = "smtp"


class EmailConfig(BaseModel):
    """Email integration configuration."""

    provider: EmailProvider
    settings: Dict[str, Any]
    templates: Optional[Dict[str, str]] = None


class EmailIntegrationResponse(BaseModel):
    """Email integration response."""

    integration_id: str
    provider: EmailProvider
    configured: bool


# Database Integration Schemas
class DatabaseType(str, Enum):
    """Database types."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    BIGQUERY = "bigquery"
    SNOWFLAKE = "snowflake"


class DatabaseConnection(BaseModel):
    """Database connection details."""

    host: str
    port: int
    database: str
    username: str
    password: str
    ssl: bool = True
    additional_params: Optional[Dict[str, Any]] = None


class SyncConfig(BaseModel):
    """Database sync configuration."""

    tables: List[str]
    schedule: str  # Cron expression
    incremental: bool = True
    id_column: str = "updated_at"
    batch_size: int = Field(1000, ge=1, le=10000)


class DatabaseIntegrationConfig(BaseModel):
    """Database integration configuration."""

    name: str = Field(..., min_length=1, max_length=255)
    type: DatabaseType
    connection: DatabaseConnection
    sync_config: SyncConfig


class DatabaseIntegrationResponse(BaseModel):
    """Database integration response."""

    integration_id: str
    name: str
    status: str
    next_sync: Optional[datetime] = None


# API Integration Schemas
class AuthType(str, Enum):
    """API authentication types."""

    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    BASIC = "basic"
    BEARER = "bearer"


class APIAuth(BaseModel):
    """API authentication configuration."""

    type: AuthType
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    token_url: Optional[HttpUrl] = None
    api_key: Optional[str] = None
    api_key_header: Optional[str] = "X-API-Key"
    username: Optional[str] = None
    password: Optional[str] = None


class APIEndpoint(BaseModel):
    """API endpoint configuration."""

    name: str
    path: str
    method: str = "GET"
    sync_interval: int = Field(3600, ge=60)  # seconds


class RateLimitConfig(BaseModel):
    """Rate limit configuration."""

    requests_per_second: int = Field(10, ge=1, le=1000)
    concurrent_requests: int = Field(5, ge=1, le=100)


class APIIntegrationConfig(BaseModel):
    """API integration configuration."""

    name: str = Field(..., min_length=1, max_length=255)
    base_url: HttpUrl
    auth: APIAuth
    endpoints: List[APIEndpoint]
    rate_limit: Optional[RateLimitConfig] = RateLimitConfig()


class APIIntegrationResponse(BaseModel):
    """API integration response."""

    integration_id: str
    name: str
    endpoints_configured: int
    status: str


# Integration Management Schemas
class Integration(BaseModel):
    """Integration model."""

    id: str
    type: IntegrationType
    name: str
    status: IntegrationStatus
    last_sync: Optional[datetime] = None
    error_count: int = 0
    config: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None


class IntegrationStatusUpdate(BaseModel):
    """Integration status update."""

    is_active: bool
    reason: Optional[str] = None


class IntegrationListResponse(BaseModel):
    """Integration list response."""

    integrations: List[Integration]


# Integration Logs Schemas
class LogStatus(str, Enum):
    """Log status enumeration."""

    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"


class IntegrationLog(BaseModel):
    """Integration activity log."""

    id: str
    timestamp: datetime
    event_type: str
    status: LogStatus
    details: Dict[str, Any]


class IntegrationLogsResponse(BaseModel):
    """Integration logs response."""

    logs: List[IntegrationLog]
    total: int
    skip: int
    limit: int


# Webhook Event Payload Schemas
class AlertTriggeredPayload(BaseModel):
    """Alert triggered event payload."""

    event: str = EventType.ALERT_TRIGGERED
    timestamp: datetime
    workspace_id: str
    data: Dict[str, Any]


class ReportCompletedPayload(BaseModel):
    """Report completed event payload."""

    event: str = EventType.REPORT_COMPLETED
    timestamp: datetime
    workspace_id: str
    data: Dict[str, Any]


class ThresholdExceededPayload(BaseModel):
    """Threshold exceeded event payload."""

    event: str = EventType.THRESHOLD_EXCEEDED
    timestamp: datetime
    workspace_id: str
    data: Dict[str, Any]


# API Response wrapper
class APIResponse(BaseModel):
    """Generic API response."""

    success: bool = True
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DateRange(BaseModel):
    """Date range filter."""

    start_date: datetime
    end_date: datetime

    @validator('end_date')
    def end_date_must_be_after_start_date(cls, v, values):
        """Validate end_date is after start_date."""
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v
