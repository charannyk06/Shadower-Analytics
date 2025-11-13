-- =====================================================================
-- Migration: 028_create_knowledge_base_tables.sql
-- Description: Create comprehensive agent knowledge base analytics tables
-- Created: 2025-11-13
-- =====================================================================

SET search_path TO analytics, public;

-- =====================================================================
-- Table: agent_knowledge_items
-- Description: Individual knowledge items in agent knowledge bases
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.agent_knowledge_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,

    -- Knowledge metadata
    knowledge_type VARCHAR(50) NOT NULL CHECK (
        knowledge_type IN ('fact', 'rule', 'procedure', 'concept', 'example', 'relationship')
    ),
    domain VARCHAR(100),
    subdomain VARCHAR(100),

    -- Content
    content TEXT NOT NULL,
    content_hash VARCHAR(64), -- SHA256 hash for deduplication
    embedding_vector FLOAT[] DEFAULT '{}', -- Vector embedding for semantic search
    embedding_model VARCHAR(100) DEFAULT 'text-embedding-ada-002',

    -- Quality metrics
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    verification_status VARCHAR(20) DEFAULT 'unverified' CHECK (
        verification_status IN ('unverified', 'pending', 'verified', 'rejected', 'outdated')
    ),
    source_reliability FLOAT CHECK (source_reliability >= 0 AND source_reliability <= 1),
    quality_score FLOAT CHECK (quality_score >= 0 AND quality_score <= 1),

    -- Usage metrics
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMPTZ,
    usefulness_score FLOAT CHECK (usefulness_score >= 0 AND usefulness_score <= 1),
    success_rate FLOAT, -- Rate of successful application

    -- Source information
    source_id UUID,
    source_type VARCHAR(50), -- 'manual', 'automated', 'transfer', 'learning'
    source_name VARCHAR(255),

    -- Relationships
    related_items UUID[] DEFAULT '{}',
    prerequisite_items UUID[] DEFAULT '{}',
    derived_from UUID[] DEFAULT '{}',
    parent_concept_id UUID,

    -- Graph metrics
    node_degree INTEGER DEFAULT 0, -- Number of connections
    centrality_score FLOAT, -- Importance in knowledge graph
    cluster_id UUID, -- Knowledge cluster/domain grouping

    -- Temporal aspects
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_validated TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    deprecation_date TIMESTAMPTZ,

    -- Metadata
    tags VARCHAR(50)[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',

    CONSTRAINT valid_scores CHECK (
        confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)
    )
);

-- Knowledge Items Indexes
CREATE INDEX idx_knowledge_items_agent ON analytics.agent_knowledge_items(agent_id, created_at DESC);
CREATE INDEX idx_knowledge_items_workspace ON analytics.agent_knowledge_items(workspace_id);
CREATE INDEX idx_knowledge_items_domain ON analytics.agent_knowledge_items(domain, subdomain);
CREATE INDEX idx_knowledge_items_type ON analytics.agent_knowledge_items(knowledge_type);
CREATE INDEX idx_knowledge_items_hash ON analytics.agent_knowledge_items(content_hash);
CREATE INDEX idx_knowledge_items_cluster ON analytics.agent_knowledge_items(cluster_id) WHERE cluster_id IS NOT NULL;
CREATE INDEX idx_knowledge_items_quality ON analytics.agent_knowledge_items(quality_score DESC) WHERE quality_score IS NOT NULL;
CREATE INDEX idx_knowledge_items_access ON analytics.agent_knowledge_items(access_count DESC);
CREATE INDEX idx_knowledge_items_verification ON analytics.agent_knowledge_items(verification_status, last_validated);

-- GIN indexes for array columns
CREATE INDEX idx_knowledge_items_related ON analytics.agent_knowledge_items USING gin(related_items);
CREATE INDEX idx_knowledge_items_tags ON analytics.agent_knowledge_items USING gin(tags);
CREATE INDEX idx_knowledge_items_metadata ON analytics.agent_knowledge_items USING gin(metadata);

