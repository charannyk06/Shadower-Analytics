"""Common shared schemas."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, date
from enum import Enum


class StatusEnum(str, Enum):
    """Status enumeration."""

    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    RUNNING = "running"


class TimeframeEnum(str, Enum):
    """Timeframe enumeration."""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class Report(BaseModel):
    """Report definition."""

    report_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    config: Optional[Dict] = None


class ReportConfig(BaseModel):
    """Report configuration."""

    name: str
    description: Optional[str] = None
    metric_types: List[str]
    filters: Optional[Dict] = None
    time_range: Optional[Dict] = None
    format: str = "json"  # 'json', 'csv', 'pdf'


class PaginationParams(BaseModel):
    """Pagination parameters."""

    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""

    total: int
    skip: int
    limit: int
    data: List[Any]


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
