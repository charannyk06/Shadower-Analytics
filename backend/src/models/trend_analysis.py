"""
Pydantic models for Trend Analysis

Type-safe data models for trend analysis responses and configurations
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime


# Type aliases
TrendDirection = Literal['increasing', 'decreasing', 'stable', 'volatile']
SeasonalityType = Literal['daily', 'weekly', 'monthly', 'quarterly', 'yearly']
GrowthType = Literal['linear', 'exponential', 'logarithmic', 'polynomial']
InsightType = Literal['trend', 'anomaly', 'pattern', 'correlation', 'forecast']
ImpactLevel = Literal['high', 'medium', 'low']


class TrendOverview(BaseModel):
    """High-level trend overview metrics"""
    current_value: float = Field(..., description="Most recent value")
    previous_value: float = Field(..., description="Initial value in timeframe")
    change: float = Field(..., description="Absolute change")
    change_percentage: float = Field(..., description="Percentage change")
    trend: TrendDirection = Field(..., description="Trend direction")
    trend_strength: float = Field(..., ge=0, le=100, description="Trend strength 0-100")
    confidence: float = Field(..., ge=0, le=1, description="Statistical confidence 0-1")


class TimeSeriesDataPoint(BaseModel):
    """Individual time series data point"""
    timestamp: str
    value: float
    moving_average: float
    upper_bound: float
    lower_bound: float
    is_anomaly: bool


class TimeSeriesStatistics(BaseModel):
    """Statistical measures for time series"""
    mean: float
    median: float
    std_dev: float = Field(..., alias="stdDev")
    variance: float
    skewness: float
    kurtosis: float
    autocorrelation: float


class TimeSeries(BaseModel):
    """Complete time series with statistics"""
    data: List[TimeSeriesDataPoint]
    statistics: TimeSeriesStatistics


class DecompositionComponent(BaseModel):
    """Component of time series decomposition"""
    timestamp: str
    value: Optional[float]


class SeasonalComponent(DecompositionComponent):
    """Seasonal component with period info"""
    period: str


class Decomposition(BaseModel):
    """Time series decomposition results"""
    trend: List[DecompositionComponent]
    seasonal: List[SeasonalComponent]
    residual: List[DecompositionComponent]
    noise: float = Field(..., ge=0, description="Noise level percentage")


class SeasonalityPattern(BaseModel):
    """Detected seasonality pattern"""
    detected: bool
    type: Optional[SeasonalityType] = None
    strength: float = Field(..., ge=0, le=100)
    peak_periods: List[str] = Field(default_factory=list)
    low_periods: List[str] = Field(default_factory=list)


class CyclicalPattern(BaseModel):
    """Detected cyclical pattern"""
    period: float = Field(..., gt=0, description="Period in days")
    amplitude: float
    phase: float
    significance: float = Field(..., ge=0, le=1)


class GrowthPattern(BaseModel):
    """Growth pattern analysis"""
    type: GrowthType
    rate: float
    acceleration: float
    projected_growth: float


class Patterns(BaseModel):
    """All detected patterns"""
    seasonality: SeasonalityPattern
    growth: GrowthPattern
    cycles: List[CyclicalPattern]


class PeriodData(BaseModel):
    """Data for a specific period"""
    start: str
    end: str
    value: float
    avg: float


class PeriodComparison(BaseModel):
    """Period-over-period comparison"""
    current_period: PeriodData
    previous_period: PeriodData
    change: float
    change_percentage: float


class MonthlyComparison(BaseModel):
    """Monthly comparison data"""
    month: str
    current: float
    previous: float
    change: float


class YearOverYearComparison(BaseModel):
    """Year-over-year comparison"""
    current_year: Optional[float]
    previous_year: Optional[float]
    change: Optional[float]
    change_percentage: Optional[float]
    monthly_comparison: List[MonthlyComparison] = Field(default_factory=list)


class Benchmarks(BaseModel):
    """Benchmark comparisons"""
    industry_average: Optional[float] = None
    top_performers: Optional[float] = None
    position: Optional[Literal['above', 'below', 'at']] = None
    percentile: Optional[float] = None


class Comparisons(BaseModel):
    """All comparison data"""
    period_comparison: PeriodComparison
    year_over_year: YearOverYearComparison
    benchmarks: Benchmarks


class Correlation(BaseModel):
    """Correlation with another metric"""
    metric: str
    correlation: float = Field(..., ge=-1, le=1)
    lag: int
    significance: float = Field(..., ge=0, le=1)
    relationship: Literal['positive', 'negative', 'none']


class ShortTermForecast(BaseModel):
    """Short-term forecast point"""
    timestamp: str
    predicted: float = Field(..., ge=0)
    upper: float = Field(..., ge=0)
    lower: float = Field(..., ge=0)
    confidence: float = Field(..., ge=0, le=1)


class ForecastRange(BaseModel):
    """Forecast value range"""
    optimistic: float = Field(..., ge=0)
    realistic: float = Field(..., ge=0)
    pessimistic: float = Field(..., ge=0)

    @validator('pessimistic')
    def pessimistic_lt_realistic(cls, v, values):
        if 'realistic' in values and v > values['realistic']:
            raise ValueError('Pessimistic must be <= realistic')
        return v

    @validator('optimistic')
    def optimistic_gt_realistic(cls, v, values):
        if 'realistic' in values and v < values['realistic']:
            raise ValueError('Optimistic must be >= realistic')
        return v


class LongTermForecast(BaseModel):
    """Long-term forecast point"""
    period: str
    predicted: float = Field(..., ge=0)
    range: ForecastRange


class ForecastAccuracy(BaseModel):
    """Forecast model accuracy metrics"""
    mape: float = Field(..., ge=0, le=100, description="Mean Absolute Percentage Error")
    rmse: float = Field(..., ge=0, description="Root Mean Square Error")
    r2: float = Field(..., ge=0, le=1, description="R-squared score")


class Forecast(BaseModel):
    """Complete forecast data"""
    short_term: List[ShortTermForecast]
    long_term: List[LongTermForecast]
    accuracy: ForecastAccuracy


class Insight(BaseModel):
    """Actionable insight"""
    type: InsightType
    title: str
    description: str
    impact: ImpactLevel
    confidence: float = Field(..., ge=0, le=1)
    recommendation: str


class TrendAnalysisResponse(BaseModel):
    """Complete trend analysis response"""
    workspace_id: str
    metric: str
    timeframe: str
    overview: TrendOverview
    time_series: TimeSeries
    decomposition: Decomposition
    patterns: Patterns
    comparisons: Comparisons
    correlations: List[Correlation]
    forecast: Forecast
    insights: List[Insight]
    error: Optional[str] = None
    message: Optional[str] = None

    class Config:
        allow_population_by_field_name = True
