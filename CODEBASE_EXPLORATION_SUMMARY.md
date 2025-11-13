# Shadower Analytics - Codebase Structure & Architecture Guide

## Project Overview

**Shadower Analytics** is a comprehensive AI agent analytics platform with:
- **Backend**: FastAPI (Python) async REST API
- **Frontend**: Next.js 14 (React 18) dashboard
- **Database**: PostgreSQL 16
- **Job Queue**: Celery with Redis broker
- **Caching**: Redis
- **Authentication**: JWT-based with Supabase integration

---

## 1. PROJECT ORGANIZATION

### Directory Structure
```
Shadower-Analytics/
├── backend/                          # FastAPI backend
│   ├── src/
│   │   ├── api/                      # API routes and endpoints
│   │   │   ├── routes/               # Individual feature routers (agents.py, metrics.py, etc.)
│   │   │   ├── main.py               # FastAPI app setup and router registration
│   │   │   ├── gateway.py            # API gateway with CORS, rate limiting
│   │   │   ├── dependencies/         # Shared dependency injection
│   │   │   ├── middleware/           # Global middleware (logging, security)
│   │   │   └── websocket/            # Real-time WebSocket support
│   │   ├── models/
│   │   │   ├── database/             # SQLAlchemy ORM models (tables.py)
│   │   │   └── schemas/              # Pydantic request/response schemas
│   │   ├── services/                 # Business logic layer
│   │   │   ├── metrics/              # Metrics calculation services
│   │   │   ├── analytics/            # Advanced analytics services
│   │   │   ├── cache/                # Redis caching utilities
│   │   │   ├── alerts/               # Alert engine and conditions
│   │   │   ├── notifications/        # Notification system
│   │   │   ├── exports/              # Data export (CSV, JSON, PDF, Excel, Parquet)
│   │   │   ├── reports/              # Report generation service
│   │   │   └── search/               # Search functionality
│   │   ├── tasks/                    # Celery background tasks
│   │   │   ├── aggregation.py        # Metrics aggregation jobs
│   │   │   ├── alerts.py             # Alert processing
│   │   │   ├── exports.py            # Export generation
│   │   │   └── maintenance.py        # Cleanup and maintenance
│   │   ├── core/                     # Core configuration and utilities
│   │   │   ├── config.py             # Environment and settings
│   │   │   ├── database.py           # Database connection and session
│   │   │   ├── redis.py              # Redis client setup
│   │   │   ├── security.py           # JWT and auth utilities
│   │   │   ├── permissions.py        # Role-based access control
│   │   │   └── exceptions.py         # Custom exceptions
│   │   ├── utils/                    # Utility functions
│   │   ├── celery_app.py             # Celery configuration
│   │   └── __init__.py
│   ├── alembic/                      # Database migrations (Alembic setup)
│   ├── tests/                        # Test suite
│   └── Dockerfile
│
├── database/                         # Database setup and migrations
│   ├── migrations/                   # SQL migration files (001_, 002_, etc.)
│   ├── procedures/                   # PostgreSQL stored procedures
│   └── test_migrations/
│
├── frontend/                         # Next.js frontend
│   ├── src/
│   │   ├── app/                      # Next.js App Router pages
│   │   │   ├── dashboard/            # Dashboard pages
│   │   │   ├── agents/               # Agent pages
│   │   │   ├── reports/              # Reports pages
│   │   │   └── page.tsx              # Root page
│   │   ├── components/               # React components
│   │   │   ├── agents/               # Agent-specific components
│   │   │   ├── dashboard/            # Dashboard components
│   │   │   ├── charts/               # Chart components (Recharts)
│   │   │   ├── execution/            # Execution metrics components
│   │   │   ├── common/               # Reusable UI components
│   │   │   └── ui/                   # Base UI elements (Shadcn-ui)
│   │   ├── hooks/                    # Custom React hooks
│   │   │   └── api/                  # API data fetching hooks (React Query)
│   │   ├── types/                    # TypeScript type definitions
│   │   ├── lib/                      # Utility functions
│   │   └── contexts/                 # React contexts
│   └── Dockerfile
│
├── jobs/                             # Background job definitions
│   ├── aggregation/                  # Aggregation jobs
│   ├── alerts/                       # Alert jobs
│   ├── maintenance/                  # Maintenance jobs
│   ├── notifications/                # Notification jobs
│   ├── celeryconfig.py               # Celery schedule configuration
│   └── Dockerfile
│
├── docker/                           # Docker configurations
│   ├── nginx/                        # Nginx configuration
│   ├── postgres/                     # PostgreSQL initialization
│   └── redis/                        # Redis configuration
│
├── docs/                             # Documentation
├── specs/                            # Feature specifications
└── docker-compose.yml                # Docker Compose setup
```

