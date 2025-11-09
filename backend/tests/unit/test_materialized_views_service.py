"""
Unit tests for MaterializedViewRefreshService

Tests cover:
- Individual view refresh
- Batch refresh operations
- Status monitoring
- Statistics retrieval
- Health checks
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.materialized_views import MaterializedViewRefreshService


@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def service(mock_db_session):
    """Create a MaterializedViewRefreshService instance"""
    return MaterializedViewRefreshService(mock_db_session)


class TestMaterializedViewRefreshService:
    """Test cases for MaterializedViewRefreshService"""

    @pytest.mark.asyncio
    async def test_refresh_view_success(self, service, mock_db_session):
        """Test successful refresh of a single view"""
        # Setup
        view_name = "mv_agent_performance"
        mock_db_session.execute.return_value = None

        # Execute
        result = await service.refresh_view(view_name, concurrent=True)

        # Assert
        assert result["success"] is True
        assert result["view_name"] == view_name
        assert result["error"] is None
        assert "started_at" in result
        assert "completed_at" in result
        assert result["duration_seconds"] > 0

        # Verify correct SQL was executed
        # refresh_view executes a single query combining timeout setting and refresh
        assert mock_db_session.execute.call_count == 1
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_view_invalid_name(self, service):
        """Test refresh with invalid view name"""
        # Execute
        result = await service.refresh_view("invalid_view", concurrent=True)

        # Assert
        assert result["success"] is False
        assert "Unknown materialized view" in result["error"]

    @pytest.mark.asyncio
    async def test_refresh_view_database_error(self, service, mock_db_session):
        """Test handling of database errors during refresh"""
        # Setup
        view_name = "mv_agent_performance"
        mock_db_session.execute.side_effect = Exception("Database connection failed")

        # Execute
        result = await service.refresh_view(view_name, concurrent=True)

        # Assert
        assert result["success"] is False
        assert result["view_name"] == view_name
        assert "Database connection failed" in result["error"]
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_view_concurrent_mode(self, service, mock_db_session):
        """Test refresh with concurrent mode enabled"""
        # Setup
        view_name = "mv_agent_performance"

        # Execute
        await service.refresh_view(view_name, concurrent=True)

        # Assert - verify CONCURRENTLY keyword was used
        calls = mock_db_session.execute.call_args_list
        refresh_call = calls[0][0][0]  # Single call combines timeout and refresh
        assert "CONCURRENTLY" in str(refresh_call)

    @pytest.mark.asyncio
    async def test_refresh_view_non_concurrent_mode(self, service, mock_db_session):
        """Test refresh with concurrent mode disabled"""
        # Setup
        view_name = "mv_agent_performance"

        # Execute
        await service.refresh_view(view_name, concurrent=False)

        # Assert - verify CONCURRENTLY keyword was NOT used
        calls = mock_db_session.execute.call_args_list
        refresh_call = calls[0][0][0]  # Single call combines timeout and refresh
        assert "CONCURRENTLY" not in str(refresh_call)

    @pytest.mark.asyncio
    async def test_refresh_all_success(self, service, mock_db_session):
        """Test successful refresh of all views"""
        # Execute
        results = await service.refresh_all(concurrent=True)

        # Assert
        assert len(results) == len(service.VIEWS)
        assert all(r["success"] for r in results)
        assert len(set(r["view_name"] for r in results)) == len(service.VIEWS)

    @pytest.mark.asyncio
    async def test_refresh_all_partial_failure(self, service, mock_db_session):
        """Test refresh when some views fail"""
        # Setup - make every other view fail
        call_count = [0]

        def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            # Each view has 1 call (combines timeout and refresh)
            # Make every other view fail
            if call_count[0] % 2 == 0:  # Every other view fails
                raise Exception("Refresh failed")
            return None

        mock_db_session.execute.side_effect = execute_side_effect

        # Execute
        results = await service.refresh_all(concurrent=True)

        # Assert
        assert len(results) == len(service.VIEWS)
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        assert len(failed) > 0  # At least some failures
        assert all("error" in r and r["error"] for r in failed)

    @pytest.mark.asyncio
    async def test_refresh_specific_views(self, service, mock_db_session):
        """Test refresh of specific subset of views"""
        # Setup
        specific_views = ["mv_agent_performance", "mv_workspace_metrics"]

        # Execute
        results = await service.refresh_all(views=specific_views)

        # Assert
        assert len(results) == len(specific_views)
        assert all(r["view_name"] in specific_views for r in results)

    @pytest.mark.asyncio
    async def test_get_refresh_status(self, service, mock_db_session):
        """Test retrieval of refresh status"""
        # Setup
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.view_name = "mv_agent_performance"
        mock_row.owner = "postgres"
        mock_row.ispopulated = True
        mock_row.hasindexes = True
        mock_row.total_size = "1024 kB"
        mock_row.data_size = "512 kB"
        mock_row.index_size = "512 kB"
        mock_row.description = "Active users summary"

        mock_result.fetchall.return_value = [mock_row]
        mock_db_session.execute.return_value = mock_result

        # Execute
        status = await service.get_refresh_status()

        # Assert
        assert len(status) == 1
        assert status[0]["view_name"] == "mv_agent_performance"
        assert status[0]["is_populated"] is True
        assert status[0]["has_indexes"] is True
        assert status[0]["total_size"] == "1024 kB"

    @pytest.mark.asyncio
    async def test_get_view_statistics(self, service, mock_db_session):
        """Test retrieval of view statistics"""
        # Setup
        view_name = "mv_agent_performance"
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.schemaname = "analytics"
        mock_row.view_name = view_name
        mock_row.rows_inserted = 1000
        mock_row.rows_updated = 50
        mock_row.rows_deleted = 10
        mock_row.live_rows = 990
        mock_row.dead_rows = 10
        mock_row.last_vacuum = datetime(2025, 11, 9, 12, 0, 0)
        mock_row.last_autovacuum = None
        mock_row.last_analyze = datetime(2025, 11, 9, 12, 0, 0)
        mock_row.last_autoanalyze = None
        mock_row.vacuum_count = 5
        mock_row.autovacuum_count = 10
        mock_row.analyze_count = 5
        mock_row.autoanalyze_count = 10

        mock_result.fetchone.return_value = mock_row
        mock_db_session.execute.return_value = mock_result

        # Execute
        stats = await service.get_view_statistics(view_name)

        # Assert
        assert stats is not None
        assert stats["view_name"] == view_name
        assert stats["live_rows"] == 990
        assert stats["dead_rows"] == 10
        assert stats["vacuum_count"] == 5

    @pytest.mark.asyncio
    async def test_get_view_statistics_not_found(self, service, mock_db_session):
        """Test statistics retrieval for non-existent view"""
        # Setup
        view_name = "mv_agent_performance"
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Execute
        stats = await service.get_view_statistics(view_name)

        # Assert
        assert stats is None

    @pytest.mark.asyncio
    async def test_get_view_statistics_invalid_name(self, service):
        """Test statistics retrieval with invalid view name"""
        # Execute & Assert
        with pytest.raises(ValueError, match="Unknown materialized view"):
            await service.get_view_statistics("invalid_view")

    @pytest.mark.asyncio
    async def test_get_row_count(self, service, mock_db_session):
        """Test row count retrieval"""
        # Setup
        view_name = "mv_agent_performance"
        mock_result = MagicMock()
        # get_row_count returns row[0] from fetchone(), so mock as tuple
        mock_result.fetchone.return_value = (1500,)
        mock_db_session.execute.return_value = mock_result

        # Execute
        count = await service.get_row_count(view_name)

        # Assert
        assert count == 1500

    @pytest.mark.asyncio
    async def test_get_row_count_invalid_name(self, service):
        """Test row count retrieval with invalid view name"""
        # Execute & Assert
        with pytest.raises(ValueError, match="Unknown materialized view"):
            await service.get_row_count("invalid_view")

    @pytest.mark.asyncio
    async def test_check_view_health_all_healthy(self, service, mock_db_session):
        """Test health check when all views are healthy"""
        # Setup
        mock_status_result = MagicMock()
        mock_status_row = MagicMock()
        mock_status_row.ispopulated = True
        mock_status_row.hasindexes = True
        mock_status_result.fetchone.return_value = mock_status_row

        mock_count_result = MagicMock()
        # get_row_count returns row[0] from fetchone(), so mock as tuple
        mock_count_result.fetchone.return_value = (100,)

        # Alternate between status and count queries
        # Each view has: 1 status query + 1 count query (via get_row_count)
        mock_db_session.execute.side_effect = [
            mock_status_result, mock_count_result
        ] * len(service.VIEWS)

        # Execute
        health_results = await service.check_view_health()

        # Assert
        assert len(health_results) == len(service.VIEWS)
        assert all(h["healthy"] for h in health_results)
        assert all(len(h["issues"]) == 0 for h in health_results)

    @pytest.mark.asyncio
    async def test_check_view_health_unpopulated_view(self, service, mock_db_session):
        """Test health check with unpopulated view"""
        # Setup - only check first view
        service.VIEWS = ["mv_agent_performance"]

        mock_status_result = MagicMock()
        mock_status_row = MagicMock()
        mock_status_row.ispopulated = False
        mock_status_row.hasindexes = True
        mock_status_result.fetchone.return_value = mock_status_row

        mock_count_result = MagicMock()
        # get_row_count returns row[0] from fetchone(), so mock as tuple
        mock_count_result.fetchone.return_value = (0,)

        mock_db_session.execute.side_effect = [
            mock_status_result, mock_count_result
        ]

        # Execute
        health_results = await service.check_view_health()

        # Assert
        assert len(health_results) == 1
        assert health_results[0]["healthy"] is False
        assert "View is not populated" in health_results[0]["issues"]
        assert "View has no rows" in health_results[0]["issues"]

    @pytest.mark.asyncio
    async def test_check_view_health_no_indexes(self, service, mock_db_session):
        """Test health check with view missing indexes"""
        # Setup - only check first view
        service.VIEWS = ["mv_agent_performance"]

        mock_status_result = MagicMock()
        mock_status_row = MagicMock()
        mock_status_row.ispopulated = True
        mock_status_row.hasindexes = False
        mock_status_result.fetchone.return_value = mock_status_row

        mock_count_result = MagicMock()
        # get_row_count returns row[0] from fetchone(), so mock as tuple
        mock_count_result.fetchone.return_value = (100,)

        mock_db_session.execute.side_effect = [
            mock_status_result, mock_count_result
        ]

        # Execute
        health_results = await service.check_view_health()

        # Assert
        assert len(health_results) == 1
        assert health_results[0]["healthy"] is False
        assert "View has no indexes" in health_results[0]["issues"]

    @pytest.mark.asyncio
    async def test_resolve_dependencies(self, service):
        """Test dependency resolution"""
        # Setup
        views = ["mv_top_agents_enhanced", "mv_agent_performance"]

        # Execute
        ordered = service._resolve_dependencies(views)

        # Assert
        # mv_agent_performance should come before mv_top_agents_enhanced
        assert ordered.index("mv_agent_performance") < ordered.index("mv_top_agents_enhanced")

    @pytest.mark.asyncio
    async def test_resolve_dependencies_no_dependencies(self, service):
        """Test dependency resolution with independent views"""
        # Setup
        views = ["mv_agent_performance", "mv_error_summary"]

        # Execute
        ordered = service._resolve_dependencies(views)

        # Assert
        assert len(ordered) == 2
        assert set(ordered) == set(views)

    @pytest.mark.asyncio
    async def test_refresh_using_function(self, service, mock_db_session):
        """Test refresh using database function"""
        # Setup
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.view_name = "mv_agent_performance"
        mock_row.refresh_started_at = datetime.now(timezone.utc)
        mock_row.refresh_completed_at = datetime.now(timezone.utc)
        mock_row.duration_seconds = 1.5
        mock_row.success = True
        mock_row.error_message = None

        mock_result.fetchall.return_value = [mock_row]
        mock_db_session.execute.return_value = mock_result

        # Execute
        results = await service.refresh_using_function(concurrent_mode=True)

        # Assert
        assert len(results) == 1
        assert results[0]["view_name"] == "mv_agent_performance"
        assert results[0]["success"] is True
        assert results[0]["duration_seconds"] == 1.5

    @pytest.mark.asyncio
    async def test_refresh_timeout_setting(self, service, mock_db_session):
        """Test that timeout is properly set"""
        # Setup
        view_name = "mv_agent_performance"

        # Execute
        await service.refresh_view(view_name)

        # Assert
        calls = mock_db_session.execute.call_args_list
        timeout_call = calls[0][0][0]  # Single call combines timeout setting and refresh
        assert f"'{service.REFRESH_TIMEOUT}s'" in str(timeout_call)

    @pytest.mark.asyncio
    async def test_service_views_list(self, service):
        """Test that service has expected views"""
        # Assert
        assert "mv_agent_performance" in service.VIEWS
        assert "mv_workspace_metrics" in service.VIEWS
        assert "mv_top_agents_enhanced" in service.VIEWS
        assert "mv_error_summary" in service.VIEWS

    @pytest.mark.asyncio
    async def test_service_dependencies(self, service):
        """Test that service has proper dependencies configured"""
        # Assert
        assert "mv_top_agents_enhanced" in service.DEPENDENCIES
        assert "mv_agent_performance" in service.DEPENDENCIES["mv_top_agents_enhanced"]
