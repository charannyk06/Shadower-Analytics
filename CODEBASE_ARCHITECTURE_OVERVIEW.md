# Shadower-Analytics Codebase Overview & Architecture

## Executive Summary

Shadower-Analytics is a comprehensive analytics platform for monitoring agent performance, user activity, and business metrics. It's a **monorepo** with a **Python FastAPI backend**, **Next.js 14 frontend**, and **PostgreSQL database** with materialized views for fast analytics queries.

---

## 1. Technology Stack

### Backend
- **Framework**: FastAPI 0.104.1
- **ORM**: SQLAlchemy 2.0.23 with asyncpg driver
- **Database**: PostgreSQL 16+
- **Task Queue**: Celery 5.3.4 with Redis broker
- **Authentication**: JWT with python-jose
- **Cache**: Redis 5.0.1
- **Analysis Libraries**: pandas, numpy, scipy, statsmodels, prophet, scikit-learn
- **Monitoring**: prometheus-client, sentry-sdk
- **API**: sse-starlette for Server-Sent Events

### Frontend
- **Framework**: Next.js 14.0.4
- **UI Library**: React 18.2.0
- **Data Fetching**: TanStack React Query 5.13.4
- **Data Tables**: TanStack React Table 8.10.7
- **Charting**: Recharts 2.10.3
- **HTTP Client**: Axios 1.6.2
- **Validation**: Zod 3.22.4
- **Styling**: Tailwind CSS 3.4.0
- **Testing**: Jest, Playwright

### Database
- **Primary**: PostgreSQL 16+
- **Connection Pool**: asyncpg with async/await
- **Migration Tool**: Alembic
- **Analytics Schema**: Separate analytics schema with materialized views

---

## 2. Directory Structure

