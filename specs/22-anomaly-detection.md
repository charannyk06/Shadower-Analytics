# Specification: Anomaly Detection System

## Overview
Implement statistical anomaly detection for metrics across all dimensions using z-scores, isolation forests, and custom thresholds.

## Technical Requirements

### Backend Implementation

#### Service: `services/anomaly_detection.py`
```python
class AnomalyDetector:
    def __init__(self):
        self.models = {}
        self.thresholds = {}
    
    async def detect_metric_anomalies(
        self,
        metric_type: str,
        workspace_id: str,
        lookback_days: int = 30
    ):
        """
        Detect anomalies in time-series metrics
        Returns list of anomaly points with scores
        """
    
    async def detect_usage_spikes(
        self,
        workspace_id: str,
        sensitivity: float = 2.5
    ):
        """
        Detect unusual spikes in credit consumption
        Uses z-score method with configurable sensitivity
        """
    
    async def detect_error_patterns(
        self,
        workspace_id: str,
        window_hours: int = 24
    ):
        """
        Identify unusual error patterns or rates
        Uses isolation forest for multivariate detection
        """
    
    async def detect_user_behavior_anomalies(
        self,
        user_id: str,
        workspace_id: str
    ):
        """
        Detect unusual user activity patterns
        Compares against historical baseline
        """
    
    async def train_baseline_model(
        self,
        metric_type: str,
        workspace_id: str,
        training_days: int = 90
    ):
        """
        Train baseline model for normal behavior
        Updates periodically with new data
        """
    
    def calculate_anomaly_score(
        self,
        value: float,
        mean: float,
        std_dev: float,
        method: str = "zscore"
    ):
        """
        Calculate anomaly score for single value
        Supports multiple scoring methods
        """

#### Database Schema
```sql
-- Anomaly detections table
CREATE TABLE analytics.anomaly_detections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL,
    metric_type VARCHAR(100) NOT NULL,
    detected_at TIMESTAMP NOT NULL,
    anomaly_value DECIMAL,
    expected_range JSONB,
    anomaly_score DECIMAL NOT NULL,
    severity VARCHAR(20) NOT NULL, -- 'low', 'medium', 'high', 'critical'
    detection_method VARCHAR(50) NOT NULL,
    context JSONB,
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by UUID,
    acknowledged_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_anomaly_workspace_time (workspace_id, detected_at DESC),
    INDEX idx_anomaly_severity (severity, is_acknowledged),
    INDEX idx_anomaly_metric (metric_type, workspace_id)
);

-- Anomaly rules configuration
CREATE TABLE analytics.anomaly_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(workspace_id, metric_type, rule_name)
);

-- Baseline models storage
CREATE TABLE analytics.baseline_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL,
    metric_type VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    model_parameters JSONB NOT NULL,
    statistics JSONB NOT NULL, -- mean, std, percentiles, etc.
    training_data_start DATE NOT NULL,
    training_data_end DATE NOT NULL,
    accuracy_metrics JSONB,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(workspace_id, metric_type, model_type)
);
```

### Frontend Components

#### Component: `components/analytics/AnomalyDetectionDashboard.tsx`
```typescript
interface AnomalyDetectionDashboardProps {
    workspaceId: string;
    dateRange: DateRange;
}

export function AnomalyDetectionDashboard({
    workspaceId,
    dateRange
}: AnomalyDetectionDashboardProps) {
    // Real-time anomaly feed
    // Anomaly timeline visualization
    // Severity distribution chart
    // Acknowledgment interface
    // Rule configuration panel
    
    return (
        <div className="anomaly-dashboard">
            <AnomalyAlertBanner />
            <AnomalyTimeline />
            <AnomalySeverityChart />
            <AnomalyDetailsTable />
            <AnomalyRuleConfiguration />
        </div>
    );
}

interface AnomalyTimelineProps {
    anomalies: Anomaly[];
    onAnomalyClick: (anomaly: Anomaly) => void;
}

export function AnomalyTimeline({
    anomalies,
    onAnomalyClick
}: AnomalyTimelineProps) {
    // Interactive timeline with anomaly markers
    // Color-coded by severity
    // Hover for details
    // Click to investigate
}

interface AnomalyRuleConfigurationProps {
    workspaceId: string;
    existingRules: AnomalyRule[];
}

export function AnomalyRuleConfiguration({
    workspaceId,
    existingRules
}: AnomalyRuleConfigurationProps) {
    // Create/edit anomaly detection rules
    // Set thresholds and sensitivities
    // Configure alert channels
    // Test rules against historical data
}
```

### API Endpoints

#### GET `/api/analytics/anomalies`
- Query parameters: workspace_id, date_from, date_to, severity, metric_type, is_acknowledged
- Returns paginated list of detected anomalies
- Includes context and recommended actions

#### POST `/api/analytics/anomalies/detect`
- Request body: { metric_type, workspace_id, method, parameters }
- Runs on-demand anomaly detection
- Returns detected anomalies immediately

#### PUT `/api/analytics/anomalies/{id}/acknowledge`
- Acknowledges an anomaly as reviewed
- Request body: { notes, is_false_positive }
- Updates anomaly record and adjusts future detection

#### POST `/api/analytics/anomalies/rules`
- Creates new anomaly detection rule
- Request body: { metric_type, method, parameters, auto_alert }
- Validates rule configuration before saving

#### GET `/api/analytics/anomalies/baseline`
- Returns baseline statistics for specified metric
- Query parameters: workspace_id, metric_type
- Used for visualization and threshold setting

### Detection Methods

1. **Z-Score Method**
   - For normally distributed metrics
   - Configurable sensitivity (standard deviations)
   - Fast and interpretable

2. **Isolation Forest**
   - For multivariate anomaly detection
   - Handles non-normal distributions
   - Good for complex patterns

3. **LSTM Autoencoder**
   - For sequential pattern anomalies
   - Learns normal behavior patterns
   - Detects subtle deviations

4. **Custom Thresholds**
   - User-defined rules
   - Business logic based
   - Immediate alerting

### Real-time Processing

```python
class AnomalyStreamProcessor:
    async def process_metric_stream(self, metric_data):
        """Process incoming metrics for anomalies in real-time"""
        # Check against active rules
        # Calculate anomaly scores
        # Trigger alerts if configured
        # Update baseline models incrementally
```

## Implementation Priority
1. Z-score detection for basic metrics
2. Custom threshold rules
3. Real-time alert system
4. Isolation forest for complex patterns
5. LSTM autoencoder for advanced detection

## Success Metrics
- Detection accuracy > 90%
- False positive rate < 5%
- Alert latency < 30 seconds
- Rule configuration time < 2 minutes