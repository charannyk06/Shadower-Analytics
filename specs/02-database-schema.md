# Specification: Database Schema

## Feature Overview
Complete PostgreSQL database schema for the analytics system using a separate `analytics` schema within the existing Supabase instance.

## Technical Requirements
- Separate `analytics` schema namespace
- Read-only access to `public` schema (main app)
- Materialized views for performance
- Time-series optimized tables
- Efficient indexing strategy

## Implementation Details

### Schema Creation
```sql
-- Create analytics schema
CREATE SCHEMA IF NOT EXISTS analytics;

-- Grant permissions
GRANT USAGE ON SCHEMA analytics TO authenticated;
GRANT CREATE ON SCHEMA analytics TO service_role;
```

### Core Tables

#### 1. User Activity Tracking
```sql
CREATE TABLE analytics.user_activity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id),
    workspace_id UUID REFERENCES public.workspaces(id),
    event_type VARCHAR(50) NOT NULL,
    event_name VARCHAR(100),
    page_path VARCHAR(255),
    session_id UUID,
    ip_address INET,
    user_agent TEXT,
    referrer TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_event_type CHECK (
        event_type IN (
            'page_view', 'agent_run', 'login', 'logout',
            'workspace_switch', 'feature_use', 'error',
            'api_call', 'export', 'report_view'
        )
    )
);

-- Indexes
CREATE INDEX idx_user_activity_user_time 
    ON analytics.user_activity(user_id, created_at DESC);
CREATE INDEX idx_user_activity_workspace_time 
    ON analytics.user_activity(workspace_id, created_at DESC);
CREATE INDEX idx_user_activity_event_type 
    ON analytics.user_activity(event_type, created_at DESC);
CREATE INDEX idx_user_activity_session 
    ON analytics.user_activity(session_id);
CREATE INDEX idx_user_activity_metadata 
    ON analytics.user_activity USING gin(metadata);
```

#### 2. Daily Metrics Rollup
```sql
CREATE TABLE analytics.daily_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_date DATE NOT NULL,
    workspace_id UUID REFERENCES public.workspaces(id),
    
    -- User metrics
    total_users INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0,
    returning_users INTEGER DEFAULT 0,
    
    -- Session metrics
    total_sessions INTEGER DEFAULT 0,
    avg_session_duration_seconds NUMERIC(10,2),
    bounce_rate NUMERIC(5,2),
    
    -- Execution metrics
    total_runs INTEGER DEFAULT 0,
    successful_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    cancelled_runs INTEGER DEFAULT 0,
    avg_runtime_seconds NUMERIC(10,2),
    median_runtime_seconds NUMERIC(10,2),
    p95_runtime_seconds NUMERIC(10,2),
    p99_runtime_seconds NUMERIC(10,2),
    
    -- Credit metrics
    total_credits_consumed NUMERIC(15,2) DEFAULT 0,
    avg_credits_per_run NUMERIC(10,2),
    credits_by_model JSONB DEFAULT '{}',
    
    -- Agent metrics
    unique_agents_run INTEGER DEFAULT 0,
    top_agents JSONB DEFAULT '[]',
    
    -- Error metrics
    total_errors INTEGER DEFAULT 0,
    error_rate NUMERIC(5,2),
    errors_by_type JSONB DEFAULT '{}',
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_daily_metric UNIQUE(metric_date, workspace_id)
);

-- Indexes
CREATE INDEX idx_daily_metrics_date 
    ON analytics.daily_metrics(metric_date DESC);
CREATE INDEX idx_daily_metrics_workspace 
    ON analytics.daily_metrics(workspace_id, metric_date DESC);
```

#### 3. Hourly Metrics (For Real-time)
```sql
CREATE TABLE analytics.hourly_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_hour TIMESTAMPTZ NOT NULL,
    workspace_id UUID REFERENCES public.workspaces(id),
    
    -- Real-time counters
    active_users INTEGER DEFAULT 0,
    total_runs INTEGER DEFAULT 0,
    successful_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    total_credits NUMERIC(10,2) DEFAULT 0,
    
    -- Performance
    avg_response_time_ms INTEGER,
    p95_response_time_ms INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_hourly_metric UNIQUE(metric_hour, workspace_id)
);

-- Indexes
CREATE INDEX idx_hourly_metrics_hour 
    ON analytics.hourly_metrics(metric_hour DESC);
CREATE INDEX idx_hourly_metrics_workspace 
    ON analytics.hourly_metrics(workspace_id, metric_hour DESC);
```

