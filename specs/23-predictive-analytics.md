# Specification: Predictive Analytics Engine

## Overview
Implement machine learning models to predict future metrics including credit consumption, user churn, error rates, and growth trajectories.

## Technical Requirements

### Backend Implementation

#### Service: `services/predictive_analytics.py`
```python
class PredictiveAnalytics:
    def __init__(self):
        self.models = {}
        self.feature_extractors = {}
    
    async def predict_credit_consumption(
        self,
        workspace_id: str,
        days_ahead: int = 30
    ):
        """
        Predict future credit consumption using ARIMA/Prophet
        Returns daily predictions with confidence intervals
        """
    
    async def predict_user_churn(
        self,
        workspace_id: str,
        users: List[str] = None
    ):
        """
        Predict probability of user churn in next 30 days
        Uses gradient boosting with behavioral features
        """
    
    async def predict_growth_metrics(
        self,
        workspace_id: str,
        metric: str,
        horizon_days: int = 90
    ):
        """
        Predict growth trajectory for DAU/WAU/MAU
        Uses ensemble of time-series models
        """
    
    async def predict_peak_usage(
        self,
        workspace_id: str,
        granularity: str = "hourly"
    ):
        """
        Predict peak usage times and capacity needs
        Helps with resource planning
        """
    
    async def predict_error_rates(
        self,
        workspace_id: str,
        agent_id: str = None
    ):
        """
        Predict future error rates based on patterns
        Identifies potential issues before they escalate
        """
    
    def extract_features(
        self,
        data: pd.DataFrame,
        feature_set: str
    ):
        """
        Extract features for ML models
        Handles time-series and behavioral features
        """
    
    async def train_model(
        self,
        model_type: str,
        training_data: pd.DataFrame,
        hyperparameters: dict = None
    ):
        """
        Train predictive model with cross-validation
        Stores model artifacts for serving
        """

#### Database Schema
```sql
-- Predictions storage
CREATE TABLE analytics.predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL,
    prediction_type VARCHAR(100) NOT NULL,
    target_metric VARCHAR(100) NOT NULL,
    prediction_date DATE NOT NULL,
    predicted_value DECIMAL,
    confidence_lower DECIMAL,
    confidence_upper DECIMAL,
    confidence_level DECIMAL DEFAULT 0.95,
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_predictions_workspace (workspace_id, prediction_type),
    INDEX idx_predictions_date (prediction_date, workspace_id),
    UNIQUE(workspace_id, prediction_type, target_metric, prediction_date)
);

-- Model metadata
CREATE TABLE analytics.ml_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255) NOT NULL,
    model_type VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    workspace_id UUID,
    target_metric VARCHAR(100) NOT NULL,
    training_params JSONB NOT NULL,
    performance_metrics JSONB NOT NULL,
    feature_importance JSONB,
    model_artifacts_path TEXT,
    training_data_start DATE,
    training_data_end DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    
    UNIQUE(model_name, version)
);

-- Churn predictions
CREATE TABLE analytics.churn_predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL,
    user_id UUID NOT NULL,
    prediction_date DATE NOT NULL,
    churn_probability DECIMAL NOT NULL,
    risk_score DECIMAL NOT NULL,
    risk_factors JSONB NOT NULL,
    recommended_actions JSONB,
    days_until_churn INTEGER,
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_churn_risk (workspace_id, risk_score DESC),
    INDEX idx_churn_user (user_id, prediction_date DESC)
);

-- Feature store
CREATE TABLE analytics.ml_features (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(50) NOT NULL, -- 'user', 'workspace', 'agent'
    entity_id UUID NOT NULL,
    feature_set VARCHAR(100) NOT NULL,
    features JSONB NOT NULL,
    computed_at TIMESTAMP NOT NULL,
    version INTEGER DEFAULT 1,
    
    INDEX idx_features_entity (entity_type, entity_id),
    UNIQUE(entity_type, entity_id, feature_set, version)
);
```

### Frontend Components

#### Component: `components/analytics/PredictiveAnalyticsDashboard.tsx`
```typescript
interface PredictiveAnalyticsDashboardProps {
    workspaceId: string;
    predictionHorizon: number;
}

