"""Unit tests for leaderboard service."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.analytics.leaderboard_service import LeaderboardService
from src.models.schemas.leaderboards import (
    TimeFrame,
    AgentCriteria,
    UserCriteria,
    WorkspaceCriteria,
    AgentLeaderboardQuery,
    UserLeaderboardQuery,
    WorkspaceLeaderboardQuery,
)


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def leaderboard_service(mock_db_session):
    """Create a LeaderboardService instance with mock database."""
    return LeaderboardService(db=mock_db_session)


class TestLeaderboardService:
    """Test suite for LeaderboardService."""

    # ===================================================================
    # INITIALIZATION TESTS
    # ===================================================================

    def test_service_initialization(self, leaderboard_service, mock_db_session):
        """Test service initializes correctly."""
        assert leaderboard_service.db == mock_db_session
        assert leaderboard_service.QUERY_TIMEOUT_SECONDS == 30
        assert leaderboard_service.MIN_RUNS_FOR_AGENT_RANKING == 5

    # ===================================================================
    # AGENT LEADERBOARD TESTS
    # ===================================================================

    @pytest.mark.asyncio
    async def test_get_agent_leaderboard_validation(self, leaderboard_service):
        """Test agent leaderboard validates workspace ID."""
        query = AgentLeaderboardQuery(
            workspaceId="invalid-uuid",
            timeframe=TimeFrame.SEVEN_DAYS,
            criteria=AgentCriteria.SUCCESS_RATE,
        )

        with pytest.raises(ValueError, match="Invalid workspace ID"):
            await leaderboard_service.get_agent_leaderboard(
                workspace_id="invalid-uuid",
                query=query,
            )

    @pytest.mark.asyncio
    async def test_get_agent_score_formula_success_rate(self, leaderboard_service):
        """Test agent score formula for success rate criteria."""
        formula = leaderboard_service._get_agent_score_formula(AgentCriteria.SUCCESS_RATE)
        assert "AVG(CASE WHEN ae.status = 'success'" in formula
        assert "0.7" in formula  # Weight for success rate

    @pytest.mark.asyncio
    async def test_get_agent_score_formula_runs(self, leaderboard_service):
        """Test agent score formula for runs criteria."""
        formula = leaderboard_service._get_agent_score_formula(AgentCriteria.RUNS)
        assert "COUNT(ae.id)" in formula

    @pytest.mark.asyncio
    async def test_get_agent_score_formula_speed(self, leaderboard_service):
        """Test agent score formula for speed criteria."""
        formula = leaderboard_service._get_agent_score_formula(AgentCriteria.SPEED)
        assert "duration" in formula.lower()

    @pytest.mark.asyncio
    async def test_get_agent_score_formula_efficiency(self, leaderboard_service):
        """Test agent score formula for efficiency criteria."""
        formula = leaderboard_service._get_agent_score_formula(AgentCriteria.EFFICIENCY)
        assert "success" in formula.lower()
        assert "credits" in formula.lower()
        assert "duration" in formula.lower()

    @pytest.mark.asyncio
    async def test_get_agent_score_formula_popularity(self, leaderboard_service):
        """Test agent score formula for popularity criteria."""
        formula = leaderboard_service._get_agent_score_formula(AgentCriteria.POPULARITY)
        assert "COUNT(DISTINCT ae.user_id)" in formula

    # ===================================================================
    # USER LEADERBOARD TESTS
    # ===================================================================

    @pytest.mark.asyncio
    async def test_get_user_leaderboard_validation(self, leaderboard_service):
        """Test user leaderboard validates workspace ID."""
        query = UserLeaderboardQuery(
            workspaceId="invalid-uuid",
            timeframe=TimeFrame.SEVEN_DAYS,
            criteria=UserCriteria.ACTIVITY,
        )

        with pytest.raises(ValueError, match="Invalid workspace ID"):
            await leaderboard_service.get_user_leaderboard(
                workspace_id="invalid-uuid",
                query=query,
            )

    @pytest.mark.asyncio
    async def test_get_user_score_formula_activity(self, leaderboard_service):
        """Test user score formula for activity criteria."""
        formula = leaderboard_service._get_user_score_formula(UserCriteria.ACTIVITY)
        assert "COUNT(DISTINCT ae.id)" in formula
        assert "agent_id" in formula.lower()

    @pytest.mark.asyncio
    async def test_get_user_score_formula_efficiency(self, leaderboard_service):
        """Test user score formula for efficiency criteria."""
        formula = leaderboard_service._get_user_score_formula(UserCriteria.EFFICIENCY)
        assert "success" in formula.lower()
        assert "credits" in formula.lower()

    @pytest.mark.asyncio
    async def test_get_user_score_formula_contribution(self, leaderboard_service):
        """Test user score formula for contribution criteria."""
        formula = leaderboard_service._get_user_score_formula(UserCriteria.CONTRIBUTION)
        assert "COUNT(DISTINCT ae.id)" in formula
        assert "agent_id" in formula.lower()

    @pytest.mark.asyncio
    async def test_get_user_score_formula_savings(self, leaderboard_service):
        """Test user score formula for savings criteria."""
        formula = leaderboard_service._get_user_score_formula(UserCriteria.SAVINGS)
        assert "credits" in formula.lower()

    @pytest.mark.asyncio
    async def test_calculate_user_achievements(self, leaderboard_service):
        """Test user achievements calculation."""
        # Mock row with high metrics
        class MockRow:
            total_actions = 150
            success_rate = 96.0
            agents_used = 12
            rank = 5

        row = MockRow()
        achievements = leaderboard_service._calculate_user_achievements(row)

        assert "Century Club" in achievements  # 100+ actions
        assert "Perfectionist" in achievements  # 95%+ success rate
        assert "Explorer" in achievements  # 10+ agents
        assert "Top Performer" in achievements  # Top 10 rank

    @pytest.mark.asyncio
    async def test_calculate_user_achievements_minimal(self, leaderboard_service):
        """Test user achievements with minimal metrics."""
        class MockRow:
            total_actions = 10
            success_rate = 50.0
            agents_used = 2
            rank = 50

        row = MockRow()
        achievements = leaderboard_service._calculate_user_achievements(row)

        assert len(achievements) == 0  # No achievements met

    # ===================================================================
    # WORKSPACE LEADERBOARD TESTS
    # ===================================================================

    @pytest.mark.asyncio
    async def test_get_workspace_score_formula_activity(self, leaderboard_service):
        """Test workspace score formula for activity criteria."""
        formula = leaderboard_service._get_workspace_score_formula(WorkspaceCriteria.ACTIVITY)
        assert "COUNT(DISTINCT ae.id)" in formula
        assert "COUNT(DISTINCT ae.user_id)" in formula
        assert "COUNT(DISTINCT ae.agent_id)" in formula

    @pytest.mark.asyncio
    async def test_get_workspace_score_formula_efficiency(self, leaderboard_service):
        """Test workspace score formula for efficiency criteria."""
        formula = leaderboard_service._get_workspace_score_formula(WorkspaceCriteria.EFFICIENCY)
        assert "success" in formula.lower()

    @pytest.mark.asyncio
    async def test_get_workspace_score_formula_growth(self, leaderboard_service):
        """Test workspace score formula for growth criteria."""
        formula = leaderboard_service._get_workspace_score_formula(WorkspaceCriteria.GROWTH)
        assert "user_id" in formula.lower()
        assert "agent_id" in formula.lower()

    @pytest.mark.asyncio
    async def test_get_workspace_score_formula_innovation(self, leaderboard_service):
        """Test workspace score formula for innovation criteria."""
        formula = leaderboard_service._get_workspace_score_formula(WorkspaceCriteria.INNOVATION)
        assert "agent_id" in formula.lower()
        assert "user_id" in formula.lower()

    # ===================================================================
    # CACHING TESTS
    # ===================================================================

    @pytest.mark.asyncio
    async def test_cache_ttl_configuration(self, leaderboard_service):
        """Test cache TTL is configured for different timeframes."""
        assert leaderboard_service.CACHE_TTL_SECONDS["24h"] == 300  # 5 minutes
        assert leaderboard_service.CACHE_TTL_SECONDS["7d"] == 900  # 15 minutes
        assert leaderboard_service.CACHE_TTL_SECONDS["30d"] == 1800  # 30 minutes
        assert leaderboard_service.CACHE_TTL_SECONDS["90d"] == 3600  # 1 hour
        assert leaderboard_service.CACHE_TTL_SECONDS["all"] == 7200  # 2 hours

    # ===================================================================
    # THRESHOLD TESTS
    # ===================================================================

    def test_ranking_thresholds(self, leaderboard_service):
        """Test minimum thresholds for rankings."""
        assert leaderboard_service.MIN_RUNS_FOR_AGENT_RANKING == 5
        assert leaderboard_service.MIN_ACTIONS_FOR_USER_RANKING == 1
        assert leaderboard_service.MIN_ACTIVITY_FOR_WORKSPACE_RANKING == 10

    # ===================================================================
    # EDGE CASE TESTS
    # ===================================================================

    @pytest.mark.asyncio
    async def test_empty_rankings(self, leaderboard_service, mock_db_session):
        """Test handling of empty rankings."""
        # Mock empty query result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        rankings = await leaderboard_service._calculate_agent_rankings(
            workspace_id="00000000-0000-0000-0000-000000000000",
            timeframe=TimeFrame.SEVEN_DAYS,
            criteria=AgentCriteria.SUCCESS_RATE,
        )

        assert rankings == []

    @pytest.mark.asyncio
    async def test_badge_assignment(self, leaderboard_service, mock_db_session):
        """Test badge assignment for top 3 rankings."""
        # Mock query result with 5 agents
        mock_result = MagicMock()

        class MockRow:
            def __init__(self, rank, score):
                self.rank = rank
                self.agent_id = f"agent-{rank}"
                self.agent_name = f"Agent {rank}"
                self.agent_type = "test"
                self.workspace_id = "workspace-1"
                self.workspace_name = "Test Workspace"
                self.total_runs = 100
                self.success_rate = 95.0
                self.avg_runtime = 1000.0
                self.credits_per_run = 10.0
                self.unique_users = 5
                self.score = score
                self.percentile = 100 - (rank - 1) * 20
                self.total_count = 5

        mock_result.fetchall.return_value = [
            MockRow(1, 100.0),
            MockRow(2, 90.0),
            MockRow(3, 80.0),
            MockRow(4, 70.0),
            MockRow(5, 60.0),
        ]
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        rankings = await leaderboard_service._calculate_agent_rankings(
            workspace_id="00000000-0000-0000-0000-000000000000",
            timeframe=TimeFrame.SEVEN_DAYS,
            criteria=AgentCriteria.SUCCESS_RATE,
        )

        assert rankings[0]["badge"] == "gold"
        assert rankings[1]["badge"] == "silver"
        assert rankings[2]["badge"] == "bronze"
        assert rankings[3]["badge"] is None
        assert rankings[4]["badge"] is None


class TestLeaderboardQueries:
    """Test leaderboard query parameter classes."""

    def test_agent_leaderboard_query_defaults(self):
        """Test default values for agent leaderboard query."""
        query = AgentLeaderboardQuery(workspaceId="workspace-123")
        assert query.timeframe == TimeFrame.SEVEN_DAYS
        assert query.criteria == AgentCriteria.SUCCESS_RATE
        assert query.limit == 100
        assert query.offset == 0

    def test_user_leaderboard_query_defaults(self):
        """Test default values for user leaderboard query."""
        query = UserLeaderboardQuery(workspaceId="workspace-123")
        assert query.timeframe == TimeFrame.SEVEN_DAYS
        assert query.criteria == UserCriteria.ACTIVITY
        assert query.limit == 100
        assert query.offset == 0

    def test_workspace_leaderboard_query_defaults(self):
        """Test default values for workspace leaderboard query."""
        query = WorkspaceLeaderboardQuery()
        assert query.timeframe == TimeFrame.SEVEN_DAYS
        assert query.criteria == WorkspaceCriteria.ACTIVITY
        assert query.limit == 100
        assert query.offset == 0

    def test_query_custom_values(self):
        """Test custom values for leaderboard queries."""
        query = AgentLeaderboardQuery(
            workspaceId="workspace-123",
            timeframe=TimeFrame.THIRTY_DAYS,
            criteria=AgentCriteria.RUNS,
            limit=50,
            offset=10,
        )
        assert query.timeframe == TimeFrame.THIRTY_DAYS
        assert query.criteria == AgentCriteria.RUNS
        assert query.limit == 50
        assert query.offset == 10
