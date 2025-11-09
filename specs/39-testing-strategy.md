# Specification: Testing Strategy

## Overview
Comprehensive testing strategy covering unit tests, integration tests, performance testing, and end-to-end testing for the analytics platform.

## Technical Requirements

### Unit Testing

#### Backend Unit Tests
```python
# backend/tests/unit/test_metrics_service.py
import pytest
from unittest.mock import Mock, patch
from services.metrics_service import MetricsService
from datetime import datetime, timedelta

class TestMetricsService:
    @pytest.fixture
    def metrics_service(self):
        return MetricsService(
            db_session=Mock(),
            redis_client=Mock()
        )
    
    def test_calculate_agent_success_rate(self, metrics_service):
        """Test agent success rate calculation"""
        # Mock data
        metrics_service.db_session.execute.return_value.fetchone.return_value = {
            'successful_runs': 85,
            'total_runs': 100
        }
        
        success_rate = metrics_service.calculate_agent_success_rate('agent_123')
        
        assert success_rate == 0.85
    
    def test_calculate_credit_consumption(self, metrics_service):
        """Test credit consumption calculation"""
        mock_data = [
            {'credits': 100, 'timestamp': datetime.now()},
            {'credits': 150, 'timestamp': datetime.now()}
        ]
        metrics_service.db_session.execute.return_value.fetchall.return_value = mock_data
        
        total = metrics_service.calculate_credit_consumption('workspace_123')
        
        assert total == 250
    
    @patch('services.metrics_service.datetime')
    def test_get_active_users_count(self, mock_datetime, metrics_service):
        """Test active users count"""
        mock_datetime.now.return_value = datetime(2024, 1, 15, 12, 0, 0)
        metrics_service.redis_client.scard.return_value = 142
        
        count = metrics_service.get_active_users_count('workspace_123')
        
        assert count == 142
        metrics_service.redis_client.scard.assert_called_once()
```

#### Frontend Unit Tests
```typescript
// frontend/src/tests/unit/components/MetricsCard.test.tsx
import { render, screen } from '@testing-library/react';
import { MetricsCard } from '@/components/analytics/MetricsCard';

describe('MetricsCard', () => {
    it('renders metric value correctly', () => {
        render(
            <MetricsCard
                title="Active Users"
                value={1234}
                change={15.5}
                changeType="increase"
            />
        );
        
        expect(screen.getByText('1,234')).toBeInTheDocument();
        expect(screen.getByText('+15.5%')).toBeInTheDocument();
    });
    
    it('applies correct color for decrease', () => {
        const { container } = render(
            <MetricsCard
                title="Error Rate"
                value={0.02}
                change={-5.3}
                changeType="decrease"
            />
        );
        
        const changeElement = container.querySelector('.text-red-500');
        expect(changeElement).toBeInTheDocument();
    });
    
    it('formats large numbers correctly', () => {
        render(
            <MetricsCard
                title="Total Credits"
                value={1500000}
                format="compact"
            />
        );
        
        expect(screen.getByText('1.5M')).toBeInTheDocument();
    });
});
```

### Integration Testing

#### API Integration Tests
```python
# backend/tests/integration/test_analytics_api.py
import pytest
from fastapi.testclient import TestClient
from main import app
from datetime import datetime, timedelta

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test_token"}

class TestAnalyticsAPI:
    def test_get_executive_summary(self, client, auth_headers):
        """Test executive summary endpoint"""
        response = client.get(
            "/api/v1/dashboard/executive/summary",
            params={
                "workspace_id": "ws_test",
                "date_from": "2024-01-01",
                "date_to": "2024-01-31"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "revenue_metrics" in data
        assert "user_metrics" in data
        assert "usage_metrics" in data
        assert "performance_metrics" in data
    
    def test_create_report_generation(self, client, auth_headers):
        """Test report generation"""
        response = client.post(
            "/api/v1/reports/generate",
            json={
                "name": "Test Report",
                "template_id": "template_daily",
                "format": "pdf",
                "date_range": {
                    "start": "2024-01-01",
                    "end": "2024-01-31"
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
    
    def test_websocket_connection(self, client):
        """Test WebSocket connection"""
        with client.websocket_connect(
            "/api/v1/ws?token=test_token&workspace_id=ws_test"
        ) as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connection_established"
            
            # Send subscription
            websocket.send_json({
                "type": "subscribe",
                "channels": ["metrics_updates"]
            })
            
            response = websocket.receive_json()
            assert response["type"] == "subscribed"
```

