-- Migration: Agent Lifecycle Analytics Tables
-- Description: Track agent lifecycle states, transitions, versions, deployments, and health metrics
-- Author: Claude Code
-- Date: 2025-11-13

-- ============================================================================
-- 1. Agent Lifecycle Events Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics.agent_lifecycle_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,

    -- Event information
    event_type VARCHAR(100) NOT NULL,  -- state_change, version_release, deployment, etc.
    previous_state VARCHAR(50),
    new_state VARCHAR(50),

    -- Metadata
    triggered_by VARCHAR(100),  -- user_id, system, api, automation
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_state_change CHECK (
        previous_state IS NULL OR previous_state != new_state
    )
);

-- Indexes for agent_lifecycle_events
CREATE INDEX idx_lifecycle_events_agent_time
    ON analytics.agent_lifecycle_events(agent_id, timestamp DESC);
CREATE INDEX idx_lifecycle_events_workspace_time
    ON analytics.agent_lifecycle_events(workspace_id, timestamp DESC);
CREATE INDEX idx_lifecycle_events_type
    ON analytics.agent_lifecycle_events(event_type);
CREATE INDEX idx_lifecycle_events_state
    ON analytics.agent_lifecycle_events(new_state);
CREATE INDEX idx_lifecycle_events_timestamp USING BRIN (timestamp);

-- ============================================================================
-- 2. Agent Versions Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics.agent_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,

    -- Version information
    version VARCHAR(50) NOT NULL,
    version_number INTEGER NOT NULL,  -- Numeric sequence for ordering
    description TEXT,
    changelog TEXT,

    -- Version metadata
    capabilities_added JSONB DEFAULT '[]',
    capabilities_removed JSONB DEFAULT '[]',
    capabilities_modified JSONB DEFAULT '[]',

    -- Performance impact
    performance_impact JSONB DEFAULT '{}',  -- speed_change, accuracy_change, cost_change

    -- Complexity metrics
    lines_of_code INTEGER,
    cyclomatic_complexity FLOAT,
    cognitive_complexity FLOAT,
    dependencies_count INTEGER,

    -- Status
    status VARCHAR(50) DEFAULT 'draft',  -- draft, testing, staging, production, deprecated
    is_active BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    released_at TIMESTAMPTZ,
    deprecated_at TIMESTAMPTZ,

    -- Constraints
    UNIQUE(agent_id, version),
    UNIQUE(agent_id, version_number)
);

-- Indexes for agent_versions
CREATE INDEX idx_agent_versions_agent
    ON analytics.agent_versions(agent_id, version_number DESC);
CREATE INDEX idx_agent_versions_workspace
    ON analytics.agent_versions(workspace_id);
CREATE INDEX idx_agent_versions_status
    ON analytics.agent_versions(status);
CREATE INDEX idx_agent_versions_active
    ON analytics.agent_versions(agent_id, is_active) WHERE is_active = TRUE;

-- ============================================================================
-- 3. Agent Deployments Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics.agent_deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    version_id UUID REFERENCES analytics.agent_versions(id) ON DELETE CASCADE,

    -- Deployment information
    deployment_type VARCHAR(50),  -- canary, blue_green, rolling, direct
    environment VARCHAR(50),  -- development, staging, production

    -- Deployment metadata
    deployment_strategy JSONB DEFAULT '{}',
    rollout_percentage INTEGER DEFAULT 100,

    -- Status
    status VARCHAR(50) DEFAULT 'pending',  -- pending, in_progress, completed, failed, rolled_back

    -- Timing
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,

    -- Results
    success_metrics JSONB DEFAULT '{}',
    failure_reason TEXT,
    rollback_from UUID REFERENCES analytics.agent_deployments(id),

    -- Triggered by
    triggered_by VARCHAR(100),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for agent_deployments
CREATE INDEX idx_deployments_agent_time
    ON analytics.agent_deployments(agent_id, started_at DESC);
CREATE INDEX idx_deployments_workspace
    ON analytics.agent_deployments(workspace_id);
CREATE INDEX idx_deployments_version
    ON analytics.agent_deployments(version_id);