```
Shadower-Analytics/
├── backend/                          # FastAPI microservice
│   ├── src/
│   │   ├── api/
│   │   │   ├── main.py              # FastAPI app entry point
│   │   │   ├── gateway.py           # API gateway with CORS, rate limiting
│   │   │   ├── routes/              # API endpoint handlers (20+ route files)
│   │   │   │   ├── agents.py        # Agent analytics endpoints
│   │   │   │   ├── metrics.py       # Execution metrics
│   │   │   │   ├── reports.py       # Reporting endpoints
│   │   │   │   ├── exports.py       # CSV/PDF/JSON export
│   │   │   │   ├── funnels.py       # Funnel analysis
│   │   │   │   ├── trends.py        # Trend detection
│   │   │   │   ├── errors.py        # Error tracking
│   │   │   │   └── ... (20 total)
│   │   │   ├── dependencies/        # Shared dependencies
│   │   │   │   ├── auth.py          # get_current_user, role checks
│   │   │   │   └── database.py      # get_db session
│   │   │   ├── middleware/          # FastAPI middleware
│   │   │   │   ├── auth.py          # JWT validation
│   │   │   │   ├── workspace.py     # Workspace access control
│   │   │   │   ├── logging.py       # Request logging
│   │   │   │   └── security.py      # Security headers
│   │   │   └── websocket/           # WebSocket handlers
│   │   ├── models/
│   │   │   ├── schemas/             # Pydantic request/response models
│   │   │   │   ├── agent_analytics.py
│   │   │   │   ├── metrics.py
│   │   │   │   ├── agents.py
│   │   │   │   ├── analytics.py
│   │   │   │   ├── auth.py
│   │   │   │   └── ... (15+ total)
│   │   │   └── database/            # SQLAlchemy ORM models
│   │   │       ├── tables.py        # All database tables
│   │   │       └── enums.py         # Enum types
│   │   ├── services/                # Business logic layer
│   │   │   ├── analytics/           # Analytics services
│   │   │   │   ├── agent_analytics_service.py
│   │   │   │   ├── funnel_analysis.py
│   │   │   │   ├── cohort_analysis.py
│   │   │   │   ├── trend_analysis_service.py
│   │   │   │   └── error_tracking_service.py
│   │   │   ├── metrics/             # Metrics calculation
│   │   │   │   ├── agent_metrics.py
│   │   │   │   ├── execution_metrics.py
│   │   │   │   ├── workspace_analytics_service.py
│   │   │   │   └── executive_service.py
│   │   │   ├── exports/             # Data export services
│   │   │   │   ├── csv_export.py
│   │   │   │   ├── pdf_export.py
│   │   │   │   ├── excel_export.py
│   │   │   │   └── json_export.py
│   │   │   ├── cache/               # Redis caching
│   │   │   ├── materialized_views/  # View refresh logic
│   │   │   ├── alerts/              # Alert notifications
│   │   │   └── events/              # Event handling
│   │   ├── tasks/                   # Celery async tasks
│   │   │   ├── aggregation.py       # Data aggregation
│   │   │   └── maintenance.py       # Cleanup, archival
│   │   ├── utils/                   # Utility functions
│   │   │   ├── validators.py        # Input validation
│   │   │   ├── calculations.py      # Math utilities
│   │   │   ├── datetime.py          # Date/time helpers
│   │   │   └── decorators.py        # Custom decorators
│   │   └── core/                    # Core configuration
│   │       ├── config.py            # Settings, environment
│   │       ├── database.py          # DB engine setup
│   │       ├── redis.py             # Redis client
│   │       ├── security.py          # JWT config
│   │       └── permissions.py       # RBAC setup
│   ├── tests/                       # Test suite
│   ├── alembic/                     # Database migration configs
│   ├── pyproject.toml               # Python project config
│   └── requirements.txt             # Python dependencies
│
├── frontend/                         # Next.js 14 dashboard
│   ├── src/
│   │   ├── app/                     # App Router (Next.js 14)
│   │   │   ├── workspaces/[id]/analytics/
│   │   │   ├── agents/[id]/
│   │   │   ├── leaderboards/
│   │   │   ├── trends/
│   │   │   ├── predictions/
│   │   │   ├── cohorts/
│   │   │   └── layout.tsx           # Root layout
│   │   ├── components/              # React components
│   │   │   ├── agents/              # Agent analytics components
│   │   │   ├── dashboard/           # Dashboard components
│   │   │   ├── execution/           # Execution metrics
│   │   │   ├── charts/              # Chart components
│   │   │   ├── auth/                # Auth components
│   │   │   ├── common/              # Reusable components
│   │   │   └── ui/                  # UI primitives
│   │   ├── hooks/                   # Custom React hooks
│   │   │   ├── api/                 # Data fetching hooks
│   │   │   │   ├── useAgentAnalytics.ts
│   │   │   │   ├── useExecutionMetrics.ts
│   │   │   │   └── ... (many more)
│   │   │   └── useAuth.ts
│   │   ├── lib/                     # Utilities
│   │   │   ├── api/                 # API client
│   │   │   └── utils.ts
│   │   ├── types/                   # TypeScript types
│   │   │   ├── agent-analytics.ts
│   │   │   ├── execution.ts
│   │   │   └── ... (15+ total)
│   │   └── contexts/                # React contexts
│   ├── package.json
│   └── tsconfig.json
│
├── database/                         # Database schemas & migrations
│   ├── migrations/                  # SQL migration files (27+)
│   │   ├── 001_create_analytics_schema.sql
│   │   ├── 002_create_base_tables.sql
│   │   ├── 003_create_materialized_views.sql
│   │   ├── 009_create_agent_analytics_tables.sql
│   │   ├── 010_create_execution_metrics_tables.sql
│   │   ├── 017_create_funnel_analysis_tables.sql
│   │   ├── 022_create_error_tracking_tables.sql
│   │   ├── 024_create_trend_analysis_tables.sql
│   │   └── ... (27 total)
│   ├── procedures/                  # PL/pgSQL functions
│   │   ├── refresh_materialized_views.sql
│   │   ├── aggregate_metrics.sql
│   │   └── cleanup_old_data.sql
│   └── test_migrations/
│
├── jobs/                             # Background job configurations
├── docker/                           # Docker configurations
├── docs/                             # Documentation
└── .github/workflows/                # CI/CD pipelines

```

---

## 3. Database Schema (PostgreSQL)

### Analytics Schema (`analytics` namespace)

#### Core Tables

