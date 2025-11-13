"""Search service for analytics data."""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, desc, asc
import logging

from ...models.schemas.search import (
    GlobalSearchResponse,
    AdvancedSearchConfig,
    AdvancedSearchResponse,
    UserSearchResult,
    AgentSearchResult,
    ActivitySearchResult,
    MetricSearchResult,
    AlertSearchResult,
    ReportSearchResult,
    SearchSuggestion,
    SearchHistoryItem,
    SavedSearchItem,
    SearchAnalyticsData,
    TopQuery,
    SearchPerformance,
    UserSearchFilters,
    AgentSearchFilters,
    ActivitySearchFilters,
    MetricSearchFilters,
    AlertSearchFilters,
    ReportSearchFilters,
)
from ...models.schemas.common import PaginationParams

logger = logging.getLogger(__name__)


class SearchService:
    """Service for search functionality."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def global_search(
        self,
        query: str,
        workspace_id: str,
        types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> GlobalSearchResponse:
        """
        Perform global search across all entity types.

        Args:
            query: Search query string
            workspace_id: Workspace context
            types: Filter by entity types
            limit: Max results per type

        Returns:
            GlobalSearchResponse with results from all types
        """
        search_types = types or ["all"]
        results = {}

        try:
            # Search users if requested
            if "all" in search_types or "users" in search_types:
                users = await self._search_users_internal(
                    query, workspace_id, limit
                )
                results["users"] = [user.dict() for user in users]

            # Search agents if requested
            if "all" in search_types or "agents" in search_types:
                agents = await self._search_agents_internal(
                    query, workspace_id, limit
                )
                results["agents"] = [agent.dict() for agent in agents]

            # Search reports if requested
            if "all" in search_types or "reports" in search_types:
                reports = await self._search_reports_internal(
                    query, workspace_id, limit
                )
                results["reports"] = [report.dict() for report in reports]

            # Search alerts if requested
            if "all" in search_types or "alerts" in search_types:
                alerts = await self._search_alerts_internal(
                    query, workspace_id, limit
                )
                results["alerts"] = [alert.dict() for alert in alerts]

            # Calculate total results
            total_results = sum(len(v) for v in results.values())

            # Generate suggestions based on query
            suggestions = await self._generate_suggestions(query, workspace_id)

            return GlobalSearchResponse(
                query=query,
                total_results=total_results,
                results=results,
                suggestions=suggestions,
            )

        except Exception as e:
            logger.error(f"Error in global search: {str(e)}", exc_info=True)
            raise

    async def advanced_search(
        self, config: AdvancedSearchConfig
    ) -> AdvancedSearchResponse:
        """
        Perform advanced search with complex filters.

        Args:
            config: Advanced search configuration

        Returns:
            AdvancedSearchResponse with filtered results
        """
        start_time = datetime.now()

        try:
            # Build query based on filters
            # This is a placeholder implementation
            # In production, you'd integrate with Elasticsearch or similar
            results = []
            aggregations = {}

            # Execute search query
            # TODO: Implement actual search logic with filters

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            return AdvancedSearchResponse(
                results=results,
                total=len(results),
                aggregations=aggregations,
                execution_time_ms=execution_time,
            )

        except Exception as e:
            logger.error(f"Error in advanced search: {str(e)}", exc_info=True)
            raise

    async def search_users(
        self,
        query: str,
        workspace_id: str,
        filters: Optional[UserSearchFilters] = None,
        pagination: Optional[PaginationParams] = None,
    ) -> Tuple[List[UserSearchResult], int]:
        """
        Search users with filters.

        Args:
            query: Search query
            workspace_id: Workspace context
            filters: User search filters
            pagination: Pagination parameters

        Returns:
            Tuple of (user results, total count)
        """
        users = await self._search_users_internal(
            query, workspace_id, pagination.limit if pagination else 100
        )
        return users, len(users)

    async def search_agents(
        self,
        query: Optional[str],
        workspace_id: str,
        filters: Optional[AgentSearchFilters] = None,
    ) -> List[AgentSearchResult]:
        """
        Search agents with performance filters.

        Args:
            query: Search query (optional)
            workspace_id: Workspace context
            filters: Agent search filters

        Returns:
            List of agent search results
        """
        return await self._search_agents_internal(query or "", workspace_id, 100)

    async def search_activities(
        self,
        workspace_id: str,
        filters: ActivitySearchFilters,
        pagination: Optional[PaginationParams] = None,
    ) -> Tuple[List[ActivitySearchResult], int]:
        """
        Search user activities and events.

        Args:
            workspace_id: Workspace context
            filters: Activity search filters
            pagination: Pagination parameters

        Returns:
            Tuple of (activity results, total count)
        """
        # Placeholder implementation
        # TODO: Implement actual activity search
        activities = []
        return activities, 0

    async def search_metrics(
        self,
        workspace_id: str,
        filters: MetricSearchFilters,
    ) -> List[MetricSearchResult]:
        """
        Search for specific metric values.

        Args:
            workspace_id: Workspace context
            filters: Metric search filters

        Returns:
            List of metric search results
        """
        # Placeholder implementation
        # TODO: Implement actual metric search
        return []

    async def search_alerts(
        self,
        query: Optional[str],
        workspace_id: str,
        filters: AlertSearchFilters,
    ) -> List[AlertSearchResult]:
        """
        Search alerts and notifications.

        Args:
            query: Search query (optional)
            workspace_id: Workspace context
            filters: Alert search filters

        Returns:
            List of alert search results
        """
        return await self._search_alerts_internal(query or "", workspace_id, 100)

    async def search_reports(
        self,
        query: Optional[str],
        workspace_id: str,
        filters: ReportSearchFilters,
    ) -> List[ReportSearchResult]:
        """
        Search generated reports.

        Args:
            query: Search query (optional)
            workspace_id: Workspace context
            filters: Report search filters

        Returns:
            List of report search results
        """
        return await self._search_reports_internal(query or "", workspace_id, 100)

    async def get_search_suggestions(
        self,
        query: str,
        workspace_id: str,
        user_id: str,
        limit: int = 10,
    ) -> List[SearchSuggestion]:
        """
        Get search suggestions based on partial query.

        Args:
            query: Partial search query
            workspace_id: Workspace context
            user_id: User context for personalization
            limit: Maximum suggestions to return

        Returns:
            List of search suggestions
        """
        return await self._generate_suggestions(query, workspace_id, limit)

    async def get_search_history(
        self,
        user_id: str,
        workspace_id: str,
        limit: int = 20,
    ) -> List[SearchHistoryItem]:
        """
        Get user's search history.

        Args:
            user_id: User ID
            workspace_id: Workspace context
            limit: Maximum history items to return

        Returns:
            List of search history items
        """
        # Placeholder implementation
        # TODO: Implement actual search history retrieval
        return []

    async def clear_search_history(
        self,
        user_id: str,
        workspace_id: str,
    ) -> bool:
        """
        Clear user's search history.

        Args:
            user_id: User ID
            workspace_id: Workspace context

        Returns:
            True if cleared successfully
        """
        # Placeholder implementation
        # TODO: Implement actual search history clearing
        return True

    async def create_saved_search(
        self,
        user_id: str,
        workspace_id: str,
        name: str,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        alert_on_match: bool = False,
        share_with_team: bool = False,
    ) -> SavedSearchItem:
        """
        Create a saved search configuration.

        Args:
            user_id: User ID
            workspace_id: Workspace context
            name: Search name
            query: Search query
            filters: Search filters
            alert_on_match: Whether to alert on matches
            share_with_team: Whether to share with team

        Returns:
            Created saved search item
        """
        # Placeholder implementation
        # TODO: Implement actual saved search creation
        return SavedSearchItem(
            id=f"search_{int(datetime.now().timestamp())}",
            name=name,
            query=query,
            filters=filters,
            alert_on_match=alert_on_match,
            share_with_team=share_with_team,
            created_at=datetime.now(),
            run_count=0,
        )

    async def get_saved_searches(
        self,
        user_id: str,
        workspace_id: str,
    ) -> List[SavedSearchItem]:
        """
        Get user's saved searches.

        Args:
            user_id: User ID
            workspace_id: Workspace context

        Returns:
            List of saved search items
        """
        # Placeholder implementation
        # TODO: Implement actual saved search retrieval
        return []

    async def get_search_analytics(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> SearchAnalyticsData:
        """
        Get analytics about search usage.

        Args:
            workspace_id: Workspace context
            start_date: Start date for analysis
            end_date: End date for analysis

        Returns:
            Search analytics data
        """
        # Placeholder implementation
        # TODO: Implement actual search analytics
        return SearchAnalyticsData(
            total_searches=0,
            unique_users=0,
            avg_searches_per_user=0.0,
            top_queries=[],
            no_results_queries=[],
            avg_results_per_search=0.0,
            search_performance=SearchPerformance(
                avg_response_time_ms=0.0,
                p95_response_time_ms=0.0,
            ),
        )

    # Internal helper methods

    async def _search_users_internal(
        self, query: str, workspace_id: str, limit: int
    ) -> List[UserSearchResult]:
        """Internal method to search users."""
        # Placeholder implementation
        # TODO: Implement actual user search with SQL queries
        return []

    async def _search_agents_internal(
        self, query: str, workspace_id: str, limit: int
    ) -> List[AgentSearchResult]:
        """Internal method to search agents."""
        # Placeholder implementation
        # TODO: Implement actual agent search with SQL queries
        return []

    async def _search_alerts_internal(
        self, query: str, workspace_id: str, limit: int
    ) -> List[AlertSearchResult]:
        """Internal method to search alerts."""
        # Placeholder implementation
        # TODO: Implement actual alert search with SQL queries
        return []

    async def _search_reports_internal(
        self, query: str, workspace_id: str, limit: int
    ) -> List[ReportSearchResult]:
        """Internal method to search reports."""
        # Placeholder implementation
        # TODO: Implement actual report search with SQL queries
        return []

    async def _generate_suggestions(
        self, query: str, workspace_id: str, limit: int = 10
    ) -> List[str]:
        """Internal method to generate search suggestions."""
        # Placeholder implementation
        # TODO: Implement actual suggestion generation
        suggestions = []

        # Common suggestions based on partial query
        common_queries = [
            "error rate by agent",
            "active users",
            "high latency agents",
            "failed executions",
            "credit usage",
        ]

        # Filter suggestions that match the query
        for suggestion in common_queries:
            if query.lower() in suggestion.lower():
                suggestions.append(suggestion)

        return suggestions[:limit]
