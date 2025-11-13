"""Report schemas."""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class ReportFormat(str, Enum):
    """Report format enumeration."""
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"
    PPTX = "pptx"


class ReportStatus(str, Enum):
    """Report job status enumeration."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportSection(str, Enum):
    """Report section types."""
    EXECUTIVE_SUMMARY = "executive_summary"
    USER_ANALYTICS = "user_analytics"
    AGENT_PERFORMANCE = "agent_performance"
    FINANCIAL_METRICS = "financial_metrics"
    TRENDS = "trends"
    COMPARISONS = "comparisons"
    ANOMALIES = "anomalies"


class DeliveryMethod(str, Enum):
    """Report delivery methods."""
    EMAIL = "email"
    DOWNLOAD = "download"
    WEBHOOK = "webhook"
    SLACK = "slack"


class ReportFrequency(str, Enum):
    """Report scheduling frequency."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class TemplateCategory(str, Enum):
    """Template categories."""
    EXECUTIVE = "executive"
    OPERATIONAL = "operational"
    TECHNICAL = "technical"
    FINANCIAL = "financial"
    CUSTOM = "custom"


class SectionType(str, Enum):
    """Section types for templates."""
    CHART = "chart"
    TABLE = "table"
    TEXT = "text"
    METRIC = "metric"
    IMAGE = "image"


class VisualizationType(str, Enum):
    """Visualization types."""
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    AREA_CHART = "area_chart"
    SCATTER_PLOT = "scatter_plot"
    HEATMAP = "heatmap"


class DataExportFormat(str, Enum):
    """Data export formats."""
    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"
    EXCEL = "excel"


class CompressionType(str, Enum):
    """Compression types."""
    NONE = "none"
    GZIP = "gzip"
    ZIP = "zip"


# ============================================================================
# Base Schemas
# ============================================================================

class DateRange(BaseModel):
    """Date range for reports."""
    start: datetime
    end: datetime


class ReportFilters(BaseModel):
    """Filters for report data."""
    agents: Optional[List[str]] = None
    users: Optional[List[str]] = None
    workspaces: Optional[List[str]] = None
    status: Optional[List[str]] = None


class DeliveryConfig(BaseModel):
    """Report delivery configuration."""
    method: DeliveryMethod
    recipients: List[str]
    webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None


# ============================================================================
# Report Generation Schemas
# ============================================================================

class ReportConfigRequest(BaseModel):
    """Report generation request configuration."""
    name: str = Field(..., min_length=1, max_length=255)
    template_id: Optional[str] = None
    format: ReportFormat
    sections: List[ReportSection]
    date_range: DateRange
    filters: Optional[ReportFilters] = Field(default_factory=ReportFilters)
    delivery: DeliveryConfig


class ReportJobResponse(BaseModel):
    """Report job creation response."""
    job_id: str
    status: ReportStatus
    estimated_completion: int  # seconds
    tracking_url: str


class ReportJobStatusResponse(BaseModel):
    """Report job status response."""
    job_id: str
    status: ReportStatus
    progress: int  # 0-100
    current_section: Optional[str] = None
    completed_at: Optional[datetime] = None
    download_url: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Template Schemas
# ============================================================================

class SectionDefinition(BaseModel):
    """Section definition for templates."""
    type: SectionType
    title: str
    metric: Optional[str] = None
    visualization: Optional[VisualizationType] = None
    data_source: Optional[str] = None
    columns: Optional[List[str]] = None
    template: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)


class LayoutConfig(BaseModel):
    """Layout configuration for templates."""
    orientation: str = "portrait"  # portrait or landscape
    margins: Dict[str, float] = Field(default_factory=lambda: {
        "top": 1,
        "bottom": 1,
        "left": 1,
        "right": 1
    })


class TemplateResponse(BaseModel):
    """Template response."""
    id: str
    name: str
    description: Optional[str] = None
    category: TemplateCategory
    sections: List[str]
    formats: List[ReportFormat]
    is_custom: bool
    preview_url: Optional[str] = None
    usage_count: Optional[int] = 0


class TemplatesListResponse(BaseModel):
    """Templates list response."""
    templates: List[TemplateResponse]