---

## 2. DATABASE SCHEMA & MIGRATIONS

### Location
`/home/user/Shadower-Analytics/database/migrations/`

### Database
- **Type**: PostgreSQL 16
- **Name**: `shadower_analytics`
- **User**: `postgres`
- **Port**: `5432`

### Key Tables for Analytics

#### Core Execution Tables
- **execution_logs**: Individual execution records
  - Columns: execution_id, agent_id, user_id, workspace_id, status, duration, credits_used, started_at, completed_at
  - Indexes: (agent_id, started_at), (workspace_id, started_at), (status, started_at)

#### Agent Analytics Tables (Migration 009)
- **agent_runs**: Individual agent executions with resource tracking
  - Columns: agent_id, workspace_id, user_id, status, runtime_seconds, started_at, credits_consumed, tokens_used, model_name, concurrent_runs
  
- **agent_errors**: Error tracking and categorization
  - Columns: agent_id, error_type, error_category, error_severity, error_message, error_stack
  
- **agent_performance_hourly**: Hourly aggregated metrics
  - Columns: agent_id, workspace_id, hour, total_runs, successful_runs, failed_runs, avg_runtime, total_credits

- **agent_optimization_suggestions**: AI-generated recommendations
  - Columns: agent_id, suggestion_text, category, impact_estimate, effort_estimate

- **agent_user_feedback**: User satisfaction tracking
  - Columns: agent_id, user_id, rating (1-5), feedback_text, created_at

- **agent_model_usage**: Model consumption tracking
  - Columns: agent_id, model_name, calls, tokens, credits

#### Materialized Views
- **agent_analytics_summary**: Pre-aggregated daily summaries for performance

### Metrics & Aggregation Tables
- **execution_metrics_daily**: Daily aggregated metrics
- **execution_metrics_hourly**: Hourly aggregated metrics
- **execution_queue**: Queue depth tracking
- **execution_patterns**: Pattern and anomaly detection

### Migration Strategy
1. SQL migrations in `/database/migrations/`
2. Numbered sequentially: 001_, 002_, 003_, etc.
3. Both raw SQL files and Alembic Python migrations
4. Run manually or via Alembic: `alembic upgrade head`

---

## 3. API ROUTES & ENDPOINTS

### Location
`/home/user/Shadower-Analytics/backend/src/api/routes/`

### Current Routers (All include JWT authentication)

| Route Module | Prefix | Key Endpoints |
|---|---|---|
| **agents.py** | `/api/v1/agents` | GET /{id}/analytics, GET /{id}/stats, GET /{id}/executions |
| **metrics.py** | `/api/v1/metrics` | GET /execution, GET /execution/realtime, GET /execution/throughput |
| **dashboard.py** | `/api/v1/dashboard` | GET /summary, GET /metrics, GET /detailed |
| **analytics.py** | `/api/v1/analytics` | GET /overview, POST /compare |
| **executive.py** | `/api/v1/executive` | GET /summary, GET /trends |
| **reports.py** | `/api/v1/reports` | GET /, POST /, GET /{id}, PUT /{id} |
| **exports.py** | `/api/v1/exports` | POST /, GET /{id} |
| **predictions.py** | `/api/v1/predictions` | GET /anomalies, GET /forecasts |
| **alerts.py** | `/api/v1/alerts` | GET /, POST /, PUT /{id} |
| **notifications.py** | `/api/v1/notifications` | GET /preferences, PUT /preferences |
| **funnels.py** | `/api/v1/funnels` | POST /analyze |
| **trends.py** | `/api/v1/trends` | GET / with filters |
| **leaderboards.py** | `/api/v1/leaderboards` | GET /agents, GET /users |
| **anomalies.py** | `/api/v1/anomalies` | GET /, POST /detect |
| **search.py** | `/api/v1/search` | POST /query |
| **user_activity.py** | `/api/v1/user-activity` | GET /, POST /events |
| **websocket.py** | `/ws/metrics/{workspace_id}` | WebSocket real-time updates |

