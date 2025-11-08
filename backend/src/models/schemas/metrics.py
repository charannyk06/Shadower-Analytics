"""Metric schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


class TimeRange(BaseModel):
    """Time range for queries."""

    start_date: date
    end_date: date


class MetricValue(BaseModel):
    """Single metric value with timestamp."""

    timestamp: datetime
    value: float
    metric_name: str


class ExecutiveMetrics(BaseModel):
    """Executive dashboard metrics."""

    mrr: float = Field(..., description="Monthly Recurring Revenue")
    churn_rate: float = Field(..., description="Customer churn rate")
    ltv: float = Field(..., description="Customer Lifetime Value")
    dau: int = Field(..., description="Daily Active Users")
    wau: int = Field(..., description="Weekly Active Users")
    mau: int = Field(..., description="Monthly Active Users")
    total_executions: int = Field(default=0)
    success_rate: float = Field(default=0.0)


class MetricTrend(BaseModel):
    """Metric trend data."""

    metric_name: str
    values: List[MetricValue]
    trend_direction: str  # 'up', 'down', 'stable'
    change_percentage: float
