-- Migration: Create Predictive Analytics Tables
-- Description: Creates tables for storing ML predictions, model metadata, churn predictions, and feature store
-- Author: Claude Code
-- Date: 2025-11-12

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- PREDICTIONS TABLE
-- Stores all types of predictions with confidence intervals
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics.predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL,
    prediction_type VARCHAR(100) NOT NULL,  -- 'credit_consumption', 'growth', 'error_rate', 'peak_usage'
    target_metric VARCHAR(100) NOT NULL,    -- 'credits', 'dau', 'error_count', etc.
    prediction_date DATE NOT NULL,
    predicted_value DECIMAL(20, 4),
    confidence_lower DECIMAL(20, 4),
    confidence_upper DECIMAL(20, 4),
    confidence_level DECIMAL(3, 2) DEFAULT 0.95,
    model_version VARCHAR(50),
    metadata JSONB DEFAULT '{}'::jsonb,     -- Additional prediction context
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    CONSTRAINT unique_prediction UNIQUE(workspace_id, prediction_type, target_metric, prediction_date)
);

CREATE INDEX idx_predictions_workspace ON analytics.predictions(workspace_id, prediction_type);
CREATE INDEX idx_predictions_date ON analytics.predictions(prediction_date, workspace_id);
CREATE INDEX idx_predictions_type ON analytics.predictions(prediction_type, target_metric);
CREATE INDEX idx_predictions_created ON analytics.predictions(created_at DESC);

-- ============================================================================
-- ML MODELS TABLE
-- Stores metadata about trained models
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics.ml_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255) NOT NULL,
    model_type VARCHAR(100) NOT NULL,       -- 'prophet', 'arima', 'xgboost', 'random_forest', 'ensemble'
    version VARCHAR(50) NOT NULL,
    workspace_id UUID,                       -- NULL for global models
    target_metric VARCHAR(100) NOT NULL,
    training_params JSONB NOT NULL DEFAULT '{}'::jsonb,
    performance_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,  -- MAPE, RMSE, MAE, AUC, etc.
    feature_importance JSONB,
    model_artifacts_path TEXT,              -- Path to serialized model
    training_data_start DATE,
    training_data_end DATE,
    training_record_count INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    CONSTRAINT unique_model_version UNIQUE(model_name, version)
);

CREATE INDEX idx_ml_models_active ON analytics.ml_models(is_active, model_type);
CREATE INDEX idx_ml_models_workspace ON analytics.ml_models(workspace_id, target_metric);
CREATE INDEX idx_ml_models_type ON analytics.ml_models(model_type, target_metric);
CREATE INDEX idx_ml_models_last_used ON analytics.ml_models(last_used_at DESC);

-- ============================================================================
-- CHURN PREDICTIONS TABLE
-- Stores user-level churn predictions
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics.churn_predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL,
    user_id UUID NOT NULL,
    prediction_date DATE NOT NULL,
    churn_probability DECIMAL(5, 4) NOT NULL CHECK (churn_probability >= 0 AND churn_probability <= 1),
    risk_score DECIMAL(5, 2) NOT NULL,      -- 0-100 risk score
    risk_level VARCHAR(20) NOT NULL,        -- 'low', 'medium', 'high', 'critical'
    risk_factors JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommended_actions JSONB DEFAULT '[]'::jsonb,
    days_until_churn INTEGER,
    model_version VARCHAR(50),
    features_used JSONB,                    -- Features used for this prediction
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    CONSTRAINT unique_churn_prediction UNIQUE(workspace_id, user_id, prediction_date)
);

CREATE INDEX idx_churn_risk ON analytics.churn_predictions(workspace_id, risk_score DESC);
CREATE INDEX idx_churn_user ON analytics.churn_predictions(user_id, prediction_date DESC);
CREATE INDEX idx_churn_level ON analytics.churn_predictions(workspace_id, risk_level, prediction_date DESC);
CREATE INDEX idx_churn_date ON analytics.churn_predictions(prediction_date DESC);

