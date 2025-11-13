"""
Unit tests for advanced error analytics services.

Tests root cause analysis, adaptive recovery, and business impact calculation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import json


class TestRootCauseAnalyzer:
    """Tests for RootCauseAnalyzer service."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = Mock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        return db

    @pytest.fixture
    def sample_error_data(self):
        """Sample error data for testing."""
        return {
            "error_id": "550e8400-e29b-41d4-a716-446655440000",
            "workspace_id": "660e8400-e29b-41d4-a716-446655440000",
            "error_type": "TimeoutError",
            "message": "Operation timed out after 30 seconds",
            "severity": "high",
            "first_seen": datetime.utcnow() - timedelta(hours=24),
            "last_seen": datetime.utcnow(),
            "occurrence_count": 25,
            "stack_trace": "Error: timeout at line 42",
            "context": {},
            "users_affected": ["user1", "user2"],
            "agents_affected": ["agent1"],
            "occurrences": [
                {"occurred_at": datetime.utcnow().isoformat(), "metadata": {}}
            ]
        }

    @pytest.mark.asyncio
    async def test_identify_immediate_cause_timeout(self, mock_db, sample_error_data):
        """Test identification of immediate cause for timeout error."""
        from backend.src.services.analytics.root_cause_analyzer import RootCauseAnalyzer

        analyzer = RootCauseAnalyzer(mock_db)

        # Mock database response
        mock_db.execute.return_value.fetchone.return_value = None

        immediate_cause = await analyzer._identify_immediate_cause(sample_error_data)

        assert "timeout" in immediate_cause.lower() or "time limit" in immediate_cause.lower()

    @pytest.mark.asyncio
    async def test_trace_root_causes_returns_list(self, mock_db, sample_error_data):
        """Test that root cause tracing returns a list of potential causes."""
        from backend.src.services.analytics.root_cause_analyzer import RootCauseAnalyzer

        analyzer = RootCauseAnalyzer(mock_db)

        root_causes = await analyzer._trace_root_causes(sample_error_data, depth=3)

        assert isinstance(root_causes, list)
        if len(root_causes) > 0:
            assert "cause" in root_causes[0]
            assert "probability" in root_causes[0]
            assert "evidence" in root_causes[0]
            assert "remediation" in root_causes[0]

    @pytest.mark.asyncio
    async def test_identify_contributing_factors(self, mock_db, sample_error_data):
        """Test identification of contributing factors."""
        from backend.src.services.analytics.root_cause_analyzer import RootCauseAnalyzer

        analyzer = RootCauseAnalyzer(mock_db)

        factors = await analyzer._identify_contributing_factors(sample_error_data)

        assert isinstance(factors, list)
        # Should identify multiple users as contributing factor
        assert any("user" in str(factor).lower() for factor in factors)


