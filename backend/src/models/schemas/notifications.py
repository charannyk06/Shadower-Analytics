"""Notification system schemas."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


class NotificationChannelEnum(str, Enum):
    """Notification channel enumeration."""

    IN_APP = "in_app"
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    DISCORD = "discord"
    WEBHOOK = "webhook"


class NotificationFrequencyEnum(str, Enum):
    """Notification frequency enumeration."""

    IMMEDIATE = "immediate"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


class NotificationPriorityEnum(str, Enum):
    """Notification priority enumeration."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatusEnum(str, Enum):
    """Notification status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeliveryStatusEnum(str, Enum):
    """Delivery status enumeration."""

    SENT = "sent"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    FAILED = "failed"
    READ = "read"
    CLICKED = "clicked"


class DigestTypeEnum(str, Enum):
    """Digest type enumeration."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


# =====================================================================
# Notification Preference Schemas
# =====================================================================


class NotificationPreferenceBase(BaseModel):
    """Base notification preference schema."""

    notification_type: str
    channel: NotificationChannelEnum
    is_enabled: bool = True
    frequency: NotificationFrequencyEnum = NotificationFrequencyEnum.IMMEDIATE
    schedule_time: Optional[datetime] = None
    schedule_timezone: str = "UTC"
    filter_rules: Dict[str, Any] = Field(default_factory=dict)


class NotificationPreferenceCreate(NotificationPreferenceBase):
    """Create notification preference schema."""

    user_id: str
    workspace_id: str


class NotificationPreferenceUpdate(BaseModel):
    """Update notification preference schema."""

    is_enabled: Optional[bool] = None
    frequency: Optional[NotificationFrequencyEnum] = None
    schedule_time: Optional[datetime] = None
    schedule_timezone: Optional[str] = None
    filter_rules: Optional[Dict[str, Any]] = None


class NotificationPreference(NotificationPreferenceBase):
    """Notification preference response schema."""

    id: str
    user_id: str
    workspace_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =====================================================================
# Notification Template Schemas
# =====================================================================


class NotificationTemplateBase(BaseModel):
    """Base notification template schema."""

    template_name: str
    notification_type: str
    channel: NotificationChannelEnum
    subject_template: Optional[str] = None
    body_template: str
    variables: List[str] = Field(default_factory=list)
    preview_data: Optional[Dict[str, Any]] = None
    is_active: bool = True


class NotificationTemplateCreate(NotificationTemplateBase):
    """Create notification template schema."""

    pass


class NotificationTemplateUpdate(BaseModel):
    """Update notification template schema."""

    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    variables: Optional[List[str]] = None
    preview_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class NotificationTemplate(NotificationTemplateBase):
    """Notification template response schema."""

    id: str
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =====================================================================
# Notification Queue Schemas
# =====================================================================


class NotificationQueueBase(BaseModel):
    """Base notification queue schema."""

    notification_type: str
    recipient_id: str
    recipient_email: Optional[str] = None
    channel: NotificationChannelEnum
    priority: NotificationPriorityEnum = NotificationPriorityEnum.NORMAL
    payload: Dict[str, Any] = Field(default_factory=dict)
    scheduled_for: Optional[datetime] = None


class NotificationQueueCreate(NotificationQueueBase):
    """Create notification queue entry schema."""

    pass


class NotificationQueue(NotificationQueueBase):
    """Notification queue response schema."""

    id: str
    status: NotificationStatusEnum
    attempts: int
    max_attempts: int
    last_attempt_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# =====================================================================
# Notification Log Schemas
# =====================================================================


class NotificationLogBase(BaseModel):
    """Base notification log schema."""

    user_id: str
    workspace_id: str
    notification_type: str
    channel: NotificationChannelEnum
    subject: Optional[str] = None
    preview: Optional[str] = None
    full_content: Optional[str] = None
    delivery_status: DeliveryStatusEnum


class NotificationLogCreate(NotificationLogBase):
    """Create notification log schema."""

    notification_id: Optional[str] = None
    tracking_data: Dict[str, Any] = Field(default_factory=dict)


class NotificationLog(NotificationLogBase):
    """Notification log response schema."""

    id: str
    notification_id: Optional[str] = None
    sent_at: datetime
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    tracking_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


# =====================================================================
# Digest Queue Schemas
# =====================================================================


class DigestQueueBase(BaseModel):
    """Base digest queue schema."""

    user_id: str
    workspace_id: str
    digest_type: DigestTypeEnum
    period_start: datetime
    period_end: datetime
    events: List[Dict[str, Any]] = Field(default_factory=list)
    summary_stats: Dict[str, Any] = Field(default_factory=dict)


class DigestQueueCreate(DigestQueueBase):
    """Create digest queue entry schema."""

    pass