class CreateTemplateRequest(BaseModel):
    """Create template request."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: TemplateCategory = TemplateCategory.CUSTOM
    sections: List[SectionDefinition]
    layout: Optional[LayoutConfig] = Field(default_factory=LayoutConfig)


class CreateTemplateResponse(BaseModel):
    """Create template response."""
    template_id: str
    status: str


# ============================================================================
# Scheduled Reports Schemas
# ============================================================================

class ScheduleConfig(BaseModel):
    """Schedule configuration."""
    time: str  # HH:MM format
    timezone: str = "UTC"
    day_of_week: Optional[str] = None  # for weekly
    day_of_month: Optional[int] = Field(None, ge=1, le=31)  # for monthly

    @validator('time')
    def validate_time(cls, v):
        """Validate time format."""
        try:
            hours, minutes = v.split(':')
            if not (0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59):
                raise ValueError
        except:
            raise ValueError('time must be in HH:MM format')
        return v


class RecipientConfig(BaseModel):
    """Recipient configuration."""
    emails: List[str] = Field(default_factory=list)
    slack_channels: List[str] = Field(default_factory=list)
    webhooks: List[str] = Field(default_factory=list)


class CreateScheduleRequest(BaseModel):
    """Create schedule request."""
    name: str = Field(..., min_length=1, max_length=255)
    template_id: str
    frequency: ReportFrequency
    schedule: ScheduleConfig
    recipients: RecipientConfig
    filters: Optional[ReportFilters] = Field(default_factory=ReportFilters)


class CreateScheduleResponse(BaseModel):
    """Create schedule response."""
    schedule_id: str
    status: str
    next_run: datetime


class ScheduleResponse(BaseModel):
    """Schedule response."""
    id: str
    name: str
    template_id: str
    frequency: ReportFrequency
    schedule: Dict[str, Any]
    recipients: List[str]
    is_active: bool
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    successful_runs: int = 0
    failed_runs: int = 0


class SchedulesListResponse(BaseModel):
    """Schedules list response."""
    schedules: List[ScheduleResponse]


# ============================================================================
# Report History Schemas
# ============================================================================

class HistoricalReportResponse(BaseModel):
    """Historical report response."""
    id: str
    name: str
    type: str
    generated_at: datetime
    generated_by: str
    format: ReportFormat
    file_size: int
    page_count: Optional[int] = None
    download_url: str
    expires_at: Optional[datetime] = None
    download_count: int = 0


class ReportHistoryResponse(BaseModel):
    """Report history response."""
    reports: List[HistoricalReportResponse]
    total: int
    skip: int
    limit: int


# ============================================================================
# Export Schemas
# ============================================================================

class DataExportRequest(BaseModel):
    """Data export request."""
    data_sources: List[str]
    format: DataExportFormat
    date_range: DateRange
    compression: CompressionType = CompressionType.NONE
    include_metadata: bool = True


class DataExportResponse(BaseModel):
    """Data export response."""
    job_id: str
    estimated_size: Optional[int] = None
    estimated_time: Optional[int] = None  # seconds


# ============================================================================
# Sharing Schemas
# ============================================================================

class ShareReportRequest(BaseModel):
    """Share report request."""
    recipients: List[str]
    message: Optional[str] = None
    expiration_days: int = Field(7, ge=1, le=90)
    require_password: bool = False
    allow_download: bool = True


class ShareReportResponse(BaseModel):
    """Share report response."""
    share_url: str
    password: Optional[str] = None
    expires_at: datetime


# ============================================================================
# Analytics Schemas
# ============================================================================

class ReportUsageItem(BaseModel):
    """Report usage item."""
    template: Optional[str] = None
    user: Optional[str] = None
    count: int


class ReportFormatUsage(BaseModel):
    """Report format usage."""
    pdf: int = 0
    excel: int = 0
    csv: int = 0
    json: int = 0


class ReportAnalyticsResponse(BaseModel):
    """Report analytics response."""
    report_analytics: Dict[str, Any]


# ============================================================================
# Webhook Schemas
# ============================================================================

class WebhookRequest(BaseModel):
    """Webhook registration request."""
    url: str = Field(..., regex=r'^https?://')
    events: List[str]
    secret: Optional[str] = None
    is_active: bool = True


class WebhookResponse(BaseModel):
    """Webhook response."""
    webhook_id: str
    status: str


class WebhookListItem(BaseModel):
    """Webhook list item."""
    id: str
    url: str
    events: List[str]
    is_active: bool
    total_deliveries: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    last_delivery_at: Optional[datetime] = None
    created_at: datetime


# ============================================================================
# Common Response Schemas
# ============================================================================

class APIResponse(BaseModel):
    """Generic API response."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
