"""Search API routes."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from datetime import datetime, date
import logging

from ...core.database import get_db
from ...models.schemas.search import (
    GlobalSearchResponse,
    AdvancedSearchConfig,
    AdvancedSearchResponse,
    UserSearchResult,
    UserSearchFilters,
    AgentSearchResult,
    AgentSearchFilters,
    ActivitySearchResult,
    ActivitySearchFilters,
    MetricSearchResult,
    MetricSearchFilters,
    AlertSearchResult,
    AlertSearchFilters,
    ReportSearchResult,
    ReportSearchFilters,
    SearchSuggestionsResponse,
    SearchSuggestion,
    SearchHistoryResponse,
    SearchHistoryItem,
    SavedSearchConfig,
    SavedSearchResponse,
    SavedSearchListResponse,
    SearchAnalyticsResponse,
    SearchAnalyticsData,
    DateRangeFilter,
)
from ...models.schemas.common import PaginationParams, PaginatedResponse
from ...services.search import SearchService
from ...middleware.auth import get_current_user
from ...middleware.workspace import validate_workspace_access
from ...middleware.permissions import require_admin
from ...utils.validators import validate_workspace_id

router = APIRouter(prefix="/api/v1/search", tags=["search"])
logger = logging.getLogger(__name__)


# Global Search Endpoints


@router.get("/global", response_model=GlobalSearchResponse)
async def global_search(
    q: str = Query(..., min_length=1, description="Search query"),
    types: Optional[List[str]] = Query(None, description="Filter by type"),
    workspace_id: str = Query(..., description="Workspace ID"),
    limit: int = Query(20, ge=1, le=100, description="Max results per type"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
) -> GlobalSearchResponse:
    """
    Global search across all analytics data.

    **Parameters:**
    - **q**: Search query string
    - **types**: Optional list to filter by type (users, agents, reports, alerts)
    - **workspace_id**: Workspace context for the search
    - **limit**: Maximum results to return per type (default: 20)

    **Returns:**
    - Search results grouped by entity type
    - Total result count
    - Search suggestions based on query
    """
    try:
        validated_workspace_id = validate_workspace_id(workspace_id)

        logger.info(
            f"Global search for query '{q}' in workspace {validated_workspace_id} "
            f"(user: {current_user.get('user_id')})"
        )

        service = SearchService(db)
        results = await service.global_search(
            query=q,
            workspace_id=validated_workspace_id,
            types=types,
            limit=limit,
        )

        return results

    except Exception as e:
        logger.error(f"Error in global search: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform global search: {str(e)}",
        )


@router.post("/advanced", response_model=AdvancedSearchResponse)
async def advanced_search(
    search_config: AdvancedSearchConfig,
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
) -> AdvancedSearchResponse:
    """
    Advanced search with complex filters.

    **Request Body:**
    - **query**: Search query string
    - **filters**: Complex filters (date range, entities, metrics)
    - **aggregations**: Aggregation configurations
    - **sort**: Sort configurations
    - **highlight**: Highlight configurations for matched terms
    - **workspace_id**: Workspace context

    **Returns:**
    - Filtered search results
    - Total count
    - Aggregation results
    - Execution time metrics
    """
    try:
        validated_workspace_id = validate_workspace_id(search_config.workspace_id)

        logger.info(
            f"Advanced search for query '{search_config.query}' "
            f"in workspace {validated_workspace_id} "
            f"(user: {current_user.get('user_id')})"
        )

        service = SearchService(db)
        results = await service.advanced_search(search_config)

        return results

    except Exception as e:
        logger.error(f"Error in advanced search: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform advanced search: {str(e)}",
        )


# Entity Search Endpoints


@router.get("/users", response_model=PaginatedResponse)
async def search_users(
    q: str = Query(..., min_length=1, description="Search query"),
    workspace_id: str = Query(..., description="Workspace ID"),
    active_only: bool = Query(False, description="Filter active users only"),
    min_activity: Optional[int] = Query(None, description="Minimum activity threshold"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Page size"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
) -> PaginatedResponse:
    """
    Search users with filters.

    **Parameters:**
    - **q**: Search in name, email, or user ID
    - **workspace_id**: Workspace context
    - **active_only**: Only return active users
    - **min_activity**: Minimum activity threshold

    **Returns:**
    - List of matching users with their metrics
    - Pagination metadata
    """
    try:
        validated_workspace_id = validate_workspace_id(workspace_id)

        filters = UserSearchFilters(
            active_only=active_only,
            min_activity=min_activity,
        )

        pagination = PaginationParams(skip=skip, limit=limit)

        service = SearchService(db)
        users, total = await service.search_users(
            query=q,
            workspace_id=validated_workspace_id,
            filters=filters,
            pagination=pagination,
        )

        return PaginatedResponse(
            total=total,
            skip=skip,
            limit=limit,
            data=[user.dict() for user in users],
        )

    except Exception as e:
        logger.error(f"Error searching users: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search users: {str(e)}",
        )


@router.get("/agents", response_model=List[AgentSearchResult])
async def search_agents(
    q: Optional[str] = Query(None, description="Search query"),
    workspace_id: str = Query(..., description="Workspace ID"),
    min_success_rate: Optional[float] = Query(
        None, ge=0, le=100, description="Minimum success rate"
    ),
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
) -> List[AgentSearchResult]:
    """
    Search agents with performance filters.

    **Parameters:**
    - **q**: Search in name, description, or tags
    - **workspace_id**: Workspace context
    - **min_success_rate**: Minimum success rate filter
    - **agent_type**: Filter by agent type

    **Returns:**
    - List of matching agents with performance metrics
    """
    try:
        validated_workspace_id = validate_workspace_id(workspace_id)

        filters = AgentSearchFilters(
            min_success_rate=min_success_rate,
            agent_type=agent_type,
        )

        service = SearchService(db)
        agents = await service.search_agents(
            query=q,
            workspace_id=validated_workspace_id,
            filters=filters,
        )

        return agents

    except Exception as e:
        logger.error(f"Error searching agents: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search agents: {str(e)}",
        )


# Activity Search


@router.get("/activities", response_model=PaginatedResponse)
async def search_activities(
    workspace_id: str = Query(..., description="Workspace ID"),
    user_ids: Optional[List[str]] = Query(None, description="Filter by user IDs"),
    event_types: Optional[List[str]] = Query(None, description="Filter by event types"),
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Page size"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
) -> PaginatedResponse:
    """
    Search user activities and events.

    **Parameters:**
    - **workspace_id**: Workspace context
    - **user_ids**: Optional list of user IDs to filter
    - **event_types**: Optional list of event types to filter
    - **start_date**: Start date for activity search
    - **end_date**: End date for activity search

    **Returns:**
    - List of matching activities
    - Pagination metadata
    """
    try:
        validated_workspace_id = validate_workspace_id(workspace_id)

        filters = ActivitySearchFilters(
            user_ids=user_ids,
            event_types=event_types,
            date_range=DateRangeFilter(start=start_date, end=end_date),
        )

        pagination = PaginationParams(skip=skip, limit=limit)

        service = SearchService(db)
        activities, total = await service.search_activities(
            workspace_id=validated_workspace_id,
            filters=filters,
            pagination=pagination,
        )

        return PaginatedResponse(
            total=total,
            skip=skip,
            limit=limit,
            data=[activity.dict() for activity in activities],
        )

    except Exception as e:
        logger.error(f"Error searching activities: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search activities: {str(e)}",
        )


# Metric Search


@router.get("/metrics", response_model=List[MetricSearchResult])
async def search_metrics(
    workspace_id: str = Query(..., description="Workspace ID"),
    metric_name: Optional[str] = Query(None, description="Metric name pattern"),
    value_min: Optional[float] = Query(None, description="Minimum value"),
    value_max: Optional[float] = Query(None, description="Maximum value"),
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    include_anomalies_only: bool = Query(False, description="Only anomalies"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
) -> List[MetricSearchResult]:
    """
    Search for specific metric values.

    **Parameters:**
    - **workspace_id**: Workspace context
    - **metric_name**: Pattern to match metric names
    - **value_min**: Minimum value threshold
    - **value_max**: Maximum value threshold
    - **start_date**: Start date for metric search
    - **end_date**: End date for metric search
    - **include_anomalies_only**: Only return anomalous metrics

    **Returns:**
    - List of matching metrics with their values
    """
    try:
        validated_workspace_id = validate_workspace_id(workspace_id)

        from ...models.schemas.search import ValueRange

        value_range = None
        if value_min is not None or value_max is not None:
            value_range = ValueRange(min=value_min, max=value_max)

        filters = MetricSearchFilters(
            metric_name=metric_name,
            value_range=value_range,
            date_range=DateRangeFilter(start=start_date, end=end_date),
            include_anomalies_only=include_anomalies_only,
        )

        service = SearchService(db)
        metrics = await service.search_metrics(
            workspace_id=validated_workspace_id,
            filters=filters,
        )

        return metrics

    except Exception as e:
        logger.error(f"Error searching metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search metrics: {str(e)}",
        )


# Alert Search


@router.get("/alerts", response_model=List[AlertSearchResult])
async def search_alerts(
    q: Optional[str] = Query(None, description="Search in title and message"),
    workspace_id: str = Query(..., description="Workspace ID"),
    severity: Optional[List[str]] = Query(None, description="Filter by severity"),
    status: Optional[List[str]] = Query(None, description="Filter by status"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
) -> List[AlertSearchResult]:
    """
    Search alerts and notifications.

    **Parameters:**
    - **q**: Search in title and message fields
    - **workspace_id**: Workspace context
    - **severity**: Filter by severity levels (low, medium, high, critical)
    - **status**: Filter by status (active, acknowledged, resolved)

    **Returns:**
    - List of matching alerts
    """
    try:
        validated_workspace_id = validate_workspace_id(workspace_id)

        from ...models.schemas.search import AlertSeverityEnum, AlertStatusEnum

        severity_filters = None
        if severity:
            severity_filters = [AlertSeverityEnum(s) for s in severity]

        status_filters = None
        if status:
            status_filters = [AlertStatusEnum(s) for s in status]

        filters = AlertSearchFilters(
            severity=severity_filters,
            status=status_filters,
        )

        service = SearchService(db)
        alerts = await service.search_alerts(
            query=q,
            workspace_id=validated_workspace_id,
            filters=filters,
        )

        return alerts

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid filter value: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error searching alerts: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search alerts: {str(e)}",
        )


# Report Search


@router.get("/reports", response_model=List[ReportSearchResult])
async def search_reports(
    q: Optional[str] = Query(None, description="Search in name and description"),
    workspace_id: str = Query(..., description="Workspace ID"),
    report_type: Optional[List[str]] = Query(None, description="Filter by type"),
    created_by: Optional[str] = Query(None, description="Filter by creator"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
) -> List[ReportSearchResult]:
    """
    Search generated reports.

    **Parameters:**
    - **q**: Search in name and description
    - **workspace_id**: Workspace context
    - **report_type**: Filter by report type (scheduled, on_demand, automated)
    - **created_by**: Filter by creator email

    **Returns:**
    - List of matching reports with metadata
    """
    try:
        validated_workspace_id = validate_workspace_id(workspace_id)

        from ...models.schemas.search import ReportTypeEnum

        type_filters = None
        if report_type:
            type_filters = [ReportTypeEnum(t) for t in report_type]

        filters = ReportSearchFilters(
            report_type=type_filters,
            created_by=created_by,
        )

        service = SearchService(db)
        reports = await service.search_reports(
            query=q,
            workspace_id=validated_workspace_id,
            filters=filters,
        )

        return reports

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid filter value: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error searching reports: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search reports: {str(e)}",
        )


# Search Suggestions


@router.get("/suggestions", response_model=SearchSuggestionsResponse)
async def get_search_suggestions(
    q: str = Query(..., min_length=1, description="Partial search query"),
    workspace_id: str = Query(..., description="Workspace ID"),
    limit: int = Query(10, ge=1, le=50, description="Max suggestions"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
) -> SearchSuggestionsResponse:
    """
    Get search suggestions based on partial query.

    **Parameters:**
    - **q**: Partial search query
    - **workspace_id**: Workspace context
    - **limit**: Maximum number of suggestions to return

    **Returns:**
    - List of search suggestions with relevance scores
    """
    try:
        validated_workspace_id = validate_workspace_id(workspace_id)

        service = SearchService(db)
        suggestions = await service.get_search_suggestions(
            query=q,
            workspace_id=validated_workspace_id,
            user_id=current_user.get("user_id"),
            limit=limit,
        )

        # Convert strings to SearchSuggestion objects
        suggestion_objects = [
            SearchSuggestion(text=s, type="query", score=0.9)
            for s in suggestions
        ]

        return SearchSuggestionsResponse(
            query=q,
            suggestions=suggestion_objects,
        )

    except Exception as e:
        logger.error(f"Error getting search suggestions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get search suggestions: {str(e)}",
        )


# Search History


@router.get("/history", response_model=SearchHistoryResponse)
async def get_search_history(
    workspace_id: str = Query(..., description="Workspace ID"),
    limit: int = Query(20, ge=1, le=100, description="Max history items"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
) -> SearchHistoryResponse:
    """
    Get user's search history.

    **Parameters:**
    - **workspace_id**: Workspace context
    - **limit**: Maximum number of history items to return

    **Returns:**
    - List of recent searches with metadata
    """
    try:
        validated_workspace_id = validate_workspace_id(workspace_id)

        service = SearchService(db)
        history = await service.get_search_history(
            user_id=current_user.get("user_id"),
            workspace_id=validated_workspace_id,
            limit=limit,
        )

        return SearchHistoryResponse(
            searches=history,
            total=len(history),
        )

    except Exception as e:
        logger.error(f"Error getting search history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get search history: {str(e)}",
        )


@router.delete("/history")
async def clear_search_history(
    workspace_id: str = Query(..., description="Workspace ID"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
) -> Dict[str, bool]:
    """
    Clear user's search history.

    **Parameters:**
    - **workspace_id**: Workspace context

    **Returns:**
    - Confirmation of history clearing
    """
    try:
        validated_workspace_id = validate_workspace_id(workspace_id)

        service = SearchService(db)
        cleared = await service.clear_search_history(
            user_id=current_user.get("user_id"),
            workspace_id=validated_workspace_id,
        )

        return {"cleared": cleared}

    except Exception as e:
        logger.error(f"Error clearing search history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear search history: {str(e)}",
        )


# Saved Searches


@router.post("/saved", response_model=SavedSearchResponse)
async def save_search(
    search_config: SavedSearchConfig,
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
) -> SavedSearchResponse:
    """
    Save search configuration.

    **Request Body:**
    - **name**: Name for the saved search
    - **query**: Search query string
    - **filters**: Optional search filters
    - **alert_on_match**: Whether to trigger alerts on matches
    - **share_with_team**: Whether to share with team members
    - **workspace_id**: Workspace context

    **Returns:**
    - Created saved search ID and metadata
    """
    try:
        validated_workspace_id = validate_workspace_id(search_config.workspace_id)

        service = SearchService(db)
        saved_search = await service.create_saved_search(
            user_id=current_user.get("user_id"),
            workspace_id=validated_workspace_id,
            name=search_config.name,
            query=search_config.query,
            filters=search_config.filters,
            alert_on_match=search_config.alert_on_match,
            share_with_team=search_config.share_with_team,
        )

        return SavedSearchResponse(
            id=saved_search.id,
            name=saved_search.name,
            created=True,
        )

    except Exception as e:
        logger.error(f"Error saving search: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save search: {str(e)}",
        )


@router.get("/saved", response_model=SavedSearchListResponse)
async def get_saved_searches(
    workspace_id: str = Query(..., description="Workspace ID"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace_access=Depends(validate_workspace_access),
) -> SavedSearchListResponse:
    """
    Get user's saved searches.

    **Parameters:**
    - **workspace_id**: Workspace context

    **Returns:**
    - List of saved searches with metadata
    """
    try:
        validated_workspace_id = validate_workspace_id(workspace_id)

        service = SearchService(db)
        saved_searches = await service.get_saved_searches(
            user_id=current_user.get("user_id"),
            workspace_id=validated_workspace_id,
        )

        return SavedSearchListResponse(
            saved_searches=saved_searches,
            total=len(saved_searches),
        )

    except Exception as e:
        logger.error(f"Error getting saved searches: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get saved searches: {str(e)}",
        )


# Search Analytics


@router.get("/analytics", response_model=SearchAnalyticsResponse)
async def get_search_analytics(
    workspace_id: str = Query(..., description="Workspace ID"),
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_admin),
    workspace_access=Depends(validate_workspace_access),
) -> SearchAnalyticsResponse:
    """
    Get analytics about search usage.

    **Requires admin permissions.**

    **Parameters:**
    - **workspace_id**: Workspace context
    - **start_date**: Start date for analytics
    - **end_date**: End date for analytics

    **Returns:**
    - Comprehensive search usage analytics including:
      - Total searches and unique users
      - Top queries and queries with no results
      - Search performance metrics
    """
    try:
        validated_workspace_id = validate_workspace_id(workspace_id)

        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        service = SearchService(db)
        analytics = await service.get_search_analytics(
            workspace_id=validated_workspace_id,
            start_date=start_datetime,
            end_date=end_datetime,
        )

        return SearchAnalyticsResponse(
            search_analytics=analytics,
            date_range=DateRangeFilter(start=start_date, end=end_date),
        )

    except Exception as e:
        logger.error(f"Error getting search analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get search analytics: {str(e)}",
        )
