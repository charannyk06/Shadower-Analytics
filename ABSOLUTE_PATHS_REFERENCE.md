# Absolute File Paths Reference

## Project Root
```
/home/user/Shadower-Analytics
```

---

## BACKEND CORE FILES

### API Configuration & Main
```
/home/user/Shadower-Analytics/backend/src/api/main.py          # FastAPI app setup
/home/user/Shadower-Analytics/backend/src/api/gateway.py       # API gateway, rate limiting, CORS
/home/user/Shadower-Analytics/backend/src/api/models.py        # API request/response models
/home/user/Shadower-Analytics/backend/src/api/validation.py    # Request validation utilities
/home/user/Shadower-Analytics/backend/src/api/versioning.py    # API versioning logic
```

### Core Configuration & Infrastructure
```
/home/user/Shadower-Analytics/backend/src/core/config.py          # Settings and environment variables
/home/user/Shadower-Analytics/backend/src/core/database.py        # SQLAlchemy setup and session management
/home/user/Shadower-Analytics/backend/src/core/redis.py           # Redis client initialization
/home/user/Shadower-Analytics/backend/src/core/security.py        # JWT and authentication utilities
/home/user/Shadower-Analytics/backend/src/core/permissions.py     # Role-based access control (RBAC)
/home/user/Shadower-Analytics/backend/src/core/token_manager.py   # Token creation and validation
/home/user/Shadower-Analytics/backend/src/core/privacy.py         # PII filtering and privacy utilities
/home/user/Shadower-Analytics/backend/src/core/exceptions.py      # Custom exception classes
/home/user/Shadower-Analytics/backend/src/core/constants.py       # Application constants
```

### Dependencies (Injection)
```
/home/user/Shadower-Analytics/backend/src/api/dependencies/
├── auth.py                                    # JWT and user authentication
└── (other dependency providers)
```

### Middleware
```
/home/user/Shadower-Analytics/backend/src/api/middleware/
├── logging.py                                 # Request/response logging
└── security.py                                # Security headers
```

### WebSocket
```
/home/user/Shadower-Analytics/backend/src/api/websocket/
├── __init__.py
├── events.py                                  # WebSocket event handlers
└── managers.py                                # Connection management
```

### Celery Configuration
```
/home/user/Shadower-Analytics/backend/src/celery_app.py        # Celery app setup
```

---

## BACKEND ROUTES (API Endpoints)

All routes located in: `/home/user/Shadower-Analytics/backend/src/api/routes/`

```
agents.py                   # /api/v1/agents
alerts.py                   # /api/v1/alerts
admin.py                    # /api/v1/admin
analytics.py                # /api/v1/analytics
anomalies.py                # /api/v1/anomalies
auth.py                     # /api/v1/auth
comparisons.py              # /api/v1/comparisons
credits.py                  # /api/v1/credits
dashboard.py                # /api/v1/dashboard
errors.py                   # /api/v1/errors
executive.py                # /api/v1/executive
exports.py                  # /api/v1/exports
funnels.py                  # /api/v1/funnels
health.py                   # /api/v1/health
integrations.py             # /api/v1/integrations
leaderboards.py             # /api/v1/leaderboards
materialized_views.py       # /api/v1/materialized-views
metrics.py                  # /api/v1/metrics
moving_averages.py          # /api/v1/moving-averages
notifications.py            # /api/v1/notifications
predictions.py              # /api/v1/predictions
reports.py                  # /api/v1/reports
search.py                   # /api/v1/search
trends.py                   # /api/v1/trends
user_activity.py            # /api/v1/user-activity
users.py                    # /api/v1/users
websocket.py                # /ws/metrics/{workspace_id}
workspaces.py               # /api/v1/workspaces
```

---

## BACKEND MODELS & SCHEMAS

### Database Models (ORM)
```
/home/user/Shadower-Analytics/backend/src/models/database/
├── __init__.py
├── tables.py                # All SQLAlchemy ORM models
└── enums.py                 # Database enums
```