-- ============================================================================
-- ML FEATURES TABLE (Feature Store)
-- Stores computed features for ML models
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics.ml_features (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(50) NOT NULL,       -- 'user', 'workspace', 'agent'
    entity_id UUID NOT NULL,
    feature_set VARCHAR(100) NOT NULL,      -- 'behavioral', 'temporal', 'engagement', etc.
    features JSONB NOT NULL,
    computed_at TIMESTAMP NOT NULL,
    version INTEGER DEFAULT 1,
    expires_at TIMESTAMP,                   -- Optional TTL for features

    -- Indexes
    CONSTRAINT unique_features UNIQUE(entity_type, entity_id, feature_set, version)
);

CREATE INDEX idx_ml_features_entity ON analytics.ml_features(entity_type, entity_id, feature_set);
CREATE INDEX idx_ml_features_computed ON analytics.ml_features(computed_at DESC);
CREATE INDEX idx_ml_features_expires ON analytics.ml_features(expires_at) WHERE expires_at IS NOT NULL;

-- ============================================================================
-- PREDICTION PERFORMANCE TABLE
-- Tracks actual vs predicted values for model monitoring
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics.prediction_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prediction_id UUID NOT NULL REFERENCES analytics.predictions(id) ON DELETE CASCADE,
    actual_value DECIMAL(20, 4),
    prediction_error DECIMAL(20, 4),        -- abs(actual - predicted)
    percentage_error DECIMAL(10, 4),        -- MAPE component
    within_confidence_interval BOOLEAN,
    measured_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    UNIQUE(prediction_id)
);

CREATE INDEX idx_prediction_performance_measured ON analytics.prediction_performance(measured_at DESC);
CREATE INDEX idx_prediction_performance_accuracy ON analytics.prediction_performance(within_confidence_interval);

-- ============================================================================
-- WHAT-IF SCENARIOS TABLE
-- Stores what-if scenario analysis results
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics.what_if_scenarios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL,
    scenario_name VARCHAR(255) NOT NULL,
    base_scenario JSONB NOT NULL,          -- Baseline assumptions
    adjustments JSONB NOT NULL,             -- Parameter adjustments
    predictions JSONB NOT NULL,             -- Resulting predictions
    metrics_impact JSONB,                   -- Impact on key metrics
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    UNIQUE(workspace_id, scenario_name, created_at)
);

CREATE INDEX idx_what_if_workspace ON analytics.what_if_scenarios(workspace_id, created_at DESC);

-- ============================================================================
-- MODEL TRAINING JOBS TABLE
-- Tracks model training jobs and their status
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics.model_training_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID REFERENCES analytics.ml_models(id) ON DELETE CASCADE,
    job_status VARCHAR(50) NOT NULL,        -- 'queued', 'running', 'completed', 'failed'
    model_type VARCHAR(100) NOT NULL,
    target_metric VARCHAR(100) NOT NULL,
    training_params JSONB,
    data_start_date DATE,
    data_end_date DATE,
    record_count INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    duration_seconds INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    CHECK (job_status IN ('queued', 'running', 'completed', 'failed'))
);

CREATE INDEX idx_training_jobs_status ON analytics.model_training_jobs(job_status, created_at DESC);
CREATE INDEX idx_training_jobs_model ON analytics.model_training_jobs(model_id);

-- ============================================================================
-- FORECASTING CACHE TABLE
-- Caches expensive forecast computations
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics.forecasting_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cache_key VARCHAR(255) NOT NULL UNIQUE,
    workspace_id UUID NOT NULL,
    prediction_type VARCHAR(100) NOT NULL,
    target_metric VARCHAR(100) NOT NULL,
    forecast_data JSONB NOT NULL,
    parameters JSONB,
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    hit_count INTEGER DEFAULT 0,

    -- Indexes
    CHECK (expires_at > created_at)
);

CREATE INDEX idx_forecasting_cache_workspace ON analytics.forecasting_cache(workspace_id, prediction_type);
CREATE INDEX idx_forecasting_cache_expires ON analytics.forecasting_cache(expires_at);
CREATE INDEX idx_forecasting_cache_key ON analytics.forecasting_cache(cache_key);

