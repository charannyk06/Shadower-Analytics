# Anomaly Detection System

## Overview

The Anomaly Detection System provides statistical anomaly detection for metrics across all dimensions using z-scores, isolation forests, and custom thresholds. It enables real-time monitoring and alerting for unusual patterns in time-series data.

## Features

### Detection Methods

1. **Z-Score Detection**
   - Statistical outlier detection for normally distributed data
   - Configurable sensitivity (standard deviations)
   - Global and rolling window modes
   - Fast and interpretable results

2. **Isolation Forest**
   - Multivariate anomaly detection
   - Handles non-normal distributions
   - Effective for complex patterns
   - Suitable for high-dimensional data

3. **Custom Thresholds**
   - User-defined business logic rules
   - Immediate alerting capabilities
   - Flexible parameter configuration

### Monitored Metrics

- `runtime_seconds` - Execution duration anomalies
- `credits_consumed` - Usage spike detection
- `tokens_used` - Token consumption patterns
- `executions` - Execution count anomalies
- `error_rate` - Error pattern detection
- `success_rate` - Success rate degradation
- `user_activity` - Behavioral anomalies
- `api_latency` - Performance degradation

### Severity Levels

- **Low**: 2.0σ - Minor deviations from normal
- **Medium**: 2.5σ - Moderate anomalies requiring attention
- **High**: 3.0σ - Significant anomalies requiring immediate action
- **Critical**: 4.0σ - Severe anomalies requiring urgent response

## Architecture

### Database Schema

#### anomaly_detections
Stores detected anomalies with full context and metadata.

```sql
CREATE TABLE analytics.anomaly_detections (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    metric_type VARCHAR(100) NOT NULL,
    detected_at TIMESTAMP NOT NULL,
    anomaly_value DECIMAL,
    expected_range JSONB,
    anomaly_score DECIMAL NOT NULL,
    severity VARCHAR(20) NOT NULL,
    detection_method VARCHAR(50) NOT NULL,
    context JSONB,
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by UUID,
    acknowledged_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### anomaly_rules
Configuration for automatic anomaly detection rules.

```sql
CREATE TABLE analytics.anomaly_rules (
    id UUID PRIMARY KEY,
    workspace_id UUID,
    metric_type VARCHAR(100) NOT NULL,
    rule_name VARCHAR(255) NOT NULL,
    detection_method VARCHAR(50) NOT NULL,
    parameters JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    auto_alert BOOLEAN DEFAULT FALSE,
    alert_channels JSONB,
    created_by UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### baseline_models
Statistical baselines for normal behavior patterns.

```sql
CREATE TABLE analytics.baseline_models (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    metric_type VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    model_parameters JSONB NOT NULL,
    statistics JSONB NOT NULL,
    training_data_start DATE NOT NULL,
    training_data_end DATE NOT NULL,
    accuracy_metrics JSONB,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### API Endpoints

#### Detection Endpoints

**GET `/api/v1/anomalies/{workspace_id}`**
- Get paginated list of detected anomalies
- Query parameters: date_from, date_to, severity, metric_type, is_acknowledged, page, page_size
- Returns: Paginated anomaly list with metadata

**POST `/api/v1/anomalies/{workspace_id}/detect`**
- Run on-demand anomaly detection
- Body: DetectAnomaliesRequest (metric_type, lookback_days, sensitivity, method)
- Returns: List of detected anomalies

**POST `/api/v1/anomalies/{workspace_id}/detect/usage-spikes`**
- Detect unusual credit consumption spikes
- Body: DetectUsageSpikesRequest (sensitivity, window_hours)
- Returns: List of usage spike anomalies

**POST `/api/v1/anomalies/{workspace_id}/detect/error-patterns`**
- Identify unusual error patterns
- Body: DetectErrorPatternsRequest (window_hours)
- Returns: List of error pattern anomalies

**POST `/api/v1/anomalies/{workspace_id}/detect/user-behavior`**
- Detect unusual user activity patterns
- Body: DetectUserBehaviorRequest (user_id, lookback_days)
- Returns: List of behavioral anomalies

#### Management Endpoints

**PUT `/api/v1/anomalies/{workspace_id}/{anomaly_id}/acknowledge`**
- Acknowledge an anomaly as reviewed
- Body: AcknowledgeAnomalyRequest (notes, is_false_positive)
- Returns: Updated anomaly record

**GET `/api/v1/anomalies/{workspace_id}/rules`**
- Get anomaly detection rules
- Query parameters: is_active, metric_type
- Returns: List of configured rules

**POST `/api/v1/anomalies/{workspace_id}/rules`**
- Create new anomaly detection rule
- Body: CreateAnomalyRuleRequest
- Returns: Created rule

#### Baseline Model Endpoints

**POST `/api/v1/anomalies/{workspace_id}/baseline/train`**
- Train baseline model for normal behavior
- Body: TrainBaselineRequest (metric_type, training_days, model_type)
- Returns: Model statistics and metadata

**GET `/api/v1/anomalies/{workspace_id}/baseline`**
- Get baseline models for workspace
- Query parameters: metric_type
- Returns: List of baseline models

**GET `/api/v1/anomalies/{workspace_id}/summary`**
- Get summary statistics for anomalies
- Query parameters: days
- Returns: Aggregated anomaly statistics

## Usage Examples

### 1. Detect Anomalies in Credit Consumption

```bash
curl -X POST "http://localhost:8000/api/v1/anomalies/workspace-123/detect" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "metricType": "credits_consumed",
    "lookbackDays": 30,
    "sensitivity": 2.5,
    "method": "zscore"
  }'
