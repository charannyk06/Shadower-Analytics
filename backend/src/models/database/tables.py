"""SQLAlchemy database models."""

from uuid import uuid4
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, JSON, Enum, Index, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class UserMetric(Base):
    """User metrics table."""

    __tablename__ = "user_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    metric_date = Column(DateTime, index=True, nullable=False)
    sessions_count = Column(Integer, default=0)
    executions_count = Column(Integer, default=0)
    active_duration = Column(Float, default=0.0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class AgentMetric(Base):
    """Agent metrics table."""

    __tablename__ = "agent_metrics"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String, index=True, nullable=False)
    metric_date = Column(DateTime, index=True, nullable=False)
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)
    avg_duration = Column(Float, default=0.0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class ExecutionLog(Base):
    """Execution logs table."""

    __tablename__ = "execution_logs"
    __table_args__ = (
        # Compound indices for comparison queries performance
        Index('idx_execution_logs_agent_date', 'agent_id', 'started_at'),
        Index('idx_execution_logs_workspace_date', 'workspace_id', 'started_at'),
        Index('idx_execution_logs_status_date', 'status', 'started_at'),
        Index('idx_execution_logs_agent_workspace', 'agent_id', 'workspace_id', 'started_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String, unique=True, index=True, nullable=False)
    agent_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)
    status = Column(String, index=True, nullable=False)
    duration = Column(Float)
    credits_used = Column(Integer, default=0)
    metadata = Column(JSON)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())


class WorkspaceMetric(Base):
    """Workspace metrics table."""

    __tablename__ = "workspace_metrics"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(String, index=True, nullable=False)
    metric_date = Column(DateTime, index=True, nullable=False)
    total_users = Column(Integer, default=0)
    active_users = Column(Integer, default=0)
    total_agents = Column(Integer, default=0)
    total_executions = Column(Integer, default=0)
    credits_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class UserActivity(Base):
    """User activity event tracking table."""

    __tablename__ = "user_activity"
    __table_args__ = (
        # Compound indices for performance optimization
        Index('idx_user_activity_workspace_created', 'workspace_id', 'created_at'),
        Index('idx_user_activity_user_workspace', 'user_id', 'workspace_id'),
        Index('idx_user_activity_session_created', 'session_id', 'created_at'),
        Index('idx_user_activity_workspace_event_type', 'workspace_id', 'event_type'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True)
    session_id = Column(String, index=True)

    # Event details
    event_type = Column(String(50), nullable=False, index=True)
    event_name = Column(String(100))
    page_path = Column(String(255))

    # Context
    ip_address = Column(String)
    user_agent = Column(String)
    referrer = Column(String)
    device_type = Column(String(20))
    browser = Column(String(50))
    os = Column(String(50))
    country_code = Column(String(2))

    # Event data
    metadata = Column(JSON, default={})

    created_at = Column(DateTime, default=func.now(), index=True)


class UserSegment(Base):
    """User segments table for behavioral analysis."""

    __tablename__ = "user_segments"
    __table_args__ = {'schema': 'analytics'}

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, index=True)
    segment_name = Column(String(100), nullable=False)
    segment_type = Column(String(50))

    # Segment definition
    criteria = Column(JSON, nullable=False)

    # Cached metrics
    user_count = Column(Integer, default=0)
    avg_engagement = Column(Float)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class AgentLeaderboard(Base):
    """Agent leaderboard rankings table."""

    __tablename__ = "agent_leaderboard"
    __table_args__ = (
        Index('idx_agent_leaderboard_workspace_timeframe', 'workspace_id', 'timeframe', 'criteria', 'rank'),
        Index('idx_agent_leaderboard_rank', 'timeframe', 'criteria', 'rank'),
        Index('idx_agent_leaderboard_calculated', 'calculated_at'),
        Index('idx_agent_leaderboard_agent', 'agent_id', 'timeframe'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, index=True, nullable=False)
    agent_id = Column(String, index=True, nullable=False)

    # Ranking information
    rank = Column(Integer, nullable=False)
    previous_rank = Column(Integer)
    rank_change = Column(String(10))  # 'up', 'down', 'same', 'new'

    # Timeframe and criteria
    timeframe = Column(String(20), nullable=False)  # '24h', '7d', '30d', '90d', 'all'
    criteria = Column(String(50), nullable=False)  # 'runs', 'success_rate', 'speed', 'efficiency', 'popularity'

    # Agent metrics (snapshot)
    total_runs = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    avg_runtime = Column(Float, default=0.0)
    credits_per_run = Column(Float, default=0.0)
    unique_users = Column(Integer, default=0)

    # Score and percentile
    score = Column(Float, nullable=False)
    percentile = Column(Float)
    badge = Column(String(20))  # 'gold', 'silver', 'bronze'

    # Metadata
    calculated_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class UserLeaderboard(Base):
    """User leaderboard rankings table."""

    __tablename__ = "user_leaderboard"
    __table_args__ = (
        Index('idx_user_leaderboard_workspace_timeframe', 'workspace_id', 'timeframe', 'criteria', 'rank'),
        Index('idx_user_leaderboard_rank', 'timeframe', 'criteria', 'rank'),
        Index('idx_user_leaderboard_calculated', 'calculated_at'),
        Index('idx_user_leaderboard_user', 'user_id', 'timeframe'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)

    # Ranking information
    rank = Column(Integer, nullable=False)
    previous_rank = Column(Integer)
    rank_change = Column(String(10))  # 'up', 'down', 'same', 'new'

    # Timeframe and criteria
    timeframe = Column(String(20), nullable=False)  # '24h', '7d', '30d', '90d', 'all'
    criteria = Column(String(50), nullable=False)  # 'activity', 'efficiency', 'contribution', 'savings'

    # User metrics (snapshot)
    total_actions = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    credits_used = Column(Float, default=0.0)
    credits_saved = Column(Float, default=0.0)
    agents_used = Column(Integer, default=0)

    # Score and percentile
    score = Column(Float, nullable=False)
    percentile = Column(Float)

    # Achievements stored as JSON array
    achievements = Column(JSON, default=[])

    # Metadata
    calculated_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class WorkspaceLeaderboard(Base):
    """Workspace leaderboard rankings table."""

    __tablename__ = "workspace_leaderboard"
    __table_args__ = (
        Index('idx_workspace_leaderboard_timeframe', 'timeframe', 'criteria', 'rank'),
        Index('idx_workspace_leaderboard_rank', 'timeframe', 'criteria', 'rank'),
        Index('idx_workspace_leaderboard_calculated', 'calculated_at'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, index=True, nullable=False)

    # Ranking information
    rank = Column(Integer, nullable=False)
    previous_rank = Column(Integer)
    rank_change = Column(String(10))  # 'up', 'down', 'same', 'new'

    # Timeframe and criteria
    timeframe = Column(String(20), nullable=False)  # '24h', '7d', '30d', '90d', 'all'
    criteria = Column(String(50), nullable=False)  # 'activity', 'efficiency', 'growth', 'innovation'

    # Workspace metrics (snapshot)
    total_activity = Column(Integer, default=0)
    active_users = Column(Integer, default=0)
    agent_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    health_score = Column(Float, default=0.0)

    # Score and tier
    score = Column(Float, nullable=False)
    tier = Column(String(20))  # 'platinum', 'gold', 'silver', 'bronze'

    # Metadata
    calculated_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class ExecutionMetricsHourly(Base):
    """Hourly execution metrics aggregation table."""

    __tablename__ = "execution_metrics_hourly"
    __table_args__ = (
        Index('idx_exec_metrics_hourly_workspace_hour', 'workspace_id', 'hour'),
        Index('idx_exec_metrics_hourly_hour', 'hour'),
        {'schema': 'analytics'}
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(String, index=True, nullable=False)
    hour = Column(DateTime, index=True, nullable=False)

    # Execution counts
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)

    # Performance metrics
    avg_runtime = Column(Float, default=0.0)
    p50_runtime = Column(Float, default=0.0)
    p95_runtime = Column(Float, default=0.0)
    p99_runtime = Column(Float, default=0.0)

    # Resource consumption
    total_credits = Column(Integer, default=0)
    avg_credits_per_run = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class FunnelDefinition(Base):
    """Funnel definitions table."""

    __tablename__ = "funnel_definitions"
    __table_args__ = (
        Index('idx_funnel_definitions_workspace', 'workspace_id', 'status'),
        Index('idx_funnel_definitions_created', 'created_at'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    workspace_id = Column(String, index=True, nullable=False)

    # Funnel metadata
    name = Column(String(255), nullable=False)
    description = Column(String)
    status = Column(String(20), nullable=False, default='active')  # 'active', 'paused', 'archived'

    # Funnel configuration stored as JSON
    steps = Column(JSON, nullable=False)

    # Analysis settings
    timeframe = Column(String(20), default='30d')
    segment_by = Column(String(50))

    # Metadata
    created_by = Column(String)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class ExecutionMetricsDaily(Base):
    """Daily execution metrics aggregation table."""

    __tablename__ = "execution_metrics_daily"
    __table_args__ = (
        Index('idx_exec_metrics_daily_workspace_date', 'workspace_id', 'date'),
        Index('idx_exec_metrics_daily_date', 'date'),
        {'schema': 'analytics'}
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(String, index=True, nullable=False)
    date = Column(DateTime, index=True, nullable=False)

    # Execution counts
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)

    # Performance metrics
    avg_runtime = Column(Float, default=0.0)
    p50_runtime = Column(Float, default=0.0)
    p95_runtime = Column(Float, default=0.0)
    p99_runtime = Column(Float, default=0.0)

    # Resource consumption
    total_credits = Column(Integer, default=0)
    avg_credits_per_run = Column(Float, default=0.0)

    # Activity metrics
    unique_users = Column(Integer, default=0)
    unique_agents = Column(Integer, default=0)

    # Health score
    health_score = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class FunnelAnalysisResult(Base):
    """Funnel analysis results table."""

    __tablename__ = "funnel_analysis_results"
    __table_args__ = (
        Index('idx_funnel_results_funnel', 'funnel_id', 'analysis_start'),
        Index('idx_funnel_results_workspace_time', 'workspace_id', 'analysis_start', 'analysis_end'),
        Index('idx_funnel_results_calculated', 'calculated_at'),
        Index('idx_funnel_results_segment', 'funnel_id', 'segment_name'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    funnel_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)

    # Analysis timeframe
    analysis_start = Column(DateTime, nullable=False)
    analysis_end = Column(DateTime, nullable=False)

    # Step results stored as JSON array
    step_results = Column(JSON, nullable=False)

    # Overall funnel metrics
    total_entered = Column(Integer, nullable=False, default=0)
    total_completed = Column(Integer, nullable=False, default=0)
    overall_conversion_rate = Column(Float, nullable=False, default=0.0)
    avg_time_to_complete = Column(Float)
    biggest_drop_off_step = Column(String(255))
    biggest_drop_off_rate = Column(Float)

    # Segment analysis
    segment_name = Column(String(100))
    segment_results = Column(JSON)

    # Metadata
    calculated_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())


class FunnelStepPerformance(Base):
    """Funnel step performance table."""

    __tablename__ = "funnel_step_performance"
    __table_args__ = (
        Index('idx_funnel_step_performance_funnel', 'funnel_id', 'step_order', 'period_start'),
        Index('idx_funnel_step_performance_period', 'period_start', 'period_end'),
        Index('idx_funnel_step_performance_conversion', 'funnel_id', 'conversion_rate'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    funnel_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)

    # Step identification
    step_id = Column(String(100), nullable=False)
    step_name = Column(String(255), nullable=False)
    step_order = Column(Integer, nullable=False)
    event_name = Column(String(255), nullable=False)

    # Time period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Step metrics
    total_users = Column(Integer, nullable=False, default=0)
    unique_users = Column(Integer, nullable=False, default=0)
    users_from_previous_step = Column(Integer, nullable=False, default=0)
    conversion_rate = Column(Float, nullable=False, default=0.0)
    drop_off_rate = Column(Float, nullable=False, default=0.0)
    avg_time_from_previous = Column(Float)
    median_time_from_previous = Column(Float)

    # Drop-off analysis
    drop_off_reasons = Column(JSON)

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class UserActivityHourly(Base):
    """Hourly user activity aggregation table."""

    __tablename__ = "user_activity_hourly"
    __table_args__ = (
        Index('idx_user_activity_hourly_workspace_hour', 'workspace_id', 'hour'),
        Index('idx_user_activity_hourly_user_hour', 'user_id', 'hour'),
        {'schema': 'analytics'}
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    hour = Column(DateTime, index=True, nullable=False)

    # Activity counts
    total_events = Column(Integer, default=0)
    page_views = Column(Integer, default=0)
    unique_sessions = Column(Integer, default=0)

    # Engagement metrics
    active_duration_seconds = Column(Float, default=0.0)
    avg_session_duration = Column(Float, default=0.0)

    # Event type breakdown (JSON for flexibility)
    event_type_counts = Column(JSON, default={})

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class CreditConsumptionHourly(Base):
    """Hourly credit consumption aggregation table."""

    __tablename__ = "credit_consumption_hourly"
    __table_args__ = (
        Index('idx_credit_hourly_workspace_hour', 'workspace_id', 'hour'),
        Index('idx_credit_hourly_user_hour', 'user_id', 'hour'),
        {'schema': 'analytics'}
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=True)
    agent_id = Column(String, index=True, nullable=True)
    hour = Column(DateTime, index=True, nullable=False)

    # Credit metrics
    total_credits = Column(Integer, default=0)
    avg_credits_per_execution = Column(Float, default=0.0)
    peak_credits_per_execution = Column(Integer, default=0)

    # Efficiency metrics
    executions_count = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    credits_per_success = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class UserFunnelJourney(Base):
    """User funnel journeys table."""

    __tablename__ = "user_funnel_journeys"
    __table_args__ = (
        Index('idx_user_journeys_funnel_status', 'funnel_id', 'status', 'started_at'),
        Index('idx_user_journeys_user', 'user_id', 'started_at'),
        Index('idx_user_journeys_workspace', 'workspace_id', 'started_at'),
        Index('idx_user_journeys_segment', 'funnel_id', 'user_segment'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    funnel_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)

    # Journey tracking
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    last_step_reached = Column(String(100))
    last_step_order = Column(Integer)
    status = Column(String(20), nullable=False)  # 'in_progress', 'completed', 'abandoned'

    # Journey path
    journey_path = Column(JSON, nullable=False, default=lambda: [])

    # Time metrics
    total_time_spent = Column(Float)
    time_per_step = Column(JSON)

    # User segment
    user_segment = Column(String(100))

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class AlertRule(Base):
    """Alert rules configuration table."""

    __tablename__ = "alert_rules"
    __table_args__ = (
        Index('idx_alert_rules_workspace', 'workspace_id', 'is_active'),
        Index('idx_alert_rules_workspace_name', 'workspace_id', 'rule_name', unique=True),
        Index('idx_alert_rules_active_next_check', 'is_active', 'last_evaluated_at'),
        Index('idx_alert_rules_severity', 'severity'),
        {'schema': 'analytics'}
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    workspace_id = Column(PG_UUID(as_uuid=True), index=True, nullable=False)
    rule_name = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    metric_type = Column(String(100), nullable=False)
    condition_type = Column(String(50), nullable=False)  # 'threshold', 'change', 'anomaly', 'pattern'
    condition_config = Column(JSON, nullable=False)
    severity = Column(String(20), nullable=False)  # 'info', 'warning', 'critical', 'emergency'
    is_active = Column(Boolean, nullable=False, default=True)
    check_interval_minutes = Column(Integer, nullable=False, default=5)
    cooldown_minutes = Column(Integer, nullable=False, default=60)
    notification_channels = Column(JSON, nullable=False)
    escalation_policy_id = Column(PG_UUID(as_uuid=True), ForeignKey('analytics.escalation_policies.id', ondelete='SET NULL'), nullable=True)
    created_by = Column(PG_UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_evaluated_at = Column(DateTime, nullable=True)
    last_triggered_at = Column(DateTime, nullable=True)


class Alert(Base):
    """Alert instances table."""

    __tablename__ = "alerts"
    __table_args__ = (
        Index('idx_alerts_workspace', 'workspace_id', 'triggered_at'),
        Index('idx_alerts_unresolved', 'workspace_id', 'resolved_at'),
        Index('idx_alerts_severity', 'severity', 'acknowledged_at'),
        Index('idx_alerts_rule', 'rule_id', 'triggered_at'),
        Index('idx_alerts_escalation', 'escalated', 'escalation_level'),
        {'schema': 'analytics'}
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    workspace_id = Column(PG_UUID(as_uuid=True), index=True, nullable=False)
    rule_id = Column(PG_UUID(as_uuid=True), ForeignKey('analytics.alert_rules.id', ondelete='CASCADE'), nullable=False)
    alert_title = Column(String(500), nullable=False)
    alert_message = Column(String, nullable=False)
    severity = Column(String(20), nullable=False)
    metric_value = Column(Numeric, nullable=True)
    threshold_value = Column(Numeric, nullable=True)
    triggered_at = Column(DateTime, nullable=False)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(PG_UUID(as_uuid=True), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(PG_UUID(as_uuid=True), nullable=True)
    resolution_notes = Column(String, nullable=True)
    alert_context = Column(JSON, nullable=True)
    notification_sent = Column(Boolean, nullable=False, default=False)
    notification_channels = Column(JSON, nullable=True)
    escalated = Column(Boolean, nullable=False, default=False)
    escalation_level = Column(Integer, nullable=False, default=0)


class NotificationHistory(Base):
    """Notification history table."""

    __tablename__ = "notification_history"
    __table_args__ = (
        Index('idx_notifications_alert', 'alert_id'),
        Index('idx_notifications_status', 'delivery_status', 'sent_at'),
        Index('idx_notifications_channel', 'channel', 'sent_at'),
        {'schema': 'analytics'}
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    alert_id = Column(PG_UUID(as_uuid=True), ForeignKey('analytics.alerts.id', ondelete='CASCADE'), nullable=False)
    channel = Column(String(50), nullable=False)
    recipient = Column(String, nullable=False)
    sent_at = Column(DateTime, nullable=False, default=func.now())
    delivery_status = Column(String(20), nullable=False)  # 'pending', 'sent', 'failed', 'bounced'
    error_message = Column(String, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    response_data = Column(JSON, nullable=True)


class EscalationPolicy(Base):
    """Escalation policies table."""

    __tablename__ = "escalation_policies"
    __table_args__ = (
        Index('idx_escalation_policies_workspace', 'workspace_id'),
        Index('idx_escalation_policies_workspace_name', 'workspace_id', 'policy_name', unique=True),
        {'schema': 'analytics'}
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    workspace_id = Column(PG_UUID(as_uuid=True), index=True, nullable=False)
    policy_name = Column(String(255), nullable=False)
    escalation_levels = Column(JSON, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class AlertSuppression(Base):
    """Alert suppression rules table."""

    __tablename__ = "alert_suppressions"
    __table_args__ = (
        Index('idx_suppression_active', 'workspace_id', 'start_time', 'end_time'),
        Index('idx_suppression_time_range', 'start_time', 'end_time'),
        {'schema': 'analytics'}
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    workspace_id = Column(PG_UUID(as_uuid=True), index=True, nullable=False)
    suppression_type = Column(String(50), nullable=False)  # 'rule', 'pattern', 'maintenance'
    pattern = Column(JSON, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    reason = Column(String, nullable=True)
    created_by = Column(PG_UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=func.now())
