"""Analytics API schemas."""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List, Any
from datetime import datetime, date
from enum import Enum

__all__ = [
    # Enums
    "AggregationType",
    "Granularity",
    "Interpolation",
    "TrendMethod",
    "SeasonalityType",
    "ForecastModel",
    "AnomalyMethod",
    "Period",
    # Request models
    "DateRange",
    "MetricsAggregateRequest",
    "TimeseriesRequest",
    "TrendDetectionRequest",
    "SeasonalPatternsRequest",
    "ForecastConfig",
    "AnomalyConfig",
    "CohortConfig",
    "FunnelConfig",
    "ComparisonConfig",
    # Response models
    "AggregatedMetricsResponse",
    "TimeseriesResponse",
    "TrendAnalysis",
    "SeasonalityResponse",
    "ForecastCreationResponse",
    "ForecastResponse",
    "AnomalyDetectionResponse",
    "AnomalyRulesResponse",
    "CohortCreationResponse",
    "CohortRetentionResponse",
    "FunnelCreationResponse",
    "FunnelAnalysisResponse",
    "ComparisonResponse",
    "DistributionResponse",
    # Supporting models
    "AggregationGroup",
    "TimeseriesMetric",
    "TimeseriesDataPoint",
    "MetricStatistics",
    "ChangePoint",
    "TrendForecast",
    "SeasonalPattern",
    "ForecastPrediction",
    "ForecastResult",
    "ModelMetrics",
    "Anomaly",
    "AnomalyRule",
    "RetentionPeriod",
    "RetentionMetrics",
    "FunnelStep",
    "FunnelAnalysisResult",
    "MetricChange",
    "HistogramBin",
    "DistributionData",
    "DistributionStatistics",
    "Percentiles",
]


class AggregationType(str, Enum):
    """Aggregation types for metrics."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"


class Granularity(str, Enum):
    """Time series granularity."""
    MINUTELY = "minutely"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class Interpolation(str, Enum):
    """Interpolation methods for filling gaps."""
    LINEAR = "linear"
    PREVIOUS = "previous"
    ZERO = "zero"


class TrendMethod(str, Enum):
    """Trend detection methods."""
    LINEAR = "linear"
    POLYNOMIAL = "polynomial"
    SEASONAL = "seasonal"


class SeasonalityType(str, Enum):
    """Seasonality detection types."""
    AUTO = "auto"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ForecastModel(str, Enum):
    """Forecast model types."""
    PROPHET = "prophet"
    ARIMA = "arima"
    LSTM = "lstm"


class AnomalyMethod(str, Enum):
    """Anomaly detection methods."""
    ZSCORE = "zscore"
    ISOLATION_FOREST = "isolation_forest"
    LSTM = "lstm"
    THRESHOLD = "threshold"


class Period(str, Enum):
    """Period types for cohort analysis."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# Request models
class DateRange(BaseModel):
    """Date range for queries."""
    start: date
    end: date

    @validator('end')
    def validate_date_range(cls, v, values):
        """Validate end date is after start and range is not too large."""
        if 'start' in values:
            if v < values['start']:
                raise ValueError('end date must be after start date')
            days_diff = (v - values['start']).days
            if days_diff > 365:
                raise ValueError('date range cannot exceed 365 days')
        return v


class MetricsAggregateRequest(BaseModel):
    """Request for aggregated metrics."""
    workspace_id: str
    metrics: List[str] = Field(..., max_items=50, description="Metrics to aggregate")
    aggregation: AggregationType = AggregationType.SUM
    group_by: Optional[List[str]] = Field(None, max_items=10, description="Fields to group by")
    filters: Optional[Dict[str, Any]] = None
    date_range: DateRange


class TimeseriesRequest(BaseModel):
    """Request for time-series metrics."""
    workspace_id: str
    metrics: List[str] = Field(..., max_items=50, description="Metrics to retrieve")
    granularity: Granularity = Granularity.HOURLY
    fill_gaps: bool = True
    interpolation: Interpolation = Interpolation.LINEAR
    date_range: DateRange


class TrendDetectionRequest(BaseModel):
    """Request for trend detection."""
    workspace_id: str
    metric: str
    method: TrendMethod = TrendMethod.LINEAR
    confidence: float = Field(0.95, ge=0.0, le=1.0)
    date_range: DateRange


class SeasonalPatternsRequest(BaseModel):
    """Request for seasonal pattern analysis."""
    workspace_id: str
    metric: str
    seasonality: SeasonalityType = SeasonalityType.AUTO
    date_range: DateRange


class ForecastConfig(BaseModel):
    """Configuration for forecasting."""
    metric: str
    horizon_days: int = Field(30, ge=1, le=365)
    model: ForecastModel = ForecastModel.PROPHET
    confidence_level: float = Field(0.95, ge=0.0, le=1.0)
    include_seasonality: bool = True


class AnomalyConfig(BaseModel):
    """Configuration for anomaly detection."""
    metric: str
    method: AnomalyMethod = AnomalyMethod.ISOLATION_FOREST
    sensitivity: float = Field(2.5, ge=0.0, le=10.0)
    lookback_days: int = Field(30, ge=1, le=365)


class CohortConfig(BaseModel):
    """Configuration for cohort creation."""
    name: str
    filters: Dict[str, Any]
    description: Optional[str] = None


class FunnelConfig(BaseModel):
    """Configuration for funnel creation."""
    name: str
    steps: List[Dict[str, str]]
    description: Optional[str] = None

    @validator('steps')
    def validate_steps(cls, v):
        if len(v) < 2:
            raise ValueError('Funnel must have at least 2 steps')
        for step in v:
            if 'name' not in step or 'event' not in step:
                raise ValueError('Each step must have name and event')
        return v


