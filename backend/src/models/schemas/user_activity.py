"""User activity tracking schemas."""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime


class ActivityByDate(BaseModel):
    """Activity metrics for a specific date."""

    date: str
    active_users: int
    sessions: int
    events: int


class ActivityMetrics(BaseModel):
    """User activity metrics."""

    dau: int = Field(..., description="Daily Active Users")
    wau: int = Field(..., description="Weekly Active Users")
    mau: int = Field(..., description="Monthly Active Users")

    new_users: int
    returning_users: int
    reactivated_users: int
    churned_users: int

    avg_sessions_per_user: float
    avg_session_duration: float
    bounce_rate: float
    engagement_score: float

    activity_by_hour: List[int]
    activity_by_day_of_week: List[int]
    activity_by_date: List[ActivityByDate]


class SessionLengthDistribution(BaseModel):
    """Session length distribution."""

    zero_to_30s: int = Field(..., alias="0-30s")
    thirty_s_to_2m: int = Field(..., alias="30s-2m")
    two_m_to_5m: int = Field(..., alias="2m-5m")
    five_m_to_15m: int = Field(..., alias="5m-15m")
    fifteen_m_to_30m: int = Field(..., alias="15m-30m")
    thirty_m_plus: int = Field(..., alias="30m+")

    class Config:
        populate_by_name = True


class DeviceBreakdown(BaseModel):
    """Device type breakdown."""

    desktop: int
    mobile: int
    tablet: int


class LocationData(BaseModel):
    """Location metrics."""

    users: int
    sessions: int


class SessionAnalytics(BaseModel):
    """Session analytics data."""

    total_sessions: int
    avg_session_length: float
    median_session_length: float

    session_length_distribution: SessionLengthDistribution
    device_breakdown: DeviceBreakdown
    browser_breakdown: Dict[str, int]
    location_breakdown: Dict[str, LocationData]


class FeatureData(BaseModel):
    """Individual feature usage data."""

    feature_name: str
    category: str
    usage_count: int
    unique_users: int
    avg_time_spent: float
    adoption_rate: float
    retention_rate: float


class AdoptionFunnelStage(BaseModel):
    """Feature adoption funnel stage."""

    stage: str
    users: int
    dropoff_rate: float


class TopFeature(BaseModel):
    """Top used feature."""

    feature: str
    usage: int
    trend: Literal["increasing", "stable", "decreasing"]


class UnusedFeature(BaseModel):
    """Unused feature data."""

    feature: str
    last_used: Optional[str] = None


class FeatureUsage(BaseModel):
    """Feature usage analytics."""

    features: List[FeatureData]
    adoption_funnel: List[AdoptionFunnelStage]
    top_features: List[TopFeature]
    unused_features: List[UnusedFeature]


class DropoffPoint(BaseModel):
    """Journey dropoff point."""

    step: str
    dropoff_rate: float


class CommonPath(BaseModel):
    """Common user journey path."""

    path: List[str]
    frequency: int
    avg_completion: float
    dropoff_points: List[DropoffPoint]


class EntryPoint(BaseModel):
    """User entry point."""

    page: str
    count: int
    bounce_rate: float


class ExitPoint(BaseModel):
    """User exit point."""

    page: str
    count: int
    avg_time_before_exit: float


class ConversionPathData(BaseModel):
    """Conversion path data."""

    steps: List[str]
    conversions: int
    conversion_rate: float


class ConversionPath(BaseModel):
    """Goal conversion paths."""

    goal: str
    paths: List[ConversionPathData]


class UserJourney(BaseModel):
    """User journey analytics."""

    common_paths: List[CommonPath]
    entry_points: List[EntryPoint]
    exit_points: List[ExitPoint]
    conversion_paths: List[ConversionPath]


class RetentionCurvePoint(BaseModel):
    """Retention curve data point."""

    day: int
    retention_rate: float
    active_users: int


class CohortRetention(BaseModel):
    """Cohort retention data."""

    day1: float
    day7: float
    day14: float
    day30: float
    day60: float
    day90: float


class Cohort(BaseModel):
    """User cohort data."""

    cohort_date: str
    cohort_size: int
    retention: CohortRetention


class RiskSegment(BaseModel):
    """At-risk user segment."""

    segment: str
    users: int
    churn_probability: float
    characteristics: List[str]


class ChurnAnalysis(BaseModel):
    """Churn analysis data."""

    churn_rate: float
    avg_lifetime: float
    risk_segments: List[RiskSegment]


class Retention(BaseModel):
    """Retention analytics."""

    retention_curve: List[RetentionCurvePoint]
    cohorts: List[Cohort]
    churn_analysis: ChurnAnalysis


class UserSegmentData(BaseModel):
    """User segment information."""

    segment_name: str
    segment_type: Literal["behavioral", "demographic", "technographic"]
    user_count: int
    characteristics: List[str]
    avg_engagement: float
    avg_revenue: float


class UserActivityData(BaseModel):
    """Complete user activity analytics response."""

    user_id: Optional[str] = None
    workspace_id: str
    timeframe: str

    activity_metrics: ActivityMetrics
    session_analytics: SessionAnalytics
    feature_usage: FeatureUsage
    user_journey: UserJourney
    retention: Retention
    segments: List[UserSegmentData]


class TrackActivityRequest(BaseModel):
    """Request schema for tracking user activity events."""

    user_id: str = Field(..., min_length=1, max_length=255, description="User ID")
    session_id: Optional[str] = Field(None, max_length=255, description="Session ID")
    event_type: str = Field(..., min_length=1, max_length=50, description="Event type (e.g., page_view, feature_use, custom)")
    event_name: Optional[str] = Field(None, max_length=100, description="Event name")
    page_path: Optional[str] = Field(None, max_length=255, description="Page path")

    # Context fields
    ip_address: Optional[str] = Field(None, description="IP address (will be anonymized)")
    user_agent: Optional[str] = Field(None, max_length=500, description="User agent string")
    referrer: Optional[str] = Field(None, max_length=500, description="Referrer URL")
    device_type: Optional[str] = Field(None, max_length=20, description="Device type (desktop, mobile, tablet)")
    browser: Optional[str] = Field(None, max_length=50, description="Browser name")
    os: Optional[str] = Field(None, max_length=50, description="Operating system")
    country_code: Optional[str] = Field(None, max_length=2, description="ISO country code")

    # Additional event data
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional event metadata")

    @validator('event_type')
    def validate_event_type(cls, v):
        """Validate event type."""
        allowed_types = ['page_view', 'feature_use', 'custom', 'click', 'form_submit', 'error', 'session_start', 'session_end']
        if v not in allowed_types:
            raise ValueError(f"event_type must be one of: {', '.join(allowed_types)}")
        return v

    @validator('country_code')
    def validate_country_code(cls, v):
        """Validate country code format."""
        if v is not None and len(v) != 2:
            raise ValueError("country_code must be a 2-letter ISO code")
        return v.upper() if v else None

    @validator('metadata')
    def validate_metadata(cls, v):
        """Validate metadata size to prevent abuse."""
        if v is not None:
            import json
            # Limit metadata to 10KB
            if len(json.dumps(v)) > 10240:
                raise ValueError("metadata too large (max 10KB)")
        return v


class TrackActivityResponse(BaseModel):
    """Response schema for track activity endpoint."""

    success: bool
    activity_id: str
