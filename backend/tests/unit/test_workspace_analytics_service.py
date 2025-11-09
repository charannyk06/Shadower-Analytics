"""Unit tests for workspace analytics service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.metrics.workspace_analytics_service import (
    WorkspaceAnalyticsService,
    WorkspaceAnalyticsConstants,
)


class TestWorkspaceAnalyticsService:
    """Test suite for WorkspaceAnalyticsService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create service instance with mock database."""
        return WorkspaceAnalyticsService(mock_db)

    def test_calculate_start_date_24h(self, service):
        """Test start date calculation for 24h timeframe."""
        now = datetime.utcnow()
        start_date = service._calculate_start_date("24h")
        delta = now - start_date

        # Should be approximately 1 day
        assert 0.9 <= delta.days <= 1.1

    def test_calculate_start_date_7d(self, service):
        """Test start date calculation for 7d timeframe."""
        now = datetime.utcnow()
        start_date = service._calculate_start_date("7d")
        delta = now - start_date

        # Should be approximately 7 days
        assert 6.9 <= delta.days <= 7.1

    def test_calculate_start_date_30d(self, service):
        """Test start date calculation for 30d timeframe."""
        now = datetime.utcnow()
        start_date = service._calculate_start_date("30d")
        delta = now - start_date

        # Should be approximately 30 days
        assert 29.9 <= delta.days <= 30.1

    def test_calculate_start_date_90d(self, service):
        """Test start date calculation for 90d timeframe."""
        now = datetime.utcnow()
        start_date = service._calculate_start_date("90d")
        delta = now - start_date

        # Should be approximately 90 days
        assert 89.9 <= delta.days <= 90.1

    def test_calculate_start_date_invalid_defaults_to_30d(self, service):
        """Test that invalid timeframe defaults to 30 days."""
        now = datetime.utcnow()
        start_date = service._calculate_start_date("invalid")
        delta = now - start_date

        # Should default to 30 days
        assert 29.9 <= delta.days <= 30.1

    def test_calculate_health_score_perfect_scores(self, service):
        """Test health score calculation with perfect component scores."""
        overview = {
            "successRate": 100.0,
            "memberActivityRate": 100.0,
        }
        member_analytics = {
            "engagementLevels": {"high": 10, "medium": 0, "low": 0}
        }
        agent_usage = {
            "efficiencyScore": 100
        }

        result = service._calculate_health_score(overview, member_analytics, agent_usage)

        assert result["overall"] == 100.0
        assert result["components"]["successRate"] == 100.0
        assert result["components"]["activity"] == 100.0
        assert result["components"]["engagement"] == 100.0
        assert result["components"]["efficiency"] == 100.0

    def test_calculate_health_score_zero_scores(self, service):
        """Test health score calculation with zero component scores."""
        overview = {
            "successRate": 0.0,
            "memberActivityRate": 0.0,
        }
        member_analytics = {
            "engagementLevels": {"high": 0, "medium": 0, "low": 10}
        }
        agent_usage = {
            "efficiencyScore": 0
        }

        result = service._calculate_health_score(overview, member_analytics, agent_usage)

        assert result["overall"] == 0.0
        assert result["components"]["successRate"] == 0.0
        assert result["components"]["activity"] == 0.0
        assert result["components"]["engagement"] == 0.0
        assert result["components"]["efficiency"] == 0.0

    def test_calculate_health_score_mixed_scores(self, service):
        """Test health score calculation with mixed component scores."""
        overview = {
            "successRate": 85.0,
            "memberActivityRate": 70.0,
        }
        member_analytics = {
            "engagementLevels": {"high": 5, "medium": 10, "low": 5}
        }
        agent_usage = {
            "efficiencyScore": 90
        }

        result = service._calculate_health_score(overview, member_analytics, agent_usage)

        # Overall should be weighted average
        expected = (
            85.0 * WorkspaceAnalyticsConstants.HEALTH_WEIGHT_SUCCESS_RATE +
            70.0 * WorkspaceAnalyticsConstants.HEALTH_WEIGHT_ACTIVITY +
            25.0 * WorkspaceAnalyticsConstants.HEALTH_WEIGHT_ENGAGEMENT +  # 5/20 * 100
            90.0 * WorkspaceAnalyticsConstants.HEALTH_WEIGHT_EFFICIENCY
        )

        assert abs(result["overall"] - expected) < 0.1

    def test_calculate_health_score_with_error_returns_defaults(self, service):
        """Test health score calculation handles errors gracefully."""
        # Pass invalid data structure
        overview = {}
        member_analytics = {}
        agent_usage = {}

        result = service._calculate_health_score(overview, member_analytics, agent_usage)

        # Should return default zero scores
        assert result["overall"] == 0.0
        assert result["components"]["successRate"] == 0.0
        assert result["components"]["activity"] == 0.0
        assert result["components"]["engagement"] == 0.0
        assert result["components"]["efficiency"] == 0.0

    def test_get_empty_overview(self, service):
        """Test empty overview structure."""
        result = service._get_empty_overview()

        assert result["workspaceName"] == ""
        assert result["createdAt"] is None
        assert result["totalMembers"] == 0
        assert result["activeMembers"] == 0
        assert result["memberActivityRate"] == 0.0
        assert result["totalActivity"] == 0
        assert result["totalRuns"] == 0
        assert result["successfulRuns"] == 0
        assert result["failedRuns"] == 0
        assert result["successRate"] == 0.0
        assert result["avgRuntime"] == 0.0

    def test_get_empty_agent_usage(self, service):
        """Test empty agent usage structure."""
        result = service._get_empty_agent_usage()

        assert result["totalAgents"] == 0
        assert result["totalRuns"] == 0
        assert result["successfulRuns"] == 0
        assert result["successRate"] == 0.0
        assert result["avgRuntime"] == 0.0
        assert result["totalCredits"] == 0.0
        assert result["efficiencyScore"] == WorkspaceAnalyticsConstants.DEFAULT_EFFICIENCY_SCORE

    @pytest.mark.asyncio
    async def test_get_workspace_overview_workspace_not_found(self, service, mock_db):
        """Test workspace overview when workspace doesn't exist."""
        # Mock empty result for workspace query
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()

        with pytest.raises(ValueError, match="Workspace .* not found"):
            await service._get_workspace_overview("nonexistent_workspace", start_date, end_date)

    @pytest.mark.asyncio
    async def test_get_workspace_overview_success(self, service, mock_db):
        """Test successful workspace overview retrieval."""
        # Mock workspace data
        workspace_row = Mock()
        workspace_row.workspace_id = "ws_123"
        workspace_row.workspace_name = "Test Workspace"
        workspace_row.created_at = datetime.utcnow()
        workspace_row.total_members = 10
        workspace_row.active_members = 7

        # Mock activity data
        activity_row = Mock()
        activity_row.total_activity = 100
        activity_row.active_users = 7
        activity_row.active_days = 15

        # Mock runs data
        runs_row = Mock()
        runs_row.total_runs = 50
        runs_row.successful_runs = 40
        runs_row.failed_runs = 10
        runs_row.avg_runtime = 15.5

        # Set up mock to return different values for different queries
        call_count = [0]

        def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            mock_result = Mock()
            if call_count[0] == 1:
                mock_result.fetchone.return_value = workspace_row
            elif call_count[0] == 2:
                mock_result.fetchone.return_value = activity_row
            else:
                mock_result.fetchone.return_value = runs_row
            return mock_result

        mock_db.execute.side_effect = execute_side_effect

        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()

        result = await service._get_workspace_overview("ws_123", start_date, end_date)

        assert result["workspaceName"] == "Test Workspace"
        assert result["totalMembers"] == 10
        assert result["activeMembers"] == 7
        assert result["memberActivityRate"] == 70.0  # 7/10 * 100
        assert result["totalActivity"] == 100
        assert result["totalRuns"] == 50
        assert result["successfulRuns"] == 40
        assert result["failedRuns"] == 10
        assert result["successRate"] == 80.0  # 40/50 * 100
        assert result["avgRuntime"] == 15.5

    @pytest.mark.asyncio
    async def test_get_member_analytics_empty_data(self, service, mock_db):
        """Test member analytics with no data."""
        # Mock empty result
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()

        result = await service._get_member_analytics("ws_123", start_date, end_date)

        assert result["topMembers"] == []
        assert result["engagementLevels"] == {"high": 0, "medium": 0, "low": 0}
        assert result["totalAnalyzed"] == 0

    @pytest.mark.asyncio
    async def test_get_member_analytics_with_data(self, service, mock_db):
        """Test member analytics with member data."""
        # Mock member rows with different engagement levels
        member_rows = [
            Mock(
                user_id="user1",
                activity_count=60,  # High engagement
                active_days=20,
                last_activity=datetime.utcnow()
            ),
            Mock(
                user_id="user2",
                activity_count=30,  # Medium engagement
                active_days=15,
                last_activity=datetime.utcnow()
            ),
            Mock(
                user_id="user3",
                activity_count=10,  # Low engagement
                active_days=5,
                last_activity=datetime.utcnow()
            ),
        ]

        mock_result = Mock()
        mock_result.fetchall.return_value = member_rows
        mock_db.execute.return_value = mock_result

        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()

        result = await service._get_member_analytics("ws_123", start_date, end_date)

        assert len(result["topMembers"]) == 3
        assert result["engagementLevels"]["high"] == 1
        assert result["engagementLevels"]["medium"] == 1
        assert result["engagementLevels"]["low"] == 1
        assert result["totalAnalyzed"] == 3

        # Check first member (high engagement)
        assert result["topMembers"][0]["userId"] == "user1"
        assert result["topMembers"][0]["activityCount"] == 60
        assert result["topMembers"][0]["engagement"] == "high"

    @pytest.mark.asyncio
    async def test_get_agent_usage_no_data(self, service, mock_db):
        """Test agent usage with no data."""
        # Mock empty result
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()

        result = await service._get_agent_usage("ws_123", start_date, end_date)

        # Should return empty structure
        assert result == service._get_empty_agent_usage()

    @pytest.mark.asyncio
    async def test_get_agent_usage_with_data(self, service, mock_db):
        """Test agent usage with data."""
        # Mock agent usage data
        agent_row = Mock()
        agent_row.total_agents = 5
        agent_row.total_runs = 100
        agent_row.successful_runs = 85
        agent_row.avg_runtime = 12.5
        agent_row.total_credits = 250.75

        mock_result = Mock()
        mock_result.fetchone.return_value = agent_row
        mock_db.execute.return_value = mock_result

        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()

        result = await service._get_agent_usage("ws_123", start_date, end_date)

        assert result["totalAgents"] == 5
        assert result["totalRuns"] == 100
        assert result["successfulRuns"] == 85
        assert result["successRate"] == 85.0
        assert result["avgRuntime"] == 12.5
        assert result["totalCredits"] == 250.75
        assert result["efficiencyScore"] == 85  # int(85/100 * 100)