-- Comments
COMMENT ON TABLE analytics.agent_knowledge_items IS 'Individual knowledge items in agent knowledge bases';
COMMENT ON COLUMN analytics.agent_knowledge_items.embedding_vector IS 'Vector embedding for semantic similarity search';
COMMENT ON COLUMN analytics.agent_knowledge_items.centrality_score IS 'Importance score in the knowledge graph based on connections';
COMMENT ON COLUMN analytics.agent_knowledge_items.content_hash IS 'SHA256 hash of content for deduplication';

-- =====================================================================
-- Table: knowledge_sources
-- Description: Sources of knowledge for quality tracking
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.knowledge_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,

    -- Source details
    source_type VARCHAR(50) NOT NULL CHECK (
        source_type IN ('documentation', 'training_data', 'user_feedback', 'api',
                       'database', 'web_scrape', 'manual_entry', 'agent_transfer')
    ),
    source_name VARCHAR(255) NOT NULL,
    source_url TEXT,

    -- Quality metrics
    reliability_score FLOAT CHECK (reliability_score >= 0 AND reliability_score <= 1),
    reliability_category VARCHAR(30) CHECK (
        reliability_category IN ('highly_reliable', 'reliable', 'moderately_reliable', 'unreliable')
    ),

    -- Usage statistics
    items_count INTEGER DEFAULT 0,
    avg_confidence FLOAT,
    avg_usefulness FLOAT,
    verification_rate FLOAT,
    total_accesses INTEGER DEFAULT 0,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_used TIMESTAMPTZ
);

CREATE INDEX idx_knowledge_sources_agent ON analytics.knowledge_sources(agent_id);
CREATE INDEX idx_knowledge_sources_type ON analytics.knowledge_sources(source_type);
CREATE INDEX idx_knowledge_sources_reliability ON analytics.knowledge_sources(reliability_score DESC) WHERE reliability_score IS NOT NULL;

COMMENT ON TABLE analytics.knowledge_sources IS 'Tracking sources of knowledge for quality assessment';

