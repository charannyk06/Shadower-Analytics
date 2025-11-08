"""Workspace schemas."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class WorkspaceMetrics(BaseModel):
    """Workspace basic metrics."""

    workspace_id: str
    workspace_name: str
    total_users: int = 0
    total_agents: int = 0
    total_executions: int = 0
    created_at: Optional[datetime] = None


class WorkspaceStats(BaseModel):
    """Detailed workspace statistics."""

    workspace_id: str
    workspace_name: str
    total_users: int
    active_users: int
    total_agents: int
    active_agents: int
    total_executions: int
    success_rate: float
    avg_credits_per_day: float
    total_credits_used: int
