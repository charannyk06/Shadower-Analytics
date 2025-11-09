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