**1. Agent Analytics Tables**
```
agent_runs (UUID PK)
├── agent_id, workspace_id, user_id
├── status (completed/failed/cancelled/timeout)
├── runtime_seconds, started_at, completed_at
├── credits_consumed, tokens_used, model_name
├── user_rating (1-5), user_feedback
├── error_type, error_message, error_stack
└── metadata (JSONB)

agent_errors (UUID PK)
├── agent_id, workspace_id, agent_run_id (FK)
├── error_type, error_category, error_severity
├── error_message, error_stack, error_context
├── auto_recovered, recovery_time_seconds
├── affected_users, business_impact
└── Indexes: agent_time, type, category, workspace

agent_performance_hourly (UUID PK)
├── agent_id, workspace_id, metric_hour
├── total_runs, successful_runs, failed_runs
├── avg/p50/p95 runtime statistics
├── total_credits, total_tokens, unique_users
└── UNIQUE(agent_id, metric_hour)

agent_user_feedback (UUID PK)
├── agent_id, workspace_id, user_id, agent_run_id
├── rating (1-5), comment
├── feedback_category, sentiment, sentiment_score
└── Indexes: agent_time, user, rating, workspace

agent_model_usage (UUID PK)
├── agent_id, workspace_id, metric_date
├── model_name, model_provider
├── total_calls, total_tokens, total_credits
├── prompt_tokens, completion_tokens
└── UNIQUE(agent_id, model_name, metric_date)

agent_optimization_suggestions (UUID PK)
├── agent_id, workspace_id
├── suggestion_type, title, description
├── estimated_impact, effort_level, priority
├── status (active/implemented/dismissed)
├── baseline_metrics, post_implementation_metrics
└── Indexes: agent, workspace, type
```

**2. Execution Metrics Tables**
```
execution_metrics_hourly
├── workspace_id, hour (TIMESTAMPTZ)
├── total_executions, successful_executions
├── avg/p50/p95/p99 runtime
├── total_credits, total_tokens
└── UNIQUE(workspace_id, hour)

execution_queue
├── execution_id, queue_timestamp
├── status, priority, agent_id
└── For queue depth tracking

execution_patterns
├── Anomalies, bursts, patterns
└── For real-time pattern detection
```

**3. Leaderboard Tables**
```
agent_leaderboard
├── workspace_id, agent_id
├── rank, previous_rank, rank_change
├── timeframe (24h/7d/30d/90d/all)
├── criteria (runs/success_rate/speed/efficiency)
├── Snapshot metrics (total_runs, success_rate, avg_runtime)
├── score, percentile, badge
└── Indexes: workspace_timeframe, rank, calculated_at

user_leaderboard
├── workspace_id, user_id
├── Similar structure to agent_leaderboard
├── achievements (JSON array)
└── Criteria: activity/efficiency/contribution/savings

workspace_leaderboard
├── workspace_id only (no user/agent)
├── Criteria: activity/efficiency/growth/innovation
├── tier (platinum/gold/silver/bronze)
└── Health score, active users
```

**4. User Activity Tables**
```
user_activity (schema: analytics)
├── id (String PK)
├── user_id, workspace_id, session_id
├── event_type, event_name, page_path
├── ip_address, user_agent, referrer
├── device_type, browser, os, country_code
├── metadata (JSON)
└── Indexes: workspace_created, user_workspace, session

user_segments
├── workspace_id, segment_name
├── segment_type, criteria (JSONB)
├── user_count, avg_engagement
└── Timestamps
```

**5. Other Analytics Tables**
```
error_tracking
├── Detailed error categorization
├── Error frequency, severity, impact
└── Recovery metrics

trend_analysis
├── Time series trends
├── Forecasting data
└── Anomaly detection results

funnel_analysis
├── Funnel steps and conversions
├── User progression tracking
└── Funnel metrics

credit_consumption
├── Daily/hourly credit tracking
├── Cost analysis per agent/user
└── Budget tracking
```

#### Materialized Views

```
agent_analytics_summary
├── Pre-aggregated daily metrics for fast queries
├── agent_id, workspace_id, metric_date
├── All aggregations: runs, success_rate, runtime stats
├── Indexes on agent_date and workspace_date
└── Refreshed periodically with REFRESH MATERIALIZED VIEW

Refresh Functions:
├── analytics.refresh_agent_analytics_summary()
├── Uses concurrent refresh to avoid locks
└── Can be called manually or via jobs
```

#### Key Indexes Strategy

- **BRIN Indexes**: For time-series columns (`started_at`, `created_at`)
  - More space-efficient for large datasets
  - Fast range queries on time ranges
  
