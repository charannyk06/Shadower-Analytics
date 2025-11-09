"""
Unit tests for ComparisonService
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.models.comparison_views import (
    ComparisonType,
    ComparisonFilters,
    ComparisonOptions,
)
from src.services.comparison_service import ComparisonService


class TestComparisonService:
    """Test suite for ComparisonService"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = AsyncMock()
        return db

    @pytest.fixture
    def comparison_service(self, mock_db):
        """ComparisonService instance"""
        return ComparisonService(mock_db)

    @pytest.fixture
    def sample_filters(self):
        """Sample comparison filters"""
        return ComparisonFilters(
            agent_ids=["agent-1", "agent-2", "agent-3"],
            start_date=datetime.utcnow() - timedelta(days=7),
            end_date=datetime.utcnow(),
        )

    @pytest.fixture
    def sample_options(self):
        """Sample comparison options"""
        return ComparisonOptions(
            include_recommendations=True,
            include_visual_diff=True,
            include_statistics=True,
        )

    # ========================================================================
    # Agent Comparison Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_compare_agents_success(
        self, comparison_service, sample_filters, sample_options
    ):
        """Test successful agent comparison"""
        response = await comparison_service.generate_comparison(
            comparison_type=ComparisonType.AGENTS,
            filters=sample_filters,
            options=sample_options,
        )

        assert response.success is True
        assert response.data is not None
        assert response.data.type == ComparisonType.AGENTS
        assert response.data.agent_comparison is not None
        assert len(response.data.agent_comparison.agents) == 3
        assert response.metadata.processing_time > 0
        assert response.metadata.entity_count == 3

    @pytest.mark.asyncio
    async def test_compare_agents_too_few(
        self, comparison_service, sample_options
    ):
        """Test agent comparison with too few agents"""
        filters = ComparisonFilters(agent_ids=["agent-1"])

        response = await comparison_service.generate_comparison(
            comparison_type=ComparisonType.AGENTS,
            filters=filters,
            options=sample_options,
        )

        assert response.success is False
        assert response.error is not None
        assert "at least 2 agents" in response.error.message.lower()

    @pytest.mark.asyncio
    async def test_agent_comparison_winner_determination(
        self, comparison_service, sample_filters, sample_options
    ):
        """Test winner determination in agent comparison"""
        response = await comparison_service.generate_comparison(
            comparison_type=ComparisonType.AGENTS,
            filters=sample_filters,
            options=sample_options,
        )

        assert response.success is True
        agent_comparison = response.data.agent_comparison

        # Winner should be one of the compared agents
        agent_ids = [a.id for a in agent_comparison.agents]
        assert agent_comparison.winner in agent_ids

        # Winner score should be between 0 and 100
        assert 0 <= agent_comparison.winner_score <= 100

    @pytest.mark.asyncio
    async def test_agent_comparison_recommendations(
        self, comparison_service, sample_filters, sample_options
    ):
        """Test recommendation generation"""
        response = await comparison_service.generate_comparison(
            comparison_type=ComparisonType.AGENTS,
            filters=sample_filters,
            options=sample_options,
        )

        assert response.success is True
        recommendations = response.data.agent_comparison.recommendations

        # Should have some recommendations
        assert isinstance(recommendations, list)

        # Each recommendation should have required fields
        for rec in recommendations:
            assert rec.type is not None
            assert rec.priority is not None
            assert rec.title
            assert rec.description
            assert isinstance(rec.affected_agents, list)

    # ========================================================================
    # Period Comparison Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_compare_periods_success(
        self, comparison_service, sample_options
    ):
        """Test successful period comparison"""
        filters = ComparisonFilters(
            start_date=datetime.utcnow() - timedelta(days=7),
            end_date=datetime.utcnow(),
        )

        response = await comparison_service.generate_comparison(
            comparison_type=ComparisonType.PERIODS,
            filters=filters,
            options=sample_options,
        )

        assert response.success is True
        assert response.data is not None
        assert response.data.type == ComparisonType.PERIODS
        assert response.data.period_comparison is not None

        period_comp = response.data.period_comparison
        assert period_comp.current is not None
        assert period_comp.previous is not None
        assert period_comp.change is not None

    @pytest.mark.asyncio
    async def test_period_comparison_changes(
        self, comparison_service, sample_options
    ):
        """Test change calculation in period comparison"""
        filters = ComparisonFilters(
            start_date=datetime.utcnow() - timedelta(days=7),
            end_date=datetime.utcnow(),
        )

        response = await comparison_service.generate_comparison(
            comparison_type=ComparisonType.PERIODS,
            filters=filters,
            options=sample_options,
        )

        assert response.success is True
        change = response.data.period_comparison.change

        # All change fields should be present
        assert change.total_runs is not None
        assert change.success_rate is not None
        assert change.average_runtime is not None
        assert change.total_cost is not None

        # Each change should have required properties
        assert change.total_runs.trend in ["up", "down", "stable"]
        assert change.total_runs.direction in ["positive", "negative", "neutral"]
        assert isinstance(change.total_runs.significant, bool)

    @pytest.mark.asyncio
    async def test_period_comparison_improvements_regressions(
        self, comparison_service, sample_options
    ):
        """Test improvement and regression identification"""
        filters = ComparisonFilters(
            start_date=datetime.utcnow() - timedelta(days=7),
            end_date=datetime.utcnow(),
        )

        response = await comparison_service.generate_comparison(
            comparison_type=ComparisonType.PERIODS,
            filters=filters,
            options=sample_options,
        )

        assert response.success is True
        period_comp = response.data.period_comparison

        # Should have lists (may be empty)
        assert isinstance(period_comp.improvements, list)
        assert isinstance(period_comp.regressions, list)

        # Should have a summary
        assert period_comp.summary
        assert len(period_comp.summary) > 0

    # ========================================================================
    # Workspace Comparison Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_compare_workspaces_success(
        self, comparison_service, sample_options
    ):
        """Test successful workspace comparison"""
        filters = ComparisonFilters(
            workspace_ids=["ws-1", "ws-2", "ws-3"]
        )

        response = await comparison_service.generate_comparison(
            comparison_type=ComparisonType.WORKSPACES,
            filters=filters,
            options=sample_options,
        )

        assert response.success is True
        assert response.data is not None
        assert response.data.type == ComparisonType.WORKSPACES
        assert response.data.workspace_comparison is not None

        ws_comp = response.data.workspace_comparison
        assert len(ws_comp.workspaces) == 3
        assert ws_comp.benchmarks is not None
        assert ws_comp.rankings is not None

    @pytest.mark.asyncio
    async def test_workspace_comparison_rankings(
        self, comparison_service, sample_options
    ):
        """Test workspace ranking generation"""
        filters = ComparisonFilters(
            workspace_ids=["ws-1", "ws-2", "ws-3", "ws-4"]
        )

        response = await comparison_service.generate_comparison(
            comparison_type=ComparisonType.WORKSPACES,
            filters=filters,
            options=sample_options,
        )

        assert response.success is True
        rankings = response.data.workspace_comparison.rankings

        # Should have rankings for all workspaces
        assert len(rankings.rankings) == 4

        # Rankings should be sorted by rank
        for i, ranking in enumerate(rankings.rankings):
            assert ranking.rank == i + 1
            assert 0 <= ranking.score <= 100
            assert 0 <= ranking.percentile <= 100
            assert isinstance(ranking.strengths, list)
            assert isinstance(ranking.weaknesses, list)

    # ========================================================================
    # Metric Comparison Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_compare_metrics_success(
        self, comparison_service, sample_options
    ):
        """Test successful metric comparison"""
        filters = ComparisonFilters(
            metric_names=["success_rate"],
        )

        response = await comparison_service.generate_comparison(
            comparison_type=ComparisonType.METRICS,
            filters=filters,
            options=sample_options,
        )

        assert response.success is True
        assert response.data is not None
        assert response.data.type == ComparisonType.METRICS
        assert response.data.metric_comparison is not None

        metric_comp = response.data.metric_comparison
        assert metric_comp.metric_name == "success_rate"
        assert len(metric_comp.entities) >= 2

    @pytest.mark.asyncio
    async def test_metric_comparison_statistics(
        self, comparison_service, sample_options
    ):
        """Test statistical calculations"""
        filters = ComparisonFilters(
            metric_names=["success_rate"],
        )

        response = await comparison_service.generate_comparison(
            comparison_type=ComparisonType.METRICS,
            filters=filters,
            options=sample_options,
        )

        assert response.success is True
        stats = response.data.metric_comparison.statistics

        # All statistical measures should be present
        assert stats.mean is not None
        assert stats.median is not None
        assert stats.standard_deviation >= 0
        assert stats.min <= stats.max
        assert stats.p25 <= stats.median <= stats.p75

    @pytest.mark.asyncio
    async def test_metric_comparison_distribution(
        self, comparison_service, sample_options
    ):
        """Test distribution calculation"""
        filters = ComparisonFilters(
            metric_names=["success_rate"],
        )

        response = await comparison_service.generate_comparison(
            comparison_type=ComparisonType.METRICS,
            filters=filters,
            options=sample_options,
        )

        assert response.success is True
        distribution = response.data.metric_comparison.distribution

        # Should have buckets
        assert len(distribution.buckets) > 0

        # Bucket percentages should sum to ~100
        total_percentage = sum(b.percentage for b in distribution.buckets)
        assert 99 <= total_percentage <= 101

        # Distribution properties
        assert isinstance(distribution.is_normal, bool)

    @pytest.mark.asyncio
    async def test_metric_comparison_outliers(
        self, comparison_service, sample_options
    ):
        """Test outlier detection"""
        filters = ComparisonFilters(
            metric_names=["success_rate"],
        )

        response = await comparison_service.generate_comparison(
            comparison_type=ComparisonType.METRICS,
            filters=filters,
            options=sample_options,
        )

        assert response.success is True
        outliers = response.data.metric_comparison.outliers

        # Outliers should have required fields
        for outlier in outliers:
            assert abs(outlier.z_score) > 2  # Outliers have |z| > 2
            assert outlier.type in ["high", "low"]
            assert outlier.severity in ["mild", "moderate", "extreme"]

    # ========================================================================
    # Performance Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_comparison_performance(
        self, comparison_service, sample_filters, sample_options
    ):
        """Test that comparison completes within performance target"""
        response = await comparison_service.generate_comparison(
            comparison_type=ComparisonType.AGENTS,
            filters=sample_filters,
            options=sample_options,
        )

        assert response.success is True
        # Should complete in less than 1.5 seconds
        assert response.metadata.processing_time < 1.5

    # ========================================================================
    # Error Handling Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_invalid_comparison_type(
        self, comparison_service, sample_filters, sample_options
    ):
        """Test handling of invalid comparison type"""
        with pytest.raises(ValueError):
            await comparison_service.generate_comparison(
                comparison_type="invalid_type",
                filters=sample_filters,
                options=sample_options,
            )