class TestAdaptiveRecoveryEngine:
    """Tests for AdaptiveRecoveryEngine service."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = Mock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        return db

    @pytest.fixture
    def sample_strategy(self):
        """Sample recovery strategy."""
        return Mock(
            strategy_id="retry_exponential",
            strategy_name="Exponential Backoff Retry",
            strategy_type="retry",
            success_rate=0.85,
            avg_recovery_time_ms=2000,
            total_invocations=100,
            config={"max_attempts": 3, "initial_delay_ms": 1000, "multiplier": 2}
        )

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self, mock_db):
        """Test that circuit breaker opens after threshold failures."""
        from backend.src.services.analytics.adaptive_recovery_engine import AdaptiveRecoveryEngine

        engine = AdaptiveRecoveryEngine(mock_db)
        agent_id = "test-agent-123"

        # Implement circuit breaker
        cb_config = engine.implement_circuit_breaker(agent_id)
        assert cb_config["state"] == "closed"

        # Trigger failures
        for _ in range(5):
            await engine._update_circuit_breaker(agent_id, success=False)

        # Circuit should now be open
        assert engine._is_circuit_open(agent_id) == True

    @pytest.mark.asyncio
    async def test_circuit_breaker_closes_after_success(self, mock_db):
        """Test that circuit breaker closes after successful recovery."""
        from backend.src.services.analytics.adaptive_recovery_engine import AdaptiveRecoveryEngine

        engine = AdaptiveRecoveryEngine(mock_db)
        agent_id = "test-agent-123"

        # Set up circuit breaker in half-open state
        engine.implement_circuit_breaker(agent_id)
        engine.circuit_breakers[agent_id]["state"] = "half-open"

        # Successful recovery should close circuit
        await engine._update_circuit_breaker(agent_id, success=True)

        assert engine.circuit_breakers[agent_id]["state"] == "closed"

    @pytest.mark.asyncio
    async def test_strategy_scoring(self, mock_db, sample_strategy):
        """Test recovery strategy scoring algorithm."""
        from backend.src.services.analytics.adaptive_recovery_engine import AdaptiveRecoveryEngine

        engine = AdaptiveRecoveryEngine(mock_db)

        error = {
            "error_type": "TimeoutError",
            "severity": "high"
        }
        history = []

        score = await engine._score_strategy(sample_strategy, error, history)

        assert isinstance(score, float)
        assert 0 <= score <= 100

    @pytest.mark.asyncio
    async def test_dry_run_returns_simulation(self, mock_db):
        """Test that dry_run mode returns simulation without executing."""
        from backend.src.services.analytics.adaptive_recovery_engine import AdaptiveRecoveryEngine

        engine = AdaptiveRecoveryEngine(mock_db)
        error_id = "550e8400-e29b-41d4-a716-446655440000"

        # Mock database responses
        mock_db.execute.return_value.fetchone.return_value = Mock(
            error_id=error_id,
            workspace_id="workspace-123",
            error_type="TimeoutError",
            severity="high",
            agents_affected=["agent-1"]
        )
        mock_db.execute.return_value.fetchall.return_value = []

        result = await engine.auto_recover(error_id, dry_run=True)

        assert result["status"] in ["dry_run", "not_recoverable", "circuit_open", "no_strategy"]


class TestBusinessImpactCalculator:
    """Tests for BusinessImpactCalculator service."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = Mock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        return db

    @pytest.fixture
    def sample_error_data(self):
        """Sample error data for impact calculation."""
        return {
            "error_id": "550e8400-e29b-41d4-a716-446655440000",
            "workspace_id": "660e8400-e29b-41d4-a716-446655440000",
            "error_type": "TimeoutError",
            "severity": "critical",
            "first_seen": datetime.utcnow() - timedelta(hours=2),
            "last_seen": datetime.utcnow(),
            "resolved_at": None,
            "occurrence_count": 50,
            "users_affected": [f"user{i}" for i in range(25)],
            "agents_affected": ["agent1", "agent2"],
            "credits_lost": 1000.0,
            "executions_affected": 75
        }

    def test_calculate_financial_impact(self, mock_db, sample_error_data):
        """Test financial impact calculation."""
        from backend.src.services.analytics.business_impact_calculator import BusinessImpactCalculator

        calculator = BusinessImpactCalculator(mock_db)

        financial = calculator._calculate_financial_impact(sample_error_data, {})

        assert "lost_revenue" in financial
        assert "additional_costs" in financial
        assert "credit_refunds" in financial
        assert financial["lost_revenue"] > 0
        assert financial["credit_refunds"] > 0  # Critical error should trigger refunds

    @pytest.mark.asyncio
    async def test_calculate_operational_impact(self, mock_db, sample_error_data):
        """Test operational impact calculation."""
        from backend.src.services.analytics.business_impact_calculator import BusinessImpactCalculator

        calculator = BusinessImpactCalculator(mock_db)

        # Mock SLA check
        mock_db.execute.return_value.fetchone.return_value = None

        operational = await calculator._calculate_operational_impact(sample_error_data, {})

        assert "downtime_minutes" in operational
        assert "affected_workflows" in operational
        assert "manual_intervention_hours" in operational
        assert "sla_violations" in operational
        assert operational["downtime_minutes"] > 0

    def test_calculate_user_impact_critical(self, mock_db, sample_error_data):
        """Test user impact calculation for critical error."""
        from backend.src.services.analytics.business_impact_calculator import BusinessImpactCalculator

        calculator = BusinessImpactCalculator(mock_db)

        user_impact = calculator._calculate_user_impact(sample_error_data, {})

        assert "affected_users" in user_impact
        assert "user_satisfaction_impact" in user_impact
        assert "churn_risk" in user_impact
        assert "support_tickets_generated" in user_impact

        assert user_impact["affected_users"] == 25
        assert user_impact["churn_risk"] > 0.1  # Critical error should have significant churn risk
        assert user_impact["support_tickets_generated"] > 0

    def test_calculate_reputation_impact(self, mock_db, sample_error_data):
        """Test reputation impact calculation."""
        from backend.src.services.analytics.business_impact_calculator import BusinessImpactCalculator

        calculator = BusinessImpactCalculator(mock_db)

        reputation = calculator._calculate_reputation_impact(sample_error_data, {})

        assert "severity_score" in reputation
        assert "public_visibility" in reputation
        assert "recovery_time_expectation" in reputation

        # Critical error with many users should have high visibility risk
        assert reputation["public_visibility"] == True
        assert reputation["severity_score"] > 50

    def test_determine_overall_severity_critical(self, mock_db):
        """Test overall severity determination for critical case."""
        from backend.src.services.analytics.business_impact_calculator import BusinessImpactCalculator

        calculator = BusinessImpactCalculator(mock_db)

        financial = {"total_financial_impact": 1500.0}
        operational = {"downtime_minutes": 180}
        user = {"affected_users": 150, "churn_risk": 0.3}
        reputation = {"public_visibility": True}

        severity = calculator._determine_overall_severity(
            financial, operational, user, reputation
        )

        assert severity == "critical"

    def test_determine_overall_severity_low(self, mock_db):
        """Test overall severity determination for low impact case."""
        from backend.src.services.analytics.business_impact_calculator import BusinessImpactCalculator

        calculator = BusinessImpactCalculator(mock_db)

        financial = {"total_financial_impact": 50.0}
        operational = {"downtime_minutes": 10}
        user = {"affected_users": 5, "churn_risk": 0.01}
        reputation = {"public_visibility": False}

        severity = calculator._determine_overall_severity(
            financial, operational, user, reputation
        )

        assert severity == "low"


class TestErrorCorrelationAnalysis:
    """Tests for error correlation and cascading failure detection."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = Mock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_detect_cascading_failure(self, mock_db):
        """Test cascading failure detection."""
        # Mock query results
        mock_db.execute.return_value.fetchall.return_value = [
            Mock(
                initial_error_id="error-1",
                cascade_chain=["error-1", "error-2", "error-3"],
                cascade_length=3,
                affected_agents=5,
                cascade_severity="moderate_cascade"
            )
        ]

        # Test would call the SQL function and verify results
        # This is a placeholder for integration with actual DB
        pass


# Pytest configuration
@pytest.fixture(autouse=True)
def reset_circuit_breakers():
    """Reset circuit breaker state between tests."""
    from backend.src.services.analytics.adaptive_recovery_engine import AdaptiveRecoveryEngine

    # Create temporary instance to clear state
    engine = AdaptiveRecoveryEngine(Mock())
    engine.circuit_breakers.clear()

    yield

    engine.circuit_breakers.clear()