- **Composite Indexes**: For common filter combinations
  - `(agent_id, started_at DESC)` - Most queries
  - `(workspace_id, started_at DESC)` - Workspace queries
  - `(workspace_id, timeframe, criteria, rank)` - Leaderboard queries

- **GIN Indexes**: For JSONB columns (metadata, criteria)

---

## 4. API Architecture

### Route Organization (FastAPI)

```
/api/v1/
├── /auth/                          # Authentication
│   ├── POST /login
│   ├── POST /logout
│   └── POST /refresh
│
├── /agents/                        # Agent Analytics
│   ├── GET / (list agents with metrics)
│   ├── GET /{agent_id}/analytics
│   ├── GET /{agent_id}/performance
│   ├── GET /{agent_id}/stats
│   └── GET /{agent_id}/executions
│
├── /metrics/                       # Execution Metrics
│   ├── GET /execution (comprehensive)
│   ├── GET /execution/realtime
│   ├── GET /execution/throughput
│   └── GET /execution/latency
│
├── /reports/                       # Reporting
│   ├── POST / (create report)
│   ├── GET / (list reports)
│   ├── GET /{report_id}
│   ├── PUT /{report_id}
│   └── DELETE /{report_id}
│
├── /exports/                       # Data Export
│   ├── POST /csv
│   ├── POST /pdf
│   ├── POST /json
│   └── POST /excel
│
├── /funnels/                       # Funnel Analysis
│   ├── POST / (create funnel)
│   └── GET /{funnel_id}/analysis
│
├── /trends/                        # Trend Analysis
│   ├── GET /detection
│   ├── GET /forecast
│   └── GET /patterns
│
├── /leaderboards/                  # Leaderboards
│   ├── GET /agents
│   ├── GET /users
│   └── GET /workspaces
│
├── /errors/                        # Error Tracking
│   ├── GET / (error summary)
│   ├── GET /patterns
│   └── GET /{error_id}
│
├── /workspaces/                    # Workspace Management
│   ├── GET /
│   ├── GET /{workspace_id}/summary
│   └── GET /{workspace_id}/health
│
├── /executive/                     # Executive Dashboard
│   ├── GET /overview
│   ├── GET /metrics
│   ├── GET /kpis
│   └── GET /health
│
└── /ws/                            # WebSocket
    └── GET /metrics (real-time updates)
```

### Authentication Flow

```
Client Request
    ↓
FastAPI receives JWT in header/query
    ↓
middleware/auth.py validates JWT
    ↓
get_current_user dependency extracts claims
    ↓
Claims include: user_id, email, workspaceId, role, permissions
    ↓
Endpoint checks role/permissions via requires_* dependencies
    ↓
validate_workspace_access checks user can access workspace
    ↓
Endpoint executes with authenticated context
```

---

## 5. Service Layer (Business Logic)

### Analytics Services

**AgentAnalyticsService** (`agent_analytics_service.py`)
- `get_agent_analytics()` - Main comprehensive analytics
- Queries: agent_runs, agent_errors, agent_performance_hourly, agent_user_feedback
- Calculates: performance, resources, errors, user metrics, comparisons, suggestions
- Returns: AgentAnalyticsResponse (Pydantic model)
- Features: Query timeouts (30s), result limits, fail-fast error handling

**ExecutionMetricsService** (`execution_metrics.py`)
- Real-time execution monitoring
- Throughput, latency, queue depth tracking
- Performance by agent/workspace
- Pattern detection and anomalies

**TrendAnalysisService** (`trend_analysis_service.py`)
- Time series trend detection
- Prophet-based forecasting
- Seasonal pattern analysis
- Anomaly detection with confidence intervals

**CohortAnalysisService** (`cohort_analysis.py`)
- User behavior segmentation
- Retention curves
- Cohort comparison

**FunnelAnalysisService** (`funnel_analysis.py`)
- Funnel step tracking
- Conversion rates
- Dropout analysis

**ExecutiveService** (`executive_service.py`)
- High-level business metrics
- MRR, Churn, LTV calculations
- Revenue tracking
- KPI aggregation

### Export Services

- **CSVExport**: Pandas-based CSV generation
- **PDFExport**: Reportlab-based PDF generation
- **ExcelExport**: openpyxl-based Excel generation
- **JSONExport**: Structured JSON export with metadata

### Cache Services