#### 4. Agent Performance
```sql
CREATE TABLE analytics.agent_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES public.agents(id),
    metric_date DATE NOT NULL,
    workspace_id UUID REFERENCES public.workspaces(id),
    
    -- Execution stats
    total_runs INTEGER DEFAULT 0,
    successful_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    cancelled_runs INTEGER DEFAULT 0,
    
    -- Performance metrics
    avg_runtime_seconds NUMERIC(10,2),
    min_runtime_seconds NUMERIC(10,2),
    max_runtime_seconds NUMERIC(10,2),
    p50_runtime_seconds NUMERIC(10,2),
    p75_runtime_seconds NUMERIC(10,2),
    p95_runtime_seconds NUMERIC(10,2),
    p99_runtime_seconds NUMERIC(10,2),
    
    -- Resource usage
    total_credits NUMERIC(15,2) DEFAULT 0,
    avg_credits_per_run NUMERIC(10,2),
    total_tokens_used INTEGER DEFAULT 0,
    avg_tokens_per_run INTEGER,
    
    -- User interaction
    unique_users INTEGER DEFAULT 0,
    avg_user_rating NUMERIC(3,2),
    total_feedback_count INTEGER DEFAULT 0,
    
    -- Error tracking
    error_types JSONB DEFAULT '{}',
    common_failure_reasons JSONB DEFAULT '[]',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_agent_performance UNIQUE(agent_id, metric_date)
);

-- Indexes
CREATE INDEX idx_agent_performance_agent 
    ON analytics.agent_performance(agent_id, metric_date DESC);
CREATE INDEX idx_agent_performance_date 
    ON analytics.agent_performance(metric_date DESC);
CREATE INDEX idx_agent_performance_workspace 
    ON analytics.agent_performance(workspace_id, metric_date DESC);
```

#### 5. User Cohorts
```sql
CREATE TABLE analytics.user_cohorts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cohort_period VARCHAR(20) NOT NULL, -- 'daily', 'weekly', 'monthly'
    cohort_date DATE NOT NULL,
    workspace_id UUID REFERENCES public.workspaces(id),
    
    -- Cohort data
    initial_users INTEGER NOT NULL,
    retention_data JSONB NOT NULL, -- {"day_1": 95, "day_7": 80, ...}
    
    -- Metrics
    ltv_estimate NUMERIC(10,2),
    avg_revenue_per_user NUMERIC(10,2),
    churn_rate NUMERIC(5,2),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_cohort UNIQUE(cohort_period, cohort_date, workspace_id)
);

-- Indexes
CREATE INDEX idx_user_cohorts_date 
    ON analytics.user_cohorts(cohort_date DESC);
CREATE INDEX idx_user_cohorts_workspace 
    ON analytics.user_cohorts(workspace_id, cohort_date DESC);
```

#### 6. Alert Configurations
```sql
CREATE TABLE analytics.alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES public.workspaces(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    
    -- Rule configuration
    metric_type VARCHAR(50) NOT NULL,
    condition VARCHAR(20) NOT NULL, -- 'greater_than', 'less_than', 'equals'
    threshold_value NUMERIC(10,2) NOT NULL,
    evaluation_window_minutes INTEGER DEFAULT 5,
    
    -- Notification settings
    notification_channels JSONB DEFAULT '[]', -- ['email', 'slack', 'webhook']
    notification_recipients JSONB DEFAULT '[]',
    
    -- State tracking
    last_triggered_at TIMESTAMPTZ,
    trigger_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES public.users(id)
);

-- Indexes
CREATE INDEX idx_alert_rules_workspace 
    ON analytics.alert_rules(workspace_id);
CREATE INDEX idx_alert_rules_active 
    ON analytics.alert_rules(is_active) WHERE is_active = true;
```

#### 7. Alert History
```sql
CREATE TABLE analytics.alert_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_rule_id UUID REFERENCES analytics.alert_rules(id),
    workspace_id UUID REFERENCES public.workspaces(id),
    
    -- Alert details
    triggered_at TIMESTAMPTZ DEFAULT NOW(),
    metric_value NUMERIC(10,2),
    threshold_value NUMERIC(10,2),
    
    -- Notification details
    notifications_sent JSONB DEFAULT '[]',
    notification_status VARCHAR(20) DEFAULT 'pending',
    
    -- Resolution
    acknowledged_by UUID REFERENCES public.users(id),
    acknowledged_at TIMESTAMPTZ,
    notes TEXT
);

-- Indexes
CREATE INDEX idx_alert_history_rule 
    ON analytics.alert_history(alert_rule_id, triggered_at DESC);
CREATE INDEX idx_alert_history_workspace 
    ON analytics.alert_history(workspace_id, triggered_at DESC);
```

### Materialized Views