### API Schemas (Pydantic)
```
/home/user/Shadower-Analytics/backend/src/models/schemas/
├── __init__.py
├── common.py                # Common/shared schemas
├── agents.py                # Agent-related schemas
├── agent_analytics.py       # Agent analytics response schemas
├── analytics.py             # General analytics schemas
├── anomalies.py             # Anomaly detection schemas
├── auth.py                  # Authentication schemas
├── comparisons.py           # Comparison schemas
├── credits.py               # Credit/cost schemas
├── dashboard.py             # Dashboard schemas
├── errors.py                # Error tracking schemas
├── executive.py             # Executive dashboard schemas
├── exports.py               # Export schemas
├── funnels.py               # Funnel analysis schemas
├── health.py                # Health check schemas
├── integrations.py          # Integration schemas
├── leaderboards.py          # Leaderboard schemas
├── materialized_views.py    # Materialized view schemas
├── metrics.py               # Metrics schemas
├── notifications.py         # Notification schemas
├── predictions.py           # Prediction schemas
├── reports.py               # Report schemas
├── search.py                # Search schemas
├── trends.py                # Trend analysis schemas
├── user_activity.py         # User activity schemas
├── users.py                 # User schemas
├── workspaces.py            # Workspace schemas
└── comparison_views.py      # Comparison view schemas
```

---

## BACKEND SERVICES (Business Logic)

### Metrics Services
```
/home/user/Shadower-Analytics/backend/src/services/metrics/
├── __init__.py
├── agent_metrics.py              # Agent metrics calculations
├── execution_metrics.py          # Execution metrics service
├── user_metrics.py               # User activity metrics
├── credit_metrics.py             # Credit/cost tracking
├── business_metrics.py           # Business KPIs
├── workspace_analytics_service.py # Workspace-level analytics
├── executive_service.py          # Executive dashboard metrics
└── constants.py                  # Metric constants and thresholds
```

### Advanced Analytics Services
```
/home/user/Shadower-Analytics/backend/src/services/analytics/
├── __init__.py
├── agent_analytics_service.py         # Comprehensive agent analytics
├── error_tracking_service.py          # Error analysis and patterns
├── anomaly_detection.py               # Anomaly detection engine
├── funnel_analysis.py                 # Conversion funnel tracking
├── cohort_analysis.py                 # User cohort analysis
├── retention_analysis.py              # User retention metrics
├── trend_analysis.py                  # Trend detection and analysis
├── trend_analysis_service.py          # Advanced trend analysis
├── trend_analysis_constants.py        # Trend analysis constants
├── user_activity.py                  # User behavior tracking
├── credit_consumption.py              # Credit analytics
├── credit_consumption_predictor.py   # Credit prediction
├── predictions.py                    # Predictive analytics
├── predictive_analytics.py           # Advanced predictions
├── percentiles.py                    # Percentile calculations
├── moving_averages.py                # Moving average calculations
├── growth_metrics_predictor.py       # Growth predictions
├── error_rate_predictor.py           # Error rate forecasting
├── peak_usage_predictor.py           # Peak usage predictions
├── user_churn_predictor.py           # Churn prediction
└── leaderboard_service.py            # Ranking and leaderboards
```

### Cache Services
```
/home/user/Shadower-Analytics/backend/src/services/cache/
├── __init__.py
├── redis_cache.py              # Redis operations
├── decorator.py                # @cache decorator
├── invalidation.py             # Cache invalidation logic
├── keys.py                     # Cache key pattern definitions
└── metrics.py                  # Cache performance metrics
```

### Other Services
```
/home/user/Shadower-Analytics/backend/src/services/
├── comparison_service.py       # Comparison analytics
├── admin_service.py            # Admin operations
├── reports/
│   ├── __init__.py
│   └── report_service.py       # Report generation
├── exports/
│   ├── __init__.py
│   ├── export_processor.py     # Main export orchestration
│   ├── csv_export.py           # CSV export
│   ├── json_export.py          # JSON export
│   ├── pdf_export.py           # PDF export
│   ├── excel_export.py         # Excel export
│   └── parquet_export.py       # Parquet export
├── notifications/
│   ├── __init__.py
│   ├── notification_system.py  # Main notification system
│   ├── channel_manager.py      # Multi-channel delivery
│   ├── preference_manager.py   # User preferences
│   ├── template_engine.py      # Template processing
│   ├── digest_builder.py       # Digest creation
│   └── delivery_tracker.py     # Delivery tracking
├── alerts/
│   ├── __init__.py
│   ├── alert_engine.py         # Alert processing engine
│   ├── engine.py               # Alert logic
│   ├── conditions.py           # Alert conditions
│   ├── thresholds.py           # Alert thresholds
│   ├── channels.py             # Alert channels
│   └── notifications.py        # Alert notifications
├── aggregation/
│   ├── __init__.py
│   ├── aggregator.py           # Main aggregation logic
│   ├── materialized.py         # Materialized view aggregation
│   └── rollup.py               # Data rollup logic
├── materialized_views/
│   ├── __init__.py
│   └── refresh_service.py      # Materialized view refresh
├── search/
│   ├── __init__.py
│   └── search_service.py       # Full-text search
├── events/
│   ├── __init__.py
│   └── handlers.py             # Event handlers
└── __init__.py
```