export function PredictiveAnalyticsDashboard({
    workspaceId,
    predictionHorizon
}: PredictiveAnalyticsDashboardProps) {
    // Forecast visualizations
    // Churn risk dashboard
    // Growth projections
    // Capacity planning view
    
    return (
        <div className="predictive-dashboard">
            <PredictionSummaryCards />
            <ConsumptionForecast />
            <ChurnRiskMatrix />
            <GrowthProjections />
            <CapacityPlanning />
        </div>
    );
}

interface ConsumptionForecastProps {
    predictions: PredictionData[];
    historical: HistoricalData[];
}

export function ConsumptionForecast({
    predictions,
    historical
}: ConsumptionForecastProps) {
    // Line chart with historical data and predictions
    // Confidence intervals shaded
    // Interactive hover for details
    // Scenario adjustment controls
}

interface ChurnRiskMatrixProps {
    users: UserChurnRisk[];
    onUserSelect: (userId: string) => void;
}

export function ChurnRiskMatrix({
    users,
    onUserSelect
}: ChurnRiskMatrixProps) {
    // Heatmap of users by churn risk
    // Sortable by risk factors
    // Click for detailed analysis
    // Bulk action capabilities
}

interface GrowthProjectionsProps {
    metrics: GrowthMetric[];
    scenarios: GrowthScenario[];
}

export function GrowthProjections({
    metrics,
    scenarios
}: GrowthProjectionsProps) {
    // Multiple growth scenarios
    // Best/worst/likely cases
    // Milestone predictions
    // Goal tracking overlay
}
```

### API Endpoints

#### GET `/api/analytics/predictions/consumption`
- Query parameters: workspace_id, days_ahead, granularity
- Returns consumption predictions with confidence intervals
- Includes breakdown by feature/service

#### GET `/api/analytics/predictions/churn`
- Query parameters: workspace_id, risk_threshold, limit
- Returns users with churn risk scores
- Includes risk factors and recommended interventions

#### POST `/api/analytics/predictions/generate`
- Request body: { prediction_type, target_metric, horizon, parameters }
- Generates new predictions on-demand
- Returns prediction ID for async tracking

#### GET `/api/analytics/predictions/growth`
- Query parameters: workspace_id, metric, horizon_days
- Returns growth projections with scenarios
- Includes milestone predictions

#### POST `/api/analytics/predictions/what-if`
- Request body: { base_scenario, adjustments, metrics }
- Runs what-if analysis with adjusted parameters
- Returns impact on predictions

### Machine Learning Models

1. **Time-Series Forecasting**
   - Prophet for seasonal patterns
   - ARIMA for trend analysis
   - LSTM for complex sequences
   - Ensemble for robustness

2. **Classification Models**
   - XGBoost for churn prediction
   - Random Forest for risk scoring
   - Logistic Regression for interpretability
   - Neural networks for complex patterns

3. **Feature Engineering**
   - Lag features (1d, 7d, 30d)
   - Rolling statistics
   - Seasonal decomposition
   - Behavioral sequences
   - Interaction features

4. **Model Management**
   - A/B testing framework
   - Champion/challenger setup
   - Automated retraining
   - Performance monitoring

### Implementation Example

```python
class CreditConsumptionPredictor:
    async def predict(self, workspace_id: str, days_ahead: int):
        # Load historical data
        data = await self.load_historical_data(workspace_id)
        
        # Feature engineering
        features = self.engineer_features(data)
        
        # Load or train model
        model = await self.get_model(workspace_id)
        
        # Generate predictions
        predictions = model.predict(features, periods=days_ahead)
        
        # Calculate confidence intervals
        intervals = self.calculate_intervals(predictions, model)
        
        # Store and return
        await self.store_predictions(predictions, intervals)
        return predictions
```

## Implementation Priority
1. Credit consumption forecasting
2. User churn prediction
3. Growth metric projections
4. Error rate predictions
5. Advanced what-if scenarios

## Success Metrics
- Prediction accuracy (MAPE) < 10%
- Churn prediction AUC > 0.85
- Model training time < 5 minutes
- Prediction latency < 500ms