-- =====================================================================
-- Table: knowledge_validation_events
-- Description: Knowledge validation and verification tracking
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.knowledge_validation_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_item_id UUID NOT NULL REFERENCES analytics.agent_knowledge_items(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,

    -- Validation details
    validation_type VARCHAR(50) NOT NULL CHECK (
        validation_type IN ('manual', 'automated', 'crowd_sourced', 'cross_reference', 'usage_based')
    ),
    validator_id VARCHAR(100), -- User ID or system identifier
    validation_method TEXT,

    -- Results
    is_valid BOOLEAN NOT NULL,
    confidence_level FLOAT CHECK (confidence_level >= 0 AND confidence_level <= 1),
    previous_status VARCHAR(20),
    new_status VARCHAR(20),

    -- Error details (if invalid)
    error_details JSONB DEFAULT '{}',
    corrections_applied JSONB DEFAULT '{}',

    -- Impact assessment
    affected_decisions INTEGER DEFAULT 0,
    affected_users INTEGER DEFAULT 0,
    business_impact VARCHAR(20) CHECK (
        business_impact IN ('none', 'low', 'medium', 'high', 'critical')
    ),

    -- Metadata
    notes TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_validation_events_knowledge ON analytics.knowledge_validation_events(knowledge_item_id, created_at DESC);
CREATE INDEX idx_validation_events_agent ON analytics.knowledge_validation_events(agent_id);
CREATE INDEX idx_validation_events_validity ON analytics.knowledge_validation_events(is_valid, created_at DESC);
CREATE INDEX idx_validation_events_impact ON analytics.knowledge_validation_events(business_impact) WHERE business_impact IN ('high', 'critical');

COMMENT ON TABLE analytics.knowledge_validation_events IS 'Tracking knowledge validation and verification activities';

-- =====================================================================
-- Table: knowledge_transfers
-- Description: Cross-agent knowledge sharing tracking
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.knowledge_transfers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_agent_id UUID NOT NULL,
    target_agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,

    -- Transfer details
    knowledge_item_ids UUID[] NOT NULL,
    knowledge_domain VARCHAR(100),
    transfer_type VARCHAR(50) CHECK (
        transfer_type IN ('full_copy', 'adaptive_copy', 'reference', 'merge')
    ),

    -- Quality metrics
    knowledge_quality_score FLOAT CHECK (knowledge_quality_score >= 0 AND knowledge_quality_score <= 1),
    transfer_successful BOOLEAN DEFAULT TRUE,
    adaptation_time_hours NUMERIC(10,2),

    -- Performance impact
    performance_before FLOAT,
    performance_after FLOAT,
    performance_improvement FLOAT,

    -- Transfer metadata
    transferred_items_count INTEGER NOT NULL,
    failed_items_count INTEGER DEFAULT 0,
    conflict_resolution_strategy VARCHAR(50),

    -- Metadata
    notes TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_knowledge_transfers_source ON analytics.knowledge_transfers(source_agent_id, created_at DESC);
CREATE INDEX idx_knowledge_transfers_target ON analytics.knowledge_transfers(target_agent_id, created_at DESC);
CREATE INDEX idx_knowledge_transfers_workspace ON analytics.knowledge_transfers(workspace_id);
CREATE INDEX idx_knowledge_transfers_domain ON analytics.knowledge_transfers(knowledge_domain);
CREATE INDEX idx_knowledge_transfers_success ON analytics.knowledge_transfers(transfer_successful, performance_improvement);

COMMENT ON TABLE analytics.knowledge_transfers IS 'Tracking knowledge transfer between agents';

-- =====================================================================
-- Table: knowledge_retrieval_logs
-- Description: Knowledge retrieval performance tracking
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.knowledge_retrieval_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    knowledge_item_id UUID REFERENCES analytics.agent_knowledge_items(id) ON DELETE SET NULL,

    -- Query details
    query_text TEXT,
    query_embedding FLOAT[] DEFAULT '{}',
    query_type VARCHAR(50) CHECK (
        query_type IN ('semantic', 'keyword', 'structured', 'hybrid')
    ),

    -- Retrieval performance
    retrieval_time_ms INTEGER NOT NULL,
    cache_hit BOOLEAN DEFAULT FALSE,
    results_count INTEGER DEFAULT 0,
    results_examined INTEGER DEFAULT 0,

    -- Effectiveness metrics
    result_used BOOLEAN DEFAULT FALSE,
    result_rank INTEGER, -- Position of used result in results list
    user_satisfied BOOLEAN,

    -- Search quality (if feedback available)
    precision_score FLOAT,
    relevance_score FLOAT,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_retrieval_logs_agent ON analytics.knowledge_retrieval_logs(agent_id, created_at DESC);
CREATE INDEX idx_retrieval_logs_knowledge ON analytics.knowledge_retrieval_logs(knowledge_item_id) WHERE knowledge_item_id IS NOT NULL;
CREATE INDEX idx_retrieval_logs_performance ON analytics.knowledge_retrieval_logs(retrieval_time_ms);
CREATE INDEX idx_retrieval_logs_cache ON analytics.knowledge_retrieval_logs(cache_hit, created_at DESC);
CREATE INDEX idx_retrieval_logs_effectiveness ON analytics.knowledge_retrieval_logs(result_used, user_satisfied);

COMMENT ON TABLE analytics.knowledge_retrieval_logs IS 'Tracking knowledge retrieval performance and effectiveness';

-- =====================================================================
-- Table: knowledge_drift_events
-- Description: Knowledge drift detection events
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.knowledge_drift_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    knowledge_item_id UUID REFERENCES analytics.agent_knowledge_items(id) ON DELETE SET NULL,

    -- Drift details
    drift_type VARCHAR(50) NOT NULL CHECK (
        drift_type IN ('concept_drift', 'fact_staleness', 'rule_conflict', 'accuracy_degradation', 'semantic_shift')
    ),
    drift_score FLOAT NOT NULL CHECK (drift_score >= 0 AND drift_score <= 1),
    drift_detected BOOLEAN DEFAULT TRUE,

    -- Context
    baseline_value JSONB,
    current_value JSONB,
    affected_concepts TEXT[],

    -- Impact assessment
    severity VARCHAR(20) CHECK (
        severity IN ('low', 'medium', 'high', 'critical')
    ),
    affected_operations INTEGER DEFAULT 0,

    -- Remediation
    remediation_required BOOLEAN DEFAULT FALSE,
    remediation_applied BOOLEAN DEFAULT FALSE,
    remediation_plan JSONB,

    -- Detection metadata
    detection_method VARCHAR(100),
    detection_confidence FLOAT,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_drift_events_agent ON analytics.knowledge_drift_events(agent_id, created_at DESC);
CREATE INDEX idx_drift_events_knowledge ON analytics.knowledge_drift_events(knowledge_item_id) WHERE knowledge_item_id IS NOT NULL;
CREATE INDEX idx_drift_events_type ON analytics.knowledge_drift_events(drift_type, severity);
CREATE INDEX idx_drift_events_unresolved ON analytics.knowledge_drift_events(resolved_at) WHERE resolved_at IS NULL;
CREATE INDEX idx_drift_events_severity ON analytics.knowledge_drift_events(severity, created_at DESC) WHERE severity IN ('high', 'critical');

COMMENT ON TABLE analytics.knowledge_drift_events IS 'Tracking detected knowledge drift events';

-- =====================================================================
-- Table: knowledge_graph_metrics
-- Description: Periodic snapshots of knowledge graph structure
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.knowledge_graph_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,

    -- Graph structure metrics
    total_nodes INTEGER NOT NULL,
    total_edges INTEGER NOT NULL,
    graph_density FLOAT,
    average_degree FLOAT,
    clustering_coefficient FLOAT,
    connected_components INTEGER,
    max_path_length INTEGER,

    -- Node type distribution
    concepts_count INTEGER DEFAULT 0,
    facts_count INTEGER DEFAULT 0,
    procedures_count INTEGER DEFAULT 0,
    examples_count INTEGER DEFAULT 0,
    rules_count INTEGER DEFAULT 0,
    relationships_count INTEGER DEFAULT 0,

    -- Quality metrics
    avg_node_quality FLOAT,
    avg_edge_strength FLOAT,
    redundancy_ratio FLOAT,
    coverage_score FLOAT,

    -- Evolution metrics
    growth_rate FLOAT,
    update_frequency FLOAT,
    deprecation_rate FLOAT,
    quality_trend VARCHAR(20) CHECK (
        quality_trend IN ('improving', 'stable', 'degrading')
    ),

    -- Performance metrics
    avg_query_time_ms INTEGER,
    avg_traversal_depth FLOAT,
    cache_hit_rate FLOAT,

    -- Metadata
    snapshot_type VARCHAR(20) DEFAULT 'scheduled' CHECK (
        snapshot_type IN ('scheduled', 'on_demand', 'post_optimization')
    ),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_graph_metrics_agent ON analytics.knowledge_graph_metrics(agent_id, created_at DESC);
CREATE INDEX idx_graph_metrics_workspace ON analytics.knowledge_graph_metrics(workspace_id, created_at DESC);
CREATE INDEX idx_graph_metrics_quality ON analytics.knowledge_graph_metrics(quality_trend, created_at DESC);

COMMENT ON TABLE analytics.knowledge_graph_metrics IS 'Periodic snapshots of knowledge graph structure and metrics';

-- =====================================================================
-- Table: knowledge_domains
-- Description: Knowledge domain coverage and quality tracking
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.knowledge_domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,

    -- Domain information
    domain VARCHAR(100) NOT NULL,
    subdomain VARCHAR(100),

    -- Coverage metrics
    item_count INTEGER DEFAULT 0,
    coverage_percentage FLOAT,
    depth_score FLOAT CHECK (depth_score >= 0 AND depth_score <= 1),
    breadth_score FLOAT CHECK (breadth_score >= 0 AND breadth_score <= 1),

    -- Quality metrics
    quality_score FLOAT CHECK (quality_score >= 0 AND quality_score <= 1),
    avg_confidence FLOAT,
    verification_rate FLOAT,

    -- Usage metrics
    access_frequency FLOAT,
    usefulness_score FLOAT,

    -- Temporal tracking
    last_updated TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Metadata
    metadata JSONB DEFAULT '{}',

    CONSTRAINT unique_agent_domain UNIQUE (agent_id, domain, subdomain)
);

