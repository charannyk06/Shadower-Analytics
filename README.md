# Shadow Analytics

A comprehensive analytics platform for monitoring agent performance, user activity, and business metrics.

## 🏗️ Architecture

This is a monorepo containing:

- **Backend**: FastAPI-based analytics service
- **Frontend**: Next.js 14 dashboard with real-time updates
- **Database**: PostgreSQL with materialized views and aggregations
- **Jobs**: Celery-based background tasks for data processing
- **Docker**: Containerized development environment

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- PostgreSQL 16+
- Redis 7+

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd shadower-analytics
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start development environment**
   ```bash
   make dev
   ```

   This will start:
   - Backend API: http://localhost:8000
   - Frontend Dashboard: http://localhost:3000
   - PostgreSQL: localhost:5432
   - Redis: localhost:6379

### Alternative: Manual Setup

#### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
uvicorn src.api.main:app --reload
```

#### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## 📊 Features

### Authentication & Authorization
- **Shared JWT Authentication**: Seamless authentication with the main Shadower app
- **Role-Based Access Control (RBAC)**: Fine-grained permissions for owner, admin, member, and viewer roles
- **Workspace Permissions**: Multi-workspace support with workspace-level access control
- **Automatic Token Refresh**: Tokens are automatically refreshed before expiration
- **Secure**: HTTPS-only in production, rate limiting, audit logging

### Executive Dashboard
- Real-time business metrics (MRR, Churn, LTV)
- User engagement metrics (DAU, WAU, MAU)
- Agent performance analytics
- Revenue and credit usage tracking

### Analytics
- Cohort analysis
- Funnel analysis
- Trend detection
- Anomaly detection
- Predictive analytics

### Agent Monitoring
- Execution statistics
- Success/failure rates
- Performance trends
- Resource usage

### User Analytics
- Activity tracking
- Engagement metrics
- Retention analysis
- User segmentation

### Export & Reporting
- CSV, PDF, JSON exports
- Custom report builder
- Scheduled reports
- API access

## 🛠️ Development

### Available Commands

```bash
make help              # Show all available commands
make install           # Install all dependencies
make dev               # Start development environment
make test              # Run all tests
make lint              # Run linters
make format            # Format code
make migrate           # Run database migrations
make seed              # Seed database with sample data
```

### Running Tests

```bash
# Backend tests
cd backend
pytest -v --cov=src

# Frontend tests
cd frontend
npm run test

# E2E tests
npm run test:e2e
```

### Code Quality

```bash
# Backend
make lint-backend      # Run flake8, black, mypy
make format-backend    # Auto-format with black and isort

# Frontend
make lint-frontend     # Run ESLint
make format-frontend   # Auto-format with Prettier
```

## 📁 Project Structure

```
shadower-analytics/
├── backend/          # FastAPI analytics service
├── frontend/         # Next.js dashboard
├── database/         # SQL migrations and seeds
├── jobs/             # Celery background tasks
├── docker/           # Docker configurations
├── scripts/          # Utility scripts
├── docs/             # Documentation
└── .github/          # CI/CD workflows
```

## 🔧 Configuration

### Environment Variables

See `.env.example` for all available configuration options.

Key variables:

**Backend:**
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `JWT_SECRET_KEY`: Secret for JWT tokens (must match main app!)
- `JWT_ALGORITHM`: JWT algorithm (HS256 or RS256)
- `JWT_EXPIRATION_HOURS`: Token expiration time (default: 24)
- `MAIN_APP_URL`: URL of the main Shadower app

**Frontend:**
- `NEXT_PUBLIC_ANALYTICS_API_URL`: Backend API URL
- `NEXT_PUBLIC_MAIN_APP_URL`: Main Shadower app URL for auth

## 🔐 Authentication System

### How It Works

1. Users authenticate in the main Shadower app
2. JWT token is generated with user claims (id, email, workspace, role, permissions)
3. Token is shared with Analytics microservice via URL parameter or localStorage
4. Analytics validates token using shared JWT secret
5. Token is automatically refreshed before expiration

### JWT Token Structure

```typescript
{
  sub: "user-id",           // User ID
  email: "user@example.com",
  workspaceId: "ws-123",    // Current workspace
  workspaces: ["ws-123"],   // All accessible workspaces
  role: "admin",            // owner | admin | member | viewer
  permissions: ["view_analytics", "export_analytics"],
  iat: 1234567890,          // Issued at
  exp: 1234567890           // Expiration
}
```

### Roles and Permissions

- **Owner**: Full access to all features and workspaces
- **Admin**: Access to analytics, reports, alerts, and management features
- **Member**: View and export analytics, view alerts
- **Viewer**: Read-only access to analytics

### Integrating with Main App

Add a button in the main Shadower app to open Analytics:

```typescript
import { useAuth } from '@/hooks/useAuth';

