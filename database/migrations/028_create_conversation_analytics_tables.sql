-- =====================================================================
-- Migration: 028_create_conversation_analytics_tables.sql
-- Description: Create comprehensive conversation analytics tables for
--              agent conversation pattern analysis, user interactions,
--              context management, and communication effectiveness
-- Created: 2025-11-13
-- =====================================================================

-- Set search path
SET search_path TO analytics, public;

-- =====================================================================
-- Core Conversation Tables
-- =====================================================================

-- Conversation analytics aggregated metrics table
CREATE TABLE IF NOT EXISTS conversation_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL UNIQUE,
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    user_id UUID NOT NULL,

    -- Session data
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    total_duration_ms BIGINT,
    idle_time_ms BIGINT DEFAULT 0,
    active_time_ms BIGINT DEFAULT 0,

    -- Message metrics
    total_messages INTEGER DEFAULT 0,
    user_messages INTEGER DEFAULT 0,
    agent_messages INTEGER DEFAULT 0,
    system_messages INTEGER DEFAULT 0,
    average_response_time_ms BIGINT,
    message_velocity NUMERIC(10, 2), -- messages per minute

    -- Token usage
    input_tokens BIGINT DEFAULT 0,
    output_tokens BIGINT DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    cost_usd NUMERIC(10, 4) DEFAULT 0,
    tokens_per_message NUMERIC(10, 2),

    -- Interaction quality scores (0-1 scale)
    sentiment_score NUMERIC(5, 4),
    clarity_score NUMERIC(5, 4),
    relevance_score NUMERIC(5, 4),
    completion_rate NUMERIC(5, 4),
    user_satisfaction NUMERIC(5, 4),

    -- Overall conversation status
    status VARCHAR(20) DEFAULT 'active', -- active, completed, abandoned, timeout
    goal_achieved BOOLEAN,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Message-level analytics table
CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    message_index INTEGER NOT NULL,

    -- Message details
    role VARCHAR(20) NOT NULL, -- 'user', 'agent', 'system'
    content TEXT NOT NULL,
    tokens_used INTEGER,
    response_time_ms INTEGER,

    -- Content analysis
    sentiment_score NUMERIC(5, 4),
    emotion_primary VARCHAR(50), -- happy, frustrated, confused, satisfied, neutral
    emotion_confidence NUMERIC(5, 4),
    emotion_intensity NUMERIC(5, 4),

    -- Intent and entity extraction
    intent_classification VARCHAR(100),
    intent_confidence NUMERIC(5, 4),
    entity_extraction JSONB DEFAULT '{}',

    -- Quality metrics
    relevance_score NUMERIC(5, 4),
    completeness_score NUMERIC(5, 4),
    clarity_score NUMERIC(5, 4),

    -- Error tracking
    error_occurred BOOLEAN DEFAULT FALSE,
    error_type VARCHAR(100),
    retry_count INTEGER DEFAULT 0,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Context management metrics table
CREATE TABLE IF NOT EXISTS conversation_context_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL,
    agent_id UUID NOT NULL,

    -- Context window metrics
    context_tokens_used INTEGER DEFAULT 0,
    useful_context_tokens INTEGER DEFAULT 0,
    context_efficiency NUMERIC(5, 4), -- useful_tokens / total_tokens
    context_switches_per_conversation INTEGER DEFAULT 0,

    -- Topic tracking
    topics_discussed JSONB DEFAULT '[]',
    topic_switches INTEGER DEFAULT 0,
    topic_coherence_score NUMERIC(5, 4),

    -- Memory and recall
    working_memory_usage INTEGER,
    long_term_recall_count INTEGER DEFAULT 0,
    reference_accuracy NUMERIC(5, 4),

    -- Measurement timestamp
    measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Intent recognition analytics table
