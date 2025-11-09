# Specification: Analytics API Endpoints

## Overview
Define analytics-specific API endpoints for metrics, trends, predictions, and advanced analytics features.

## Technical Requirements

### Metrics Endpoints

#### GET `/api/v1/analytics/metrics/aggregate`
```python
@router.get("/metrics/aggregate")
async def get_aggregated_metrics(
    workspace_id: str,
    metrics: List[str],
    aggregation: str = "sum",  # sum, avg, min, max, count
    group_by: Optional[List[str]] = None,
    filters: Optional[Dict] = None,
    date_range: DateRange,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Returns aggregated metrics with grouping options
    
    Example:
    GET /api/v1/analytics/metrics/aggregate?
        metrics=credits_consumed,executions&
        aggregation=sum&
        group_by=agent_id,date&
        filters={"status":"success"}
    """
    return {
        "aggregations": [
            {
                "group": {"agent_id": "agent_123", "date": "2024-01-15"},
                "metrics": {
                    "credits_consumed": 5420,
                    "executions": 234
                }
            }
        ],
        "totals": {
            "credits_consumed": 125000,
            "executions": 5420
        }
    }
```

#### GET `/api/v1/analytics/metrics/timeseries`
```python
@router.get("/metrics/timeseries")
async def get_timeseries_metrics(
    workspace_id: str,
    metrics: List[str],
    granularity: str = "hourly",  # minutely, hourly, daily, weekly, monthly
    fill_gaps: bool = True,
    interpolation: str = "linear",  # linear, previous, zero
    date_range: DateRange,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Returns time-series data with gap filling
    """
    return {
        "series": [
            {
                "metric": "active_users",
                "data": [
                    {"timestamp": "2024-01-15T00:00:00Z", "value": 145},
                    {"timestamp": "2024-01-15T01:00:00Z", "value": 132}
                ],
                "statistics": {
                    "min": 102,
                    "max": 245,
                    "avg": 156,
                    "std_dev": 23.4
                }
            }
        ]
    }
```

### Trend Analysis Endpoints

#### GET `/api/v1/analytics/trends/detect`
```python
@router.get("/trends/detect")
async def detect_trends(
    workspace_id: str,
    metric: str,
    method: str = "linear",  # linear, polynomial, seasonal
    confidence: float = 0.95,
    date_range: DateRange,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Detect trends in metrics using statistical methods
    """
    return {
        "trend": {
            "direction": "increasing",
            "slope": 12.5,
            "r_squared": 0.89,
            "confidence_interval": [10.2, 14.8],
            "change_points": [
                {
                    "date": "2024-01-10",
                    "type": "acceleration",
                    "confidence": 0.92
                }
            ],
            "forecast": {
                "next_7_days": 156.2,
                "next_30_days": 672.5
            }
        }
    }
```

#### GET `/api/v1/analytics/trends/seasonal`
```python
@router.get("/trends/seasonal")
async def get_seasonal_patterns(
    workspace_id: str,
    metric: str,
    seasonality: str = "auto",  # auto, daily, weekly, monthly
    date_range: DateRange,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Identify seasonal patterns in metrics
    """
    return {
        "seasonality": {
            "period": "weekly",
            "strength": 0.78,
            "peak_days": ["Monday", "Tuesday"],
            "peak_hours": [14, 15, 16],
            "low_periods": ["Saturday", "Sunday"],
            "pattern": [
                {"day": "Monday", "index": 1.25},
                {"day": "Tuesday", "index": 1.18}
            ]
        }
    }
```

### Prediction Endpoints

#### POST `/api/v1/analytics/predictions/forecast`
```python
@router.post("/predictions/forecast")
async def create_forecast(
    workspace_id: str,
    forecast_config: ForecastConfig,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Generate forecasts for specified metrics
    
    Request body:
    {
        "metric": "credits_consumed",
        "horizon_days": 30,
        "model": "prophet",  # prophet, arima, lstm
        "confidence_level": 0.95,
        "include_seasonality": true
    }
    """
    forecast_id = await generate_forecast(workspace_id, forecast_config)
    
    return {
        "forecast_id": forecast_id,
        "status": "processing",
        "estimated_completion": 30  # seconds
    }
```

#### GET `/api/v1/analytics/predictions/{forecast_id}`
```python
@router.get("/predictions/{forecast_id}")
async def get_forecast_results(
    forecast_id: str,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Retrieve forecast results
    """
    forecast = await get_forecast(forecast_id)
    
    return {
        "forecast": {
            "predictions": [
                {
                    "date": "2024-02-01",
                    "value": 5420,
                    "lower_bound": 5100,
                    "upper_bound": 5740
                }
            ],
            "model_metrics": {
                "mape": 8.2,
                "rmse": 145.6,
                "confidence": 0.95
            }
        }
    }
```

### Anomaly Detection Endpoints

#### POST `/api/v1/analytics/anomalies/detect`
```python
@router.post("/anomalies/detect")
async def detect_anomalies(
    workspace_id: str,
    anomaly_config: AnomalyConfig,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Run anomaly detection on metrics
    
    Request body:
    {
        "metric": "error_rate",
        "method": "isolation_forest",  # zscore, isolation_forest, lstm
        "sensitivity": 2.5,
        "lookback_days": 30
    }
    """
    anomalies = await detect_metric_anomalies(workspace_id, anomaly_config)
    
    return {
        "anomalies": [
            {
                "timestamp": "2024-01-15T14:30:00Z",
                "metric_value": 0.15,
                "expected_range": [0.01, 0.05],
                "anomaly_score": 3.2,
                "severity": "high"
            }
        ]
    }
```