CREATE INDEX idx_knowledge_domains_agent ON analytics.knowledge_domains(agent_id);
CREATE INDEX idx_knowledge_domains_domain ON analytics.knowledge_domains(domain, subdomain);
CREATE INDEX idx_knowledge_domains_quality ON analytics.knowledge_domains(quality_score DESC) WHERE quality_score IS NOT NULL;
CREATE INDEX idx_knowledge_domains_coverage ON analytics.knowledge_domains(coverage_percentage DESC) WHERE coverage_percentage IS NOT NULL;

COMMENT ON TABLE analytics.knowledge_domains IS 'Tracking knowledge domain coverage and quality';

-- =====================================================================
-- Table: knowledge_lifecycle_stages
-- Description: Tracking knowledge item lifecycle transitions
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics.knowledge_lifecycle_stages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_item_id UUID NOT NULL REFERENCES analytics.agent_knowledge_items(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL,

    -- Lifecycle stage
    stage VARCHAR(30) NOT NULL CHECK (
        stage IN ('acquisition', 'validation', 'active_use', 'maintenance', 'deprecation', 'archived')
    ),
    previous_stage VARCHAR(30),

    -- Transition details
    trigger_event VARCHAR(100),
    trigger_reason TEXT,
    automated BOOLEAN DEFAULT FALSE,

    -- Duration in previous stage
    duration_days NUMERIC(10,2),

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_lifecycle_stages_knowledge ON analytics.knowledge_lifecycle_stages(knowledge_item_id, created_at DESC);
CREATE INDEX idx_lifecycle_stages_agent ON analytics.knowledge_lifecycle_stages(agent_id, stage);
CREATE INDEX idx_lifecycle_stages_stage ON analytics.knowledge_lifecycle_stages(stage, created_at DESC);

COMMENT ON TABLE analytics.knowledge_lifecycle_stages IS 'Tracking knowledge item lifecycle stage transitions';

-- =====================================================================
-- Materialized View: knowledge_source_quality
-- Description: Aggregated source quality metrics
-- =====================================================================

CREATE MATERIALIZED VIEW analytics.knowledge_source_quality AS
WITH source_metrics AS (
    SELECT
        ki.agent_id,
        ki.source_id,
        ks.source_type,
        ks.source_name,
        COUNT(ki.id) as items_from_source,
        AVG(ki.confidence_score) as avg_confidence,
        AVG(ki.usefulness_score) as avg_usefulness,
        SUM(ki.access_count) as total_accesses,
        COUNT(CASE WHEN ki.verification_status = 'verified' THEN 1 END)::float /
            NULLIF(COUNT(*), 0) as verification_rate
    FROM analytics.agent_knowledge_items ki
    LEFT JOIN analytics.knowledge_sources ks ON ki.source_id = ks.id
    WHERE ki.source_id IS NOT NULL
    GROUP BY ki.agent_id, ki.source_id, ks.source_type, ks.source_name
),
source_reliability AS (
    SELECT
        source_id,
        agent_id,
        (COALESCE(avg_confidence, 0) * 0.3 +
         COALESCE(avg_usefulness, 0) * 0.3 +
         COALESCE(verification_rate, 0) * 0.2 +
         LEAST(items_from_source / 100.0, 1) * 0.2) as reliability_score,
        CASE
            WHEN COALESCE(avg_confidence, 0) > 0.8 AND COALESCE(verification_rate, 0) > 0.7 THEN 'highly_reliable'
            WHEN COALESCE(avg_confidence, 0) > 0.6 AND COALESCE(verification_rate, 0) > 0.5 THEN 'reliable'
            WHEN COALESCE(avg_confidence, 0) > 0.4 THEN 'moderately_reliable'
            ELSE 'unreliable'
        END as reliability_category
    FROM source_metrics
)
SELECT
    sm.*,
    sr.reliability_score,
    sr.reliability_category,
    RANK() OVER (PARTITION BY sm.agent_id ORDER BY sr.reliability_score DESC) as source_rank
FROM source_metrics sm
JOIN source_reliability sr ON sm.source_id = sr.source_id AND sm.agent_id = sr.agent_id;

CREATE UNIQUE INDEX idx_source_quality_pk ON analytics.knowledge_source_quality(agent_id, source_id);
CREATE INDEX idx_source_quality_rank ON analytics.knowledge_source_quality(agent_id, source_rank);

COMMENT ON MATERIALIZED VIEW analytics.knowledge_source_quality IS 'Aggregated quality metrics for knowledge sources';

-- =====================================================================
-- Materialized View: knowledge_transfer_analytics
-- Description: Cross-agent knowledge transfer effectiveness
-- =====================================================================

CREATE MATERIALIZED VIEW analytics.knowledge_transfer_analytics AS
WITH transfer_events AS (
    SELECT
        source_agent_id,
        target_agent_id,
        workspace_id,
        COUNT(*) as transfer_count,
        AVG(knowledge_quality_score) as avg_quality,
        SUM(CASE WHEN transfer_successful THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) as success_rate,
        AVG(adaptation_time_hours) as avg_adaptation_time,
        AVG(performance_improvement) as avg_performance_gain,
        SUM(transferred_items_count) as total_items_transferred,
        SUM(failed_items_count) as total_items_failed
    FROM analytics.knowledge_transfers
    WHERE created_at > NOW() - INTERVAL '30 days'
    GROUP BY source_agent_id, target_agent_id, workspace_id
),
transfer_effectiveness AS (
    SELECT
        target_agent_id,
        workspace_id,
        COUNT(DISTINCT source_agent_id) as knowledge_sources,
        AVG(avg_performance_gain) as overall_performance_gain,
        SUM(transfer_count) as total_transfers_received
    FROM transfer_events
    GROUP BY target_agent_id, workspace_id
)
SELECT
    te.*,
    tef.overall_performance_gain,
    CASE
        WHEN te.success_rate > 0.8 AND COALESCE(te.avg_performance_gain, 0) > 0.1 THEN 'highly_effective'
        WHEN te.success_rate > 0.6 AND COALESCE(te.avg_performance_gain, 0) > 0.05 THEN 'effective'
        WHEN te.success_rate > 0.4 THEN 'moderately_effective'
        ELSE 'ineffective'
    END as transfer_effectiveness
FROM transfer_events te
LEFT JOIN transfer_effectiveness tef ON te.target_agent_id = tef.target_agent_id AND te.workspace_id = tef.workspace_id;

CREATE UNIQUE INDEX idx_transfer_analytics_pk ON analytics.knowledge_transfer_analytics(source_agent_id, target_agent_id, workspace_id);
CREATE INDEX idx_transfer_analytics_target ON analytics.knowledge_transfer_analytics(target_agent_id);
CREATE INDEX idx_transfer_analytics_effectiveness ON analytics.knowledge_transfer_analytics(transfer_effectiveness);

COMMENT ON MATERIALIZED VIEW analytics.knowledge_transfer_analytics IS 'Aggregated knowledge transfer effectiveness metrics';

-- =====================================================================
-- Function: update_knowledge_item_timestamp
-- Description: Automatically update updated_at timestamp
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.update_knowledge_item_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_knowledge_item_timestamp
    BEFORE UPDATE ON analytics.agent_knowledge_items
    FOR EACH ROW
    EXECUTE FUNCTION analytics.update_knowledge_item_timestamp();

COMMENT ON FUNCTION analytics.update_knowledge_item_timestamp() IS 'Automatically update knowledge item timestamp on modification';

-- =====================================================================
-- Function: increment_knowledge_access_count
-- Description: Increment access count and update last accessed timestamp
-- =====================================================================

CREATE OR REPLACE FUNCTION analytics.increment_knowledge_access_count(
    p_knowledge_item_id UUID
)
RETURNS VOID AS $$
BEGIN
    UPDATE analytics.agent_knowledge_items
    SET
        access_count = access_count + 1,
        last_accessed = NOW()
    WHERE id = p_knowledge_item_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.increment_knowledge_access_count(UUID) IS 'Increment knowledge item access count';

-- =====================================================================
-- Grant permissions
-- =====================================================================

-- Grant read access to authenticated users
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO authenticated;
GRANT SELECT ON ALL MATERIALIZED VIEWS IN SCHEMA analytics TO authenticated;

-- Grant write access to service role
GRANT ALL ON ALL TABLES IN SCHEMA analytics TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA analytics TO service_role;
GRANT ALL ON ALL MATERIALIZED VIEWS IN SCHEMA analytics TO service_role;

-- =====================================================================
-- End of migration
-- =====================================================================