CREATE TABLE IF NOT EXISTS intent_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,

    -- Intent details
    intent_type VARCHAR(100) NOT NULL,
    confidence_score NUMERIC(5, 4),
    was_correct BOOLEAN,

    -- Performance metrics
    processing_time_ms INTEGER,
    frequency INTEGER DEFAULT 1,

    -- Common phrases for this intent
    common_phrases TEXT[] DEFAULT '{}',

    -- Timestamps
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Entity extraction performance table
CREATE TABLE IF NOT EXISTS entity_extraction_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,

    -- Entity details
    entity_type VARCHAR(100) NOT NULL,
    extraction_accuracy NUMERIC(5, 4),
    false_positive_rate NUMERIC(5, 4),
    false_negative_rate NUMERIC(5, 4),
    avg_confidence NUMERIC(5, 4),

    -- Error tracking
    common_errors JSONB DEFAULT '[]',

    -- Metrics period
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversation turn-taking metrics table
CREATE TABLE IF NOT EXISTS conversation_turn_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL,

    -- Turn patterns
    average_turns NUMERIC(10, 2),
    user_initiated_turns INTEGER DEFAULT 0,
    agent_initiated_turns INTEGER DEFAULT 0,

    -- Turn length statistics
    user_avg_length NUMERIC(10, 2),
    agent_avg_length NUMERIC(10, 2),
    length_correlation NUMERIC(5, 4),

    -- Interruption patterns
    user_interruptions INTEGER DEFAULT 0,
    agent_interruptions INTEGER DEFAULT 0,
    clarification_requests INTEGER DEFAULT 0,

    -- Conversation dynamics (0-1 scale)
    momentum_score NUMERIC(5, 4),
    engagement_score NUMERIC(5, 4),
    reciprocity_index NUMERIC(5, 4),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversation engagement metrics table
CREATE TABLE IF NOT EXISTS conversation_engagement_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    user_id UUID NOT NULL,

    -- Engagement scores (0-1 scale)
    interaction_depth NUMERIC(5, 4),
    user_investment NUMERIC(5, 4),
    conversation_momentum NUMERIC(5, 4),
    topic_exploration NUMERIC(5, 4),
    question_quality NUMERIC(5, 4),
    feedback_indicators NUMERIC(5, 4),
    overall_score NUMERIC(5, 4),

    -- Engagement level categorization
    engagement_level VARCHAR(20), -- very_low, low, medium, high, very_high

    -- Recommendations
    recommendations JSONB DEFAULT '[]',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversation outcome tracking table