#### GET `/api/v1/analytics/anomalies/rules`
```python
@router.get("/anomalies/rules")
async def get_anomaly_rules(
    workspace_id: str,
    is_active: Optional[bool] = None,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Get configured anomaly detection rules
    """
    rules = await get_workspace_anomaly_rules(workspace_id, is_active)
    
    return {
        "rules": [
            {
                "id": "rule_123",
                "name": "High Error Rate",
                "metric": "error_rate",
                "threshold": 0.05,
                "method": "threshold",
                "is_active": True,
                "auto_alert": True
            }
        ]
    }
```

### Cohort Analysis Endpoints

#### POST `/api/v1/analytics/cohorts/create`
```python
@router.post("/cohorts/create")
async def create_cohort(
    workspace_id: str,
    cohort_config: CohortConfig,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Create a user cohort for analysis
    
    Request body:
    {
        "name": "Power Users",
        "filters": {
            "min_executions": 100,
            "min_credits": 1000,
            "date_joined_after": "2024-01-01"
        }
    }
    """
    cohort_id = await create_user_cohort(workspace_id, cohort_config)
    
    return {
        "cohort_id": cohort_id,
        "user_count": 342
    }
```

#### GET `/api/v1/analytics/cohorts/{cohort_id}/retention`
```python
@router.get("/cohorts/{cohort_id}/retention")
async def get_cohort_retention(
    cohort_id: str,
    period: str = "daily",  # daily, weekly, monthly
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Get retention analysis for cohort
    """
    retention = await calculate_cohort_retention(cohort_id, period)
    
    return {
        "retention": {
            "cohort_size": 342,
            "retention_curve": [
                {"period": 0, "retained": 342, "percentage": 100},
                {"period": 1, "retained": 291, "percentage": 85},
                {"period": 7, "retained": 247, "percentage": 72}
            ],
            "metrics": {
                "day_1_retention": 85,
                "day_7_retention": 72,
                "day_30_retention": 61
            }
        }
    }
```

### Funnel Analysis Endpoints

#### POST `/api/v1/analytics/funnels/create`
```python
@router.post("/funnels/create")
async def create_funnel(
    workspace_id: str,
    funnel_config: FunnelConfig,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Create a conversion funnel
    
    Request body:
    {
        "name": "Onboarding Funnel",
        "steps": [
            {"name": "Sign Up", "event": "user_registered"},
            {"name": "First Login", "event": "user_logged_in"},
            {"name": "First Execution", "event": "execution_completed"}
        ]
    }
    """
    funnel_id = await create_conversion_funnel(workspace_id, funnel_config)
    
    return {
        "funnel_id": funnel_id,
        "status": "created"
    }
```

#### GET `/api/v1/analytics/funnels/{funnel_id}/analysis`
```python
@router.get("/funnels/{funnel_id}/analysis")
async def get_funnel_analysis(
    funnel_id: str,
    date_range: DateRange,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Get funnel conversion analysis
    """
    analysis = await analyze_funnel(funnel_id, date_range)
    
    return {
        "funnel": {
            "total_entered": 1000,
            "total_converted": 612,
            "overall_conversion": 61.2,
            "steps": [
                {
                    "name": "Sign Up",
                    "users": 1000,
                    "conversion": 100,
                    "drop_off": 0
                },
                {
                    "name": "First Login",
                    "users": 850,
                    "conversion": 85,
                    "drop_off": 15,
                    "avg_time_to_convert": 3600  # seconds
                }
            ]
        }
    }
```

### Comparison Endpoints

#### POST `/api/v1/analytics/compare/periods`
```python
@router.post("/compare/periods")
async def compare_periods(
    workspace_id: str,
    comparison_config: ComparisonConfig,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Compare metrics across time periods
    
    Request body:
    {
        "metrics": ["active_users", "credits_consumed"],
        "period_1": {"start": "2024-01-01", "end": "2024-01-31"},
        "period_2": {"start": "2023-01-01", "end": "2023-01-31"}
    }
    """
    comparison = await compare_time_periods(workspace_id, comparison_config)
    
    return {
        "comparison": {
            "period_1": {
                "active_users": 3421,
                "credits_consumed": 125000
            },
            "period_2": {
                "active_users": 2854,
                "credits_consumed": 98000
            },
            "changes": {
                "active_users": {
                    "absolute": 567,
                    "percentage": 19.8
                },
                "credits_consumed": {
                    "absolute": 27000,
                    "percentage": 27.5
                }
            }
        }
    }
```

### Statistical Analysis Endpoints

#### GET `/api/v1/analytics/statistics/distribution`
```python
@router.get("/statistics/distribution")
async def get_metric_distribution(
    workspace_id: str,
    metric: str,
    bins: int = 10,
    date_range: DateRange,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Get statistical distribution of metric values
    """
    distribution = await calculate_distribution(workspace_id, metric, date_range, bins)
    
    return {
        "distribution": {
            "histogram": [
                {"bin": "[0-10)", "count": 145},
                {"bin": "[10-20)", "count": 234}
            ],
            "statistics": {
                "mean": 45.6,
                "median": 42.0,
                "mode": 40.0,
                "std_dev": 12.3,
                "variance": 151.29,
                "skewness": 0.45,
                "kurtosis": 2.8,
                "percentiles": {
                    "p25": 32.0,
                    "p50": 42.0,
                    "p75": 58.0,
                    "p95": 78.0,
                    "p99": 92.0
                }
            }
        }
    }
```

## Implementation Priority
1. Basic metrics aggregation
2. Time-series endpoints
3. Trend detection
4. Anomaly detection
5. Advanced analytics (cohorts, funnels)

## Success Metrics
- Query response time < 500ms (p95)
- Forecast accuracy (MAPE) < 10%
- Anomaly detection precision > 90%
- API availability > 99.9%