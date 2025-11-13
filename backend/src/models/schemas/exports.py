"""Pydantic schemas for export functionality."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ExportStatusEnum(str, Enum):
    """Export job status."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExportFormatEnum(str, Enum):
    """Export format types."""

    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"
    PARQUET = "parquet"


class CompressionTypeEnum(str, Enum):
    """Compression types."""

    NONE = "none"
    GZIP = "gzip"
    ZIP = "zip"
    BZ2 = "bz2"


class DeliveryMethodEnum(str, Enum):
    """Delivery method types."""

    DOWNLOAD = "download"
    EMAIL = "email"
    S3 = "s3"
    FTP = "ftp"


class SplitByEnum(str, Enum):
    """Split by types."""

    MONTH = "month"
    WEEK = "week"
    SIZE = "size"


class DataSourceType(str, Enum):
    """Data source types."""

    USER_ACTIVITY = "user_activity"
    AGENT_PERFORMANCE = "agent_performance"
    CREDIT_CONSUMPTION = "credit_consumption"
    ERROR_LOGS = "error_logs"
    EXECUTION_LOGS = "execution_logs"


# Data Source Configuration


class DateRangeFilter(BaseModel):
    """Date range filter."""

    start: str = Field(..., description="Start date in ISO format")
    end: str = Field(..., description="End date in ISO format")


class DataSourceFilters(BaseModel):
    """Filters for data source."""

    date_range: Optional[DateRangeFilter] = None
    workspace_id: Optional[str] = None
    agent_ids: Optional[List[str]] = None
    user_ids: Optional[List[str]] = None
    custom_filters: Optional[Dict[str, Any]] = None


class DataSourceConfig(BaseModel):
    """Data source configuration."""

    type: DataSourceType
    filters: Optional[DataSourceFilters] = None
    fields: Optional[List[str]] = None
    aggregation: Optional[str] = None  # daily, weekly, monthly


# Split and Delivery Configuration


class SplitFilesConfig(BaseModel):
    """Split files configuration."""

    enabled: bool = False
    max_size_mb: int = Field(100, ge=1, le=10000)
    split_by: SplitByEnum = SplitByEnum.SIZE


class S3Config(BaseModel):
    """S3 delivery configuration."""

    bucket: str
    prefix: Optional[str] = None
    region: Optional[str] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None


class FTPConfig(BaseModel):
    """FTP delivery configuration."""

    host: str
    port: int = 21
    username: str
    password: str
    path: Optional[str] = None


class DeliveryConfig(BaseModel):
    """Delivery configuration."""

    method: DeliveryMethodEnum = DeliveryMethodEnum.DOWNLOAD
    email_recipients: Optional[List[str]] = None
    s3_config: Optional[S3Config] = None
    ftp_config: Optional[FTPConfig] = None


# Encryption Configuration


class EncryptionConfig(BaseModel):
    """Encryption configuration."""

    enabled: bool = False
    method: str = "AES256"
    password_protected: bool = False
    password: Optional[str] = None


# Export Configuration


class ExportConfig(BaseModel):
    """Complete export configuration."""

    name: str = Field(..., min_length=1, max_length=255)
    data_sources: List[DataSourceConfig] = Field(..., min_items=1)
    format: ExportFormatEnum = ExportFormatEnum.CSV
    compression: CompressionTypeEnum = CompressionTypeEnum.NONE
    split_files: Optional[SplitFilesConfig] = None
    delivery: Optional[DeliveryConfig] = None
    encryption: Optional[EncryptionConfig] = None


# Export Response Models


class ExportEstimate(BaseModel):
    """Export size and time estimate."""

    size_mb: float
    time_seconds: int
    row_count: int


class ExportFileInfo(BaseModel):
    """Information about an exported file."""

    filename: str
    size_mb: float
    rows: int
    download_url: str
    checksum: str


class ExportProgress(BaseModel):
    """Export job progress."""

    percentage: float = Field(..., ge=0, le=100)
    rows_processed: int
    total_rows: int
    current_table: Optional[str] = None
    files_created: int


class CreateExportResponse(BaseModel):
    """Response for create export job."""

    job_id: str
    status: ExportStatusEnum
    estimated_size_mb: float
    estimated_time_seconds: int
    estimated_rows: int
    tracking_url: str


class ExportStatusResponse(BaseModel):
    """Response for export status query."""

    job_id: str
    status: ExportStatusEnum
    progress: ExportProgress
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    files: Optional[List[ExportFileInfo]] = None
    error: Optional[str] = None


# Template Models