class ComparisonConfig(BaseModel):
    """Configuration for period comparison."""
    metrics: List[str]
    period_1: DateRange
    period_2: DateRange


# Response models
class MetricStatistics(BaseModel):
    """Statistics for a metric."""
    min: float
    max: float
    avg: float
    std_dev: float


class AggregationGroup(BaseModel):
    """Aggregation group result."""
    group: Dict[str, Any]
    metrics: Dict[str, float]


class AggregatedMetricsResponse(BaseModel):
    """Response for aggregated metrics."""
    aggregations: List[AggregationGroup]
    totals: Dict[str, float]


class TimeseriesDataPoint(BaseModel):
    """Time series data point."""
    timestamp: datetime
    value: float


class TimeseriesMetric(BaseModel):
    """Time series metric with data."""
    metric: str
    data: List[TimeseriesDataPoint]
    statistics: MetricStatistics


class TimeseriesResponse(BaseModel):
    """Response for time-series data."""
    series: List[TimeseriesMetric]


class ChangePoint(BaseModel):
    """Detected change point in trend."""
    date: date
    type: str
    confidence: float


class TrendForecast(BaseModel):
    """Trend forecast values."""
    next_7_days: float
    next_30_days: float


class TrendAnalysis(BaseModel):
    """Trend analysis result."""
    direction: str
    slope: float
    r_squared: float
    confidence_interval: List[float]
    change_points: List[ChangePoint]
    forecast: TrendForecast


class SeasonalPattern(BaseModel):
    """Seasonal pattern data."""
    period: str
    index: float


class SeasonalityResponse(BaseModel):
    """Response for seasonality analysis."""
    period: str
    strength: float
    peak_days: List[str]
    peak_hours: List[int]
    low_periods: List[str]
    pattern: List[SeasonalPattern]


class ForecastCreationResponse(BaseModel):
    """Response for forecast creation."""
    forecast_id: str
    status: str
    estimated_completion: int  # seconds


class ForecastPrediction(BaseModel):
    """Individual forecast prediction."""
    date: date
    value: float
    lower_bound: float
    upper_bound: float


class ModelMetrics(BaseModel):
    """Model performance metrics."""
    mape: float
    rmse: float
    confidence: float


class ForecastResult(BaseModel):
    """Forecast result."""
    predictions: List[ForecastPrediction]
    model_metrics: ModelMetrics


class ForecastResponse(BaseModel):
    """Response for forecast retrieval."""
    forecast: ForecastResult


class Anomaly(BaseModel):
    """Detected anomaly."""
    timestamp: datetime
    metric_value: float
    expected_range: List[float]
    anomaly_score: float
    severity: str


class AnomalyDetectionResponse(BaseModel):
    """Response for anomaly detection."""
    anomalies: List[Anomaly]


class AnomalyRule(BaseModel):
    """Anomaly detection rule."""
    id: str
    name: str
    metric: str
    threshold: float
    method: str
    is_active: bool
    auto_alert: bool


class AnomalyRulesResponse(BaseModel):
    """Response for anomaly rules."""
    rules: List[AnomalyRule]


class CohortCreationResponse(BaseModel):
    """Response for cohort creation."""
    cohort_id: str
    user_count: int


class RetentionPeriod(BaseModel):
    """Retention data for a period."""
    period: int
    retained: int
    percentage: float


class RetentionMetrics(BaseModel):
    """Retention metrics."""
    day_1_retention: float
    day_7_retention: float
    day_30_retention: float


class CohortRetentionResponse(BaseModel):
    """Response for cohort retention."""
    cohort_size: int
    retention_curve: List[RetentionPeriod]
    metrics: RetentionMetrics


class FunnelCreationResponse(BaseModel):
    """Response for funnel creation."""
    funnel_id: str
    status: str


class FunnelStep(BaseModel):
    """Funnel step analysis."""
    name: str
    users: int
    conversion: float
    drop_off: float
    avg_time_to_convert: Optional[int] = None  # seconds


class FunnelAnalysisResult(BaseModel):
    """Funnel analysis result."""
    total_entered: int
    total_converted: int
    overall_conversion: float
    steps: List[FunnelStep]


class FunnelAnalysisResponse(BaseModel):
    """Response for funnel analysis."""
    funnel: FunnelAnalysisResult


# Note: PeriodMetrics removed - use Dict[str, float] directly in responses


class MetricChange(BaseModel):
    """Change in metric between periods."""
    absolute: float
    percentage: float


class ComparisonResponse(BaseModel):
    """Response for period comparison."""
    period_1: Dict[str, float]
    period_2: Dict[str, float]
    changes: Dict[str, MetricChange]


class HistogramBin(BaseModel):
    """Histogram bin."""
    bin: str
    count: int


class Percentiles(BaseModel):
    """Percentile values."""
    p25: float
    p50: float
    p75: float
    p95: float
    p99: float


class DistributionStatistics(BaseModel):
    """Distribution statistics."""
    mean: float
    median: float
    mode: float
    std_dev: float
    variance: float
    skewness: float
    kurtosis: float
    percentiles: Percentiles


class DistributionData(BaseModel):
    """Distribution data."""
    histogram: List[HistogramBin]
    statistics: DistributionStatistics


class DistributionResponse(BaseModel):
    """Response for distribution analysis."""
    distribution: DistributionData