### API Gateway Features
- **Rate Limiting**: Per workspace limits (1000 req/hour default)
- **CORS**: Configured for frontend access
- **Cache Headers**: X-Cache, Cache-Control
- **Versioning**: All endpoints prefixed with `/api/v1/`

---

## 4. DATABASE TYPE

**PostgreSQL 16 (Alpine)**

Key Features Used:
- Async driver: asyncpg
- ORM: SQLAlchemy 2.0+ (async)
- UUID type support
- JSONB for flexible metadata
- BRIN indexes for time-series data
- Materialized views for aggregation
- Row-level security (RLS) available
- LISTEN/NOTIFY for real-time updates

Connection String Format:
```
postgresql://postgres:postgres@postgres:5432/shadower_analytics
```

---

## 5. FRAMEWORKS & TECH STACK

### Backend
- **FastAPI**: REST API framework (0.104+)
- **SQLAlchemy**: ORM with async support (2.0+)
- **Pydantic**: Data validation and serialization
- **asyncpg**: PostgreSQL async driver
- **Celery**: Distributed task queue
- **Redis**: Caching and job broker
- **APScheduler/Celery Beat**: Job scheduling
- **JWT**: Authentication (python-jose)

### Frontend
- **Next.js**: React framework (14+)
- **React**: UI library (18+)
- **React Query**: Data fetching and caching (5+)
- **Tailwind CSS**: Styling (3.4+)
- **Recharts**: Charting library (2.10+)
- **Shadcn/ui**: Component library
- **TypeScript**: Type safety

### Infrastructure
- **Docker & Docker Compose**: Containerization
- **Nginx**: Reverse proxy (port 3000 for frontend, 8000 for backend)
- **Flower**: Celery monitoring (port 5555)

---

## 6. ANALYTICS & METRICS CODE LOCATION

### Services Layer
`/home/user/Shadower-Analytics/backend/src/services/`

#### Metrics Services (Calculation Layer)
```
services/metrics/
├── agent_metrics.py              # Agent performance metrics
├── execution_metrics.py          # Execution tracking metrics
├── user_metrics.py               # User activity metrics
├── credit_metrics.py             # Cost/credit tracking
├── business_metrics.py           # Business KPIs
├── workspace_analytics_service.py # Workspace-level analytics
├── executive_service.py          # Executive dashboard metrics
└── constants.py                  # Metric calculation constants
```

#### Advanced Analytics Services
```
services/analytics/
├── agent_analytics_service.py    # Comprehensive agent analytics
├── error_tracking_service.py     # Error analysis and patterns
├── anomaly_detection.py          # Anomaly detection engine
├── funnel_analysis.py            # Conversion funnel tracking
├── cohort_analysis.py            # User cohort analysis
├── retention_analysis.py         # User retention metrics
├── trend_analysis.py             # Trend detection
├── user_activity.py              # User behavior tracking
├── credit_consumption.py         # Credit analytics
├── predictions.py                # Predictive analytics
├── percentiles.py                # Percentile calculations
├── moving_averages.py            # Moving average calculations
└── leaderboard_service.py        # Ranking and leaderboards
```

#### Caching Services
```
services/cache/
├── redis_cache.py               # Redis operations
├── decorator.py                 # @cache decorator
├── invalidation.py              # Cache invalidation logic
├── keys.py                      # Cache key patterns
└── metrics.py                   # Cache performance metrics
```

#### Other Services
```
services/
├── reports/report_service.py     # Report generation
├── exports/                      # CSV, JSON, PDF, Excel, Parquet export
├── notifications/                # Email, Slack, Teams notifications
├── aggregation/                  # Data aggregation jobs
├── alerts/                       # Alert engine
└── search/search_service.py      # Full-text search
```

### Frontend Components
`/home/user/Shadower-Analytics/frontend/src/components/`