CREATE INDEX idx_deployments_status
    ON analytics.agent_deployments(status);
CREATE INDEX idx_deployments_environment
    ON analytics.agent_deployments(environment);

-- ============================================================================
-- 4. Agent Health Scores Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics.agent_health_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,

    -- Overall score
    overall_score FLOAT NOT NULL,  -- 0-100
    health_status VARCHAR(50),  -- excellent, good, fair, poor, critical

    -- Component scores
    performance_score FLOAT,
    reliability_score FLOAT,
    usage_score FLOAT,
    maintenance_score FLOAT,
    cost_score FLOAT,

    -- Detailed metrics
    component_scores JSONB DEFAULT '{}',
    improvement_recommendations JSONB DEFAULT '[]',

    -- Trend
    trend VARCHAR(20),  -- improving, stable, declining
    previous_score FLOAT,
    score_change FLOAT,

    -- Timestamp
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    calculation_period_start TIMESTAMPTZ,
    calculation_period_end TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for agent_health_scores
CREATE INDEX idx_health_scores_agent_time
    ON analytics.agent_health_scores(agent_id, calculated_at DESC);
CREATE INDEX idx_health_scores_workspace
    ON analytics.agent_health_scores(workspace_id);
CREATE INDEX idx_health_scores_status
    ON analytics.agent_health_scores(health_status);
CREATE INDEX idx_health_scores_score
    ON analytics.agent_health_scores(overall_score DESC);

-- ============================================================================
-- 5. Agent Retirement Candidates Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics.agent_retirement_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,

    -- Retirement metrics
    days_since_last_use INTEGER,
    total_executions_30d INTEGER DEFAULT 0,
    recent_avg_rating FLOAT,
    active_users_30d INTEGER DEFAULT 0,
    dependent_agents_count INTEGER DEFAULT 0,

    -- Priority
    retirement_priority VARCHAR(20),  -- low, medium, high, critical
    retirement_score FLOAT,

    -- Recommended replacement
    recommended_replacement_id UUID,
    migration_effort VARCHAR(20),  -- low, medium, high

    -- Migration planning
    affected_workflows JSONB DEFAULT '[]',
    estimated_migration_days INTEGER,
    risk_assessment JSONB DEFAULT '{}',

    -- Status
    status VARCHAR(50) DEFAULT 'candidate',  -- candidate, approved, in_migration, retired

    -- Timestamps
    identified_at TIMESTAMPTZ DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(agent_id, identified_at)
);

-- Indexes for agent_retirement_candidates
CREATE INDEX idx_retirement_candidates_workspace
    ON analytics.agent_retirement_candidates(workspace_id);
CREATE INDEX idx_retirement_candidates_priority
    ON analytics.agent_retirement_candidates(retirement_priority, retirement_score DESC);
CREATE INDEX idx_retirement_candidates_status
    ON analytics.agent_retirement_candidates(status);

-- ============================================================================
-- 6. Version Performance Comparison View
-- ============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.agent_version_performance AS
SELECT
    av.id as version_id,
    av.agent_id,
    av.workspace_id,
    av.version,
    av.version_number,
    av.released_at as version_released,
    av.status as version_status,

    -- Execution metrics
    COUNT(DISTINCT ar.id) as total_executions,
    AVG(ar.runtime_seconds) as avg_duration,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ar.runtime_seconds) as p50_duration,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ar.runtime_seconds) as p95_duration,

    -- Success metrics
    COUNT(*) FILTER (WHERE ar.status = 'completed') as successful_executions,
    COUNT(*) FILTER (WHERE ar.status = 'failed') as failed_executions,
    CASE
        WHEN COUNT(*) > 0
        THEN COUNT(*) FILTER (WHERE ar.status = 'completed')::float / COUNT(*)::float
        ELSE 0
    END as success_rate,

    -- Resource metrics
    AVG(ar.credits_consumed) as avg_credits,
    SUM(ar.credits_consumed) as total_credits,
    AVG(ar.tokens_used) as avg_tokens,
    SUM(ar.tokens_used) as total_tokens,

    -- User metrics
    AVG(ar.user_rating) as avg_rating,
    COUNT(DISTINCT ar.user_id) as unique_users,

    -- Errors
    COUNT(DISTINCT ae.id) as error_count,

    -- Last updated
    NOW() as last_refreshed
