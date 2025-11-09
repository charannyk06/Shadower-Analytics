"""Leaderboard schemas for competitive rankings."""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TimeFrame(str, Enum):
    """Timeframe enumeration for leaderboards."""

    TWENTY_FOUR_HOURS = "24h"
    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"
    NINETY_DAYS = "90d"
    ALL_TIME = "all"


class RankChange(str, Enum):
    """Rank change direction."""

    UP = "up"
    DOWN = "down"
    SAME = "same"
    NEW = "new"


class Badge(str, Enum):
    """Achievement badges for top performers."""

    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"


class Tier(str, Enum):
    """Performance tiers."""

    PLATINUM = "platinum"
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"


class AgentCriteria(str, Enum):
    """Ranking criteria for agents."""

    RUNS = "runs"
    SUCCESS_RATE = "success_rate"
    SPEED = "speed"
    EFFICIENCY = "efficiency"
    POPULARITY = "popularity"


class UserCriteria(str, Enum):
    """Ranking criteria for users."""

    ACTIVITY = "activity"
    EFFICIENCY = "efficiency"
    CONTRIBUTION = "contribution"
    SAVINGS = "savings"


class WorkspaceCriteria(str, Enum):
    """Ranking criteria for workspaces."""

    ACTIVITY = "activity"
    EFFICIENCY = "efficiency"
    GROWTH = "growth"
    INNOVATION = "innovation"


# ===================================================================
# AGENT LEADERBOARD SCHEMAS
# ===================================================================

class AgentInfo(BaseModel):
    """Agent information in leaderboard."""

    id: str
    name: str
    type: str
    workspace: str


class AgentMetrics(BaseModel):
    """Agent performance metrics."""

    totalRuns: int = Field(0, alias="total_runs")
    successRate: float = Field(0.0, alias="success_rate")
    avgRuntime: float = Field(0.0, alias="avg_runtime")
    creditsPerRun: float = Field(0.0, alias="credits_per_run")
    uniqueUsers: int = Field(0, alias="unique_users")

    class Config:
        allow_population_by_field_name = True


class AgentRanking(BaseModel):
    """Agent ranking entry."""

    rank: int
    previousRank: Optional[int] = Field(None, alias="previous_rank")
    change: RankChange
    agent: AgentInfo
    metrics: AgentMetrics
    score: float
    percentile: float
    badge: Optional[Badge] = None

    class Config:
        allow_population_by_field_name = True


class AgentLeaderboardData(BaseModel):
    """Agent leaderboard data."""

    criteria: AgentCriteria
    rankings: List[AgentRanking]


# ===================================================================
# USER LEADERBOARD SCHEMAS
# ===================================================================

class UserInfo(BaseModel):
    """User information in leaderboard."""

    id: str
    name: str
    avatar: Optional[str] = None
    workspace: str


class UserMetrics(BaseModel):
    """User performance metrics."""

    totalActions: int = Field(0, alias="total_actions")
    successRate: float = Field(0.0, alias="success_rate")
    creditsUsed: float = Field(0.0, alias="credits_used")
    creditsSaved: float = Field(0.0, alias="credits_saved")
    agentsUsed: int = Field(0, alias="agents_used")

    class Config:
        allow_population_by_field_name = True


class UserRanking(BaseModel):
    """User ranking entry."""

    rank: int
    previousRank: Optional[int] = Field(None, alias="previous_rank")
    change: RankChange
    user: UserInfo
    metrics: UserMetrics
    score: float
    percentile: float
    achievements: List[str] = []

    class Config:
        allow_population_by_field_name = True


class UserLeaderboardData(BaseModel):
    """User leaderboard data."""

    criteria: UserCriteria
    rankings: List[UserRanking]


# ===================================================================
# WORKSPACE LEADERBOARD SCHEMAS
# ===================================================================

class WorkspaceInfo(BaseModel):
    """Workspace information in leaderboard."""

    id: str
    name: str
    plan: str
    memberCount: int = Field(0, alias="member_count")

    class Config:
        allow_population_by_field_name = True


