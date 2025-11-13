"""Standardized API request and response models.

Provides consistent data structures for API communication.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Generic, TypeVar
from datetime import datetime
from enum import Enum


# Generic type for data in responses
T = TypeVar('T')


class APIResponse(BaseModel):
    """Standard API response wrapper.

    Provides consistent response format across all endpoints.
    """
    success: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @classmethod
    def success_response(cls, data: Any, metadata: Optional[Dict[str, Any]] = None):
        """Create a successful response."""
        return cls(
            success=True,
            data=data,
            metadata=metadata or {}
        )

    @classmethod
    def error_response(cls, error: str, metadata: Optional[Dict[str, Any]] = None):
        """Create an error response."""
        return cls(
            success=False,
            error=error,
            metadata=metadata or {}
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper.

    Used for endpoints that return lists of items.
    """
    success: bool = True
    data: List[T]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @classmethod
    def create(
        cls,
        data: List[T],
        total: int,
        page: int,
        per_page: int,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Create a paginated response."""
        pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        return cls(
            success=True,
            data=data,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
            metadata=metadata or {}
        )


class ErrorCode(str, Enum):
    """Standard error codes."""
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    BAD_REQUEST = "BAD_REQUEST"
    CONFLICT = "CONFLICT"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class ErrorResponse(BaseModel):
    """Error response format.

    Provides detailed error information for debugging.
    """
    error: str
    code: ErrorCode
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    path: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PaginationParams(BaseModel):
    """Pagination parameters for list requests."""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(default=50, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: Optional[str] = Field(default="desc", description="Sort order (asc/desc)")

    @field_validator('sort_order')
    @classmethod
    def validate_sort_order(cls, v):
        """Validate sort order."""
        if v and v.lower() not in ['asc', 'desc']:
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return v.lower() if v else 'desc'


class DateRangeParams(BaseModel):
    """Date range parameters for time-based queries."""
    start_date: datetime
    end_date: datetime
    timezone: str = Field(default="UTC", description="Timezone for date interpretation")

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v, info):
        """Validate end_date is after start_date."""
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError("end_date must be after start_date")
        return v

    def validate_max_range(self, max_days: int = 365):
        """Validate date range doesn't exceed maximum."""
        days = (self.end_date - self.start_date).days
        if days > max_days:
            raise ValueError(f"Date range exceeds maximum of {max_days} days")


class MetricValue(BaseModel):
    """Single metric value with metadata."""
    name: str
    value: float
    unit: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TimeSeriesDataPoint(BaseModel):
    """Single data point in a time series."""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TimeSeries(BaseModel):
    """Time series data."""
    name: str
    data: List[TimeSeriesDataPoint]
    unit: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HealthStatus(str, Enum):
    """Health status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceHealth(BaseModel):
    """Health check for a single service."""
    name: str
    status: HealthStatus
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HealthCheckResponse(BaseModel):
    """Comprehensive health check response."""
    status: HealthStatus
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: List[ServiceHealth] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RateLimitInfo(BaseModel):
    """Rate limit information."""
    limit: int
    remaining: int
    reset: int  # Unix timestamp
    window_seconds: int


class CacheInfo(BaseModel):
    """Cache metadata."""
    hit: bool
    key: Optional[str] = None
    ttl: Optional[int] = None
    age: Optional[int] = None


class RequestMetadata(BaseModel):
    """Request metadata for responses."""
    request_id: Optional[str] = None
    rate_limit: Optional[RateLimitInfo] = None
    cache: Optional[CacheInfo] = None
    processing_time_ms: Optional[float] = None


# Export endpoint models
class ExportFormat(str, Enum):
    """Supported export formats."""
    CSV = "csv"
    JSON = "json"
    PDF = "pdf"
    EXCEL = "excel"


class ExportRequest(BaseModel):
    """Request to export data."""
    format: ExportFormat
    date_range: Optional[DateRangeParams] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    include_metadata: bool = Field(default=True)


class ExportResponse(BaseModel):
    """Response for export requests."""
    export_id: str
    status: str
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Report models
class ReportStatus(str, Enum):
    """Report generation status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportRequest(BaseModel):
    """Request to generate a report."""
    report_type: str
    date_range: DateRangeParams
    workspace_id: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    format: ExportFormat = ExportFormat.PDF


class ReportResponse(BaseModel):
    """Report generation response."""
    report_id: str
    status: ReportStatus
    download_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Analytics models
class AnalyticsQuery(BaseModel):
    """Analytics query parameters."""
    workspace_id: str
    date_range: DateRangeParams
    metrics: List[str]
    dimensions: Optional[List[str]] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    aggregation: Optional[str] = Field(default="sum", description="Aggregation method")


class MetricAggregation(str, Enum):
    """Metric aggregation methods."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    P50 = "p50"
    P95 = "p95"
    P99 = "p99"


# WebSocket models
class WebSocketMessage(BaseModel):
    """WebSocket message format."""
    type: str
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WebSocketSubscription(BaseModel):
    """WebSocket subscription request."""
    channel: str
    workspace_id: str
    filters: Dict[str, Any] = Field(default_factory=dict)
