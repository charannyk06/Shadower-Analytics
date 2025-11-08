"""Agent schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class AgentMetrics(BaseModel):
    """Agent basic metrics."""

    agent_id: str
    agent_name: str
    total_executions: int = 0
    success_rate: float = 0.0
    avg_duration: float = 0.0
    last_execution: Optional[datetime] = None


class AgentPerformance(BaseModel):
    """Detailed agent performance metrics."""

    agent_id: str
    agent_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    avg_duration: float
    p95_duration: float
    p99_duration: float
    error_rate: float
    trends: Optional[List[Dict]] = None


class AgentStats(BaseModel):
    """Statistical analysis for agent."""

    agent_id: str
    stats: Dict
    distribution: Optional[Dict] = None
    percentiles: Optional[Dict] = None