#### 1. Active Users Summary
```sql
CREATE MATERIALIZED VIEW analytics.mv_active_users AS
WITH user_activity AS (
    SELECT 
        DATE(created_at) as activity_date,
        user_id,
        workspace_id
    FROM analytics.user_activity
    WHERE created_at >= NOW() - INTERVAL '90 days'
    
    UNION
    
    SELECT 
        DATE(started_at) as activity_date,
        user_id,
        workspace_id
    FROM public.agent_runs
    WHERE started_at >= NOW() - INTERVAL '90 days'
)
SELECT 
    activity_date,
    workspace_id,
    COUNT(DISTINCT user_id) as daily_active_users,
    COUNT(DISTINCT user_id) FILTER (
        WHERE activity_date >= CURRENT_DATE - INTERVAL '7 days'
    ) as weekly_active_users,
    COUNT(DISTINCT user_id) FILTER (
        WHERE activity_date >= CURRENT_DATE - INTERVAL '30 days'
    ) as monthly_active_users
FROM user_activity
GROUP BY activity_date, workspace_id;

-- Indexes
CREATE UNIQUE INDEX idx_mv_active_users 
    ON analytics.mv_active_users(activity_date, workspace_id);
```

#### 2. Top Performing Agents
```sql
CREATE MATERIALIZED VIEW analytics.mv_top_agents AS
SELECT 
    a.id as agent_id,
    a.name as agent_name,
    a.workspace_id,
    COUNT(ar.id) as total_runs_30d,
    COUNT(ar.id) FILTER (WHERE ar.status = 'completed') as successful_runs_30d,
    COALESCE(
        COUNT(ar.id) FILTER (WHERE ar.status = 'completed')::NUMERIC / 
        NULLIF(COUNT(ar.id), 0) * 100, 
        0
    ) as success_rate,
    AVG(ar.runtime_seconds) as avg_runtime,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ar.runtime_seconds) as median_runtime,
    SUM(ar.credits_consumed) as total_credits_30d,
    COUNT(DISTINCT ar.user_id) as unique_users_30d,
    MAX(ar.started_at) as last_run_at
FROM public.agents a
LEFT JOIN public.agent_runs ar ON a.id = ar.agent_id
WHERE ar.started_at >= NOW() - INTERVAL '30 days'
GROUP BY a.id, a.name, a.workspace_id
ORDER BY total_runs_30d DESC;

-- Indexes
CREATE UNIQUE INDEX idx_mv_top_agents 
    ON analytics.mv_top_agents(agent_id);
CREATE INDEX idx_mv_top_agents_workspace 
    ON analytics.mv_top_agents(workspace_id, total_runs_30d DESC);
```

#### 3. Workspace Summary
```sql
CREATE MATERIALIZED VIEW analytics.mv_workspace_summary AS
SELECT 
    w.id as workspace_id,
    w.name as workspace_name,
    COUNT(DISTINCT u.id) as total_members,
    COUNT(DISTINCT a.id) as total_agents,
    COUNT(DISTINCT ar.id) as total_runs_30d,
    SUM(ar.credits_consumed) as total_credits_30d,
    AVG(ar.runtime_seconds) as avg_runtime_30d,
    COUNT(DISTINCT ar.user_id) as active_users_30d
FROM public.workspaces w
LEFT JOIN public.workspace_members wm ON w.id = wm.workspace_id
LEFT JOIN public.users u ON wm.user_id = u.id
LEFT JOIN public.agents a ON w.id = a.workspace_id
LEFT JOIN public.agent_runs ar ON a.id = ar.agent_id 
    AND ar.started_at >= NOW() - INTERVAL '30 days'
GROUP BY w.id, w.name;

-- Indexes
CREATE UNIQUE INDEX idx_mv_workspace_summary 
    ON analytics.mv_workspace_summary(workspace_id);
```

### Functions and Procedures

#### 1. Refresh All Materialized Views
```sql
CREATE OR REPLACE FUNCTION analytics.refresh_all_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_active_users;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_top_agents;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_workspace_summary;
END;
$$ LANGUAGE plpgsql;
```

#### 2. Calculate Percentiles
```sql
CREATE OR REPLACE FUNCTION analytics.calculate_percentiles(
    values NUMERIC[],
    percentiles NUMERIC[]
)
RETURNS NUMERIC[] AS $$
DECLARE
    result NUMERIC[];
    p NUMERIC;
BEGIN
    FOREACH p IN ARRAY percentiles LOOP
        result := array_append(
            result, 
            PERCENTILE_CONT(p) WITHIN GROUP (ORDER BY unnest(values))
        );
    END LOOP;
    RETURN result;
END;
$$ LANGUAGE plpgsql;
```

