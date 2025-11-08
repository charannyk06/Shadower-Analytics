"""User schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, date


class UserMetrics(BaseModel):
    """User engagement metrics."""

    dau: int = Field(..., description="Daily Active Users")
    wau: int = Field(..., description="Weekly Active Users")
    mau: int = Field(..., description="Monthly Active Users")
    retention_rate: float = Field(..., description="User retention rate")
    avg_session_duration: Optional[float] = None
    total_sessions: Optional[int] = None


class UserActivity(BaseModel):
    """User activity data."""

    user_id: str
    timestamp: datetime
    activity_type: str
    metadata: Optional[Dict] = None


class CohortAnalysis(BaseModel):
    """Cohort analysis data."""

    cohort_date: date
    cohort_size: int
    retention_rates: Dict[int, float]  # period -> retention rate
    cohort_type: str  # 'daily', 'weekly', 'monthly'