FROM analytics.agent_versions av
LEFT JOIN analytics.agent_runs ar
    ON ar.agent_id = av.agent_id
    AND ar.started_at >= av.released_at
    AND (av.deprecated_at IS NULL OR ar.started_at < av.deprecated_at)
LEFT JOIN analytics.agent_errors ae
    ON ae.agent_id = av.agent_id
    AND ae.occurred_at >= av.released_at
    AND (av.deprecated_at IS NULL OR ae.occurred_at < av.deprecated_at)
WHERE av.released_at IS NOT NULL
GROUP BY
    av.id, av.agent_id, av.workspace_id, av.version,
    av.version_number, av.released_at, av.status;

-- Indexes for materialized view
CREATE UNIQUE INDEX idx_version_performance_version
    ON analytics.agent_version_performance(version_id);
CREATE INDEX idx_version_performance_agent
    ON analytics.agent_version_performance(agent_id, version_number DESC);
CREATE INDEX idx_version_performance_workspace
    ON analytics.agent_version_performance(workspace_id);

-- ============================================================================
-- 7. Agent Lifecycle Summary View
-- ============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.agent_lifecycle_summary AS
WITH current_states AS (
    SELECT DISTINCT ON (agent_id)
        agent_id,
        workspace_id,
        new_state as current_state,
        timestamp as current_state_since,
        triggered_by
    FROM analytics.agent_lifecycle_events
    WHERE event_type = 'state_change'
    ORDER BY agent_id, timestamp DESC
),
state_durations AS (
    SELECT
        agent_id,
        new_state as state,
        AVG(EXTRACT(EPOCH FROM (
            LEAD(timestamp) OVER (PARTITION BY agent_id ORDER BY timestamp) - timestamp
        ))) as avg_duration_seconds,
        COUNT(*) as occurrence_count
    FROM analytics.agent_lifecycle_events
    WHERE event_type = 'state_change' AND new_state IS NOT NULL
    GROUP BY agent_id, new_state
),
transition_counts AS (
    SELECT
        agent_id,
        COUNT(*) as total_transitions,
        MIN(timestamp) as first_transition,
        MAX(timestamp) as last_transition
    FROM analytics.agent_lifecycle_events
    WHERE event_type = 'state_change'
    GROUP BY agent_id
),
version_counts AS (
    SELECT
        agent_id,
        COUNT(*) as total_versions,
        COUNT(*) FILTER (WHERE status = 'production') as production_versions,
        MAX(version_number) as latest_version_number
    FROM analytics.agent_versions
    GROUP BY agent_id
),
deployment_counts AS (
    SELECT
        agent_id,
        COUNT(*) as total_deployments,
        COUNT(*) FILTER (WHERE status = 'completed') as successful_deployments,
        COUNT(*) FILTER (WHERE status = 'failed') as failed_deployments,
        COUNT(*) FILTER (WHERE status = 'rolled_back') as rollback_count,
        MAX(started_at) as last_deployment
    FROM analytics.agent_deployments
    GROUP BY agent_id
)
SELECT
    cs.agent_id,
    cs.workspace_id,
    cs.current_state,
    cs.current_state_since,
    EXTRACT(EPOCH FROM (NOW() - cs.current_state_since)) / 86400 as days_in_current_state,

    -- Lifecycle metrics
    tc.total_transitions,
    tc.first_transition as lifecycle_started,
    tc.last_transition as last_state_change,
    EXTRACT(EPOCH FROM (NOW() - tc.first_transition)) / 86400 as total_lifecycle_days,

    -- Version metrics
    COALESCE(vc.total_versions, 0) as total_versions,
    COALESCE(vc.production_versions, 0) as production_versions,
    COALESCE(vc.latest_version_number, 0) as latest_version_number,

    -- Deployment metrics
    COALESCE(dc.total_deployments, 0) as total_deployments,
    COALESCE(dc.successful_deployments, 0) as successful_deployments,
    COALESCE(dc.failed_deployments, 0) as failed_deployments,
    COALESCE(dc.rollback_count, 0) as rollback_count,
    dc.last_deployment,
    CASE
        WHEN dc.total_deployments > 0
        THEN dc.successful_deployments::float / dc.total_deployments::float
        ELSE 0
    END as deployment_success_rate,

    -- State duration aggregates
    (
        SELECT jsonb_object_agg(state, avg_duration_seconds)
        FROM state_durations sd
        WHERE sd.agent_id = cs.agent_id
    ) as avg_state_durations,

    NOW() as last_refreshed
