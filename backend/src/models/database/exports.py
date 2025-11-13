"""Database models for export functionality."""

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Boolean,
    JSON,
    Text,
    Enum as SQLEnum,
    ForeignKey,
    Float,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

from .tables import Base


class ExportStatus(str, enum.Enum):
    """Export job status."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExportFormat(str, enum.Enum):
    """Export format types."""

    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"
    PARQUET = "parquet"


class CompressionType(str, enum.Enum):
    """Compression types."""

    NONE = "none"
    GZIP = "gzip"
    ZIP = "zip"
    BZ2 = "bz2"


class DeliveryMethod(str, enum.Enum):
    """Delivery method types."""

    DOWNLOAD = "download"
    EMAIL = "email"
    S3 = "s3"
    FTP = "ftp"


class ExportJob(Base):
    """Export job model."""

    __tablename__ = "export_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Configuration
    config = Column(JSON, nullable=False)
    data_sources = Column(JSON, nullable=False)
    format = Column(SQLEnum(ExportFormat), nullable=False)
    compression = Column(SQLEnum(CompressionType), default=CompressionType.NONE)

    # Delivery configuration
    delivery_method = Column(SQLEnum(DeliveryMethod), default=DeliveryMethod.DOWNLOAD)
    delivery_config = Column(JSON)

    # Encryption configuration
    encryption_enabled = Column(Boolean, default=False)
    encryption_config = Column(JSON)

    # Status and progress
    status = Column(SQLEnum(ExportStatus), default=ExportStatus.QUEUED, index=True)
    progress_percent = Column(Float, default=0.0)
    rows_processed = Column(BigInteger, default=0)
    total_rows = Column(BigInteger, default=0)
    current_table = Column(String(255))
    files_created = Column(Integer, default=0)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Estimates
    estimated_size_mb = Column(Float)
    estimated_time_seconds = Column(Integer)
    estimated_rows = Column(BigInteger)

    # Results
    files = Column(JSON)  # List of generated files with metadata
    total_size_mb = Column(Float)
    error_message = Column(Text)

    # Celery task info
    celery_task_id = Column(String(255), index=True)

    # Relationships
    template_id = Column(UUID(as_uuid=True), ForeignKey("export_templates.id"), nullable=True)
    template = relationship("ExportTemplate", back_populates="jobs")


class ExportTemplate(Base):
    """Export template model."""

    __tablename__ = "export_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)

    # Template details
    name = Column(String(255), nullable=False)
    description = Column(Text)
    configuration = Column(JSON, nullable=False)

    # Metadata
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used_at = Column(DateTime)
    use_count = Column(Integer, default=0)

    # Relationships
    jobs = relationship("ExportJob", back_populates="template")
    schedules = relationship("ExportSchedule", back_populates="template")


class ExportSchedule(Base):
    """Scheduled export model."""

    __tablename__ = "export_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)

    # Schedule details
    name = Column(String(255), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("export_templates.id"), nullable=False)

    # Schedule configuration
    frequency = Column(String(50), nullable=False)  # daily, weekly, monthly
    schedule_config = Column(JSON, nullable=False)  # cron expression, timezone, etc.

    # Retention
    retention_config = Column(JSON)  # keep_exports_days, auto_cleanup

    # Status
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Execution tracking
    last_run_at = Column(DateTime)
    last_job_id = Column(UUID(as_uuid=True))
    next_run_at = Column(DateTime, index=True)
    run_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)

    # Relationships
    template = relationship("ExportTemplate", back_populates="schedules")


class ExportFile(Base):
    """Export file metadata model."""

    __tablename__ = "export_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("export_jobs.id"), nullable=False, index=True)

    # File details
    filename = Column(String(512), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_index = Column(Integer, nullable=False)
    size_mb = Column(Float, nullable=False)
    row_count = Column(BigInteger)
    checksum = Column(String(255))

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    downloaded_count = Column(Integer, default=0)
    last_downloaded_at = Column(DateTime)

    # Storage info
    storage_type = Column(String(50), default="local")  # local, s3, etc.
    storage_metadata = Column(JSON)


class ExportMetadata(Base):
    """Export metadata and lineage model."""

    __tablename__ = "export_metadata"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("export_jobs.id"), nullable=False, index=True)

    # Schema information
    schema_info = Column(JSON, nullable=False)  # tables, columns, types

    # Statistics
    statistics = Column(JSON)  # row counts, date ranges, etc.

    # Lineage
    source_database = Column(String(255))
    export_timestamp = Column(DateTime, nullable=False)
    filters_applied = Column(JSON)
    transformations_applied = Column(JSON)

    # Validation
    validation_status = Column(String(50))
    validation_results = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