class WorkspaceMetrics(BaseModel):
    """Workspace performance metrics."""

    totalActivity: int = Field(0, alias="total_activity")
    activeUsers: int = Field(0, alias="active_users")
    agentCount: int = Field(0, alias="agent_count")
    successRate: float = Field(0.0, alias="success_rate")
    healthScore: float = Field(0.0, alias="health_score")

    class Config:
        allow_population_by_field_name = True


class WorkspaceRanking(BaseModel):
    """Workspace ranking entry."""

    rank: int
    previousRank: Optional[int] = Field(None, alias="previous_rank")
    change: RankChange
    workspace: WorkspaceInfo
    metrics: WorkspaceMetrics
    score: float
    tier: Tier

    class Config:
        allow_population_by_field_name = True


class WorkspaceLeaderboardData(BaseModel):
    """Workspace leaderboard data."""

    criteria: WorkspaceCriteria
    rankings: List[WorkspaceRanking]


# ===================================================================
# COMBINED LEADERBOARDS RESPONSE
# ===================================================================

class Leaderboards(BaseModel):
    """Complete leaderboards data."""

    timeframe: TimeFrame
    agentLeaderboard: Optional[AgentLeaderboardData] = Field(None, alias="agent_leaderboard")
    userLeaderboard: Optional[UserLeaderboardData] = Field(None, alias="user_leaderboard")
    workspaceLeaderboard: Optional[WorkspaceLeaderboardData] = Field(None, alias="workspace_leaderboard")
    calculatedAt: datetime = Field(default_factory=datetime.now, alias="calculated_at")

    class Config:
        allow_population_by_field_name = True


# ===================================================================
# REQUEST SCHEMAS
# ===================================================================

class LeaderboardQuery(BaseModel):
    """Query parameters for leaderboard requests."""

    timeframe: TimeFrame = TimeFrame.SEVEN_DAYS
    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)


class AgentLeaderboardQuery(LeaderboardQuery):
    """Query parameters for agent leaderboard."""

    criteria: AgentCriteria = AgentCriteria.SUCCESS_RATE
    workspaceId: Optional[str] = Field(None, alias="workspace_id")

    class Config:
        allow_population_by_field_name = True


class UserLeaderboardQuery(LeaderboardQuery):
    """Query parameters for user leaderboard."""

    criteria: UserCriteria = UserCriteria.ACTIVITY
    workspaceId: Optional[str] = Field(None, alias="workspace_id")

    class Config:
        allow_population_by_field_name = True


class WorkspaceLeaderboardQuery(LeaderboardQuery):
    """Query parameters for workspace leaderboard."""

    criteria: WorkspaceCriteria = WorkspaceCriteria.ACTIVITY


# ===================================================================
# INTERNAL/DATABASE SCHEMAS
# ===================================================================

class AgentLeaderboardRecord(BaseModel):
    """Agent leaderboard database record."""

    id: str
    workspace_id: str
    agent_id: str
    rank: int
    previous_rank: Optional[int] = None
    rank_change: str
    timeframe: str
    criteria: str
    total_runs: int
    success_rate: float
    avg_runtime: float
    credits_per_run: float
    unique_users: int
    score: float
    percentile: float
    badge: Optional[str] = None
    calculated_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserLeaderboardRecord(BaseModel):
    """User leaderboard database record."""

    id: str
    workspace_id: str
    user_id: str
    rank: int
    previous_rank: Optional[int] = None
    rank_change: str
    timeframe: str
    criteria: str
    total_actions: int
    success_rate: float
    credits_used: float
    credits_saved: float
    agents_used: int
    score: float
    percentile: float
    achievements: List[str]
    calculated_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkspaceLeaderboardRecord(BaseModel):
    """Workspace leaderboard database record."""

    id: str
    workspace_id: str
    rank: int
    previous_rank: Optional[int] = None
    rank_change: str
    timeframe: str
    criteria: str
    total_activity: int
    active_users: int
    agent_count: int
    success_rate: float
    health_score: float
    score: float
    tier: str
    calculated_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