#### Database Integration Tests
```python
# backend/tests/integration/test_database.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, UserActivity, AgentPerformance
from datetime import datetime

@pytest.fixture
def db_session():
    engine = create_engine("postgresql://test_db")
    SessionLocal = sessionmaker(bind=engine)
    
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(bind=engine)

class TestDatabaseOperations:
    def test_user_activity_insertion(self, db_session):
        """Test inserting user activity"""
        activity = UserActivity(
            user_id="user_123",
            workspace_id="ws_456",
            action="agent_execution",
            timestamp=datetime.now()
        )
        
        db_session.add(activity)
        db_session.commit()
        
        result = db_session.query(UserActivity).filter_by(
            user_id="user_123"
        ).first()
        
        assert result is not None
        assert result.action == "agent_execution"
    
    def test_materialized_view_refresh(self, db_session):
        """Test materialized view refresh"""
        # Insert test data
        for i in range(100):
            db_session.add(AgentPerformance(
                agent_id=f"agent_{i}",
                success_rate=0.8 + (i * 0.001),
                total_executions=i * 10
            ))
        db_session.commit()
        
        # Refresh materialized view
        db_session.execute("REFRESH MATERIALIZED VIEW agent_performance_summary")
        
        # Query view
        result = db_session.execute(
            "SELECT COUNT(*) FROM agent_performance_summary"
        ).scalar()
        
        assert result == 100
```

### Performance Testing

#### Load Testing with Locust
```python
# backend/tests/performance/locustfile.py
from locust import HttpUser, task, between
import random
import json

class AnalyticsUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login and get auth token"""
        response = self.client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def get_dashboard(self):
        """Get dashboard data"""
        self.client.get(
            "/api/v1/dashboard/executive/summary",
            headers=self.headers,
            params={
                "workspace_id": "ws_test",
                "date_range": "30d"
            }
        )
    
    @task(2)
    def get_agent_performance(self):
        """Get agent performance metrics"""
        agent_id = f"agent_{random.randint(1, 100)}"
        self.client.get(
            f"/api/v1/analytics/agents/{agent_id}/performance",
            headers=self.headers
        )
    
    @task(1)
    def generate_report(self):
        """Generate report"""
        self.client.post(
            "/api/v1/reports/generate",
            headers=self.headers,
            json={
                "template": "daily_summary",
                "format": "pdf"
            }
        )
    
    @task(4)
    def websocket_metrics(self):
        """Connect to WebSocket for real-time metrics"""
        with self.client.websocket(
            f"/api/v1/ws?token={self.token}",
            subprotocols=["websocket"]
        ) as ws:
            ws.send(json.dumps({
                "type": "subscribe",
                "channels": ["metrics"]
            }))
            
            # Receive 10 messages
            for _ in range(10):
                data = ws.receive()
                if not data:
                    break
```

#### Performance Benchmarks
```yaml
# backend/tests/performance/benchmarks.yml
benchmarks:
  api_response_times:
    dashboard_summary:
      p50: 100ms
      p95: 200ms
      p99: 500ms
    
    report_generation:
      p50: 1s
      p95: 3s
      p99: 5s
    
    real_time_metrics:
      p50: 50ms
      p95: 100ms
      p99: 200ms
  
  database_queries:
    simple_select:
      max_time: 50ms
    
    aggregation_query:
      max_time: 200ms
    
    materialized_view:
      max_time: 100ms
  
  concurrent_users:
    min: 1000
    target: 5000
    max: 10000
  
  throughput:
    requests_per_second: 1000
    websocket_connections: 5000
```

### End-to-End Testing

