"""SQLAlchemy database models."""

from uuid import uuid4
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, JSON, Enum, Index, Numeric, Date
from sqlalchemy.dialects import postgresql
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


class AnomalyDetection(Base):
    """Anomaly detections table."""

    __tablename__ = "anomaly_detections"
    __table_args__ = (
        Index('idx_anomaly_workspace_time', 'workspace_id', 'detected_at'),
        Index('idx_anomaly_severity_ack', 'severity', 'is_acknowledged'),
        Index('idx_anomaly_metric_workspace', 'metric_type', 'workspace_id'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    workspace_id = Column(String, index=True, nullable=False)
    metric_type = Column(String(100), index=True, nullable=False)
    detected_at = Column(DateTime, index=True, nullable=False)
    anomaly_value = Column(Numeric)
    expected_range = Column(JSON)
    anomaly_score = Column(Numeric, nullable=False)
    severity = Column(String(20), index=True, nullable=False)  # low, medium, high, critical
    detection_method = Column(String(50), nullable=False)  # zscore, isolation_forest, lstm, threshold
    context = Column(JSON)
    is_acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_by = Column(String)
    acknowledged_at = Column(DateTime)
    notes = Column(String)
    created_at = Column(DateTime, default=func.now())


class AnomalyRule(Base):
    """Anomaly detection rules configuration table."""

    __tablename__ = "anomaly_rules"
    __table_args__ = (
        Index('idx_anomaly_rules_workspace_metric', 'workspace_id', 'metric_type'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    workspace_id = Column(String, index=True)  # NULL = global rule
    metric_type = Column(String(100), index=True, nullable=False)
    rule_name = Column(String(255), nullable=False)
    detection_method = Column(String(50), nullable=False)
    parameters = Column(JSON, nullable=False)
    is_active = Column(Boolean, index=True, default=True, nullable=False)
    auto_alert = Column(Boolean, default=False, nullable=False)
    alert_channels = Column(JSON)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class BaselineModel(Base):
    """Baseline models storage for anomaly detection."""

    __tablename__ = "baseline_models"
    __table_args__ = (
        Index('idx_baseline_models_workspace_metric', 'workspace_id', 'metric_type'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    workspace_id = Column(String, index=True, nullable=False)
    metric_type = Column(String(100), index=True, nullable=False)
    model_type = Column(String(50), index=True, nullable=False)  # zscore, isolation_forest, lstm
    model_parameters = Column(JSON, nullable=False)
    statistics = Column(JSON, nullable=False)  # mean, std, percentiles
    training_data_start = Column(Date, nullable=False)
    training_data_end = Column(Date, nullable=False)
    accuracy_metrics = Column(JSON)
    last_updated = Column(DateTime, default=func.now())


# =====================================================================
# Authentication and Authorization Models
# =====================================================================


class APIKey(Base):
    """API keys for programmatic access to analytics."""

    __tablename__ = "api_keys"
    __table_args__ = (
        Index('idx_api_keys_workspace', 'workspace_id'),
        Index('idx_api_keys_user', 'user_id'),
        Index('idx_api_keys_active', 'is_active'),
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    user_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)

    # Permissions and access control
    permissions = Column(JSON, default=list, nullable=False)
    rate_limit = Column(Integer, default=1000)  # requests per hour

    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_used = Column(DateTime, index=True)
    usage_count = Column(Integer, default=0)

    # Expiration
    expires_at = Column(DateTime, index=True)

    # Audit fields
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    revoked_at = Column(DateTime)
    revoked_by = Column(String)


class UserSession(Base):
    """User sessions for tracking active login sessions."""

    __tablename__ = "user_sessions"
    __table_args__ = (
        Index('idx_user_sessions_user', 'user_id'),
        Index('idx_user_sessions_active', 'is_active'),
        Index('idx_user_sessions_user_active', 'user_id', 'is_active'),
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    user_id = Column(String, index=True, nullable=False)

    # Session token (hashed)
    session_token_hash = Column(String(255), unique=True, nullable=False, index=True)

    # Device and location information
    device_info = Column(String(255))
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(String(500))

    # Geolocation
    country_code = Column(String(2))
    city = Column(String(100))
    location = Column(String(255))  # Combined location string

    # Session status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=func.now(), index=True)
    last_active = Column(DateTime, default=func.now(), index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    terminated_at = Column(DateTime)


class RefreshToken(Base):
    """Refresh tokens for token renewal without re-authentication."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index('idx_refresh_tokens_user', 'user_id'),
        Index('idx_refresh_tokens_active', 'is_active'),
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    user_id = Column(String, index=True, nullable=False)

    # Token (hashed)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)

    # Associated access token (for revocation)
    access_token_jti = Column(String(255), index=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_revoked = Column(Boolean, default=False, nullable=False)

    # Device tracking
    device_info = Column(String(255))
    ip_address = Column(String(45))

    # Timestamps
    created_at = Column(DateTime, default=func.now(), index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime)
    last_used = Column(DateTime)


# =====================================================================
# Notification System Models
# =====================================================================


class NotificationPreference(Base):
    """User notification preferences per workspace and type."""

    __tablename__ = "notification_preferences"
    __table_args__ = (
        Index('idx_notification_prefs_user', 'user_id', 'workspace_id'),
        Index('idx_notification_prefs_type', 'notification_type', 'is_enabled'),
        Index('idx_notification_prefs_enabled', 'is_enabled', 'channel'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    user_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)
    notification_type = Column(String(100), nullable=False)
    channel = Column(String(50), nullable=False)
    is_enabled = Column(Boolean, default=True)
    frequency = Column(String(20), default='immediate')  # immediate, hourly, daily, weekly
    schedule_time = Column(DateTime)
    schedule_timezone = Column(String(50), default='UTC')
    filter_rules = Column(JSON, default={})

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class NotificationTemplate(Base):
    """Notification templates for different channels."""

    __tablename__ = "notification_templates"
    __table_args__ = (
        Index('idx_notification_templates_type', 'notification_type', 'channel', 'is_active'),
        Index('idx_notification_templates_active', 'is_active'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    template_name = Column(String(255), unique=True, nullable=False)
    notification_type = Column(String(100), nullable=False)
    channel = Column(String(50), nullable=False)
    subject_template = Column(String)
    body_template = Column(String, nullable=False)
    variables = Column(JSON, nullable=False, default=[])
    preview_data = Column(JSON)
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class NotificationQueue(Base):
    """Queue for pending and scheduled notifications."""

    __tablename__ = "notification_queue"
    __table_args__ = (
        Index('idx_notification_queue_status', 'status', 'scheduled_for'),
        Index('idx_notification_queue_recipient', 'recipient_id', 'status'),
        Index('idx_notification_queue_scheduled', 'scheduled_for'),
        Index('idx_notification_queue_priority', 'priority', 'scheduled_for'),
        Index('idx_notification_queue_created', 'created_at'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    notification_type = Column(String(100), nullable=False)
    recipient_id = Column(String, index=True, nullable=False)
    recipient_email = Column(String(255))
    channel = Column(String(50), nullable=False)
    priority = Column(String(20), default='normal')  # low, normal, high, urgent
    payload = Column(JSON, nullable=False, default={})
    status = Column(String(20), default='pending')  # pending, processing, delivered, failed, cancelled
    scheduled_for = Column(DateTime, default=func.now())
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    last_attempt_at = Column(DateTime)
    delivered_at = Column(DateTime)
    failed_at = Column(DateTime)
    error_message = Column(String)

    created_at = Column(DateTime, default=func.now())


class NotificationLog(Base):
    """Historical log of all sent notifications."""

    __tablename__ = "notification_log"
    __table_args__ = (
        Index('idx_notification_log_user', 'user_id', 'sent_at'),
        Index('idx_notification_log_workspace', 'workspace_id', 'notification_type', 'sent_at'),
        Index('idx_notification_log_type', 'notification_type', 'sent_at'),
        Index('idx_notification_log_channel', 'channel', 'sent_at'),
        Index('idx_notification_log_status', 'delivery_status', 'sent_at'),
        Index('idx_notification_log_unread', 'user_id', 'read_at'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    notification_id = Column(String, index=True)  # Reference to notification_queue
    user_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)
    notification_type = Column(String(100), nullable=False)
    channel = Column(String(50), nullable=False)
    subject = Column(String)
    preview = Column(String)
    full_content = Column(String)
    sent_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    delivered_at = Column(DateTime)
    read_at = Column(DateTime)
    clicked_at = Column(DateTime)
    delivery_status = Column(String(20), nullable=False)  # sent, delivered, bounced, failed, read, clicked
    tracking_data = Column(JSON, default={})

    created_at = Column(DateTime, default=func.now())


class DigestQueue(Base):
    """Queue for periodic digest notifications."""

    __tablename__ = "digest_queue"
    __table_args__ = (
        Index('idx_digest_queue_pending', 'is_sent', 'period_end'),
        Index('idx_digest_queue_user', 'user_id', 'workspace_id', 'digest_type'),
        Index('idx_digest_queue_period', 'period_start', 'period_end'),
        Index('idx_digest_queue_unique', 'user_id', 'workspace_id', 'digest_type', 'period_start', unique=True),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    user_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)
    digest_type = Column(String(50), nullable=False)  # daily, weekly, monthly, custom
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    events = Column(JSON, nullable=False, default=[])
    summary_stats = Column(JSON, default={})
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime)
    notification_id = Column(String)  # Reference to notification_queue

    created_at = Column(DateTime, default=func.now())


class NotificationChannel(Base):
    """Channel configuration per workspace (webhooks, API keys)."""

    __tablename__ = "notification_channels"
    __table_args__ = (
        Index('idx_notification_channels_workspace', 'workspace_id', 'is_enabled'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    workspace_id = Column(String, index=True, nullable=False)
    channel = Column(String(50), nullable=False)  # email, slack, teams, discord, webhook
    is_enabled = Column(Boolean, default=True)
    configuration = Column(JSON, nullable=False, default={})  # Webhook URLs, API keys, etc.
    last_test_at = Column(DateTime)
    last_test_status = Column(String(20))  # success, failed

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class NotificationSubscription(Base):
    """User subscriptions to specific notification topics."""

    __tablename__ = "notification_subscriptions"
    __table_args__ = (
        Index('idx_notification_subscriptions_user', 'user_id', 'workspace_id'),
        Index('idx_notification_subscriptions_type', 'subscription_type', 'is_subscribed'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    user_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)
    subscription_type = Column(String(100), nullable=False)
    is_subscribed = Column(Boolean, default=True)
    metadata = Column(JSON, default={})

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# =====================================================================
# Reports System Models
# =====================================================================


class ReportJob(Base):
    """Report generation jobs table."""

    __tablename__ = "report_jobs"
    __table_args__ = (
        Index('idx_report_jobs_workspace_created', 'workspace_id', 'created_at'),
        Index('idx_report_jobs_status', 'status', 'created_at'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    workspace_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)

    # Report configuration
    report_name = Column(String(255), nullable=False)
    template_id = Column(String, index=True)
    report_format = Column(String(20), nullable=False)  # pdf, excel, csv, json
    sections = Column(JSON, default=[])
    date_range = Column(JSON)
    filters = Column(JSON, default={})
    delivery_config = Column(JSON)

    # Job status
    status = Column(String(20), index=True, nullable=False, default='queued')  # queued, processing, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    current_section = Column(String(100))

    # Results
    file_path = Column(String)
    file_size = Column(Integer)
    page_count = Column(Integer)
    download_url = Column(String)

    # Error handling
    error_message = Column(String)
    retry_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=func.now(), index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    expires_at = Column(DateTime)
    generation_time = Column(Float)  # seconds


class ReportTemplate(Base):
    """Report templates table."""

    __tablename__ = "report_templates"
    __table_args__ = (
        Index('idx_report_templates_workspace_category', 'workspace_id', 'category'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    workspace_id = Column(String, index=True)  # NULL for global templates

    # Template metadata
    name = Column(String(255), nullable=False)
    description = Column(String)
    category = Column(String(50), index=True)  # executive, operational, technical, financial
    is_custom = Column(Boolean, default=False, nullable=False)

    # Template configuration
    sections = Column(JSON, nullable=False)  # Array of section definitions
    layout = Column(JSON)  # Page layout settings
    supported_formats = Column(JSON, default=['pdf', 'excel'])

    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime)

    # Metadata
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True, nullable=False)


class ReportSchedule(Base):
    """Scheduled reports table."""

    __tablename__ = "report_schedules"
    __table_args__ = (
        Index('idx_report_schedules_workspace_active', 'workspace_id', 'is_active'),
        Index('idx_report_schedules_next_run', 'next_run_at'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    workspace_id = Column(String, index=True, nullable=False)

    # Schedule configuration
    name = Column(String(255), nullable=False)
    template_id = Column(String, index=True, nullable=False)
    frequency = Column(String(20), nullable=False)  # daily, weekly, monthly, quarterly
    schedule_config = Column(JSON, nullable=False)  # time, timezone, day_of_week, etc.

    # Recipients
    recipients = Column(JSON, nullable=False)  # emails, slack_channels, webhooks

    # Filters
    filters = Column(JSON, default={})

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_run_at = Column(DateTime)
    next_run_at = Column(DateTime, index=True)
    last_job_id = Column(String)
    last_status = Column(String(20))

    # Statistics
    successful_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)

    # Metadata
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class GeneratedReport(Base):
    """Historical generated reports table."""

    __tablename__ = "generated_reports"
    __table_args__ = (
        Index('idx_generated_reports_workspace_date', 'workspace_id', 'generated_at'),
        Index('idx_generated_reports_type', 'report_type', 'generated_at'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    workspace_id = Column(String, index=True, nullable=False)
    job_id = Column(String, index=True)

    # Report metadata
    report_name = Column(String(255), nullable=False)
    report_type = Column(String(50), index=True)  # scheduled, manual, ad-hoc
    template_id = Column(String, index=True)

    # File information
    file_path = Column(String, nullable=False)
    filename = Column(String(255), nullable=False)
    file_format = Column(String(20), nullable=False)
    file_size = Column(Integer)
    page_count = Column(Integer)
    content_type = Column(String(100))

    # Access control
    generated_by = Column(String, nullable=False)
    shared_with = Column(JSON, default=[])
    is_public = Column(Boolean, default=False)

    # Download tracking
    download_count = Column(Integer, default=0)
    last_downloaded_at = Column(DateTime)

    # Timestamps
    generated_at = Column(DateTime, default=func.now(), index=True)
    expires_at = Column(DateTime, index=True)


class ReportShare(Base):
    """Report sharing links table."""

    __tablename__ = "report_shares"
    __table_args__ = (
        Index('idx_report_shares_report_created', 'report_id', 'created_at'),
        Index('idx_report_shares_token', 'share_token'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    report_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)

    # Share configuration
    share_token = Column(String(100), unique=True, index=True, nullable=False)
    share_url = Column(String, nullable=False)
    recipients = Column(JSON, default=[])
    message = Column(String)

    # Access control
    password_hash = Column(String)
    require_password = Column(Boolean, default=False)
    allow_download = Column(Boolean, default=True)

    # Tracking
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime)

    # Metadata
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)


class ReportWebhook(Base):
    """Report webhooks table."""

    __tablename__ = "report_webhooks"
    __table_args__ = (
        Index('idx_report_webhooks_workspace_active', 'workspace_id', 'is_active'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    workspace_id = Column(String, index=True, nullable=False)

    # Webhook configuration
    url = Column(String, nullable=False)
    events = Column(JSON, nullable=False)  # report.generated, report.failed, etc.
    secret = Column(String)

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Statistics
    total_deliveries = Column(Integer, default=0)
    successful_deliveries = Column(Integer, default=0)
    failed_deliveries = Column(Integer, default=0)
    last_delivery_at = Column(DateTime)
    last_delivery_status = Column(String(20))

    # Metadata
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# =====================================================================
# Agent Collaboration Analytics Models
# =====================================================================


class MultiAgentWorkflow(Base):
    """Multi-agent workflows table."""

    __tablename__ = "multi_agent_workflows"
    __table_args__ = (
        Index('idx_workflows_workspace_status', 'workspace_id', 'status'),
        Index('idx_workflows_started', 'started_at'),
        Index('idx_workflows_workflow_type', 'workflow_type', 'started_at'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    workflow_id = Column(String, unique=True, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)

    # Workflow definition
    workflow_name = Column(String(255), nullable=False)
    workflow_type = Column(String(50), index=True)  # sequential, parallel, conditional, hybrid
    workflow_version = Column(String(50))
    workflow_definition = Column(JSON, nullable=False)  # Complete workflow configuration

    # Execution metrics
    status = Column(String(20), index=True, nullable=False)  # running, completed, failed, partial
    started_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    completed_at = Column(DateTime)
    total_duration_ms = Column(Integer)

    # Collaboration metrics
    agents_involved = Column(Integer, default=0)
    handoffs_count = Column(Integer, default=0)
    parallel_executions = Column(Integer, default=0)
    coordination_efficiency = Column(Float)  # 0-1 score
    communication_overhead = Column(Float)  # percentage
    bottleneck_score = Column(Float)  # 0-1 score (higher = more bottlenecks)
    synergy_index = Column(Float)  # 0-1 score (higher = better synergy)

    # Performance metrics
    success_rate = Column(Float)
    resource_cost = Column(Float)

    # Metadata
    created_by = Column(String)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class AgentInteraction(Base):
    """Agent interactions table."""

    __tablename__ = "agent_interactions"
    __table_args__ = (
        Index('idx_interactions_workflow', 'workflow_id', 'created_at'),
        Index('idx_interactions_agents', 'source_agent_id', 'target_agent_id'),
        Index('idx_interactions_type', 'interaction_type', 'created_at'),
        Index('idx_interactions_workspace', 'workspace_id', 'created_at'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    workflow_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)
    source_agent_id = Column(String, index=True, nullable=False)
    target_agent_id = Column(String, index=True, nullable=False)

    # Interaction details
    interaction_type = Column(String(50), index=True)  # handoff, request, response, notification, sync
    payload_size_bytes = Column(Integer)
    data_transferred = Column(JSON)
    transformation_applied = Column(String)

    # Performance metrics
    interaction_duration_ms = Column(Integer)
    queue_time_ms = Column(Integer)
    processing_time_ms = Column(Integer)

    # Quality metrics
    data_quality_score = Column(Float)
    compatibility_score = Column(Float)
    error_occurred = Column(Boolean, default=False, nullable=False)
    retry_count = Column(Integer, default=0)

    # Error details
    error_message = Column(String)
    error_type = Column(String(100))

    created_at = Column(DateTime, default=func.now(), index=True)


class AgentHandoff(Base):
    """Agent handoffs table."""

    __tablename__ = "agent_handoffs"
    __table_args__ = (
        Index('idx_handoffs_workflow', 'workflow_id', 'handoff_time'),
        Index('idx_handoffs_agents', 'source_agent_id', 'target_agent_id'),
        Index('idx_handoffs_success', 'handoff_success', 'handoff_time'),
        Index('idx_handoffs_workspace', 'workspace_id', 'handoff_time'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    handoff_id = Column(String, unique=True, index=True, nullable=False)
    workflow_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)
    source_agent_id = Column(String, index=True, nullable=False)
    target_agent_id = Column(String, index=True, nullable=False)

    # Handoff performance
    preparation_time_ms = Column(Integer)
    transfer_time_ms = Column(Integer)
    acknowledgment_time_ms = Column(Integer)
    total_handoff_time_ms = Column(Integer)

    # Data metrics
    data_size_bytes = Column(Integer)
    data_completeness = Column(Float)  # 0-1 score
    schema_compatible = Column(Boolean)
    transformation_required = Column(Boolean)

    # Quality metrics
    handoff_success = Column(Boolean, nullable=False, index=True)
    data_integrity_maintained = Column(Boolean)
    context_preserved = Column(Float)  # 0-1 score
    information_loss = Column(Float)  # percentage

    # Recovery metrics
    retry_attempts = Column(Integer, default=0)
    recovery_strategy = Column(String(100))
    recovery_time_ms = Column(Integer)

    # Failure details
    failure_reason = Column(String)

    handoff_time = Column(DateTime, nullable=False, default=func.now(), index=True)
    created_at = Column(DateTime, default=func.now())


class AgentDependency(Base):
    """Agent dependencies table."""

    __tablename__ = "agent_dependencies"
    __table_args__ = (
        Index('idx_dependencies_workspace', 'workspace_id', 'is_active'),
        Index('idx_dependencies_agents', 'agent_id', 'depends_on_agent_id'),
        Index('idx_dependencies_type', 'dependency_type', 'is_active'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    workspace_id = Column(String, index=True, nullable=False)
    agent_id = Column(String, index=True, nullable=False)
    depends_on_agent_id = Column(String, index=True, nullable=False)

    # Dependency details
    dependency_type = Column(String(50), index=True)  # data, control, sequence, conditional
    dependency_strength = Column(Float)  # 0-1 score (1 = critical dependency)
    is_circular = Column(Boolean, default=False)
    is_critical_path = Column(Boolean, default=False, index=True)

    # Dependency metadata
    description = Column(String)
    dependency_definition = Column(JSON)

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_verified = Column(DateTime)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class CollaborationMetrics(Base):
    """Collaboration metrics aggregation table."""

    __tablename__ = "collaboration_metrics"
    __table_args__ = (
        Index('idx_collab_metrics_workspace_period', 'workspace_id', 'period_start', 'period_end'),
        Index('idx_collab_metrics_agent_period', 'agent_id', 'period_start'),
        Index('idx_collab_metrics_calculated', 'calculated_at'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    workspace_id = Column(String, index=True, nullable=False)
    agent_id = Column(String, index=True)  # NULL for workspace-level metrics

    # Time period
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    period_type = Column(String(20), nullable=False)  # hourly, daily, weekly, monthly

    # Collaboration efficiency
    collaboration_efficiency_score = Column(Float)
    avg_interaction_time_ms = Column(Float)
    error_rate = Column(Float)
    avg_quality_score = Column(Float)
    avg_compatibility = Column(Float)

    # Workflow metrics
    workflows_participated = Column(Integer, default=0)
    successful_workflows = Column(Integer, default=0)
    failed_workflows = Column(Integer, default=0)
    avg_workflow_duration_ms = Column(Float)

    # Interaction metrics
    total_interactions = Column(Integer, default=0)
    outgoing_interactions = Column(Integer, default=0)
    incoming_interactions = Column(Integer, default=0)
    handoffs_given = Column(Integer, default=0)
    handoffs_received = Column(Integer, default=0)

    # Load metrics
    avg_queue_length = Column(Float)
    peak_load = Column(Integer)
    idle_time_percentage = Column(Float)
    load_variance = Column(Float)

    # Collective intelligence metrics
    diversity_index = Column(Float)
    collective_accuracy = Column(Float)
    emergence_score = Column(Float)
    adaptation_rate = Column(Float)

    calculated_at = Column(DateTime, default=func.now(), index=True)
    created_at = Column(DateTime, default=func.now())


class WorkflowExecutionStep(Base):
    """Workflow execution steps table."""

    __tablename__ = "workflow_execution_steps"
    __table_args__ = (
        Index('idx_workflow_steps_workflow', 'workflow_id', 'step_order'),
        Index('idx_workflow_steps_agent', 'agent_id', 'started_at'),
        Index('idx_workflow_steps_status', 'status', 'started_at'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    workflow_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)
    agent_id = Column(String, index=True, nullable=False)

    # Step details
    step_id = Column(String(100), nullable=False)
    step_name = Column(String(255), nullable=False)
    step_order = Column(Integer, nullable=False)
    step_type = Column(String(50))  # sequential, parallel, conditional

    # Execution metrics
    status = Column(String(20), nullable=False, index=True)  # queued, running, completed, failed, skipped
    started_at = Column(DateTime, nullable=False, index=True)
    completed_at = Column(DateTime)
    duration_ms = Column(Integer)
    queue_time_ms = Column(Integer)

    # Dependencies
    depends_on_steps = Column(JSON, default=[])
    blocking_steps = Column(JSON, default=[])

    # Performance
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    credits_used = Column(Integer)

    # Results
    output_data = Column(JSON)
    error_message = Column(String)

    created_at = Column(DateTime, default=func.now())


class CollaborationPattern(Base):
    """Detected collaboration patterns table."""

    __tablename__ = "collaboration_patterns"
    __table_args__ = (
        Index('idx_collab_patterns_workspace_type', 'workspace_id', 'pattern_type'),
        Index('idx_collab_patterns_detected', 'detected_at'),
        Index('idx_collab_patterns_frequency', 'occurrence_frequency'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    workspace_id = Column(String, index=True, nullable=False)
    pattern_id = Column(String(100), unique=True, index=True, nullable=False)

    # Pattern details
    pattern_type = Column(String(50), index=True, nullable=False)  # common_workflow, cluster, communication, bottleneck
    pattern_name = Column(String(255), nullable=False)
    pattern_description = Column(String)

    # Pattern data
    agents_involved = Column(JSON, nullable=False)
    pattern_definition = Column(JSON, nullable=False)

    # Pattern metrics
    occurrence_frequency = Column(Integer, default=0, index=True)
    success_rate = Column(Float)
    avg_performance = Column(Float)
    efficiency_score = Column(Float)

    # Pattern insights
    optimization_opportunities = Column(JSON)
    redundancy_detected = Column(Boolean, default=False)
    is_optimal = Column(Boolean, default=False)

    # Detection metadata
    detected_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    last_seen = Column(DateTime)
    detection_confidence = Column(Float)  # 0-1 score

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class LoadBalancingMetric(Base):
    """Load balancing metrics table."""

    __tablename__ = "load_balancing_metrics"
    __table_args__ = (
        Index('idx_load_metrics_workspace_period', 'workspace_id', 'period_start'),
        Index('idx_load_metrics_agent', 'agent_id', 'period_start'),
        Index('idx_load_metrics_imbalance', 'gini_coefficient'),
        {'schema': 'analytics'}
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    workspace_id = Column(String, index=True, nullable=False)

    # Time period
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)
    period_type = Column(String(20), nullable=False)  # hourly, daily, weekly

    # Load distribution (per agent stored as JSON)
    load_distribution = Column(JSON, nullable=False)

    # Imbalance metrics
    gini_coefficient = Column(Float, index=True)  # 0 = perfect equality, 1 = maximum inequality
    load_skewness = Column(Float)
    load_variance = Column(Float)

    # Identified agents
    overloaded_agents = Column(JSON, default=[])
    underutilized_agents = Column(JSON, default=[])

    # Recommendations
    rebalancing_strategy = Column(String(100))
    agent_scaling_recommendations = Column(JSON)
    workflow_reassignment_suggestions = Column(JSON)

    calculated_at = Column(DateTime, default=func.now(), index=True)
    created_at = Column(DateTime, default=func.now())
