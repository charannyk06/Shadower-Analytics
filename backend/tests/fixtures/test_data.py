"""Test data fixtures and factories."""

import factory
from faker import Faker
from datetime import datetime, date, timedelta
from typing import Dict, List
import random

fake = Faker()


def get_sample_user_metrics():
    """Get sample user metrics data."""
    return {
        "dau": 150,
        "wau": 800,
        "mau": 2500,
        "retention_rate": 0.75,
    }


def get_sample_agent_metrics():
    """Get sample agent metrics data."""
    return {
        "agent_id": "sample-agent-1",
        "total_executions": 1000,
        "successful_executions": 950,
        "failed_executions": 50,
        "success_rate": 95.0,
        "avg_duration": 2.5,
    }


def get_sample_execution_logs():
    """Get sample execution logs."""
    return [
        {
            "execution_id": f"exec-{i}",
            "agent_id": "agent-1",
            "user_id": "user-1",
            "workspace_id": "workspace-1",
            "status": "success" if i % 10 != 0 else "failure",
            "duration": 2.0 + (i * 0.1),
            "started_at": datetime.now() - timedelta(hours=i),
            "completed_at": datetime.now() - timedelta(hours=i) + timedelta(seconds=2),
        }
        for i in range(100)
    ]


class UserFactory(factory.Factory):
    """Factory for creating test users."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: f"user_{fake.uuid4()}")
    email = factory.LazyAttribute(lambda o: fake.email())
    name = factory.LazyAttribute(lambda o: fake.name())
    workspace_id = factory.LazyFunction(lambda: f"ws_{fake.uuid4()}")
    created_at = factory.LazyFunction(lambda: fake.date_time_this_year())
    is_active = True


class AgentFactory(factory.Factory):
    """Factory for creating test agents."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: f"agent_{fake.uuid4()}")
    name = factory.LazyAttribute(lambda o: fake.catch_phrase())
    workspace_id = factory.LazyFunction(lambda: f"ws_{fake.uuid4()}")
    success_rate = factory.LazyFunction(lambda: round(random.uniform(0.7, 0.99), 2))
    total_executions = factory.LazyFunction(lambda: random.randint(100, 10000))
    created_at = factory.LazyFunction(lambda: fake.date_time_this_year())


class AgentRunFactory(factory.Factory):
    """Factory for creating test agent runs."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: f"run_{fake.uuid4()}")
    agent_id = factory.LazyFunction(lambda: f"agent_{fake.uuid4()}")
    workspace_id = factory.LazyFunction(lambda: f"ws_{fake.uuid4()}")
    status = factory.LazyFunction(lambda: random.choice(["success", "failed", "pending"]))
    credits_used = factory.LazyFunction(lambda: random.randint(10, 100))
    duration_ms = factory.LazyFunction(lambda: random.randint(100, 5000))
    created_at = factory.LazyFunction(lambda: fake.date_time_this_month())
    error_message = None


class WorkspaceFactory(factory.Factory):
    """Factory for creating test workspaces."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: f"ws_{fake.uuid4()}")
    name = factory.LazyAttribute(lambda o: fake.company())
    plan = factory.LazyFunction(lambda: random.choice(["free", "pro", "enterprise"]))
    credits_balance = factory.LazyFunction(lambda: random.randint(1000, 100000))
    created_at = factory.LazyFunction(lambda: fake.date_time_this_year())


class UserActivityFactory(factory.Factory):
    """Factory for creating test user activities."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: f"activity_{fake.uuid4()}")
    user_id = factory.LazyFunction(lambda: f"user_{fake.uuid4()}")
    workspace_id = factory.LazyFunction(lambda: f"ws_{fake.uuid4()}")
    action = factory.LazyFunction(
        lambda: random.choice(["agent_execution", "login", "view_dashboard", "generate_report"])
    )
    timestamp = factory.LazyFunction(lambda: fake.date_time_this_month())
    metadata = {}


class TestDataGenerator:
    """Generator for complex test data scenarios."""

    @staticmethod
    def generate_test_workspace() -> Dict:
        """Generate complete test workspace with related data."""
        workspace = WorkspaceFactory()

        # Generate users
        users = [UserFactory(workspace_id=workspace["id"]) for _ in range(10)]

        # Generate agents
        agents = [AgentFactory(workspace_id=workspace["id"]) for _ in range(5)]

        # Generate runs for each agent
        runs = []
        for agent in agents:
            for _ in range(100):
                runs.append(
                    AgentRunFactory(
                        agent_id=agent["id"],
                        workspace_id=workspace["id"]
                    )
                )

        # Generate user activities
        activities = []
        for user in users:
            for _ in range(50):
                activities.append(
                    UserActivityFactory(
                        user_id=user["id"],
                        workspace_id=workspace["id"]
                    )
                )

        return {
            "workspace": workspace,
            "users": users,
            "agents": agents,
            "runs": runs,
            "activities": activities
        }

    @staticmethod
    def generate_time_series_data(
        start_date: datetime,
        end_date: datetime,
        interval_hours: int = 1
    ) -> List[Dict]:
        """Generate time series test data."""
        data = []
        current = start_date

        while current <= end_date:
            data.append({
                "timestamp": current,
                "value": random.randint(10, 1000),
                "metric_type": random.choice(["executions", "credits", "users"]),
                "workspace_id": f"ws_{fake.uuid4()}"
            })
            current += timedelta(hours=interval_hours)

        return data

    @staticmethod
    def generate_agent_performance_data(
        agent_id: str,
        num_runs: int = 100
    ) -> List[Dict]:
        """Generate agent performance test data."""
        runs = []

        for i in range(num_runs):
            # Simulate realistic performance patterns
            success = random.random() > 0.15  # 85% success rate

            runs.append({
                "id": f"run_{i}",
                "agent_id": agent_id,
                "status": "success" if success else "failed",
                "duration_ms": random.randint(500, 5000),
                "credits_used": random.randint(10, 100),
                "created_at": datetime.now() - timedelta(days=random.randint(0, 30)),
                "error_message": None if success else fake.sentence()
            })

        return runs

    @staticmethod
    def generate_credit_consumption_data(
        workspace_id: str,
        days: int = 30
    ) -> List[Dict]:
        """Generate credit consumption test data."""
        data = []
        start_date = datetime.now() - timedelta(days=days)

        for day in range(days):
            current_date = start_date + timedelta(days=day)

            # Simulate daily usage patterns (higher on weekdays)
            is_weekday = current_date.weekday() < 5
            base_usage = 500 if is_weekday else 200

            for hour in range(24):
                # Simulate hourly variations
                hour_multiplier = 1.5 if 9 <= hour <= 17 else 0.5

                data.append({
                    "workspace_id": workspace_id,
                    "credits": int(base_usage * hour_multiplier * random.uniform(0.8, 1.2)),
                    "timestamp": current_date + timedelta(hours=hour),
                    "operation_type": random.choice(["agent_run", "report_generation", "export"])
                })

        return data