- **RedisCache**: Redis-backed caching
- Cache keys pattern: `analytics:{entity}:{id}:{timeframe}`
- TTL configurable per data type
- Decorator: `@cached(ttl=300)` for automatic caching

---

## 6. Frontend Architecture

### Component Structure

**Agent Analytics Components** (`/components/agents/`)
```
AgentHeader.tsx              # Title, actions (export, share, refresh)
PerformanceMetrics.tsx       # KPI cards (runs, success rate, avg duration)
RuntimeDistribution.tsx      # Percentile bar chart
ErrorAnalysis.tsx            # Error patterns, severity breakdown
UserSatisfaction.tsx         # Rating distribution, feedback
CostAnalysis.tsx             # Cost breakdown by model
AgentComparison.tsx          # Vs workspace/all agents/previous period
OptimizationSuggestions.tsx  # AI recommendations with cards
```

**Data Fetching Hooks** (`/hooks/api/`)
```
useAgentAnalytics()          # Full analytics with React Query
  - Caching: 1 minute stale time
  - Refetch on window focus
  - Automatic retry

useExecutionMetrics()        # Execution metrics polling
useWorkspaceMetrics()        # Workspace-level metrics
useLeaderboards()            # Leaderboard rankings
```

**Common Components** (`/components/common/`)
```
TimeframeSelector.tsx        # 24h / 7d / 30d / 90d / all
LoadingSkeletons/           # Skeleton screens while loading
ErrorBoundary/              # Error handling
```

### Data Flow

```
Page Component
    ↓
useAgentAnalytics() hook
    ↓
React Query fetches from /api/v1/agents/{id}/analytics
    ↓
Response cached in React Query
    ↓
Components receive data and render
    ↓
Update on timeframe change
    ↓
Refetch and re-render
```

### Styling & UI

- **Tailwind CSS**: Utility-first styling
- **Recharts**: Interactive charts and graphs
- **Lucide Icons**: Icon library
- **Custom UI Primitives**: Buttons, cards, tables in `/components/ui/`
- **Responsive Design**: Mobile-first approach

---

## 7. Authentication & Authorization

### JWT Token Structure

```json
{
  "sub": "user-id",
  "email": "user@example.com",
  "workspaceId": "ws-123",
  "workspaces": ["ws-123", "ws-456"],
  "role": "admin",
  "permissions": ["view_analytics", "export_analytics"],
  "iat": 1234567890,
  "exp": 1234567890
}
```

### Role-Based Access Control (RBAC)

```
Owner     → Full access to all features
Admin     → Access to analytics, reports, alerts
Member    → View & export analytics, view alerts
Viewer    → Read-only access to analytics
```

### Dependencies & Middleware

**Authentication Dependencies** (`/api/dependencies/auth.py`)
- `get_current_user` - Validates JWT, returns user dict
- `require_owner_or_admin` - Enforces role requirement
- `require_permission` - Enforces specific permission

**Middleware** (`/api/middleware/auth.py`)
- JWT token extraction from headers/query
- Token validation with shared secret
- Token refresh logic
- CORS and rate limiting

---

## 8. Analytics Implementation Patterns

### Pattern 1: Aggregation with Materialized Views

```sql
-- Create materialized view for fast queries
CREATE MATERIALIZED VIEW agent_analytics_summary AS
SELECT agent_id, workspace_id, DATE_TRUNC('day', started_at),
       COUNT(*) as total_runs,
       COUNT(*) FILTER (WHERE status='completed') as successful_runs,
       ...aggregations...
FROM agent_runs
GROUP BY agent_id, workspace_id, DATE_TRUNC('day', started_at);

-- Refresh periodically or on-demand
REFRESH MATERIALIZED VIEW CONCURRENTLY agent_analytics_summary;
```

### Pattern 2: Time Series Query with Percentiles

```python
# Backend service
query = text("""
    SELECT 
        DATE_TRUNC('hour', started_at) as hour,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY runtime) as p50,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY runtime) as p95,
        AVG(runtime) as avg_runtime
    FROM agent_runs
    WHERE agent_id = :agent_id
      AND started_at >= :start_date
    GROUP BY DATE_TRUNC('hour', started_at)
    ORDER BY hour DESC
""")
result = await db.execute(query, {"agent_id": agent_id, "start_date": start_date})
```

### Pattern 3: Error Classification & Tracking