```

### 2. Detect Usage Spikes

```bash
curl -X POST "http://localhost:8000/api/v1/anomalies/workspace-123/detect/usage-spikes" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sensitivity": 2.5,
    "windowHours": 24
  }'
```

### 3. Train Baseline Model

```bash
curl -X POST "http://localhost:8000/api/v1/anomalies/workspace-123/baseline/train" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "metricType": "runtime_seconds",
    "trainingDays": 90,
    "modelType": "zscore"
  }'
```

### 4. Create Detection Rule

```bash
curl -X POST "http://localhost:8000/api/v1/anomalies/workspace-123/rules" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "metricType": "credits_consumed",
    "ruleName": "High Credit Usage Alert",
    "detectionMethod": "zscore",
    "parameters": {
      "sensitivity": 3.0,
      "window": 24
    },
    "autoAlert": true,
    "alertChannels": ["email", "slack"]
  }'
```

### 5. Get Anomalies with Filters

```bash
curl "http://localhost:8000/api/v1/anomalies/workspace-123?severity=high&isAcknowledged=false&page=1&pageSize=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 6. Acknowledge Anomaly

```bash
curl -X PUT "http://localhost:8000/api/v1/anomalies/workspace-123/anomaly-456/acknowledge" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Investigated - caused by planned load test",
    "isFalsePositive": true
  }'
```

## Python Service Usage

### Basic Z-Score Detection

```python
from src.services.analytics.anomaly_detection import AnomalyDetectionService
import pandas as pd

# Initialize service
service = AnomalyDetectionService(db=db_session)

# Detect anomalies
anomalies = await service.detect_metric_anomalies(
    metric_type="runtime_seconds",
    workspace_id="workspace-123",
    lookback_days=30,
    sensitivity=2.5,
    method="zscore"
)

print(f"Found {len(anomalies)} anomalies")
for anomaly in anomalies:
    print(f"Anomaly at {anomaly['detected_at']}: "
          f"value={anomaly['anomaly_value']}, "
          f"score={anomaly['anomaly_score']}, "
          f"severity={anomaly['severity']}")
```

### Isolation Forest Detection

```python
# For multivariate anomaly detection
anomalies = await service.detect_error_patterns(
    workspace_id="workspace-123",
    window_hours=24
)

for anomaly in anomalies:
    print(f"Error pattern detected: {anomaly['context']['features']}")
```

### Train Baseline Model

```python
# Train baseline for normal behavior
baseline = await service.train_baseline_model(
    metric_type="credits_consumed",
    workspace_id="workspace-123",
    training_days=90,
    model_type="zscore"
)

print(f"Baseline statistics: {baseline['statistics']}")
```

### Static Methods (No Database Required)

```python
# Calculate z-score
score = AnomalyDetectionService.calculate_zscore(
    value=150.0,
    mean=100.0,
    std_dev=20.0
)
print(f"Z-score: {score}")  # Output: 2.5

# Detect anomalies in pandas Series
import pandas as pd
data = pd.Series([10, 11, 10, 9, 50, 10, 11])
data.index = pd.date_range('2024-01-01', periods=7, freq='D')

anomalies = AnomalyDetectionService.detect_zscore_anomalies(
    data=data,
    sensitivity=2.0
)
print(f"Found {len(anomalies)} anomalies")

# Determine severity
severity = AnomalyDetectionService.determine_severity(3.5)
print(f"Severity: {severity}")  # Output: high
```