class DigestQueue(DigestQueueBase):
    """Digest queue response schema."""

    id: str
    is_sent: bool
    sent_at: Optional[datetime] = None
    notification_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# =====================================================================
# Notification Channel Configuration Schemas
# =====================================================================


class NotificationChannelBase(BaseModel):
    """Base notification channel schema."""

    workspace_id: str
    channel: NotificationChannelEnum
    is_enabled: bool = True
    configuration: Dict[str, Any] = Field(default_factory=dict)


class NotificationChannelCreate(NotificationChannelBase):
    """Create notification channel schema."""

    pass


class NotificationChannelUpdate(BaseModel):
    """Update notification channel schema."""

    is_enabled: Optional[bool] = None
    configuration: Optional[Dict[str, Any]] = None


class NotificationChannel(NotificationChannelBase):
    """Notification channel response schema."""

    id: str
    last_test_at: Optional[datetime] = None
    last_test_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =====================================================================
# Notification Subscription Schemas
# =====================================================================


class NotificationSubscriptionBase(BaseModel):
    """Base notification subscription schema."""

    user_id: str
    workspace_id: str
    subscription_type: str
    is_subscribed: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NotificationSubscriptionCreate(NotificationSubscriptionBase):
    """Create notification subscription schema."""

    pass


class NotificationSubscriptionUpdate(BaseModel):
    """Update notification subscription schema."""

    is_subscribed: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationSubscription(NotificationSubscriptionBase):
    """Notification subscription response schema."""

    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =====================================================================
# Request/Response Schemas
# =====================================================================


class SendNotificationRequest(BaseModel):
    """Send notification request schema."""

    notification_type: str
    recipients: List[str]
    data: Dict[str, Any]
    priority: NotificationPriorityEnum = NotificationPriorityEnum.NORMAL
    channels: Optional[List[NotificationChannelEnum]] = None
    scheduled_for: Optional[datetime] = None

    @field_validator('recipients')
    @classmethod
    def validate_recipients(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one recipient is required')
        return v


class SendNotificationResponse(BaseModel):
    """Send notification response schema."""

    notification_ids: List[str]
    queued_count: int
    failed_count: int = 0
    message: str


class BulkNotificationRequest(BaseModel):
    """Bulk notification request schema."""

    notification_type: str
    recipients: List[str]
    data: Dict[str, Any]
    priority: NotificationPriorityEnum = NotificationPriorityEnum.NORMAL
    channels: Optional[List[NotificationChannelEnum]] = None

    @field_validator('recipients')
    @classmethod
    def validate_recipients(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one recipient is required')
        if len(v) > 1000:
            raise ValueError('Maximum 1000 recipients allowed per bulk request')
        return v


class BulkNotificationResponse(BaseModel):
    """Bulk notification response schema."""

    job_id: str
    total_recipients: int
    queued_count: int
    status: str


class TestNotificationRequest(BaseModel):
    """Test notification request schema."""

    channel: NotificationChannelEnum
    template_name: Optional[str] = None
    sample_data: Dict[str, Any] = Field(default_factory=dict)


class TestNotificationResponse(BaseModel):
    """Test notification response schema."""

    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class MarkAsReadRequest(BaseModel):
    """Mark notification as read request schema."""

    notification_ids: List[str]


class MarkAsReadResponse(BaseModel):
    """Mark as read response schema."""

    updated_count: int
    message: str


class NotificationListResponse(BaseModel):
    """Notification list response schema."""

    notifications: List[NotificationLog]
    total: int
    unread_count: int
    has_more: bool


class NotificationPreferencesResponse(BaseModel):
    """Notification preferences response schema."""

    preferences: List[NotificationPreference]
    total: int


class DigestPreviewRequest(BaseModel):
    """Digest preview request schema."""

    workspace_id: str
    digest_type: DigestTypeEnum
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class DigestPreviewResponse(BaseModel):
    """Digest preview response schema."""

    subject: str
    preview: str
    events_count: int
    summary_stats: Dict[str, Any]
    formatted_content: str


class NotificationMetrics(BaseModel):
    """Notification metrics schema."""

    workspace_id: str
    notification_type: str
    channel: NotificationChannelEnum
    total_sent: int
    total_delivered: int
    total_failed: int
    total_bounced: int
    total_read: int
    total_clicked: int
    delivery_rate: float
    open_rate: float
    click_through_rate: float
    avg_delivery_time_seconds: float


class NotificationMetricsResponse(BaseModel):
    """Notification metrics response schema."""

    metrics: List[NotificationMetrics]
    period_start: datetime
    period_end: datetime
    last_refreshed: datetime


class UnreadCountResponse(BaseModel):
    """Unread notification count response schema."""

    user_id: str
    workspace_id: Optional[str] = None
    unread_count: int