CREATE TABLE IF NOT EXISTS conversation_outcomes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL UNIQUE,
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,

    -- Goal achievement
    goal_achieved BOOLEAN,
    tasks_completed INTEGER DEFAULT 0,
    tasks_total INTEGER DEFAULT 0,
    problems_solved INTEGER DEFAULT 0,

    -- Knowledge transfer
    knowledge_transferred_score NUMERIC(5, 4),

    -- User satisfaction
    user_satisfaction_score NUMERIC(5, 4),
    follow_up_required BOOLEAN DEFAULT FALSE,

    -- Business metrics
    business_value_score NUMERIC(10, 2),
    estimated_time_saved_minutes NUMERIC(10, 2),
    cost_benefit_ratio NUMERIC(10, 2),

    -- Outcome categorization
    outcome_category VARCHAR(50), -- successful, partial, failed, abandoned

    -- Metadata
    notes TEXT,
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Emotion timeline tracking table
CREATE TABLE IF NOT EXISTS conversation_emotion_timeline (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL,
    message_id UUID NOT NULL,

    -- Emotion data
    user_emotion_primary VARCHAR(50),
    user_emotion_confidence NUMERIC(5, 4),
    user_emotion_intensity NUMERIC(5, 4),

    -- Agent response appropriateness
    agent_response_appropriateness NUMERIC(5, 4),

    -- Timestamp
    occurred_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sentiment progression tracking table
CREATE TABLE IF NOT EXISTS conversation_sentiment_progression (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL UNIQUE,

    -- Sentiment timeline
    sentiment_timeline JSONB NOT NULL DEFAULT '[]',

    -- Significant shifts
    sentiment_shifts JSONB DEFAULT '[]',

    -- Overall emotional journey
    start_emotion VARCHAR(50),
    end_emotion VARCHAR(50),
    peak_positive NUMERIC(5, 4),
    peak_negative NUMERIC(5, 4),
    emotional_variance NUMERIC(5, 4),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversation patterns cache table
CREATE TABLE IF NOT EXISTS conversation_patterns_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL,
    agent_id UUID,

    -- Pattern type
    pattern_type VARCHAR(50) NOT NULL, -- flow, topic, user_behavior, failure

    -- Pattern data
    pattern_data JSONB NOT NULL,
    frequency INTEGER DEFAULT 0,
    confidence_score NUMERIC(5, 4),

    -- Analysis period
    analysis_start TIMESTAMP NOT NULL,
    analysis_end TIMESTAMP NOT NULL,

    -- Cache metadata
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Response quality metrics table
CREATE TABLE IF NOT EXISTS response_quality_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL,
    message_id UUID NOT NULL,
    agent_id UUID NOT NULL,

    -- Quality scores (0-1 scale)
    relevance_score NUMERIC(5, 4),
    completeness_score NUMERIC(5, 4),
    accuracy_score NUMERIC(5, 4),
    tone_appropriateness NUMERIC(5, 4),
    creativity_index NUMERIC(5, 4),
    personalization_level NUMERIC(5, 4),

    -- Quality checks
    hallucination_detected BOOLEAN DEFAULT FALSE,
    consistency_score NUMERIC(5, 4),
    clarity_score NUMERIC(5, 4),

    -- Overall quality
    overall_quality_score NUMERIC(5, 4),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================================
-- Create Indexes for Performance
-- =====================================================================

-- Conversation analytics indexes
CREATE INDEX IF NOT EXISTS idx_conversation_analytics_conversation ON conversation_analytics(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_analytics_agent ON conversation_analytics(agent_id);
CREATE INDEX IF NOT EXISTS idx_conversation_analytics_workspace ON conversation_analytics(workspace_id);
CREATE INDEX IF NOT EXISTS idx_conversation_analytics_user ON conversation_analytics(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_analytics_time ON conversation_analytics(start_time);
CREATE INDEX IF NOT EXISTS idx_conversation_analytics_status ON conversation_analytics(status);
CREATE INDEX IF NOT EXISTS idx_conversation_analytics_workspace_time ON conversation_analytics(workspace_id, start_time);

-- Message-level indexes
CREATE INDEX IF NOT EXISTS idx_conv_messages_conversation ON conversation_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conv_messages_agent ON conversation_messages(agent_id);
CREATE INDEX IF NOT EXISTS idx_conv_messages_intent ON conversation_messages(intent_classification);
CREATE INDEX IF NOT EXISTS idx_conv_messages_sentiment ON conversation_messages(sentiment_score);
CREATE INDEX IF NOT EXISTS idx_conv_messages_role ON conversation_messages(role);
CREATE INDEX IF NOT EXISTS idx_conv_messages_conversation_index ON conversation_messages(conversation_id, message_index);
CREATE INDEX IF NOT EXISTS idx_conv_messages_created ON conversation_messages(created_at);

-- Context metrics indexes
CREATE INDEX IF NOT EXISTS idx_context_metrics_conversation ON conversation_context_metrics(conversation_id);
CREATE INDEX IF NOT EXISTS idx_context_metrics_agent ON conversation_context_metrics(agent_id);
CREATE INDEX IF NOT EXISTS idx_context_metrics_efficiency ON conversation_context_metrics(context_efficiency);

-- Intent analytics indexes
CREATE INDEX IF NOT EXISTS idx_intent_analytics_agent ON intent_analytics(agent_id);
CREATE INDEX IF NOT EXISTS idx_intent_analytics_workspace ON intent_analytics(workspace_id);
CREATE INDEX IF NOT EXISTS idx_intent_analytics_type ON intent_analytics(intent_type);
CREATE INDEX IF NOT EXISTS idx_intent_analytics_detected ON intent_analytics(detected_at);
CREATE INDEX IF NOT EXISTS idx_intent_analytics_workspace_type ON intent_analytics(workspace_id, intent_type);

-- Entity extraction indexes
CREATE INDEX IF NOT EXISTS idx_entity_metrics_agent ON entity_extraction_metrics(agent_id);
CREATE INDEX IF NOT EXISTS idx_entity_metrics_workspace ON entity_extraction_metrics(workspace_id);
CREATE INDEX IF NOT EXISTS idx_entity_metrics_type ON entity_extraction_metrics(entity_type);
CREATE INDEX IF NOT EXISTS idx_entity_metrics_period ON entity_extraction_metrics(period_start, period_end);

-- Turn metrics indexes
CREATE INDEX IF NOT EXISTS idx_turn_metrics_conversation ON conversation_turn_metrics(conversation_id);
CREATE INDEX IF NOT EXISTS idx_turn_metrics_engagement ON conversation_turn_metrics(engagement_score);

-- Engagement metrics indexes
CREATE INDEX IF NOT EXISTS idx_engagement_metrics_conversation ON conversation_engagement_metrics(conversation_id);
CREATE INDEX IF NOT EXISTS idx_engagement_metrics_agent ON conversation_engagement_metrics(agent_id);
CREATE INDEX IF NOT EXISTS idx_engagement_metrics_user ON conversation_engagement_metrics(user_id);
CREATE INDEX IF NOT EXISTS idx_engagement_metrics_score ON conversation_engagement_metrics(overall_score);
CREATE INDEX IF NOT EXISTS idx_engagement_metrics_level ON conversation_engagement_metrics(engagement_level);

-- Outcome indexes
CREATE INDEX IF NOT EXISTS idx_outcomes_conversation ON conversation_outcomes(conversation_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_agent ON conversation_outcomes(agent_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_workspace ON conversation_outcomes(workspace_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_category ON conversation_outcomes(outcome_category);
CREATE INDEX IF NOT EXISTS idx_outcomes_achievement ON conversation_outcomes(goal_achieved);

-- Emotion timeline indexes
CREATE INDEX IF NOT EXISTS idx_emotion_timeline_conversation ON conversation_emotion_timeline(conversation_id);
CREATE INDEX IF NOT EXISTS idx_emotion_timeline_message ON conversation_emotion_timeline(message_id);
CREATE INDEX IF NOT EXISTS idx_emotion_timeline_occurred ON conversation_emotion_timeline(occurred_at);

-- Sentiment progression indexes
CREATE INDEX IF NOT EXISTS idx_sentiment_progression_conversation ON conversation_sentiment_progression(conversation_id);

-- Patterns cache indexes
CREATE INDEX IF NOT EXISTS idx_patterns_cache_workspace ON conversation_patterns_cache(workspace_id);
CREATE INDEX IF NOT EXISTS idx_patterns_cache_agent ON conversation_patterns_cache(agent_id);
CREATE INDEX IF NOT EXISTS idx_patterns_cache_type ON conversation_patterns_cache(pattern_type);
CREATE INDEX IF NOT EXISTS idx_patterns_cache_period ON conversation_patterns_cache(analysis_start, analysis_end);
CREATE INDEX IF NOT EXISTS idx_patterns_cache_updated ON conversation_patterns_cache(last_updated);

-- Response quality indexes
CREATE INDEX IF NOT EXISTS idx_response_quality_conversation ON response_quality_metrics(conversation_id);
CREATE INDEX IF NOT EXISTS idx_response_quality_message ON response_quality_metrics(message_id);
CREATE INDEX IF NOT EXISTS idx_response_quality_agent ON response_quality_metrics(agent_id);
CREATE INDEX IF NOT EXISTS idx_response_quality_score ON response_quality_metrics(overall_quality_score);

-- =====================================================================
-- Create Materialized Views for Common Queries
-- =====================================================================

-- Agent conversation performance view
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_agent_conversation_performance AS
SELECT
    ca.agent_id,
    ca.workspace_id,
    COUNT(DISTINCT ca.conversation_id) as total_conversations,
    AVG(ca.total_messages) as avg_messages_per_conversation,
    AVG(ca.sentiment_score) as avg_sentiment,
    AVG(ca.user_satisfaction) as avg_satisfaction,
    AVG(ca.total_duration_ms / 1000.0 / 60.0) as avg_duration_minutes,
    AVG(ca.message_velocity) as avg_message_velocity,
    SUM(CASE WHEN ca.status = 'completed' THEN 1 ELSE 0 END)::float / COUNT(*) as completion_rate,
    SUM(CASE WHEN ca.goal_achieved THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) as goal_achievement_rate,
    AVG(ca.total_tokens) as avg_tokens_per_conversation,
    AVG(ca.cost_usd) as avg_cost_per_conversation
FROM conversation_analytics ca
WHERE ca.end_time IS NOT NULL
GROUP BY ca.agent_id, ca.workspace_id;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_agent_conv_perf_agent_workspace
ON mv_agent_conversation_performance(agent_id, workspace_id);

-- Conversation quality trends view
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_conversation_quality_trends AS
SELECT
    ca.workspace_id,
    ca.agent_id,
    DATE_TRUNC('hour', ca.start_time) as hour,
    COUNT(*) as conversation_count,
    AVG(ca.sentiment_score) as avg_sentiment,
    AVG(ca.clarity_score) as avg_clarity,
    AVG(ca.relevance_score) as avg_relevance,
    AVG(ca.user_satisfaction) as avg_satisfaction,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ca.average_response_time_ms) as median_response_time,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ca.average_response_time_ms) as p95_response_time
FROM conversation_analytics ca
WHERE ca.end_time IS NOT NULL
GROUP BY ca.workspace_id, ca.agent_id, DATE_TRUNC('hour', ca.start_time);

CREATE INDEX IF NOT EXISTS idx_mv_conv_quality_trends_workspace_hour
ON mv_conversation_quality_trends(workspace_id, hour);
CREATE INDEX IF NOT EXISTS idx_mv_conv_quality_trends_agent_hour
ON mv_conversation_quality_trends(agent_id, hour);

-- Intent recognition performance view
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_intent_recognition_performance AS
SELECT
    ia.agent_id,
    ia.workspace_id,
    ia.intent_type,
    COUNT(*) as total_occurrences,
    AVG(ia.confidence_score) as avg_confidence,
    SUM(CASE WHEN ia.was_correct THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) as accuracy,
    AVG(ia.processing_time_ms) as avg_processing_time,
    ARRAY_AGG(DISTINCT unnested_phrase ORDER BY ia.frequency DESC) FILTER (WHERE unnested_phrase IS NOT NULL) as top_phrases
FROM intent_analytics ia
LEFT JOIN LATERAL unnest(ia.common_phrases) as unnested_phrase ON true
GROUP BY ia.agent_id, ia.workspace_id, ia.intent_type;

CREATE INDEX IF NOT EXISTS idx_mv_intent_perf_agent_workspace
ON mv_intent_recognition_performance(agent_id, workspace_id);
CREATE INDEX IF NOT EXISTS idx_mv_intent_perf_type
ON mv_intent_recognition_performance(intent_type);

-- =====================================================================
-- Create Helper Functions
-- =====================================================================

-- Function to update conversation analytics on message insert
CREATE OR REPLACE FUNCTION update_conversation_analytics_on_message()
RETURNS TRIGGER AS $$
BEGIN
    -- Update conversation analytics with new message
    INSERT INTO conversation_analytics (
        conversation_id,
        agent_id,
        workspace_id,
        user_id,
        total_messages,
        user_messages,
        agent_messages,
        system_messages,
        start_time,
        updated_at
    )
    VALUES (
        NEW.conversation_id,
        NEW.agent_id,
        (SELECT workspace_id FROM conversation_analytics WHERE conversation_id = NEW.conversation_id LIMIT 1),
        (SELECT user_id FROM conversation_analytics WHERE conversation_id = NEW.conversation_id LIMIT 1),
        1,
        CASE WHEN NEW.role = 'user' THEN 1 ELSE 0 END,
        CASE WHEN NEW.role = 'agent' THEN 1 ELSE 0 END,
        CASE WHEN NEW.role = 'system' THEN 1 ELSE 0 END,
        NEW.created_at,
        CURRENT_TIMESTAMP
    )
    ON CONFLICT (conversation_id) DO UPDATE SET
        total_messages = conversation_analytics.total_messages + 1,
        user_messages = conversation_analytics.user_messages +
            CASE WHEN NEW.role = 'user' THEN 1 ELSE 0 END,
        agent_messages = conversation_analytics.agent_messages +
            CASE WHEN NEW.role = 'agent' THEN 1 ELSE 0 END,
        system_messages = conversation_analytics.system_messages +
            CASE WHEN NEW.role = 'system' THEN 1 ELSE 0 END,
        updated_at = CURRENT_TIMESTAMP;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for message analytics update
DROP TRIGGER IF EXISTS trg_update_conversation_analytics ON conversation_messages;
CREATE TRIGGER trg_update_conversation_analytics
    AFTER INSERT ON conversation_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_analytics_on_message();

-- Function to refresh conversation materialized views
CREATE OR REPLACE FUNCTION refresh_conversation_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_agent_conversation_performance;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_conversation_quality_trends;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_intent_recognition_performance;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- Grant Permissions
-- =====================================================================

-- Grant table permissions
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA analytics TO service_role;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO authenticated;

-- Grant sequence permissions
GRANT USAGE ON ALL SEQUENCES IN SCHEMA analytics TO service_role;

-- Grant materialized view permissions
GRANT SELECT ON mv_agent_conversation_performance TO authenticated;
GRANT SELECT ON mv_conversation_quality_trends TO authenticated;
GRANT SELECT ON mv_intent_recognition_performance TO authenticated;

-- =====================================================================
-- Add Comments for Documentation
-- =====================================================================

COMMENT ON TABLE conversation_analytics IS 'Aggregated conversation analytics with session, message, token, and quality metrics';
COMMENT ON TABLE conversation_messages IS 'Individual message-level analytics with sentiment, intent, and quality scores';
COMMENT ON TABLE conversation_context_metrics IS 'Context management and topic tracking metrics for conversations';
COMMENT ON TABLE intent_analytics IS 'Intent recognition performance and accuracy tracking';
COMMENT ON TABLE entity_extraction_metrics IS 'Entity extraction performance metrics by type';
COMMENT ON TABLE conversation_turn_metrics IS 'Turn-taking patterns and conversation dynamics';
COMMENT ON TABLE conversation_engagement_metrics IS 'User engagement scoring and quality metrics';
COMMENT ON TABLE conversation_outcomes IS 'Conversation outcome tracking including goal achievement and business value';
COMMENT ON TABLE conversation_emotion_timeline IS 'Timeline of emotional states throughout conversation';
COMMENT ON TABLE conversation_sentiment_progression IS 'Sentiment progression and emotional journey tracking';
COMMENT ON TABLE conversation_patterns_cache IS 'Cached analysis of common conversation patterns';
COMMENT ON TABLE response_quality_metrics IS 'Response quality metrics including relevance, completeness, and accuracy';

COMMENT ON MATERIALIZED VIEW mv_agent_conversation_performance IS 'Agent performance metrics aggregated from conversation analytics';
COMMENT ON MATERIALIZED VIEW mv_conversation_quality_trends IS 'Hourly trends of conversation quality metrics';
COMMENT ON MATERIALIZED VIEW mv_intent_recognition_performance IS 'Intent recognition accuracy and performance by agent and type';