class TestWorkspaceAnalyticsConstants:
    """Test suite for WorkspaceAnalyticsConstants."""

    def test_active_member_days_constant(self):
        """Test ACTIVE_MEMBER_DAYS constant value."""
        assert WorkspaceAnalyticsConstants.ACTIVE_MEMBER_DAYS == 7

    def test_engagement_thresholds(self):
        """Test engagement threshold constants."""
        assert WorkspaceAnalyticsConstants.ENGAGEMENT_HIGH_THRESHOLD == 50
        assert WorkspaceAnalyticsConstants.ENGAGEMENT_MEDIUM_THRESHOLD == 20

    def test_health_weights_sum_to_one(self):
        """Test that health score weights sum to 1.0."""
        total_weight = (
            WorkspaceAnalyticsConstants.HEALTH_WEIGHT_SUCCESS_RATE +
            WorkspaceAnalyticsConstants.HEALTH_WEIGHT_ACTIVITY +
            WorkspaceAnalyticsConstants.HEALTH_WEIGHT_ENGAGEMENT +
            WorkspaceAnalyticsConstants.HEALTH_WEIGHT_EFFICIENCY
        )
        assert abs(total_weight - 1.0) < 0.01  # Allow small floating point error

    def test_default_efficiency_score(self):
        """Test default efficiency score constant."""
        assert WorkspaceAnalyticsConstants.DEFAULT_EFFICIENCY_SCORE == 100

    def test_limits_are_positive(self):
        """Test that all limit constants are positive."""
        assert WorkspaceAnalyticsConstants.MAX_MEMBERS_LIMIT > 0
        assert WorkspaceAnalyticsConstants.MAX_DAILY_CONSUMPTION_DAYS > 0
        assert WorkspaceAnalyticsConstants.TOP_MEMBERS_LIMIT > 0