class ExportTemplateConfig(BaseModel):
    """Export template configuration."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    configuration: ExportConfig
    is_public: bool = False
    schedule: Optional["ScheduleConfig"] = None


class ScheduleConfig(BaseModel):
    """Schedule configuration."""

    enabled: bool = False
    frequency: str = Field(..., pattern="^(daily|weekly|monthly)$")
    day_of_week: Optional[str] = None
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    time: str = Field(..., pattern="^([0-1][0-9]|2[0-3]):[0-5][0-9]$")
    timezone: str = "UTC"


class ExportTemplate(BaseModel):
    """Export template."""

    id: str
    name: str
    description: Optional[str] = None
    data_sources: List[str]
    format: ExportFormatEnum
    estimated_size_mb: float
    last_used: Optional[datetime] = None
    created_by: str


class CreateTemplateResponse(BaseModel):
    """Response for create template."""

    template_id: str
    created: bool


class ExportTemplatesResponse(BaseModel):
    """Response for list templates."""

    templates: List[ExportTemplate]


# Scheduled Export Models


class RetentionConfig(BaseModel):
    """Retention configuration."""

    keep_exports_days: int = Field(90, ge=1, le=3650)
    auto_cleanup: bool = True


class ExportScheduleConfig(BaseModel):
    """Export schedule configuration."""

    name: str = Field(..., min_length=1, max_length=255)
    template_id: str
    frequency: str = Field(..., pattern="^(daily|weekly|monthly)$")
    schedule: ScheduleConfig
    retention: Optional[RetentionConfig] = None


class ExportScheduleInfo(BaseModel):
    """Scheduled export information."""

    id: str
    name: str
    template_id: str
    frequency: str
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    is_active: bool
    delivery: DeliveryConfig


class CreateScheduleResponse(BaseModel):
    """Response for create schedule."""

    schedule_id: str
    next_run: datetime


class ExportSchedulesResponse(BaseModel):
    """Response for list schedules."""

    schedules: List[ExportScheduleInfo]


# Bulk Export Models


class BulkExportType(str, Enum):
    """Bulk export type."""

    FULL_BACKUP = "full_backup"
    MIGRATION = "migration"
    AUDIT = "audit"


class PartitioningConfig(BaseModel):
    """Partitioning configuration."""

    by: str = Field(..., pattern="^(month|week|day)$")
    parallel_jobs: int = Field(4, ge=1, le=16)


class BulkExportConfig(BaseModel):
    """Bulk export configuration."""

    export_type: BulkExportType
    include_deleted: bool = False
    point_in_time: Optional[datetime] = None
    tables: List[str] = Field(..., min_items=1)
    format: ExportFormatEnum = ExportFormatEnum.PARQUET
    partitioning: Optional[PartitioningConfig] = None


class CreateBulkExportResponse(BaseModel):
    """Response for create bulk export."""

    batch_id: str
    job_ids: List[str]
    total_tables: int
    estimated_total_size_gb: float


# Format Conversion Models


class ConversionOptions(BaseModel):
    """Format conversion options."""

    excel_sheets: Optional[bool] = None
    json_pretty: Optional[bool] = None
    parquet_compression: Optional[str] = None


class ConversionConfig(BaseModel):
    """Format conversion configuration."""

    source_job_id: str
    target_format: ExportFormatEnum
    options: Optional[ConversionOptions] = None


class ConvertFormatResponse(BaseModel):
    """Response for format conversion."""

    conversion_job_id: str
    status: ExportStatusEnum


# Metadata Models


class ColumnSchema(BaseModel):
    """Column schema."""

    name: str
    type: str


class TableSchema(BaseModel):
    """Table schema."""

    name: str
    columns: List[ColumnSchema]
    row_count: int


class SchemaInfo(BaseModel):
    """Schema information."""

    tables: List[TableSchema]


class ExportStatistics(BaseModel):
    """Export statistics."""

    total_rows: int
    total_columns: int
    date_range: Optional[DateRangeFilter] = None


class ExportLineage(BaseModel):
    """Export lineage."""

    source_database: str
    export_timestamp: datetime
    filters_applied: List[str]


class ExportMetadataInfo(BaseModel):
    """Export metadata information."""

    schema: SchemaInfo
    statistics: ExportStatistics
    lineage: ExportLineage


class ExportMetadataResponse(BaseModel):
    """Response for export metadata."""

    job_id: str
    metadata: ExportMetadataInfo


# Validation Models


class ValidationTypeEnum(str, Enum):
    """Validation type."""

    CHECKSUM = "checksum"
    SCHEMA = "schema"
    FULL = "full"


class ValidationConfig(BaseModel):
    """Validation configuration."""

    job_id: str
    validation_type: ValidationTypeEnum = ValidationTypeEnum.FULL
    sample_rows: Optional[int] = Field(None, ge=1, le=10000)


class ValidationChecks(BaseModel):
    """Validation checks results."""

    checksum_valid: bool
    schema_valid: bool
    row_count_match: bool
    no_corruption: bool


class ValidationResponse(BaseModel):
    """Response for export validation."""

    valid: bool
    checks: ValidationChecks
    sample_data: Optional[List[Dict[str, Any]]] = None


# Cleanup Models


class CleanupConfig(BaseModel):
    """Cleanup configuration."""

    older_than_days: int = Field(90, ge=1, le=3650)
    keep_scheduled: bool = True
    dry_run: bool = False


class CleanupResponse(BaseModel):
    """Response for cleanup operation."""

    exports_deleted: int
    space_freed_gb: float
    dry_run: bool


class DeleteExportResponse(BaseModel):
    """Response for delete export."""

    job_id: str
    deleted: bool
    files_removed: int
    space_freed_mb: float


# General Response Model


class APIResponse(BaseModel):
    """Generic API response."""

    success: bool = True
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