```python
# Categorize errors by type, severity, recovery
class ErrorPattern:
    pattern: str           # e.g., "timeout_morning_peak"
    frequency: int         # How often it occurs
    impact: str           # low/medium/high
    auto_recovery_rate: float
    avg_recovery_time: float
    suggested_fix: str
```

### Pattern 4: Comparative Analysis

```python
# Compare current period vs previous period
comparison = {
    "vsWorkspaceAverage": {
        "successRate": agent_rate - workspace_avg,
        "runtime": agent_avg - workspace_avg_runtime,
        "creditEfficiency": agent_credits - workspace_credits
    },
    "vsAllAgents": {
        "rank": agent_rank,  # e.g., #5 out of 250
        "percentile": agent_percentile  # e.g., 98th percentile
    },
    "vsPreviousPeriod": {
        "runsChange": ((current_runs - previous_runs) / previous_runs) * 100,
        "successRateChange": current_success_rate - previous_success_rate,
        ...
    }
}
```

### Pattern 5: Optimization Suggestions (Rule-Based)

```python
suggestions = []

# Rule 1: High error rate
if error_rate > 5:
    suggestions.append({
        "type": "reliability",
        "title": "High Error Rate Detected",
        "estimatedImpact": "Could reduce 50% of errors",
        "effort": "medium"
    })

# Rule 2: High cost per run
if avg_cost_per_run > workspace_avg * 2:
    suggestions.append({
        "type": "cost",
        "title": "Consider Model Optimization",
        "estimatedImpact": "Could reduce costs by 30%",
        "effort": "high"
    })
```

### Pattern 6: Concurrent Service Calls with asyncio

```python
# Fetch multiple data sources in parallel
performance, resources, errors, user_metrics = await asyncio.gather(
    self._get_performance_metrics(agent_id, timeframe),
    self._get_resource_usage(agent_id, timeframe),
    self._get_error_analysis(agent_id, timeframe),
    self._get_user_metrics(agent_id, timeframe),
    return_exceptions=True
)

# Handle individual failures gracefully
if isinstance(errors, Exception):
    errors = {"error": "Failed to load error data"}
```

---

## 9. Current Analytics Features

### ✅ Implemented

1. **Agent Analytics**
   - Performance metrics (runs, success rate, runtime stats)
   - Resource usage (credits, tokens, costs)
   - Error analysis with patterns
   - User satisfaction (ratings, feedback)
   - Comparative analysis
   - Optimization suggestions

2. **Execution Metrics**
   - Real-time throughput monitoring
   - Latency percentiles (p50, p75, p90, p95, p99)
   - Queue depth tracking
   - Performance patterns

3. **Leaderboards**
   - Agent rankings (by runs, success rate, speed, efficiency, popularity)
   - User rankings (by activity, efficiency, contribution, savings)
   - Workspace rankings
   - Time-based rankings (24h, 7d, 30d, 90d, all)

4. **Trend Analysis**
   - Prophet-based forecasting
   - Seasonal pattern detection
   - Anomaly detection with confidence intervals
   - Historical trend visualization

5. **Funnel Analysis**
   - Funnel step tracking
   - Conversion rate calculations
   - Dropout analysis

6. **Error Tracking**
   - Error categorization (timeout, rate_limit, validation, etc.)
   - Severity levels and impact assessment
   - Recovery metrics (MTTR, auto-recovery rate)
   - Error pattern detection

7. **Export Capabilities**
   - CSV export
   - PDF report generation
   - Excel export
   - JSON export

### 🚧 Planned

1. **Agent Lifecycle Analytics** (Your implementation task)
2. **Predictive Analytics** (ML-based performance prediction)
3. **Cost Forecasting** (Budget predictions)
4. **Custom Dashboards** (User-configurable layouts)
5. **Real-time Alerts** (Threshold-based notifications)
6. **Advanced Cohort Analysis** (Behavioral segmentation)

---

## 10. Database Technology Details

### PostgreSQL Features Used

**Materialized Views**
- Pre-computed, indexed aggregations
- Concurrent refresh (no lock during update)
- Used for daily summaries

**Window Functions**
- PERCENTILE_CONT() for percentile calculations
- RANK(), ROW_NUMBER() for leaderboards
- LAG() for trend analysis