---

## BACKEND TASKS (Celery Jobs)

```
/home/user/Shadower-Analytics/backend/src/tasks/
├── __init__.py
├── aggregation.py              # Metrics aggregation tasks
├── alerts.py                   # Alert processing tasks
├── exports.py                  # Export generation tasks
└── maintenance.py              # Maintenance and cleanup tasks
```

---

## BACKEND UTILITIES

```
/home/user/Shadower-Analytics/backend/src/utils/
├── __init__.py
├── validators.py               # Input validation utilities
├── calculations.py             # Shared calculation functions
├── datetime.py                 # Date/time utilities
└── (other utility modules)
```

---

## DATABASE MIGRATIONS

```
/home/user/Shadower-Analytics/database/migrations/
├── 001_create_analytics_schema.sql
├── 002_create_base_tables.sql
├── 002_create_core_tables.sql
├── 003_create_materialized_views.sql
├── 003_create_specialized_tables.sql
├── 004_create_materialized_views.sql
├── 005_create_functions.sql
├── 006_create_triggers.sql
├── 007_create_rls_policies.sql
├── 008_create_performance_indexes.sql
├── 009_create_agent_analytics_tables.sql        # Agent analytics tables
├── 010_create_execution_metrics_tables.sql
├── 011_create_executive_dashboard_indexes.sql
├── 012_create_workspace_analytics_tables.sql
├── 013_create_enhanced_materialized_views.sql
├── 014_create_cohort_analysis_indexes.sql
├── 015_add_rls_and_secure_views.sql
├── 016_create_workspace_analytics_tables.sql
├── 017_create_funnel_analysis_tables.sql
├── 018_update_trend_analysis_cache_add_user_id.sql
├── 021_create_credit_consumption_tables.sql
├── 022_create_error_tracking_tables.sql
├── 023_create_executive_dashboard_indexes.sql
├── 024_create_trend_analysis_tables.sql
├── 025_create_workspace_analytics_tables.sql
├── 027_create_notification_tables.sql
└── 027_create_predictive_analytics_tables.sql
```

---

## ALEMBIC MIGRATIONS

```
/home/user/Shadower-Analytics/backend/alembic/
├── env.py                      # Alembic environment configuration
├── script.py.mako              # Migration template
└── versions/                   # Python migration files (if any)
```

---

## JOBS (Background Processing)

```
/home/user/Shadower-Analytics/jobs/
├── __init__.py
├── celeryconfig.py             # Celery schedule configuration
├── requirements.txt            # Job dependencies
├── Dockerfile                  # Job container
├── aggregation/                # Aggregation job definitions
│   └── (job files)
├── alerts/                     # Alert job definitions
│   └── (job files)
├── maintenance/                # Maintenance job definitions
│   └── (job files)
└── notifications/              # Notification job definitions
    └── (job files)
```

---

## FRONTEND SOURCE FILES

### Next.js App Router Pages
```
/home/user/Shadower-Analytics/frontend/src/app/
├── layout.tsx                  # Root layout
├── page.tsx                    # Homepage
├── dashboard/
│   ├── page.tsx                # Dashboard main page
│   └── (dashboard sub-pages)
├── agents/
│   ├── page.tsx                # Agents list
│   └── [id]/
│       └── page.tsx            # Agent detail page
├── reports/
│   ├── page.tsx                # Reports list
│   └── [id]/
│       └── page.tsx            # Report detail page
└── (other page routes)
```