-- ============================================================================
-- FUNCTIONS: Update timestamps
-- ============================================================================
CREATE OR REPLACE FUNCTION analytics.update_ml_models_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_ml_models_updated_at
    BEFORE UPDATE ON analytics.ml_models
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_ml_models_updated_at();

-- ============================================================================
-- FUNCTIONS: Auto-expire old forecasting cache
-- ============================================================================
CREATE OR REPLACE FUNCTION analytics.cleanup_expired_forecasting_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM analytics.forecasting_cache
    WHERE expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTIONS: Calculate prediction accuracy
-- ============================================================================
CREATE OR REPLACE FUNCTION analytics.calculate_prediction_accuracy(
    p_workspace_id UUID,
    p_prediction_type VARCHAR,
    p_days_back INTEGER DEFAULT 30
)
RETURNS TABLE(
    prediction_type VARCHAR,
    target_metric VARCHAR,
    total_predictions INTEGER,
    accurate_predictions INTEGER,
    accuracy_rate DECIMAL,
    avg_error DECIMAL,
    avg_percentage_error DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.prediction_type,
        p.target_metric,
        COUNT(*)::INTEGER as total_predictions,
        SUM(CASE WHEN pp.within_confidence_interval THEN 1 ELSE 0 END)::INTEGER as accurate_predictions,
        ROUND(
            100.0 * SUM(CASE WHEN pp.within_confidence_interval THEN 1 ELSE 0 END) / COUNT(*),
            2
        ) as accuracy_rate,
        ROUND(AVG(pp.prediction_error), 4) as avg_error,
        ROUND(AVG(ABS(pp.percentage_error)), 4) as avg_percentage_error
    FROM analytics.predictions p
    JOIN analytics.prediction_performance pp ON p.id = pp.prediction_id
    WHERE p.workspace_id = p_workspace_id
        AND p.prediction_type = p_prediction_type
        AND pp.measured_at >= CURRENT_DATE - p_days_back
    GROUP BY p.prediction_type, p.target_metric;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VIEWS: High-risk churn users
-- ============================================================================
CREATE OR REPLACE VIEW analytics.high_risk_churn_users AS
SELECT
    cp.*,
    u.email,
    u.full_name,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - u.last_active_at)) / 86400 as days_inactive
FROM analytics.churn_predictions cp
LEFT JOIN auth.users u ON cp.user_id = u.id
WHERE cp.risk_level IN ('high', 'critical')
    AND cp.prediction_date = CURRENT_DATE
ORDER BY cp.risk_score DESC;

-- ============================================================================
-- VIEWS: Model performance summary
-- ============================================================================
CREATE OR REPLACE VIEW analytics.model_performance_summary AS
SELECT
    m.model_name,
    m.model_type,
    m.version,
    m.target_metric,
    m.is_active,
    m.performance_metrics,
    COUNT(p.id) as prediction_count,
    MAX(p.created_at) as last_prediction_at,
    m.last_used_at,
    m.created_at as model_created_at
FROM analytics.ml_models m
LEFT JOIN analytics.predictions p ON p.model_version = m.version
GROUP BY m.id, m.model_name, m.model_type, m.version, m.target_metric,
         m.is_active, m.performance_metrics, m.last_used_at, m.created_at
ORDER BY m.is_active DESC, m.last_used_at DESC NULLS LAST;

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE analytics.predictions IS 'Stores all types of predictions with confidence intervals';
COMMENT ON TABLE analytics.ml_models IS 'Metadata about trained ML models';
COMMENT ON TABLE analytics.churn_predictions IS 'User-level churn predictions';
COMMENT ON TABLE analytics.ml_features IS 'Feature store for ML models';
COMMENT ON TABLE analytics.prediction_performance IS 'Tracks prediction accuracy';
COMMENT ON TABLE analytics.what_if_scenarios IS 'What-if scenario analysis results';
COMMENT ON TABLE analytics.model_training_jobs IS 'Model training job tracking';
COMMENT ON TABLE analytics.forecasting_cache IS 'Caches expensive forecast computations';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA analytics TO analytics_service;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA analytics TO analytics_service;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 027: Predictive Analytics Tables created successfully';
END $$;
