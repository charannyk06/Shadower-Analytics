"""Alert engine schemas."""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from uuid import UUID


class SeverityEnum(str, Enum):
    """Alert severity enumeration."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class ConditionTypeEnum(str, Enum):
    """Alert condition type enumeration."""

    THRESHOLD = "threshold"
    CHANGE = "change"
    ANOMALY = "anomaly"
    PATTERN = "pattern"


class DeliveryStatusEnum(str, Enum):
    """Notification delivery status enumeration."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"


class ChannelTypeEnum(str, Enum):
    """Notification channel enumeration."""

    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    PAGERDUTY = "pagerduty"


class SuppressionTypeEnum(str, Enum):
    """Alert suppression type enumeration."""

    RULE = "rule"
    PATTERN = "pattern"
    MAINTENANCE = "maintenance"


# Alert Rule Schemas
class AlertConditionConfig(BaseModel):
    """Base alert condition configuration."""

    metric: str
    operator: Optional[str] = None  # For threshold: '>', '<', '>=', '<=', '=='
    value: Optional[float] = None
    duration_minutes: Optional[int] = 5


class ThresholdCondition(AlertConditionConfig):
    """Threshold-based alert condition."""

    operator: str = Field(..., regex="^(>|<|>=|<=|==|!=)$")
    value: float


class ChangeCondition(AlertConditionConfig):
    """Change-based alert condition."""

    change_type: str = Field(..., regex="^(percent|absolute)$")
    threshold: float
    comparison_period: str = Field(..., regex="^(previous_hour|previous_day|previous_week)$")


class AnomalyCondition(AlertConditionConfig):
    """Anomaly detection alert condition."""

    sensitivity: float = Field(2.5, ge=1.0, le=5.0)
    min_deviation_duration: int = Field(10, ge=1)


class PatternCondition(AlertConditionConfig):
    """Pattern-based alert condition."""

    pattern: str
    window_minutes: int = Field(30, ge=5)
    min_occurrences: int = Field(3, ge=1)


class AlertRuleCreate(BaseModel):
    """Schema for creating an alert rule."""

    workspace_id: UUID
    rule_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    metric_type: str = Field(..., min_length=1, max_length=100)
    condition_type: ConditionTypeEnum
    condition_config: Dict[str, Any]
    severity: SeverityEnum
    is_active: bool = True
    check_interval_minutes: int = Field(5, ge=1, le=1440)
    cooldown_minutes: int = Field(60, ge=0, le=10080)
    notification_channels: List[Dict[str, Any]]
    escalation_policy_id: Optional[UUID] = None

    @validator('notification_channels')
    def validate_channels(cls, v):
        """Validate notification channels configuration."""
        if not v:
            raise ValueError("At least one notification channel is required")
        for channel in v:
            if 'type' not in channel:
                raise ValueError("Each channel must have a 'type' field")
            if channel['type'] not in ['email', 'slack', 'webhook', 'sms', 'pagerduty']:
                raise ValueError(f"Invalid channel type: {channel['type']}")
        return v


class AlertRuleUpdate(BaseModel):
    """Schema for updating an alert rule."""

    rule_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    metric_type: Optional[str] = Field(None, min_length=1, max_length=100)
    condition_type: Optional[ConditionTypeEnum] = None
    condition_config: Optional[Dict[str, Any]] = None
    severity: Optional[SeverityEnum] = None
    is_active: Optional[bool] = None
    check_interval_minutes: Optional[int] = Field(None, ge=1, le=1440)
    cooldown_minutes: Optional[int] = Field(None, ge=0, le=10080)
    notification_channels: Optional[List[Dict[str, Any]]] = None
    escalation_policy_id: Optional[UUID] = None


class AlertRuleResponse(BaseModel):
    """Schema for alert rule response."""

    id: UUID
    workspace_id: UUID
    rule_name: str
    description: Optional[str] = None
    metric_type: str
    condition_type: str
    condition_config: Dict[str, Any]
    severity: str
    is_active: bool
    check_interval_minutes: int
    cooldown_minutes: int
    notification_channels: List[Dict[str, Any]]
    escalation_policy_id: Optional[UUID] = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    last_evaluated_at: Optional[datetime] = None
    last_triggered_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Alert Schemas
class AlertResponse(BaseModel):
    """Schema for alert response."""

    id: UUID
    workspace_id: UUID
    rule_id: UUID
    alert_title: str
    alert_message: str
    severity: str
    metric_value: Optional[float] = None
    threshold_value: Optional[float] = None
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[UUID] = None
    resolution_notes: Optional[str] = None
    alert_context: Optional[Dict[str, Any]] = None
    notification_sent: bool
    notification_channels: Optional[List[Dict[str, Any]]] = None
    escalated: bool
    escalation_level: int

    class Config:
        from_attributes = True