FROM current_states cs
LEFT JOIN transition_counts tc ON tc.agent_id = cs.agent_id
LEFT JOIN version_counts vc ON vc.agent_id = cs.agent_id
LEFT JOIN deployment_counts dc ON dc.agent_id = cs.agent_id;

-- Indexes for materialized view
CREATE UNIQUE INDEX idx_lifecycle_summary_agent
    ON analytics.agent_lifecycle_summary(agent_id);
CREATE INDEX idx_lifecycle_summary_workspace
    ON analytics.agent_lifecycle_summary(workspace_id);
CREATE INDEX idx_lifecycle_summary_state
    ON analytics.agent_lifecycle_summary(current_state);

-- ============================================================================
-- 8. Functions for refreshing materialized views
-- ============================================================================

-- Function to refresh agent version performance view
CREATE OR REPLACE FUNCTION analytics.refresh_agent_version_performance()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.agent_version_performance;
END;
$$ LANGUAGE plpgsql;

-- Function to refresh agent lifecycle summary view
CREATE OR REPLACE FUNCTION analytics.refresh_agent_lifecycle_summary()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.agent_lifecycle_summary;
END;
$$ LANGUAGE plpgsql;

-- Function to refresh all lifecycle views
CREATE OR REPLACE FUNCTION analytics.refresh_all_lifecycle_views()
RETURNS VOID AS $$
BEGIN
    PERFORM analytics.refresh_agent_version_performance();
    PERFORM analytics.refresh_agent_lifecycle_summary();
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 9. Helper function to record lifecycle events
-- ============================================================================

CREATE OR REPLACE FUNCTION analytics.record_lifecycle_event(
    p_agent_id UUID,
    p_workspace_id UUID,
    p_event_type VARCHAR,
    p_previous_state VARCHAR DEFAULT NULL,
    p_new_state VARCHAR DEFAULT NULL,
    p_triggered_by VARCHAR DEFAULT 'system',
    p_metadata JSONB DEFAULT '{}'
)
RETURNS UUID AS $$
DECLARE
    v_event_id UUID;
BEGIN
    INSERT INTO analytics.agent_lifecycle_events (
        agent_id,
        workspace_id,
        event_type,
        previous_state,
        new_state,
        triggered_by,
        metadata,
        timestamp
    ) VALUES (
        p_agent_id,
        p_workspace_id,
        p_event_type,
        p_previous_state,
        p_new_state,
        p_triggered_by,
        p_metadata,
        NOW()
    )
    RETURNING id INTO v_event_id;

    RETURN v_event_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 10. Comments for documentation
-- ============================================================================

COMMENT ON TABLE analytics.agent_lifecycle_events IS 'Tracks all lifecycle events for agents including state changes, deployments, and version releases';
COMMENT ON TABLE analytics.agent_versions IS 'Stores version history and metadata for agents';
COMMENT ON TABLE analytics.agent_deployments IS 'Tracks deployment events and outcomes for agent versions';
COMMENT ON TABLE analytics.agent_health_scores IS 'Historical record of agent health score calculations';
COMMENT ON TABLE analytics.agent_retirement_candidates IS 'Identifies and tracks agents that are candidates for retirement';

COMMENT ON MATERIALIZED VIEW analytics.agent_version_performance IS 'Pre-aggregated performance metrics per agent version for fast comparison queries';
COMMENT ON MATERIALIZED VIEW analytics.agent_lifecycle_summary IS 'Comprehensive lifecycle summary for each agent including current state and key metrics';

-- ============================================================================
-- End of migration
-- ============================================================================
