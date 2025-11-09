"""SQLAlchemy database models."""

from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, JSON, Enum, Index
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