#### E2E Test Suite
```typescript
// frontend/tests/e2e/analytics-flow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Analytics Dashboard E2E', () => {
    test.beforeEach(async ({ page }) => {
        // Login
        await page.goto('/auth/login');
        await page.fill('[data-testid="email"]', 'test@example.com');
        await page.fill('[data-testid="password"]', 'password');
        await page.click('[data-testid="login-button"]');
        
        // Wait for redirect
        await page.waitForURL('/dashboard');
    });
    
    test('complete analytics workflow', async ({ page }) => {
        // Navigate to analytics
        await page.click('[data-testid="nav-analytics"]');
        await expect(page).toHaveURL('/analytics/dashboard');
        
        // Check dashboard loads
        await expect(page.locator('[data-testid="active-users-card"]')).toBeVisible();
        await expect(page.locator('[data-testid="revenue-chart"]')).toBeVisible();
        
        // Change date range
        await page.click('[data-testid="date-range-picker"]');
        await page.click('[data-testid="last-30-days"]');
        
        // Wait for data refresh
        await page.waitForResponse(resp => 
            resp.url().includes('/api/v1/dashboard') && resp.status() === 200
        );
        
        // Generate report
        await page.click('[data-testid="generate-report-btn"]');
        await page.selectOption('[data-testid="report-template"]', 'monthly');
        await page.click('[data-testid="generate-btn"]');
        
        // Check notification
        await expect(page.locator('[data-testid="success-toast"]')).toContainText(
            'Report generation started'
        );
        
        // Navigate to agent analytics
        await page.click('[data-testid="nav-agents"]');
        await expect(page.locator('[data-testid="agent-list"]')).toBeVisible();
        
        // Click on specific agent
        await page.click('[data-testid="agent-row-1"]');
        await expect(page).toHaveURL(/\/analytics\/agents\/agent_/);
        
        // Verify agent metrics
        await expect(page.locator('[data-testid="success-rate"]')).toBeVisible();
        await expect(page.locator('[data-testid="execution-chart"]')).toBeVisible();
    });
    
    test('real-time updates work', async ({ page }) => {
        await page.goto('/analytics/realtime');
        
        // Check WebSocket connection
        await expect(page.locator('[data-testid="connection-status"]')).toHaveText('Connected');
        
        // Wait for real-time update
        await page.waitForTimeout(2000);
        
        // Verify metrics update
        const initialValue = await page.locator('[data-testid="live-users"]').textContent();
        await page.waitForTimeout(5000);
        const updatedValue = await page.locator('[data-testid="live-users"]').textContent();
        
        expect(initialValue).not.toBe(updatedValue);
    });
});
```

### Test Automation

#### CI/CD Pipeline Tests
```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements-test.txt
      
      - name: Run unit tests
        run: |
          pytest backend/tests/unit --cov=backend --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
  
  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Run integration tests
        run: |
          pytest backend/tests/integration
  
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install Playwright
        run: |
          npm ci
          npx playwright install
      
      - name: Run E2E tests
        run: |
          npm run test:e2e
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/
  
  performance-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Locust tests
        run: |
          pip install locust
          locust -f backend/tests/performance/locustfile.py \
            --headless \
            --users 100 \
            --spawn-rate 10 \
            --run-time 60s \
            --host http://localhost:8000
```

### Test Data Management

```python
# backend/tests/fixtures/test_data.py
import factory
from faker import Faker
from models import User, Agent, Workspace, AgentRun

fake = Faker()

class UserFactory(factory.Factory):
    class Meta:
        model = User
    
    id = factory.LazyFunction(lambda: f"user_{fake.uuid4()}")
    email = factory.LazyAttribute(lambda o: fake.email())
    name = factory.LazyAttribute(lambda o: fake.name())
    created_at = factory.LazyFunction(fake.date_time_this_year)

class AgentFactory(factory.Factory):
    class Meta:
        model = Agent
    
    id = factory.LazyFunction(lambda: f"agent_{fake.uuid4()}")
    name = factory.LazyAttribute(lambda o: fake.catch_phrase())
    workspace_id = factory.LazyFunction(lambda: f"ws_{fake.uuid4()}")
    success_rate = factory.LazyFunction(lambda: fake.random.uniform(0.7, 0.99))
    total_executions = factory.LazyFunction(lambda: fake.random_int(100, 10000))

class TestDataGenerator:
    @staticmethod
    def generate_test_workspace():
        """Generate complete test workspace with data"""
        workspace = {
            "id": f"ws_{fake.uuid4()}",
            "name": fake.company(),
            "users": [UserFactory() for _ in range(10)],
            "agents": [AgentFactory() for _ in range(5)],
            "runs": []
        }
        
        # Generate runs for each agent
        for agent in workspace["agents"]:
            for _ in range(100):
                workspace["runs"].append({
                    "id": f"run_{fake.uuid4()}",
                    "agent_id": agent.id,
                    "status": fake.random_element(["success", "failed", "pending"]),
                    "credits_used": fake.random_int(10, 100),
                    "duration_ms": fake.random_int(100, 5000),
                    "created_at": fake.date_time_this_month()
                })
        
        return workspace
```

## Implementation Priority
1. Unit test framework setup
2. Integration test suite
3. E2E test automation
4. Performance testing
5. CI/CD pipeline integration

## Success Metrics
- Test coverage > 80%
- All critical paths covered
- Performance benchmarks met
- Zero failing tests in production