### React Components
```
/home/user/Shadower-Analytics/frontend/src/components/
├── agents/                     # Agent analytics components
│   ├── AgentHeader.tsx
│   ├── PerformanceMetrics.tsx
│   ├── RuntimeDistribution.tsx
│   ├── ErrorAnalysis.tsx
│   ├── UserSatisfaction.tsx
│   ├── CostAnalysis.tsx
│   ├── AgentComparison.tsx
│   └── OptimizationSuggestions.tsx
├── execution/                  # Execution metrics components
│   ├── ExecutionMetricsDashboard.tsx
│   ├── RealtimeExecutions.tsx
│   ├── QueueDepthIndicator.tsx
│   ├── SystemLoadMonitor.tsx
│   ├── ThroughputChart.tsx
│   ├── LatencyDistribution.tsx
│   ├── ExecutionTimeline.tsx
│   └── PerformanceByAgent.tsx
├── dashboard/                  # Dashboard components
│   ├── DashboardLayout.tsx
│   ├── MetricCards.tsx
│   ├── DashboardHeader.tsx
│   └── (other dashboard components)
├── charts/                     # Chart components
│   ├── LineChart.tsx
│   ├── BarChart.tsx
│   ├── PieChart.tsx
│   └── (other chart components)
├── workspace/                  # Workspace components
│   └── (workspace components)
├── comparisons/                # Comparison components
│   └── (comparison components)
├── trends/                     # Trend components
│   └── (trend components)
├── users/                      # User-related components
│   └── (user components)
├── leaderboards/               # Leaderboard components
│   └── (leaderboard components)
├── errors/                     # Error components
│   └── (error components)
├── credits/                    # Credit components
│   └── (credit components)
├── realtime/                   # Real-time components
│   └── (realtime components)
├── common/                     # Shared components
│   ├── TimeframeSelector.tsx
│   ├── LoadingSpinner.tsx
│   ├── ErrorBoundary.tsx
│   └── (other shared components)
├── auth/                       # Authentication components
│   └── (auth components)
└── ui/                         # Base UI elements (shadcn-ui)
    ├── button.tsx
    ├── card.tsx
    ├── input.tsx
    └── (other UI elements)
```

### React Hooks
```
/home/user/Shadower-Analytics/frontend/src/hooks/
├── api/                        # API data fetching hooks
│   ├── useAgentAnalytics.ts
│   ├── useExecutionMetrics.ts
│   ├── useMetrics.ts
│   ├── useDashboard.ts
│   ├── useReports.ts
│   ├── useAlerts.ts
│   ├── useNotifications.ts
│   ├── usePredictions.ts
│   ├── useSearch.ts
│   └── (other API hooks)
└── (other custom hooks)
```

### TypeScript Types
```
/home/user/Shadower-Analytics/frontend/src/types/
├── agents.ts                   # Agent-related types
├── agent-analytics.ts          # Agent analytics types
├── execution.ts                # Execution metrics types
├── metrics.ts                  # General metrics types
├── dashboard.ts                # Dashboard types
├── reports.ts                  # Report types
├── alerts.ts                   # Alert types
├── predictions.ts              # Prediction types
├── user.ts                     # User types
├── workspace.ts                # Workspace types
├── auth.ts                     # Authentication types
├── common.ts                   # Common/shared types
└── (other type definitions)
```

### Libraries & Utilities
```
/home/user/Shadower-Analytics/frontend/src/lib/
├── api.ts                      # API client utilities
├── auth.ts                     # Authentication utilities
├── validators.ts               # Form validation utilities
├── formatters.ts               # Data formatting utilities
└── (other utility modules)
```

### React Contexts
```
/home/user/Shadower-Analytics/frontend/src/contexts/
├── AuthContext.tsx             # Authentication context
├── WorkspaceContext.tsx        # Workspace context
└── (other contexts)
```

---

## DOCKER CONFIGURATION

```
/home/user/Shadower-Analytics/
├── docker-compose.yml                  # Main Docker Compose configuration
├── docker/
│   ├── nginx/
│   │   └── nginx.conf                  # Nginx reverse proxy config
│   ├── postgres/
│   │   └── init.sql                    # PostgreSQL initialization
│   └── redis/
│       └── redis.conf                  # Redis configuration
├── backend/
│   └── Dockerfile                      # Backend container image
├── frontend/
│   └── Dockerfile                      # Frontend container image
└── jobs/
    └── Dockerfile                      # Background jobs container
```

