"""Workspace schemas with comprehensive analytics types."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
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


# Workspace Analytics Schemas

class HealthScoreComponents(BaseModel):
    """Health score component breakdown."""

    success_rate: float = Field(..., ge=0, le=100, description="Success rate component (0-100)")
    activity: float = Field(..., ge=0, le=100, description="Activity component (0-100)")
    engagement: float = Field(..., ge=0, le=100, description="Engagement component (0-100)")
    efficiency: float = Field(..., ge=0, le=100, description="Efficiency component (0-100)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success_rate": 85.5,
                "activity": 75.0,
                "engagement": 65.2,
                "efficiency": 90.0
            }
        }
    )


class HealthScore(BaseModel):
    """Workspace health score."""

    overall: float = Field(..., ge=0, le=100, description="Overall health score (0-100)")
    components: HealthScoreComponents

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "overall": 78.9,
                "components": {
                    "success_rate": 85.5,
                    "activity": 75.0,
                    "engagement": 65.2,
                    "efficiency": 90.0
                }
            }
        }
    )


class WorkspaceOverview(BaseModel):
    """Workspace overview metrics."""

<<<<<<< HEAD
    workspace_name: str = Field(..., description="Name of the workspace")
    created_at: Optional[str] = Field(None, description="Workspace creation timestamp")
    total_members: int = Field(..., ge=0, description="Total number of members")
    active_members: int = Field(..., ge=0, description="Number of active members")
    member_activity_rate: float = Field(..., ge=0, le=100, alias="memberActivityRate", description="Percentage of active members")
    total_activity: int = Field(..., ge=0, alias="totalActivity", description="Total activity count")
    total_runs: int = Field(..., ge=0, alias="totalRuns", description="Total agent runs")
    successful_runs: int = Field(..., ge=0, alias="successfulRuns", description="Number of successful runs")
    failed_runs: int = Field(..., ge=0, alias="failedRuns", description="Number of failed runs")
    success_rate: float = Field(..., ge=0, le=100, alias="successRate", description="Success rate percentage")
    avg_runtime: float = Field(..., ge=0, alias="avgRuntime", description="Average runtime in seconds")

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "workspace_name": "Engineering Team",
                "created_at": "2024-01-15T10:30:00Z",
                "total_members": 25,
                "active_members": 18,
                "memberActivityRate": 72.0,
                "totalActivity": 1250,
                "totalRuns": 450,
                "successfulRuns": 380,
                "failedRuns": 70,
                "successRate": 84.4,
                "avgRuntime": 12.5
            }
        }
    )


class MemberEngagementLevels(BaseModel):
    """Member engagement level distribution."""

    high: int = Field(..., ge=0, description="Number of highly engaged members")
    medium: int = Field(..., ge=0, description="Number of moderately engaged members")
    low: int = Field(..., ge=0, description="Number of low engaged members")


class TopMember(BaseModel):
    """Top member activity data."""

    user_id: str = Field(..., alias="userId", description="User identifier")
    activity_count: int = Field(..., ge=0, alias="activityCount", description="Total activity count")
    active_days: int = Field(..., ge=0, alias="activeDays", description="Number of active days")
    last_activity: Optional[str] = Field(None, alias="lastActivity", description="Last activity timestamp")
    engagement: str = Field(..., description="Engagement level (high, medium, low)")

    model_config = ConfigDict(populate_by_name=True)


class MemberAnalytics(BaseModel):
    """Member activity analytics."""

    top_members: List[TopMember] = Field(..., alias="topMembers", description="Top active members")
    engagement_levels: MemberEngagementLevels = Field(..., alias="engagementLevels", description="Engagement distribution")
    total_analyzed: int = Field(..., ge=0, alias="totalAnalyzed", description="Total members analyzed")

    model_config = ConfigDict(populate_by_name=True)


class AgentUsage(BaseModel):
    """Agent usage statistics."""

    total_agents: int = Field(..., ge=0, alias="totalAgents", description="Total number of agents")
    total_runs: int = Field(..., ge=0, alias="totalRuns", description="Total agent runs")
    successful_runs: int = Field(..., ge=0, alias="successfulRuns", description="Successful runs count")
    success_rate: float = Field(..., ge=0, le=100, alias="successRate", description="Success rate percentage")
    avg_runtime: float = Field(..., ge=0, alias="avgRuntime", description="Average runtime in seconds")
    total_credits: float = Field(..., ge=0, alias="totalCredits", description="Total credits consumed")
    efficiency_score: int = Field(..., ge=0, le=100, alias="efficiencyScore", description="Efficiency score (0-100)")

    model_config = ConfigDict(populate_by_name=True)


class DailyConsumption(BaseModel):
    """Daily resource consumption data."""

    date: str = Field(..., description="Date in ISO format")
    credits: float = Field(..., ge=0, description="Credits consumed on this day")
    runs: int = Field(..., ge=0, description="Number of runs on this day")


class ResourceConsumption(BaseModel):
    """Resource consumption metrics."""

    daily_consumption: List[DailyConsumption] = Field(..., alias="dailyConsumption", description="Daily consumption data")
    total_credits: float = Field(..., ge=0, alias="totalCredits", description="Total credits consumed")
    avg_daily_credits: float = Field(..., ge=0, alias="avgDailyCredits", description="Average daily credit consumption")
    days_analyzed: int = Field(..., ge=0, alias="daysAnalyzed", description="Number of days analyzed")

    model_config = ConfigDict(populate_by_name=True)


class ActivityTrend(BaseModel):
    """Activity trend data point."""

    date: str = Field(..., description="Date in ISO format")
    activities: int = Field(..., ge=0, description="Total activities on this day")
    active_users: int = Field(..., ge=0, alias="activeUsers", description="Active users on this day")

    model_config = ConfigDict(populate_by_name=True)


class ActivityTrends(BaseModel):
    """Activity trends over time."""

    trends: List[ActivityTrend] = Field(..., description="List of activity trend data points")


class WorkspaceAnalytics(BaseModel):
    """Comprehensive workspace analytics response."""

    workspace_id: str = Field(..., alias="workspaceId", description="Workspace identifier")
    timeframe: str = Field(..., description="Timeframe for analytics (24h, 7d, 30d, 90d, all)")
    generated_at: str = Field(..., alias="generatedAt", description="Timestamp when analytics were generated")
    health_score: HealthScore = Field(..., alias="healthScore", description="Workspace health score")
    overview: WorkspaceOverview = Field(..., description="Workspace overview metrics")
    member_analytics: MemberAnalytics = Field(..., alias="memberAnalytics", description="Member activity analytics")
    agent_usage: AgentUsage = Field(..., alias="agentUsage", description="Agent usage statistics")
    resource_consumption: ResourceConsumption = Field(..., alias="resourceConsumption", description="Resource consumption data")
    activity_trends: ActivityTrends = Field(..., alias="activityTrends", description="Activity trends over time")

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "workspaceId": "ws_123abc",
                "timeframe": "30d",
                "generatedAt": "2024-11-09T10:30:00Z",
                "healthScore": {
                    "overall": 78.9,
                    "components": {
                        "success_rate": 85.5,
                        "activity": 75.0,
                        "engagement": 65.2,
                        "efficiency": 90.0
                    }
                },
                "overview": {
                    "workspace_name": "Engineering Team",
                    "total_members": 25,
                    "active_members": 18
                }
            }
        }
    )
