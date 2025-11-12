"""Anomaly detection schemas."""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any, Literal
from enum import Enum


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class SeverityLevel(str, Enum):
    """Anomaly severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DetectionMethod(str, Enum):
    """Anomaly detection methods."""
    ZSCORE = "zscore"
    ZSCORE_ROLLING = "zscore_rolling"
    ZSCORE_GLOBAL = "zscore_global"
    ISOLATION_FOREST = "isolation_forest"
    LSTM = "lstm"
    THRESHOLD = "threshold"


class ModelType(str, Enum):
    """Baseline model types."""
    ZSCORE = "zscore"
    ISOLATION_FOREST = "isolation_forest"
    LSTM = "lstm"


# Request Schemas


class DetectAnomaliesRequest(BaseModel):
    """Request schema for detecting anomalies."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    metric_type: str = Field(..., description="Type of metric to analyze")
    lookback_days: int = Field(30, ge=1, le=365, description="Days of historical data")
    sensitivity: float = Field(2.5, ge=1.0, le=5.0, description="Detection sensitivity")
    method: DetectionMethod = Field(
        DetectionMethod.ZSCORE,
        description="Detection method"
    )

    @field_validator('metric_type')
    @classmethod
    def validate_metric_type(cls, v):
        """Validate metric type against allowed values."""
        valid_metrics = [
            'runtime_seconds',
            'credits_consumed',
            'executions',
        ]
        if v not in valid_metrics:
            raise ValueError(f"metric_type must be one of {valid_metrics}")
        return v


class DetectUsageSpikesRequest(BaseModel):
    """Request schema for detecting usage spikes."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    sensitivity: float = Field(2.5, ge=1.0, le=5.0, description="Detection sensitivity")
    window_hours: int = Field(24, ge=1, le=168, description="Rolling window in hours")


class DetectErrorPatternsRequest(BaseModel):
    """Request schema for detecting error patterns."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    window_hours: int = Field(24, ge=1, le=168, description="Analysis window in hours")


class DetectUserBehaviorRequest(BaseModel):
    """Request schema for detecting user behavior anomalies."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    user_id: str = Field(..., description="User ID to analyze")
    lookback_days: int = Field(30, ge=7, le=365, description="Days of historical data")


class TrainBaselineRequest(BaseModel):
    """Request schema for training baseline model."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    metric_type: str = Field(..., description="Type of metric to model")
    training_days: int = Field(90, ge=30, le=365, description="Training period in days")
    model_type: ModelType = Field(
        ModelType.ZSCORE,
        description="Type of model to train"
    )

    @field_validator('metric_type')
    @classmethod
    def validate_metric_type(cls, v):
        """Validate metric type against allowed values."""
        valid_metrics = [
            'runtime_seconds',
            'credits_consumed',
            'executions',
        ]
        if v not in valid_metrics:
            raise ValueError(f"metric_type must be one of {valid_metrics}")
        return v


class AcknowledgeAnomalyRequest(BaseModel):
    """Request schema for acknowledging an anomaly."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    notes: Optional[str] = Field(None, max_length=1000, description="Acknowledgment notes")
    is_false_positive: bool = Field(False, description="Mark as false positive")


class CreateAnomalyRuleRequest(BaseModel):
    """Request schema for creating anomaly detection rule."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    workspace_id: Optional[str] = Field(None, description="Workspace ID (null for global)")
    metric_type: str = Field(..., description="Metric type to monitor")
    rule_name: str = Field(..., min_length=1, max_length=255, description="Rule name")
    detection_method: DetectionMethod = Field(..., description="Detection method")
    parameters: Dict[str, Any] = Field(..., description="Rule parameters")
    auto_alert: bool = Field(False, description="Enable automatic alerting")
    alert_channels: Optional[List[str]] = Field(None, description="Alert channel IDs")

    @field_validator('metric_type')
    @classmethod
    def validate_metric_type(cls, v):
        """Validate metric type against allowed values."""
        valid_metrics = [
            'runtime_seconds',
            'credits_consumed',
            'executions',
        ]
        if v not in valid_metrics:
            raise ValueError(f"metric_type must be one of {valid_metrics}")
        return v


class UpdateAnomalyRuleRequest(BaseModel):
    """Request schema for updating anomaly detection rule."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    rule_name: Optional[str] = Field(None, min_length=1, max_length=255)
    parameters: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    auto_alert: Optional[bool] = None
    alert_channels: Optional[List[str]] = None


# Response Schemas


class ExpectedRange(BaseModel):
    """Expected value range for anomaly."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    min: Optional[float] = None
    max: Optional[float] = None
    mean: Optional[float] = None
    std: Optional[float] = None


class AnomalyContext(BaseModel):
    """Context information for anomaly."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    expected_mean: Optional[float] = None
    expected_std: Optional[float] = None
    lookback_days: Optional[int] = None
    sensitivity: Optional[float] = None
    window_hours: Optional[int] = None
    features: Optional[Dict[str, Any]] = None


class AnomalyDetectionResponse(BaseModel):
    """Response schema for detected anomaly."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: Optional[str] = None
    metric_type: str
    workspace_id: str
    detected_at: str
    anomaly_value: Optional[float] = None
    expected_range: Optional[Dict[str, Any]] = None
    anomaly_score: float
    severity: SeverityLevel
    detection_method: str
    context: Optional[AnomalyContext] = None
    is_acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None


class AnomalyListResponse(BaseModel):
    """Response schema for list of anomalies."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    anomalies: List[AnomalyDetectionResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class AnomalyRuleResponse(BaseModel):
    """Response schema for anomaly detection rule."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str
    workspace_id: Optional[str] = None
    metric_type: str
    rule_name: str
    detection_method: str
    parameters: Dict[str, Any]
    is_active: bool
    auto_alert: bool
    alert_channels: Optional[List[str]] = None
    created_by: str
    created_at: str
    updated_at: str


class BaselineStatistics(BaseModel):
    """Baseline model statistics."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    mean: float
    std: float
    median: float
    q25: float
    q75: float
    min: float
    max: float
    count: int


class TrainingPeriod(BaseModel):
    """Training period information."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    start: str
    end: str
    days: int


class BaselineModelResponse(BaseModel):
    """Response schema for baseline model."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    model_id: str
    metric_type: str
    model_type: str
    statistics: BaselineStatistics
    training_period: TrainingPeriod
    accuracy_metrics: Optional[Dict[str, Any]] = None
    last_updated: Optional[str] = None


class BaselineModelDetailResponse(BaseModel):
    """Detailed response schema for baseline model."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str
    workspace_id: str
    metric_type: str
    model_type: str
    model_parameters: Dict[str, Any]
    statistics: Dict[str, Any]
    training_data_start: str
    training_data_end: str
    accuracy_metrics: Optional[Dict[str, Any]] = None
    last_updated: str


class AnomalySummaryResponse(BaseModel):
    """Summary statistics for anomalies."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    total_anomalies: int
    by_severity: Dict[str, int]
    by_metric_type: Dict[str, int]
    by_detection_method: Dict[str, int]
    acknowledged_count: int
    unacknowledged_count: int
    recent_anomalies: List[AnomalyDetectionResponse]


class HealthCheckResponse(BaseModel):
    """Health check response for anomaly detection service."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    status: Literal["healthy", "degraded", "unhealthy"]
    active_rules: int
    baseline_models: int
    recent_detections: int
    timestamp: str