class AlertAcknowledge(BaseModel):
    """Schema for acknowledging an alert."""

    acknowledged_by: UUID
    notes: Optional[str] = None


class AlertResolve(BaseModel):
    """Schema for resolving an alert."""

    resolved_by: UUID
    resolution_notes: str = Field(..., min_length=1)
    permanent_fix: bool = False


# Escalation Policy Schemas
class EscalationLevel(BaseModel):
    """Schema for an escalation level."""

    level: int = Field(..., ge=1)
    delay_minutes: int = Field(..., ge=0)
    channels: List[str]
    recipients: List[str]


class EscalationPolicyCreate(BaseModel):
    """Schema for creating an escalation policy."""

    workspace_id: UUID
    policy_name: str = Field(..., min_length=1, max_length=255)
    escalation_levels: List[EscalationLevel]
    is_active: bool = True

    @validator('escalation_levels')
    def validate_levels(cls, v):
        """Validate escalation levels."""
        if not v:
            raise ValueError("At least one escalation level is required")
        levels = [level.level for level in v]
        if len(levels) != len(set(levels)):
            raise ValueError("Escalation levels must be unique")
        return v


class EscalationPolicyUpdate(BaseModel):
    """Schema for updating an escalation policy."""

    policy_name: Optional[str] = Field(None, min_length=1, max_length=255)
    escalation_levels: Optional[List[EscalationLevel]] = None
    is_active: Optional[bool] = None


class EscalationPolicyResponse(BaseModel):
    """Schema for escalation policy response."""

    id: UUID
    workspace_id: UUID
    policy_name: str
    escalation_levels: List[Dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Alert Suppression Schemas
class AlertSuppressionCreate(BaseModel):
    """Schema for creating an alert suppression."""

    workspace_id: UUID
    suppression_type: SuppressionTypeEnum
    pattern: Dict[str, Any]
    start_time: datetime
    end_time: datetime
    reason: Optional[str] = None

    @validator('end_time')
    def validate_end_time(cls, v, values):
        """Validate that end_time is after start_time."""
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError("end_time must be after start_time")
        return v


class AlertSuppressionResponse(BaseModel):
    """Schema for alert suppression response."""

    id: UUID
    workspace_id: UUID
    suppression_type: str
    pattern: Dict[str, Any]
    start_time: datetime
    end_time: datetime
    reason: Optional[str] = None
    created_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# Notification History Schemas
class NotificationHistoryResponse(BaseModel):
    """Schema for notification history response."""

    id: UUID
    alert_id: UUID
    channel: str
    recipient: str
    sent_at: datetime
    delivery_status: str
    error_message: Optional[str] = None
    retry_count: int
    response_data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# Alert Testing Schemas
class AlertRuleTest(BaseModel):
    """Schema for testing an alert rule."""

    rule_config: AlertRuleCreate
    test_period: str = Field("24h", regex="^(1h|6h|12h|24h|7d)$")


class AlertRuleTestResult(BaseModel):
    """Schema for alert rule test results."""

    would_have_triggered: bool
    trigger_count: int
    trigger_times: List[datetime]
    sample_alerts: List[Dict[str, Any]]


# Query Schemas
class AlertQueryParams(BaseModel):
    """Schema for alert query parameters."""

    workspace_id: UUID
    severity: Optional[SeverityEnum] = None
    acknowledged: Optional[bool] = None
    resolved: Optional[bool] = None
    rule_id: Optional[UUID] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=500)


class AlertHistoryQueryParams(BaseModel):
    """Schema for alert history query parameters."""

    workspace_id: UUID
    rule_id: Optional[UUID] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)


# Dashboard Schemas
class AlertStats(BaseModel):
    """Schema for alert statistics."""

    total_alerts: int
    active_alerts: int
    acknowledged_alerts: int
    resolved_alerts: int
    critical_alerts: int
    alerts_by_severity: Dict[str, int]
    alerts_by_rule: List[Dict[str, Any]]
    recent_alerts: List[AlertResponse]


class AlertTrends(BaseModel):
    """Schema for alert trends."""

    period: str
    alert_counts: List[Dict[str, Any]]
    severity_trends: Dict[str, List[int]]
    mttr: float  # Mean time to resolve
    mtta: float  # Mean time to acknowledge
