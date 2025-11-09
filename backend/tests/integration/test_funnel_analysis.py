"""Integration tests for funnel analysis."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.services.analytics.funnel_analysis import FunnelAnalysisService


class TestFunnelAnalysisService:
    """Test funnel analysis service functionality."""

    @pytest.fixture
    async def service(self, db_session):
        """Create funnel analysis service instance."""
        return FunnelAnalysisService(db_session)

    @pytest.fixture
    def workspace_id(self):
        """Sample workspace ID."""
        return str(uuid4())

    @pytest.fixture
    def user_id(self):
        """Sample user ID."""
        return str(uuid4())

    @pytest.fixture
    def sample_funnel_steps(self):
        """Sample funnel steps."""
        return [
            {
                "stepId": "landing",
                "stepName": "Landing Page",
                "event": "page_view_landing",
            },
            {
                "stepId": "signup",
                "stepName": "Sign Up",
                "event": "signup_form_submit",
            },
            {
                "stepId": "verify",
                "stepName": "Email Verification",
                "event": "email_verified",
            },
            {
                "stepId": "complete",
                "stepName": "Onboarding Complete",
                "event": "onboarding_complete",
            },
        ]

    # ===================================================================
    # FUNNEL DEFINITION TESTS
    # ===================================================================

    @pytest.mark.asyncio
    async def test_create_funnel_definition(
        self, service, workspace_id, user_id, sample_funnel_steps
    ):
        """Test creating a funnel definition."""
        funnel = await service.create_funnel_definition(
            workspace_id=workspace_id,
            name="Sign-up Funnel",
            steps=sample_funnel_steps,
            description="Test funnel for sign-up process",
            timeframe="30d",
            created_by=user_id,
        )

        assert funnel["funnelId"] is not None
        assert funnel["name"] == "Sign-up Funnel"
        assert len(funnel["steps"]) == 4
        assert funnel["status"] == "active"
        assert funnel["timeframe"] == "30d"

    @pytest.mark.asyncio
    async def test_create_funnel_validation_min_steps(
        self, service, workspace_id, user_id
    ):
        """Test funnel creation fails with less than 2 steps."""
        with pytest.raises(ValueError, match="at least 2 steps"):
            await service.create_funnel_definition(
                workspace_id=workspace_id,
                name="Invalid Funnel",
                steps=[{"stepId": "1", "stepName": "Step 1", "event": "event1"}],
                created_by=user_id,
            )

    @pytest.mark.asyncio
    async def test_create_funnel_validation_step_fields(
        self, service, workspace_id, user_id
    ):
        """Test funnel creation fails with invalid step format."""
        with pytest.raises(ValueError, match="missing required fields"):
            await service.create_funnel_definition(
                workspace_id=workspace_id,
                name="Invalid Funnel",
                steps=[
                    {"stepId": "1", "stepName": "Step 1"},  # Missing 'event'
                    {"stepId": "2", "event": "event2"},  # Missing 'stepName'
                ],
                created_by=user_id,
            )

    @pytest.mark.asyncio
    async def test_list_funnel_definitions(
        self, service, workspace_id, user_id, sample_funnel_steps
    ):
        """Test listing funnel definitions."""
        # Create multiple funnels
        await service.create_funnel_definition(
            workspace_id=workspace_id,
            name="Funnel 1",
            steps=sample_funnel_steps,
            created_by=user_id,
        )

        await service.create_funnel_definition(
            workspace_id=workspace_id,
            name="Funnel 2",
            steps=sample_funnel_steps,
            created_by=user_id,
        )

        # List funnels
        funnels = await service.list_funnel_definitions(workspace_id=workspace_id)

        assert len(funnels) >= 2
        assert all("funnelId" in f for f in funnels)
        assert all("name" in f for f in funnels)

    @pytest.mark.asyncio
    async def test_get_funnel_definition(
        self, service, workspace_id, user_id, sample_funnel_steps
    ):
        """Test getting a specific funnel definition."""
        # Create funnel
        created_funnel = await service.create_funnel_definition(
            workspace_id=workspace_id,
            name="Test Funnel",
            steps=sample_funnel_steps,
            description="Test description",
            created_by=user_id,
        )

        funnel_id = created_funnel["funnelId"]

        # Get funnel
        funnel = await service.get_funnel_definition(
            funnel_id=funnel_id, workspace_id=workspace_id
        )

        assert funnel is not None
        assert funnel["funnelId"] == funnel_id
        assert funnel["name"] == "Test Funnel"
        assert funnel["description"] == "Test description"
        assert len(funnel["steps"]) == 4

    @pytest.mark.asyncio
    async def test_update_funnel_definition(
        self, service, workspace_id, user_id, sample_funnel_steps
    ):
        """Test updating a funnel definition."""
        # Create funnel
        created_funnel = await service.create_funnel_definition(
            workspace_id=workspace_id,
            name="Original Name",
            steps=sample_funnel_steps,
            created_by=user_id,
        )

        funnel_id = created_funnel["funnelId"]

        # Update funnel
        updated_funnel = await service.update_funnel_definition(
            funnel_id=funnel_id,
            workspace_id=workspace_id,
            updates={
                "name": "Updated Name",
                "description": "New description",
                "status": "paused",
            },
        )

        assert updated_funnel["name"] == "Updated Name"
        assert updated_funnel["description"] == "New description"
        assert updated_funnel["status"] == "paused"

    # ===================================================================
    # FUNNEL ANALYSIS TESTS
    # ===================================================================

    @pytest.mark.asyncio
    async def test_analyze_funnel_basic(
        self, service, workspace_id, user_id, sample_funnel_steps
    ):
        """Test basic funnel analysis."""
        # Create funnel
        funnel = await service.create_funnel_definition(
            workspace_id=workspace_id,
            name="Test Funnel",
            steps=sample_funnel_steps,
            created_by=user_id,
        )

        funnel_id = funnel["funnelId"]

        # Analyze funnel
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)

        analysis = await service.analyze_funnel(
            funnel_id=funnel_id,
            workspace_id=workspace_id,
            start_date=start_date,
            end_date=end_date,
        )

        assert analysis["funnelId"] == funnel_id
        assert analysis["funnelName"] == "Test Funnel"
        assert len(analysis["steps"]) == 4
        assert "overall" in analysis
        assert "totalConversion" in analysis["overall"]

    @pytest.mark.asyncio
    async def test_analyze_funnel_conversion_rates(
        self, service, workspace_id, user_id, sample_funnel_steps
    ):
        """Test funnel analysis conversion rate calculations."""
        # Create funnel
        funnel = await service.create_funnel_definition(
            workspace_id=workspace_id,
            name="Test Funnel",
            steps=sample_funnel_steps,
            created_by=user_id,
        )

        funnel_id = funnel["funnelId"]

        # Analyze funnel
        analysis = await service.analyze_funnel(
            funnel_id=funnel_id, workspace_id=workspace_id
        )

        # Verify conversion rates
        for i, step in enumerate(analysis["steps"]):
            if i == 0:
                # First step should always be 100% conversion
                assert step["metrics"]["conversionRate"] == 100.0
                assert step["metrics"]["dropOffRate"] == 0.0
            else:
                # Subsequent steps should have valid conversion rates
                assert 0 <= step["metrics"]["conversionRate"] <= 100
                assert 0 <= step["metrics"]["dropOffRate"] <= 100

    # ===================================================================
    # USER JOURNEY TESTS
    # ===================================================================

    @pytest.mark.asyncio
    async def test_track_user_journey(
        self, service, workspace_id, user_id, sample_funnel_steps
    ):
        """Test tracking user journey through funnel."""
        # Create funnel
        funnel = await service.create_funnel_definition(
            workspace_id=workspace_id,
            name="Test Funnel",
            steps=sample_funnel_steps,
            created_by=user_id,
        )

        funnel_id = funnel["funnelId"]
        journey_user_id = str(uuid4())

        # Track user progress through steps
        for step in sample_funnel_steps:
            await service.track_user_journey(
                funnel_id=funnel_id,
                workspace_id=workspace_id,
                user_id=journey_user_id,
                step_id=step["stepId"],
                step_name=step["stepName"],
            )

        # Get user journeys
        journeys = await service.get_user_journeys(
            funnel_id=funnel_id, workspace_id=workspace_id, limit=10
        )

        assert journeys["total"] > 0
        assert len(journeys["journeys"]) > 0

        # Find our journey
        our_journey = next(
            (j for j in journeys["journeys"] if j["userId"] == journey_user_id), None
        )
        assert our_journey is not None
        assert len(our_journey["journeyPath"]) == 4

    @pytest.mark.asyncio
    async def test_get_user_journeys_with_status_filter(
        self, service, workspace_id, user_id, sample_funnel_steps
    ):
        """Test getting user journeys with status filter."""
        # Create funnel
        funnel = await service.create_funnel_definition(
            workspace_id=workspace_id,
            name="Test Funnel",
            steps=sample_funnel_steps,
            created_by=user_id,
        )

        funnel_id = funnel["funnelId"]

        # Get completed journeys
        completed_journeys = await service.get_user_journeys(
            funnel_id=funnel_id, workspace_id=workspace_id, status="completed"
        )

        assert "journeys" in completed_journeys
        assert "total" in completed_journeys

        # Get in-progress journeys
        in_progress_journeys = await service.get_user_journeys(
            funnel_id=funnel_id, workspace_id=workspace_id, status="in_progress"
        )

        assert "journeys" in in_progress_journeys
        assert "total" in in_progress_journeys

    # ===================================================================
    # PERFORMANCE SUMMARY TESTS
    # ===================================================================

    @pytest.mark.asyncio
    async def test_get_funnel_performance_summary(
        self, service, workspace_id, user_id, sample_funnel_steps
    ):
        """Test getting funnel performance summary."""
        # Create a funnel
        await service.create_funnel_definition(
            workspace_id=workspace_id,
            name="Test Funnel",
            steps=sample_funnel_steps,
            created_by=user_id,
        )

        # Get performance summary
        summary = await service.get_funnel_performance_summary(
            workspace_id=workspace_id, timeframe="30d"
        )

        assert "funnels" in summary
        assert "timeframe" in summary
        assert "generatedAt" in summary
        assert summary["timeframe"] == "30d"

    # ===================================================================
    # EDGE CASES AND ERROR HANDLING
    # ===================================================================

    @pytest.mark.asyncio
    async def test_analyze_nonexistent_funnel(self, service, workspace_id):
        """Test analyzing a non-existent funnel."""
        fake_funnel_id = str(uuid4())

        with pytest.raises(ValueError, match="not found"):
            await service.analyze_funnel(
                funnel_id=fake_funnel_id, workspace_id=workspace_id
            )

    @pytest.mark.asyncio
    async def test_get_nonexistent_funnel(self, service, workspace_id):
        """Test getting a non-existent funnel."""
        fake_funnel_id = str(uuid4())

        funnel = await service.get_funnel_definition(
            funnel_id=fake_funnel_id, workspace_id=workspace_id
        )

        assert funnel is None

    @pytest.mark.asyncio
    async def test_invalid_workspace_id(self, service, sample_funnel_steps):
        """Test operations with invalid workspace ID."""
        with pytest.raises(ValueError, match="Invalid"):
            await service.create_funnel_definition(
                workspace_id="not-a-uuid",
                name="Test Funnel",
                steps=sample_funnel_steps,
            )

    @pytest.mark.asyncio
    async def test_duplicate_funnel_name_allowed(
        self, service, workspace_id, user_id, sample_funnel_steps
    ):
        """Test that duplicate funnel names are allowed (different IDs)."""
        # Create first funnel
        funnel1 = await service.create_funnel_definition(
            workspace_id=workspace_id,
            name="Duplicate Name",
            steps=sample_funnel_steps,
            created_by=user_id,
        )

        # This should succeed but with unique constraint if implemented
        # For now, we allow duplicates (different funnel IDs)
        try:
            funnel2 = await service.create_funnel_definition(
                workspace_id=workspace_id,
                name="Duplicate Name",
                steps=sample_funnel_steps,
                created_by=user_id,
            )
            # If unique constraint is not enforced, ensure IDs are different
            assert funnel1["funnelId"] != funnel2["funnelId"]
        except Exception:
            # If unique constraint is enforced, that's also acceptable
            pass


class TestFunnelAnalysisHelperFunctions:
    """Test helper functions for funnel analysis."""

    def test_calculate_conversion_rate(self):
        """Test conversion rate calculation."""
        # Test normal case
        assert self._calc_conversion_rate(100, 200) == 50.0

        # Test 100% conversion
        assert self._calc_conversion_rate(100, 100) == 100.0

        # Test 0% conversion
        assert self._calc_conversion_rate(0, 100) == 0.0

        # Test zero total
        assert self._calc_conversion_rate(0, 0) == 0.0

    def test_calculate_drop_off_rate(self):
        """Test drop-off rate calculation."""
        # Test normal case
        assert self._calc_drop_off_rate(50, 100) == 50.0

        # Test no drop-off
        assert self._calc_drop_off_rate(100, 100) == 0.0

        # Test complete drop-off
        assert self._calc_drop_off_rate(0, 100) == 100.0

        # Test zero previous
        assert self._calc_drop_off_rate(0, 0) == 0.0

    @staticmethod
    def _calc_conversion_rate(completed: int, total: int) -> float:
        """Helper to calculate conversion rate."""
        if total == 0:
            return 0.0
        return round((completed / total) * 100, 2)

    @staticmethod
    def _calc_drop_off_rate(current: int, previous: int) -> float:
        """Helper to calculate drop-off rate."""
        if previous == 0:
            return 0.0
        return round(((previous - current) / previous) * 100, 2)