**JSON Support**
- JSONB columns for flexible metadata
- GIN indexes for efficient querying
- JSON operators: ->, ->>

**Advanced Indexes**
- BRIN (Block Range INdex) for time-series
- Composite indexes for common query patterns
- Partial indexes (WHERE clauses)

**Constraints**
- CHECK constraints for valid values
- UNIQUE constraints for idempotency
- Foreign keys with CASCADE delete

---

## 11. Performance Optimizations

### Query Optimization
1. Materialized views for pre-aggregated data
2. BRIN indexes for time-series columns
3. Composite indexes for multi-column filters
4. Partial indexes to reduce size
5. Query timeout protection (30 seconds)

### Caching Strategy
1. React Query: 1-minute stale time for analytics
2. Redis: Application-level caching with TTL
3. Browser cache: Static assets, API responses
4. Selective cache invalidation on updates

### Frontend Optimization
1. Code splitting by route (Next.js automatic)
2. Lazy component loading
3. Memoization with useMemo/useCallback
4. Skeleton screens during loading

### Backend Optimization
1. Async/await with asyncpg (non-blocking)
2. Connection pooling
3. Batch operations where possible
4. Fail-fast error handling

---

## 12. Security Architecture

### API Security
- **Authentication**: JWT with HTTPS-only in production
- **Authorization**: Role-based access control (RBAC)
- **Rate Limiting**: Configurable per endpoint
- **Input Validation**: Pydantic schemas + UUID validation
- **CORS**: Configured for cross-origin requests
- **Security Headers**: X-Frame-Options, X-Content-Type-Options, etc.

### Data Security
- **PII Filtering**: Error messages truncated in responses
- **Workspace Isolation**: All queries filtered by workspace_id
- **Row-Level Security**: Can be enforced at DB level
- **Encrypted Passwords**: bcrypt hashing
- **Secure Token**: 256-bit minimum for JWT secret

### Audit Trail
- Request logging middleware
- Authentication event logging
- Error tracking with Sentry
- Prometheus metrics for monitoring

---

## 13. File Summary for Lifecycle Analytics

For your agent lifecycle analytics implementation, focus on these files:

### Database
- `/database/migrations/` - Add new lifecycle analytics tables
- **Pattern**: Check `009_create_agent_analytics_tables.sql` for structure

### Backend
- `/backend/src/api/routes/agents.py` - Add lifecycle endpoints
- `/backend/src/services/analytics/agent_analytics_service.py` - Base analytics service
- **Create**: `/backend/src/services/analytics/agent_lifecycle_service.py` for lifecycle logic
- `/backend/src/models/schemas/agent_analytics.py` - Response schemas

### Frontend
- `/frontend/src/components/agents/` - Create lifecycle components
- `/frontend/src/hooks/api/useAgentAnalytics.ts` - Adapt for lifecycle data
- **Create**: `/frontend/src/types/agent-lifecycle.ts` for TypeScript types
- `/frontend/src/app/agents/[id]/page.tsx` - Main agent page

---

## 14. Technology Selection Rationale

| Component | Technology | Why |
|-----------|-----------|-----|
| Backend | FastAPI | Async support, auto-docs, fast development |
| Database | PostgreSQL | JSON, materialized views, advanced analytics functions |
| Cache | Redis | Fast in-memory caching, Celery broker |
| Task Queue | Celery | Distributed async tasks, scheduling |
| Frontend | Next.js 14 | Server/client components, built-in optimization |
| Charts | Recharts | React-native, responsive, interactive |
| State | React Query | Powerful data synchronization, caching |
| Styling | Tailwind | Utility-first, responsive, fast development |

---

## Summary for Lifecycle Analytics Implementation

The codebase provides:
1. **Complete analytics infrastructure** with services, routes, and DB schema
2. **Proven patterns** for metrics calculation, error handling, and caching
3. **Multi-layer authentication** with workspace isolation
4. **Frontend components** ready to adapt for new analytics
5. **Export capabilities** for reports and data sharing
6. **Real-time infrastructure** with WebSocket support

Your implementation should:
1. Follow existing service layer pattern
2. Create database migration for lifecycle tables
3. Add lifecycle service with state transitions
4. Create API endpoints following route pattern
5. Build frontend components reusing common patterns
6. Add appropriate validation and error handling
7. Implement caching for performance
8. Add tests following project patterns