```
components/
├── agents/                       # Agent analytics dashboard
│   ├── AgentHeader.tsx
│   ├── PerformanceMetrics.tsx
│   ├── RuntimeDistribution.tsx
│   ├── ErrorAnalysis.tsx
│   ├── UserSatisfaction.tsx
│   ├── CostAnalysis.tsx
│   ├── AgentComparison.tsx
│   └── OptimizationSuggestions.tsx
├── execution/                    # Execution metrics components
├── dashboard/                    # Main dashboard
├── charts/                       # Chart components
└── common/                       # Shared components
```

### React Hooks
`/home/user/Shadower-Analytics/frontend/src/hooks/api/`

- `useAgentAnalytics.ts` - Agent metrics fetching
- `useExecutionMetrics.ts` - Execution metrics
- `useMetrics.ts` - General metrics
- Custom hooks use React Query for caching

---

## 7. AGENT-RELATED CODE LOCATION

### API Endpoints
**File**: `/home/user/Shadower-Analytics/backend/src/api/routes/agents.py`

Current endpoints:
- `GET /api/v1/agents/` - List agents (TODO: implement)
- `GET /api/v1/agents/{agent_id}/analytics` - Comprehensive agent analytics
- `GET /api/v1/agents/{agent_id}` - Agent details (TODO: implement fully)
- `GET /api/v1/agents/{agent_id}/stats` - Agent statistics

### Services
**Primary**: `/home/user/Shadower-Analytics/backend/src/services/analytics/agent_analytics_service.py`

**Class**: `AgentAnalyticsService`

Key Methods:
- `get_agent_analytics()` - Main analytics aggregation
- `_get_performance_metrics()` - Runtime, throughput, success rate
- `_get_error_analysis()` - Error patterns and tracking
- `_get_user_metrics()` - User satisfaction and ratings
- `_get_resource_usage()` - Credit and token consumption
- `_get_comparisons()` - Workspace and historical comparisons
- `_get_optimization_suggestions()` - AI recommendations

**Secondary**: `/home/user/Shadower-Analytics/backend/src/services/metrics/agent_metrics.py`

Basic metrics calculation functions:
- `calculate_agent_success_rate()`
- `calculate_avg_execution_time()`
- `get_agent_performance_metrics()`
- `get_top_performing_agents()`

### Database Models
**File**: `/home/user/Shadower-Analytics/backend/src/models/database/tables.py`

```python
class AgentMetric(Base):
    """Agent metrics table."""
    agent_id, metric_date, total_executions, successful_executions, 
    failed_executions, avg_duration

class ExecutionLog(Base):
    """Execution logs table."""
    agent_id, user_id, workspace_id, status, duration, credits_used,
    started_at, completed_at
```

### Schemas
**File**: `/home/user/Shadower-Analytics/backend/src/models/schemas/agent_analytics.py`

Key schemas:
- `PerformanceMetrics` - Runtime and throughput stats
- `ResourceUsage` - Credits, tokens, costs
- `ErrorAnalysis` - Error patterns
- `UserMetrics` - User satisfaction
- `AgentAnalyticsResponse` - Complete response

### Frontend Components
**Location**: `/home/user/Shadower-Analytics/frontend/src/components/agents/`

Components:
- `PerformanceMetrics.tsx` - Performance overview cards
- `RuntimeDistribution.tsx` - Runtime percentile chart
- `ErrorAnalysis.tsx` - Error patterns visualization
- `CostAnalysis.tsx` - Cost breakdown
- `OptimizationSuggestions.tsx` - Recommendations
- Custom hooks: `useAgentAnalytics.ts`

### Database Tables
**Migration**: `/home/user/Shadower-Analytics/database/migrations/009_create_agent_analytics_tables.sql`

Key tables:
- `analytics.agent_runs` - Individual execution records
- `analytics.agent_errors` - Error tracking
- `analytics.agent_performance_hourly` - Hourly aggregates
- `analytics.agent_optimization_suggestions` - Recommendations
- `analytics.agent_user_feedback` - User ratings
- Materialized view: `analytics.agent_analytics_summary`

---

## 8. EXISTING ANALYTICS PATTERNS

### Architecture Patterns to Follow

#### 1. Service Layer Pattern
```python
# Location: services/[feature_name]/
class [Feature]Service:
    async def get_[feature]_data(self, workspace_id: str, ...):
        # Implementation
        pass
    
    async def _get_subcomponent(self):
        # Helper methods
        pass

# Use asyncio.gather() for parallel queries
results = await asyncio.gather(
    self._get_component1(),
    self._get_component2(),
    self._get_component3(),
)
```

