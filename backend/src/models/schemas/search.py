"""Search schemas for API requests and responses."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


class SearchTypeEnum(str, Enum):
    """Search entity types."""

    USERS = "users"
    AGENTS = "agents"
    REPORTS = "reports"
    ALERTS = "alerts"
    ACTIVITIES = "activities"
    METRICS = "metrics"
    ALL = "all"


class SortOrderEnum(str, Enum):
    """Sort order options."""

    ASC = "asc"
    DESC = "desc"


class AlertSeverityEnum(str, Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatusEnum(str, Enum):
    """Alert status options."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class ReportTypeEnum(str, Enum):
    """Report type options."""

    SCHEDULED = "scheduled"
    ON_DEMAND = "on_demand"
    AUTOMATED = "automated"


# Global Search Schemas

class GlobalSearchResponse(BaseModel):
    """Response for global search."""

    query: str
    total_results: int
    results: Dict[str, List[Dict[str, Any]]]
    suggestions: List[str] = Field(default_factory=list)


# Advanced Search Schemas

class DateRangeFilter(BaseModel):
    """Date range filter."""

    start: date
    end: date


class ValueRange(BaseModel):
    """Value range filter."""

    min: Optional[float] = None
    max: Optional[float] = None


class MetricFilter(BaseModel):
    """Metric filter with value range."""

    metric_name: str
    value_range: Optional[ValueRange] = None


class EntityFilters(BaseModel):
    """Entity filters for advanced search."""

    agents: Optional[List[str]] = None
    users: Optional[List[str]] = None


class SearchFilters(BaseModel):
    """Advanced search filters."""

    date_range: Optional[DateRangeFilter] = None
    entities: Optional[EntityFilters] = None
    metrics: Optional[Dict[str, ValueRange]] = None


class AggregationConfig(BaseModel):
    """Aggregation configuration."""

    field: str
    type: str = Field(..., description="Aggregation type: terms, avg, sum, min, max")
    size: int = Field(10, ge=1, le=100)


class SortConfig(BaseModel):
    """Sort configuration."""

    field: str
    order: SortOrderEnum = SortOrderEnum.DESC


class HighlightConfig(BaseModel):
    """Highlight configuration."""

    fields: List[str]
    pre_tag: str = "<mark>"
    post_tag: str = "</mark>"


class AdvancedSearchConfig(BaseModel):
    """Advanced search configuration."""

    query: str
    filters: Optional[SearchFilters] = None
    aggregations: Optional[List[AggregationConfig]] = None
    sort: Optional[List[SortConfig]] = None
    highlight: Optional[HighlightConfig] = None
    workspace_id: str


class AdvancedSearchResponse(BaseModel):
    """Response for advanced search."""

    results: List[Dict[str, Any]]
    total: int
    aggregations: Optional[Dict[str, Any]] = None
    execution_time_ms: float


# Entity Search Schemas

class UserSearchResult(BaseModel):
    """User search result."""

    id: str
    email: str
    name: Optional[str] = None
    last_active: Optional[datetime] = None
    total_executions: int = 0
    match_fields: List[str] = Field(default_factory=list)
    relevance_score: Optional[float] = None


class UserSearchFilters(BaseModel):
    """User search filters."""

    active_only: bool = False
    min_activity: Optional[int] = None
    date_range: Optional[DateRangeFilter] = None


class AgentSearchResult(BaseModel):
    """Agent search result."""

    id: str
    name: str
    type: Optional[str] = None
    success_rate: Optional[float] = None
    total_executions: int = 0
    tags: List[str] = Field(default_factory=list)
    relevance_score: Optional[float] = None
    description: Optional[str] = None


class AgentSearchFilters(BaseModel):
    """Agent search filters."""

    min_success_rate: Optional[float] = Field(None, ge=0, le=100)
    agent_type: Optional[str] = None
    tags: Optional[List[str]] = None
    date_range: Optional[DateRangeFilter] = None


# Activity Search Schemas

class ActivitySearchResult(BaseModel):
    """Activity search result."""

    id: str
    user_id: str
    event_type: str
    agent_id: Optional[str] = None
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None