## Configuration

### Sensitivity Settings

- **Low Sensitivity (1.0-1.5σ)**: Detects many anomalies, higher false positive rate
- **Medium Sensitivity (2.0-2.5σ)**: Balanced detection, recommended default
- **High Sensitivity (3.0-4.0σ)**: Only critical anomalies, lower false positive rate

### Performance Limits

- `MAX_DATA_POINTS`: 50,000 - Maximum data points per query
- `MAX_LOOKBACK_DAYS`: 365 - Maximum historical data range
- `DETECTION_TIMEOUT_SECONDS`: 60 - Request timeout for detection operations

### Rate Limits

- Detection operations: 10 requests/minute, 100 requests/hour
- Rule management: 20 requests/minute, 200 requests/hour

## Security

### Workspace Isolation
- All queries enforce workspace-level access control
- RLS policies at database level
- Explicit workspace validation in middleware

### Input Validation
- Metric names validated against whitelist
- Parameterized queries prevent SQL injection
- Request size limits prevent DoS

### Authentication
- JWT-based authentication required
- Role-based access control (RBAC)
- Workspace membership verification

## Migration

Run the database migration to create required tables:

```bash
cd backend
alembic upgrade head
```

Or apply specific migration:

```bash
alembic upgrade 003_anomaly_detection
```

## Testing

Run unit tests:

```bash
cd backend
pytest tests/unit/test_anomaly_detection_service.py -v
```

Run integration tests:

```bash
pytest tests/integration/test_anomaly_detection_routes.py -v
```

Run all tests with coverage:

```bash
pytest tests/ --cov=src/services/analytics/anomaly_detection --cov-report=html
```

## Performance Considerations

### Optimization Tips

1. **Use Appropriate Lookback Windows**
   - Shorter windows (7-30 days) for faster detection
   - Longer windows (60-90 days) for better baselines

2. **Batch Processing**
   - Train baselines during off-peak hours
   - Use scheduled jobs for routine detection

3. **Caching**
   - Cache baseline statistics
   - Reuse models for similar queries

4. **Indexing**
   - Composite indexes on (workspace_id, detected_at)
   - Separate indexes for severity and metric_type

### Monitoring

Monitor these metrics for system health:
- Detection latency
- False positive rate
- Model training duration
- Database query performance

## Troubleshooting

### High False Positive Rate

**Solution**: Increase sensitivity threshold or train more comprehensive baseline

```python
# Increase sensitivity
anomalies = await service.detect_metric_anomalies(
    metric_type="runtime_seconds",
    workspace_id="workspace-123",
    sensitivity=3.5,  # Higher = fewer anomalies
    lookback_days=30
)
```

### Missing Anomalies

**Solution**: Decrease sensitivity or use isolation forest for complex patterns

```python
# Use isolation forest for multivariate detection
anomalies = await service.detect_metric_anomalies(
    metric_type="runtime_seconds",
    workspace_id="workspace-123",
    method="isolation_forest"
)
```

### Slow Detection

**Solution**: Reduce lookback window or optimize database indexes

```sql
-- Add missing index
CREATE INDEX CONCURRENTLY idx_execution_logs_workspace_started
ON execution_logs(workspace_id, started_at DESC);
```

## Future Enhancements

### Planned Features

1. **LSTM Autoencoder** - Deep learning for sequential pattern anomalies
2. **Real-time Stream Processing** - Sub-second anomaly detection
3. **Multi-workspace Comparison** - Detect anomalies relative to peer workspaces
4. **Automatic Threshold Tuning** - ML-based sensitivity optimization
5. **Anomaly Explanations** - Root cause analysis and recommendations

### Integration Roadmap

- Slack/Email alerting integration
- PagerDuty incident creation
- Grafana dashboard integration
- Webhook support for custom workflows

## Support

For issues or questions:
- GitHub Issues: https://github.com/charannyk06/Shadower-Analytics/issues
- Documentation: https://docs.shadow.com/analytics/anomaly-detection

## License

Copyright (c) 2025 Shadow Analytics Team. All rights reserved.