export function AnalyticsButton() {
  const { token } = useAuth();

  const openAnalytics = () => {
    const analyticsUrl = process.env.NEXT_PUBLIC_ANALYTICS_URL;
    const url = `${analyticsUrl}?token=${encodeURIComponent(token)}`;
    window.open(url, '_blank');
  };

  return <button onClick={openAnalytics}>View Analytics</button>;
}
```

### Protected Routes (Frontend)

```typescript
import { ProtectedRoute } from '@/components/auth';
import { ROLES, PERMISSIONS } from '@/types/permissions';

export default function ExecutivePage() {
  return (
    <ProtectedRoute
      requiredRole={[ROLES.OWNER, ROLES.ADMIN]}
      requiredPermissions={[PERMISSIONS.VIEW_EXECUTIVE_DASHBOARD]}
    >
      <ExecutiveDashboard />
    </ProtectedRoute>
  );
}
```

### Protected Endpoints (Backend)

```python
from fastapi import APIRouter, Depends
from src.api.dependencies.auth import require_owner_or_admin

router = APIRouter()

@router.get("/executive/overview")
async def get_executive_overview(
    current_user = Depends(require_owner_or_admin)
):
    # Only owners and admins can access this endpoint
    return {"data": "..."}
```

### Security Considerations

- JWT secret must be strong (256-bit minimum)
- Tokens expire after 24 hours
- Refresh tokens expire after 30 days
- HTTPS only in production
- Rate limiting on auth endpoints
- All authentication attempts are logged

### Performance Targets

- Token verification: <10ms
- Permission check: <5ms
- Token refresh: <200ms
- Auth state hydration: <100ms

### Database Migrations

```bash
# Create a new migration
make migrate-create MSG="description"

# Apply migrations
make migrate

# Rollback last migration
make migrate-rollback
```

## 🚢 Deployment

### Staging

```bash
make deploy-staging
```

### Production

```bash
make deploy-production
```

## 📈 Monitoring

- **Health Check**: `http://localhost:8000/health`
- **API Docs**: `http://localhost:8000/docs`
- **Prometheus Metrics**: `http://localhost:9090`

## 🧪 Testing

### Test Coverage Requirements

- Backend: 80% minimum
- Frontend: Component tests for all UI elements
- E2E tests for critical user flows

### Running Tests

```bash
# All tests
make test

# Backend only
make test-backend

# Frontend only
make test-frontend

# With coverage
cd backend && pytest --cov=src --cov-report=html
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Links

- [API Documentation](http://localhost:8000/docs)
- [Architecture Docs](./docs/architecture.md)
- [API Reference](./docs/api-reference.md)
- [Deployment Guide](./docs/deployment.md)

## 💡 Support

For issues and questions:
- Create an issue in GitHub
- Check existing documentation
- Contact the development team

## 🏆 Performance Targets

- Repository clone: <30 seconds
- Backend startup: <5 seconds
- Frontend build: <60 seconds
- Docker compose up: <2 minutes
- API response time: <200ms (p95)