---

## DOCUMENTATION

```
/home/user/Shadower-Analytics/
├── README.md                           # Project README
├── PROJECT_STRUCTURE_GUIDE.md         # Project structure documentation
├── AGENT_ANALYTICS_FEATURE.md         # Agent analytics implementation doc
├── EXECUTION_METRICS_IMPLEMENTATION.md # Execution metrics doc
├── FUNNEL_ANALYSIS_IMPLEMENTATION.md  # Funnel analysis doc
├── REPORTS_IMPLEMENTATION_EXAMPLES.md # Reports examples
├── REPOSITORY_STRUCTURE_REVIEW.md     # Repository structure review
├── QUICK_REFERENCE.md                 # Quick reference guide
├── SECURITY_FIXES.md                  # Security improvements
├── WEBSOCKET_GUIDE.md                 # WebSocket implementation
├── XSS_SANITIZATION_GUIDE.md         # XSS prevention guide
├── docs/
│   ├── AUTHENTICATION.md              # Authentication documentation
│   ├── CACHING.md                     # Caching strategy
│   ├── ANOMALY_DETECTION.md           # Anomaly detection docs
│   ├── ALERT_ENGINE.md                # Alert engine documentation
│   ├── API_GATEWAY_IMPLEMENTATION.md  # API gateway docs
│   ├── TREND_ANALYSIS_FEATURE.md     # Trend analysis feature
│   └── (other documentation)
├── specs/
│   ├── 10-execution-metrics.md        # Execution metrics spec
│   ├── 09-workspace-analytics.md      # Workspace analytics spec
│   └── (other specification files)
└── backend/docs/
    ├── AGGREGATION_JOBS.md            # Aggregation jobs docs
    └── CACHING.md                     # Backend caching docs
```

---

## CONFIGURATION FILES

```
/home/user/Shadower-Analytics/
├── .env.example                        # Environment variables template
├── Makefile                            # Build and development commands
├── .gitignore                          # Git ignore rules
├── LICENSE                             # License file
└── backend/
    └── (Python configuration files)
```

---

## QUICK COMMAND REFERENCE

### Starting Development Environment
```bash
cd /home/user/Shadower-Analytics
docker-compose up -d
```

### Running Tests
```bash
# Backend tests
cd /home/user/Shadower-Analytics/backend
pytest tests/ -v

# Frontend tests
cd /home/user/Shadower-Analytics/frontend
npm test
```

### Accessing Services
```
API Docs:      http://localhost:8000/docs
Frontend:      http://localhost:3000
Flower (Celery): http://localhost:5555
PostgreSQL:    postgresql://postgres:postgres@localhost:5432/shadower_analytics
Redis:         redis://localhost:6379
```

---

## Key Files to Know

**For Agent Resource Utilization Analytics Implementation:**

1. Database: `/home/user/Shadower-Analytics/database/migrations/` (create 028_create_agent_resource_tables.sql)
2. Service: `/home/user/Shadower-Analytics/backend/src/services/metrics/resource_metrics.py` (NEW)
3. Routes: `/home/user/Shadower-Analytics/backend/src/api/routes/resources.py` (NEW)
4. Schemas: `/home/user/Shadower-Analytics/backend/src/models/schemas/resources.py` (NEW)
5. Types: `/home/user/Shadower-Analytics/frontend/src/types/resources.ts` (NEW)
6. Hooks: `/home/user/Shadower-Analytics/frontend/src/hooks/api/useResourceMetrics.ts` (NEW)
7. Components: `/home/user/Shadower-Analytics/frontend/src/components/resources/` (NEW directory)

**Key Files to Reference:**

- Agent examples: `/home/user/Shadower-Analytics/backend/src/api/routes/agents.py`
- Agent service: `/home/user/Shadower-Analytics/backend/src/services/analytics/agent_analytics_service.py`
- Agent schemas: `/home/user/Shadower-Analytics/backend/src/models/schemas/agent_analytics.py`
- Metrics service: `/home/user/Shadower-Analytics/backend/src/services/metrics/execution_metrics.py`
- Main app: `/home/user/Shadower-Analytics/backend/src/api/main.py`