class ActivitySearchFilters(BaseModel):
    """Activity search filters."""

    user_ids: Optional[List[str]] = None
    event_types: Optional[List[str]] = None
    date_range: DateRangeFilter
    agent_ids: Optional[List[str]] = None


# Metric Search Schemas

class MetricSearchResult(BaseModel):
    """Metric search result."""

    name: str
    timestamp: datetime
    value: float
    tags: Optional[Dict[str, str]] = None
    anomaly: bool = False


class MetricSearchFilters(BaseModel):
    """Metric search filters."""

    metric_name: Optional[str] = None
    value_range: Optional[ValueRange] = None
    date_range: DateRangeFilter
    include_anomalies_only: bool = False


# Alert Search Schemas

class AlertSearchResult(BaseModel):
    """Alert search result."""

    id: str
    title: str
    severity: AlertSeverityEnum
    status: AlertStatusEnum
    triggered_at: datetime
    metric: Optional[str] = None
    value: Optional[float] = None
    threshold: Optional[float] = None
    message: Optional[str] = None


class AlertSearchFilters(BaseModel):
    """Alert search filters."""

    severity: Optional[List[AlertSeverityEnum]] = None
    status: Optional[List[AlertStatusEnum]] = None
    date_range: Optional[DateRangeFilter] = None
    metric_names: Optional[List[str]] = None


# Report Search Schemas

class ReportSearchResult(BaseModel):
    """Report search result."""

    id: str
    name: str
    type: ReportTypeEnum
    created_at: datetime
    created_by: str
    size_mb: Optional[float] = None
    download_url: Optional[str] = None
    description: Optional[str] = None


class ReportSearchFilters(BaseModel):
    """Report search filters."""

    report_type: Optional[List[ReportTypeEnum]] = None
    created_by: Optional[str] = None
    date_range: Optional[DateRangeFilter] = None


# Search Suggestions Schemas

class SearchSuggestion(BaseModel):
    """Search suggestion item."""

    text: str
    type: str = Field(..., description="Suggestion type: query, entity, filter")
    entity_type: Optional[str] = None
    score: float = Field(..., ge=0, le=1)


class SearchSuggestionsResponse(BaseModel):
    """Response for search suggestions."""

    query: str
    suggestions: List[SearchSuggestion]


# Search History Schemas

class SearchHistoryItem(BaseModel):
    """Search history item."""

    query: str
    timestamp: datetime
    result_count: int
    filters_used: List[str] = Field(default_factory=list)
    search_type: Optional[str] = None


class SearchHistoryResponse(BaseModel):
    """Response for search history."""

    searches: List[SearchHistoryItem]
    total: int


# Saved Search Schemas

class SavedSearchConfig(BaseModel):
    """Configuration for saved search."""

    name: str
    query: str
    filters: Optional[Dict[str, Any]] = None
    alert_on_match: bool = False
    share_with_team: bool = False
    workspace_id: str


class SavedSearchItem(BaseModel):
    """Saved search item."""

    id: str
    name: str
    query: str
    filters: Optional[Dict[str, Any]] = None
    last_run: Optional[datetime] = None
    run_count: int = 0
    alert_on_match: bool = False
    share_with_team: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None


class SavedSearchResponse(BaseModel):
    """Response for creating saved search."""

    id: str
    name: str
    created: bool = True


class SavedSearchListResponse(BaseModel):
    """Response for listing saved searches."""

    saved_searches: List[SavedSearchItem]
    total: int


# Search Analytics Schemas

class TopQuery(BaseModel):
    """Top search query."""

    query: str
    count: int


class SearchPerformance(BaseModel):
    """Search performance metrics."""

    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: Optional[float] = None


class SearchAnalyticsData(BaseModel):
    """Search analytics data."""

    total_searches: int
    unique_users: int
    avg_searches_per_user: float
    top_queries: List[TopQuery]
    no_results_queries: List[TopQuery]
    avg_results_per_search: float
    search_performance: SearchPerformance


class SearchAnalyticsResponse(BaseModel):
    """Response for search analytics."""

    search_analytics: SearchAnalyticsData
    date_range: DateRangeFilter