#### 2. API Route Pattern
```python
# Location: api/routes/[feature].py
router = APIRouter(prefix="/api/v1/[feature]", tags=["[feature]"])

@router.get("/{id}")
async def get_feature(
    id: str = Path(...),
    workspace_id: str = Query(...),
    db = Depends(get_db),
    current_user = Depends(get_current_user),
):
    # Validate permissions
    # Fetch data from service
    # Return schema response
    pass
```

#### 3. Caching Pattern
```python
from services.cache.decorator import cache

@cache(ttl=300)  # 5 minutes
async def get_metrics(self, workspace_id: str):
    # Implementation
    pass
```

#### 4. Materialized View Pattern
Used for pre-aggregated data that refreshes periodically:
```sql
CREATE MATERIALIZED VIEW analytics.[feature_summary] AS
SELECT ... FROM [base_table]
WITH DATA;

-- Refresh in background job
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.[feature_summary];
```

#### 5. Index Strategy
- Time-series: BRIN indexes on timestamp columns
- Filter queries: Composite indexes (filter_col, date_col)
- Foreign keys: Indexed automatically

---

## 9. IMPLEMENTATION RECOMMENDATIONS FOR AGENT RESOURCE UTILIZATION ANALYTICS

### For Agent Resource Utilization Analytics Feature

#### Database Layer
1. **New Tables** to create:
   - `analytics.agent_resources` - Resource metrics (CPU, memory, tokens)
   - `analytics.resource_allocations` - Allocated vs actual resources
   - `analytics.resource_trends` - Time-series resource data
   - Materialized view: `analytics.agent_resource_summary`

2. **Indexes**:
   - (agent_id, measured_at DESC) BRIN for time-series
   - (workspace_id, measured_at DESC) for workspace queries

#### Backend Services
1. **New Service**: `/backend/src/services/metrics/resource_metrics.py`
   - `get_agent_resources(agent_id, workspace_id, timeframe)`
   - `get_resource_allocation_efficiency()`
   - `compare_resource_usage()`
   - `predict_resource_needs()`

2. **API Route**: `/backend/src/api/routes/resources.py`
   - `GET /api/v1/resources/agents/{agent_id}`
   - `GET /api/v1/resources/workspace/{workspace_id}`
   - `POST /api/v1/resources/forecast`

3. **Tasks**: Add job in `/jobs/aggregation/`
   - Hourly resource aggregation task
   - Resource alert checks

#### Frontend Components
1. **New Components**: `/frontend/src/components/resources/`
   - `ResourceOverview.tsx` - Key resource metrics
   - `ResourceTimeline.tsx` - Historical trends
   - `AllocationEfficiency.tsx` - Allocation vs actual
   - `ResourceForecast.tsx` - Predicted resource needs
   - `ResourceComparison.tsx` - Agent comparison

2. **New Hook**: `/frontend/src/hooks/api/useResourceMetrics.ts`

3. **New Types**: `/frontend/src/types/resources.ts`

#### Existing Code to Extend
- Add `resource_metrics.py` to `services/metrics/`
- Extend `execution_logs` table with resource fields
- Add metrics calculation in `agent_analytics_service.py`
- Add resource section to agent detail page

---

## Summary

This is a well-structured, production-ready analytics platform with:

- **Clear separation of concerns**: API → Service → Database layers
- **Async/await throughout**: FastAPI + asyncpg + SQLAlchemy async
- **Comprehensive analytics**: 15+ specialized analytics services
- **Real-time capabilities**: WebSocket, Redis pub/sub
- **Scalable architecture**: Celery for background jobs, Redis for caching
- **Strong patterns**: Consistent routing, caching, error handling
- **Extensive features**: Metrics, predictions, alerts, reports, exports, search

For the **Agent Resource Utilization Analytics** feature, follow the established patterns:
1. Create new tables in migrations/
2. Implement service in services/metrics/
3. Add API routes in routes/resources.py
4. Build frontend components in components/resources/
5. Create React Query hooks for data fetching

All components integrate seamlessly with existing authentication, caching, and analytics infrastructure.
