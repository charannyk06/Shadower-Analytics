"""Unit tests for search service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, date

from src.services.search import SearchService
from src.models.schemas.search import (
    AdvancedSearchConfig,
    UserSearchFilters,
    AgentSearchFilters,
    ActivitySearchFilters,
    MetricSearchFilters,
    AlertSearchFilters,
    ReportSearchFilters,
    DateRangeFilter,
)
from src.models.schemas.common import PaginationParams


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = MagicMock()
    db.execute = AsyncMock()
    db.scalars = AsyncMock()
    return db


@pytest.fixture
def search_service(mock_db):
    """Create search service instance."""
    return SearchService(mock_db)


@pytest.mark.asyncio
async def test_global_search_basic(search_service):
    """Test basic global search."""
    result = await search_service.global_search(
        query="test",
        workspace_id="test-workspace-123",
        types=["all"],
        limit=20,
    )

    assert result.query == "test"
    assert result.total_results >= 0
    assert isinstance(result.results, dict)
    assert isinstance(result.suggestions, list)


@pytest.mark.asyncio
async def test_global_search_filtered_types(search_service):
    """Test global search with filtered types."""
    result = await search_service.global_search(
        query="test",
        workspace_id="test-workspace-123",
        types=["users", "agents"],
        limit=10,
    )

    assert result.query == "test"
    # Should only include requested types
    assert "users" in result.results or "agents" in result.results


@pytest.mark.asyncio
async def test_advanced_search(search_service):
    """Test advanced search."""
    config = AdvancedSearchConfig(
        query="error rate",
        workspace_id="test-workspace-123",
    )

    result = await search_service.advanced_search(config)

    assert isinstance(result.results, list)
    assert result.total >= 0
    assert result.execution_time_ms >= 0


@pytest.mark.asyncio
async def test_search_users_with_filters(search_service):
    """Test user search with filters."""
    filters = UserSearchFilters(
        active_only=True,
        min_activity=10,
    )
    pagination = PaginationParams(skip=0, limit=50)

    users, total = await search_service.search_users(
        query="test",
        workspace_id="test-workspace-123",
        filters=filters,
        pagination=pagination,
    )

    assert isinstance(users, list)
    assert total >= 0


@pytest.mark.asyncio
async def test_search_agents_with_filters(search_service):
    """Test agent search with filters."""
    filters = AgentSearchFilters(
        min_success_rate=80.0,
        agent_type="customer_service",
    )

    agents = await search_service.search_agents(
        query="support",
        workspace_id="test-workspace-123",
        filters=filters,
    )

    assert isinstance(agents, list)


@pytest.mark.asyncio
async def test_search_activities(search_service):
    """Test activity search."""
    filters = ActivitySearchFilters(
        user_ids=["user-123"],
        event_types=["execution_completed"],
        date_range=DateRangeFilter(
            start=date.today() - timedelta(days=7),
            end=date.today(),
        ),
    )
    pagination = PaginationParams(skip=0, limit=100)

    activities, total = await search_service.search_activities(
        workspace_id="test-workspace-123",
        filters=filters,
        pagination=pagination,
    )

    assert isinstance(activities, list)
    assert total >= 0


@pytest.mark.asyncio
async def test_search_metrics(search_service):
    """Test metric search."""
    from src.models.schemas.search import ValueRange

    filters = MetricSearchFilters(
        metric_name="error_rate",
        value_range=ValueRange(min=0.01, max=0.1),
        date_range=DateRangeFilter(
            start=date.today() - timedelta(days=7),
            end=date.today(),
        ),
    )

    metrics = await search_service.search_metrics(
        workspace_id="test-workspace-123",
        filters=filters,
    )

    assert isinstance(metrics, list)


@pytest.mark.asyncio
async def test_search_alerts(search_service):
    """Test alert search."""
    from src.models.schemas.search import AlertSeverityEnum, AlertStatusEnum

    filters = AlertSearchFilters(
        severity=[AlertSeverityEnum.HIGH, AlertSeverityEnum.CRITICAL],
        status=[AlertStatusEnum.ACTIVE],
    )

    alerts = await search_service.search_alerts(
        query="error",
        workspace_id="test-workspace-123",
        filters=filters,
    )

    assert isinstance(alerts, list)


@pytest.mark.asyncio
async def test_search_reports(search_service):
    """Test report search."""
    from src.models.schemas.search import ReportTypeEnum

    filters = ReportSearchFilters(
        report_type=[ReportTypeEnum.SCHEDULED],
        created_by="admin@example.com",
    )

    reports = await search_service.search_reports(
        query="monthly",
        workspace_id="test-workspace-123",
        filters=filters,
    )

    assert isinstance(reports, list)


@pytest.mark.asyncio
async def test_get_search_suggestions(search_service):
    """Test search suggestions generation."""
    suggestions = await search_service.get_search_suggestions(
        query="err",
        workspace_id="test-workspace-123",
        user_id="user-123",
        limit=10,
    )

    assert isinstance(suggestions, list)
    assert len(suggestions) <= 10


@pytest.mark.asyncio
async def test_get_search_history(search_service):
    """Test search history retrieval."""
    history = await search_service.get_search_history(
        user_id="user-123",
        workspace_id="test-workspace-123",
        limit=20,
    )

    assert isinstance(history, list)


@pytest.mark.asyncio
async def test_clear_search_history(search_service):
    """Test search history clearing."""
    result = await search_service.clear_search_history(
        user_id="user-123",
        workspace_id="test-workspace-123",
    )

    assert result is True


@pytest.mark.asyncio
async def test_create_saved_search(search_service):
    """Test saved search creation."""
    saved_search = await search_service.create_saved_search(
        user_id="user-123",
        workspace_id="test-workspace-123",
        name="High Error Agents",
        query="error rate > 5%",
        filters={"metric": "error_rate"},
        alert_on_match=True,
        share_with_team=False,
    )

    assert saved_search.id is not None
    assert saved_search.name == "High Error Agents"
    assert saved_search.query == "error rate > 5%"


@pytest.mark.asyncio
async def test_get_saved_searches(search_service):
    """Test saved searches retrieval."""
    saved_searches = await search_service.get_saved_searches(
        user_id="user-123",
        workspace_id="test-workspace-123",
    )

    assert isinstance(saved_searches, list)


@pytest.mark.asyncio
async def test_get_search_analytics(search_service):
    """Test search analytics retrieval."""
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()

    analytics = await search_service.get_search_analytics(
        workspace_id="test-workspace-123",
        start_date=start_date,
        end_date=end_date,
    )

    assert analytics.total_searches >= 0
    assert analytics.unique_users >= 0
    assert isinstance(analytics.top_queries, list)
    assert isinstance(analytics.no_results_queries, list)
    assert analytics.search_performance is not None


@pytest.mark.asyncio
async def test_generate_suggestions_with_match(search_service):
    """Test suggestion generation with matching query."""
    suggestions = await search_service._generate_suggestions(
        query="error",
        workspace_id="test-workspace-123",
        limit=5,
    )

    assert isinstance(suggestions, list)
    # Should contain suggestions matching "error"
    if suggestions:
        assert any("error" in s.lower() for s in suggestions)


@pytest.mark.asyncio
async def test_generate_suggestions_empty_query(search_service):
    """Test suggestion generation with empty query."""
    suggestions = await search_service._generate_suggestions(
        query="",
        workspace_id="test-workspace-123",
        limit=5,
    )

    assert isinstance(suggestions, list)
