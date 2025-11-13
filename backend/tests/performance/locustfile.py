"""Performance tests using Locust for load testing."""

from locust import HttpUser, task, between, events
import random
import json
from datetime import datetime, timedelta


class AnalyticsUser(HttpUser):
    """Simulated user for analytics platform load testing."""

    wait_time = between(1, 3)

    def on_start(self):
        """Called when a simulated user starts."""
        # Login and get auth token
        response = self.client.post("/api/auth/login", json={
            "email": f"test_user_{random.randint(1, 1000)}@example.com",
            "password": "test_password"
        }, catch_response=True)

        if response.status_code == 200:
            self.token = response.json().get("access_token", "test_token")
        else:
            # Use default test token if login fails
            self.token = "test_token"

        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.workspace_id = f"ws_{random.randint(1, 10)}"

    @task(3)
    def get_dashboard(self):
        """Get executive dashboard data."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        self.client.get(
            "/api/v1/dashboard/executive/summary",
            headers=self.headers,
            params={
                "workspace_id": self.workspace_id,
                "date_from": start_date.isoformat(),
                "date_to": end_date.isoformat()
            },
            name="/api/v1/dashboard/executive/summary"
        )

    @task(2)
    def get_agent_performance(self):
        """Get agent performance metrics."""
        agent_id = f"agent_{random.randint(1, 100)}"

        self.client.get(
            f"/api/v1/analytics/agents/{agent_id}/performance",
            headers=self.headers,
            params={
                "date_from": (datetime.now() - timedelta(days=7)).isoformat(),
                "date_to": datetime.now().isoformat()
            },
            name="/api/v1/analytics/agents/[id]/performance"
        )

    @task(2)
    def get_agent_list(self):
        """Get list of agents."""
        self.client.get(
            "/api/v1/analytics/agents",
            headers=self.headers,
            params={
                "workspace_id": self.workspace_id,
                "limit": 50,
                "offset": random.randint(0, 100)
            },
            name="/api/v1/analytics/agents"
        )

    @task(1)
    def generate_report(self):
        """Generate report."""
        self.client.post(
            "/api/v1/reports/generate",
            headers=self.headers,
            json={
                "name": f"Performance Report {datetime.now().isoformat()}",
                "template_id": random.choice(["daily_summary", "weekly_report", "monthly_overview"]),
                "format": random.choice(["pdf", "csv", "excel"]),
                "date_range": {
                    "start": (datetime.now() - timedelta(days=30)).isoformat(),
                    "end": datetime.now().isoformat()
                }
            },
            name="/api/v1/reports/generate"
        )

    @task(2)
    def get_credit_usage(self):
        """Get credit usage data."""
        self.client.get(
            "/api/v1/credits/usage",
            headers=self.headers,
            params={
                "workspace_id": self.workspace_id,
                "date_from": (datetime.now() - timedelta(days=30)).isoformat(),
                "date_to": datetime.now().isoformat()
            },
            name="/api/v1/credits/usage"
        )

    @task(1)
    def get_user_activity(self):
        """Get user activity metrics."""
        self.client.get(
            "/api/v1/analytics/users/activity",
            headers=self.headers,
            params={
                "workspace_id": self.workspace_id,
                "date_range": "30d"
            },
            name="/api/v1/analytics/users/activity"
        )

    @task(4)
    def get_realtime_metrics(self):
        """Get real-time metrics."""
        self.client.get(
            "/api/v1/analytics/realtime",
            headers=self.headers,
            params={
                "workspace_id": self.workspace_id
            },
            name="/api/v1/analytics/realtime"
        )


class WebSocketUser(HttpUser):
    """User for testing WebSocket connections."""

    wait_time = between(2, 5)

    def on_start(self):
        """Setup WebSocket connection."""
        self.token = "test_token"
        self.workspace_id = f"ws_{random.randint(1, 10)}"

    @task
    def websocket_metrics(self):
        """Test WebSocket connection for real-time metrics."""
        # Note: Locust WebSocket support requires additional setup
        # This is a placeholder for WebSocket testing pattern
        try:
            ws_url = f"/api/v1/ws?token={self.token}&workspace_id={self.workspace_id}"

            # In actual implementation, would use websocket library
            # For now, test HTTP fallback
            self.client.get(
                "/api/v1/analytics/realtime",
                headers={"Authorization": f"Bearer {self.token}"},
                params={"workspace_id": self.workspace_id},
                name="WebSocket Fallback"
            )
        except Exception as e:
            pass


class BurstUser(HttpUser):
    """User that simulates burst traffic patterns."""

    wait_time = between(0.1, 0.5)  # Very short wait time for burst

    def on_start(self):
        """Setup user."""
        self.token = "test_token"
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.workspace_id = f"ws_{random.randint(1, 10)}"

    @task
    def rapid_dashboard_requests(self):
        """Make rapid dashboard requests."""
        self.client.get(
            "/api/v1/dashboard/executive/summary",
            headers=self.headers,
            params={
                "workspace_id": self.workspace_id,
                "date_range": "7d"
            },
            name="Burst Dashboard Request"
        )


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the load test starts."""
    print("Load test starting...")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the load test stops."""
    print("Load test completed.")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    print(f"Average response time: {environment.stats.total.avg_response_time}ms")
    print(f"RPS: {environment.stats.total.total_rps}")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log slow requests."""
    if response_time > 1000:  # Log requests slower than 1 second
        print(f"Slow request detected: {name} - {response_time}ms")