#### 3. Aggregate Daily Metrics
```sql
CREATE OR REPLACE FUNCTION analytics.aggregate_daily_metrics(
    target_date DATE,
    target_workspace_id UUID DEFAULT NULL
)
RETURNS void AS $$
BEGIN
    INSERT INTO analytics.daily_metrics (
        metric_date,
        workspace_id,
        total_users,
        active_users,
        total_runs,
        successful_runs,
        failed_runs,
        avg_runtime_seconds,
        total_credits_consumed
    )
    SELECT 
        target_date,
        workspace_id,
        COUNT(DISTINCT user_id),
        COUNT(DISTINCT CASE 
            WHEN last_activity >= target_date 
            THEN user_id 
        END),
        COUNT(*),
        COUNT(*) FILTER (WHERE status = 'completed'),
        COUNT(*) FILTER (WHERE status = 'failed'),
        AVG(runtime_seconds),
        SUM(credits_consumed)
    FROM public.agent_runs
    WHERE DATE(started_at) = target_date
        AND (target_workspace_id IS NULL OR workspace_id = target_workspace_id)
    GROUP BY workspace_id
    ON CONFLICT (metric_date, workspace_id)
    DO UPDATE SET
        total_users = EXCLUDED.total_users,
        active_users = EXCLUDED.active_users,
        total_runs = EXCLUDED.total_runs,
        successful_runs = EXCLUDED.successful_runs,
        failed_runs = EXCLUDED.failed_runs,
        avg_runtime_seconds = EXCLUDED.avg_runtime_seconds,
        total_credits_consumed = EXCLUDED.total_credits_consumed,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;
```

### Triggers

#### 1. Update Timestamp Trigger
```sql
CREATE OR REPLACE FUNCTION analytics.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to tables
CREATE TRIGGER update_daily_metrics_updated_at
    BEFORE UPDATE ON analytics.daily_metrics
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_updated_at();

CREATE TRIGGER update_agent_performance_updated_at
    BEFORE UPDATE ON analytics.agent_performance
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_updated_at();
```

### Indexes Strategy

#### Time-based Indexes
```sql
-- Partition-friendly indexes
CREATE INDEX idx_user_activity_created_at_brin 
    ON analytics.user_activity USING brin(created_at);

CREATE INDEX idx_daily_metrics_date_brin 
    ON analytics.daily_metrics USING brin(metric_date);
```

#### Composite Indexes
```sql
-- Most common query patterns
CREATE INDEX idx_user_activity_composite 
    ON analytics.user_activity(workspace_id, user_id, created_at DESC);

CREATE INDEX idx_agent_performance_composite 
    ON analytics.agent_performance(workspace_id, metric_date DESC, total_runs DESC);
```

### Data Retention Policy
```sql
-- Function to clean old data
CREATE OR REPLACE FUNCTION analytics.cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Keep raw activity for 90 days
    DELETE FROM analytics.user_activity 
    WHERE created_at < NOW() - INTERVAL '90 days';
    
    -- Keep hourly metrics for 30 days
    DELETE FROM analytics.hourly_metrics 
    WHERE metric_hour < NOW() - INTERVAL '30 days';
    
    -- Keep daily metrics forever (or archive after 2 years)
    -- Archive logic here if needed
END;
$$ LANGUAGE plpgsql;
```

### Row-Level Security
```sql
-- Enable RLS
ALTER TABLE analytics.daily_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.agent_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.user_activity ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY workspace_isolation_daily_metrics ON analytics.daily_metrics
    FOR ALL
    USING (workspace_id IN (
        SELECT workspace_id 
        FROM public.workspace_members 
        WHERE user_id = auth.uid()
    ));

CREATE POLICY workspace_isolation_agent_performance ON analytics.agent_performance
    FOR ALL
    USING (workspace_id IN (
        SELECT workspace_id 
        FROM public.workspace_members 
        WHERE user_id = auth.uid()
    ));
```

## Testing Requirements
- Test data generation scripts
- Performance benchmarks for queries
- Index effectiveness validation
- Materialized view refresh timing

## Performance Targets
- Query response time: <100ms for indexed queries
- Materialized view refresh: <30 seconds
- Daily aggregation job: <5 minutes
- Storage growth: <1GB per month per workspace

## Security Considerations
- Row-level security for multi-tenancy
- Read-only access for analytics service to public schema
- Encrypted connections only
- Audit logging for sensitive queries

## Migration Strategy
```sql
-- Migration order
-- 1. Create schema
-- 2. Create tables
-- 3. Create indexes
-- 4. Create functions
-- 5. Create materialized views
-- 6. Create triggers
-- 7. Enable RLS
-- 8. Grant permissions
```