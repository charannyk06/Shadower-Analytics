# Specification: Repository Structure

## Feature Overview
Complete directory structure and file organization for the Shadow Analytics microservice.

## Technical Requirements
- Monorepo containing backend API and frontend dashboard
- Docker support for local development
- CI/CD configuration
- Clear separation of concerns

## Implementation Details

### Root Directory Structure
```
shadower-analytics/
├── backend/                    # FastAPI Analytics Service
├── frontend/                   # Next.js Dashboard
├── database/                   # Schema and migrations
├── jobs/                       # Background tasks
├── docker/                     # Docker configurations
├── scripts/                    # Utility scripts
├── docs/                       # Documentation
├── .github/                    # GitHub Actions
├── docker-compose.yml          # Local development
├── Makefile                    # Common commands
├── .env.example                # Environment template
├── .gitignore
├── LICENSE
└── README.md
```

### Backend Structure
```
backend/
├── src/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── executive.py       # CEO dashboard routes
│   │   │   ├── agents.py          # Agent analytics
│   │   │   ├── users.py           # User activity
│   │   │   ├── workspaces.py      # Workspace metrics
│   │   │   ├── metrics.py         # General metrics
│   │   │   ├── exports.py         # Export functionality
│   │   │   ├── reports.py         # Custom reports
│   │   │   ├── health.py          # Health checks
│   │   │   └── websocket.py       # Real-time connections
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py            # JWT verification
│   │   │   ├── cors.py            # CORS configuration
│   │   │   ├── rate_limit.py      # Rate limiting
│   │   │   └── logging.py         # Request logging
│   │   ├── dependencies/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py            # Auth dependencies
│   │   │   ├── database.py        # DB connections
│   │   │   └── cache.py           # Redis client
│   │   └── main.py                # FastAPI app
│   ├── services/
│   │   ├── __init__.py
│   │   ├── metrics/
│   │   │   ├── __init__.py
│   │   │   ├── user_metrics.py    # DAU/WAU/MAU
│   │   │   ├── agent_metrics.py   # Agent performance
│   │   │   ├── execution_metrics.py # Run statistics
│   │   │   ├── business_metrics.py # MRR/Churn/LTV
│   │   │   └── credit_metrics.py  # Usage tracking
│   │   ├── analytics/
│   │   │   ├── __init__.py
│   │   │   ├── cohort_analysis.py
│   │   │   ├── funnel_analysis.py
│   │   │   ├── trend_analysis.py
│   │   │   ├── anomaly_detection.py
│   │   │   └── predictions.py
│   │   ├── aggregation/
│   │   │   ├── __init__.py
│   │   │   ├── aggregator.py      # Main aggregation logic
│   │   │   ├── rollup.py          # Time-based rollups
│   │   │   └── materialized.py    # MV refresh
│   │   ├── alerts/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py          # Alert rule engine
│   │   │   ├── thresholds.py      # Threshold checks
│   │   │   └── notifications.py   # Send notifications
│   │   ├── exports/
│   │   │   ├── __init__.py
│   │   │   ├── csv_export.py
│   │   │   ├── pdf_export.py
│   │   │   └── json_export.py
│   │   └── cache/
│   │       ├── __init__.py
│   │       ├── redis_cache.py     # Cache implementation
│   │       └── invalidation.py    # Cache invalidation
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── metrics.py         # Metric schemas
│   │   │   ├── agents.py          # Agent schemas
│   │   │   ├── users.py           # User schemas
│   │   │   ├── workspaces.py      # Workspace schemas
│   │   │   └── common.py          # Shared schemas
│   │   └── database/
│   │       ├── __init__.py
│   │       ├── tables.py          # SQLAlchemy models
│   │       └── enums.py           # Database enums
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Settings management
│   │   ├── database.py            # Database connection
│   │   ├── redis.py               # Redis connection
│   │   ├── security.py            # Security utilities
│   │   └── exceptions.py          # Custom exceptions
│   └── utils/
│       ├── __init__.py
│       ├── datetime.py            # Date/time helpers
│       ├── calculations.py        # Math utilities
│       └── validators.py          # Input validation
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest configuration
│   ├── unit/
│   │   ├── test_metrics.py
│   │   ├── test_aggregation.py
│   │   └── test_cache.py
│   ├── integration/
│   │   ├── test_api.py
│   │   ├── test_database.py
│   │   └── test_websocket.py
│   └── fixtures/
│       ├── __init__.py
│       └── test_data.py
├── alembic/                        # Database migrations
│   ├── alembic.ini
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── pytest.ini
├── .env.example
└── Dockerfile
```

### Frontend Structure
```
frontend/
├── src/
│   ├── app/                       # Next.js 14 App Router
│   │   ├── layout.tsx
│   │   ├── page.tsx               # Landing page
│   │   ├── globals.css
│   │   ├── executive/
│   │   │   ├── page.tsx           # CEO dashboard
│   │   │   └── loading.tsx
│   │   ├── agents/
│   │   │   ├── page.tsx           # Agents list
│   │   │   ├── [id]/
│   │   │   │   └── page.tsx      # Agent details
│   │   │   └── loading.tsx
│   │   ├── users/
│   │   │   ├── page.tsx           # User analytics
│   │   │   └── cohorts/
│   │   │       └── page.tsx       # Cohort analysis
│   │   ├── workspaces/
│   │   │   ├── page.tsx           # Workspace list
│   │   │   └── [id]/
│   │   │       └── page.tsx       # Workspace details
│   │   ├── reports/
│   │   │   ├── page.tsx           # Report builder
│   │   │   └── saved/
│   │   │       └── page.tsx       # Saved reports
│   │   └── api/                   # API routes (if needed)
│   │       └── auth/
│   │           └── route.ts
│   ├── components/
│   │   ├── ui/                    # Base UI components
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Dropdown.tsx
│   │   │   └── index.ts
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── PageContainer.tsx
│   │   ├── charts/
│   │   │   ├── LineChart.tsx
│   │   │   ├── AreaChart.tsx
│   │   │   ├── BarChart.tsx
│   │   │   ├── PieChart.tsx
│   │   │   ├── TrendChart.tsx
│   │   │   └── ChartContainer.tsx
│   │   ├── metrics/
│   │   │   ├── MetricCard.tsx
│   │   │   ├── MetricGrid.tsx
│   │   │   ├── MetricTrend.tsx
│   │   │   ├── MetricComparison.tsx
│   │   │   └── MetricSkeleton.tsx
│   │   ├── tables/
│   │   │   ├── DataTable.tsx
│   │   │   ├── TablePagination.tsx
│   │   │   ├── TableFilters.tsx
│   │   │   ├── TableExport.tsx
│   │   │   └── columns/
│   │   │       ├── agentColumns.tsx
│   │   │       └── userColumns.tsx
│   │   ├── realtime/
│   │   │   ├── RealtimeIndicator.tsx
│   │   │   ├── LiveCounter.tsx
│   │   │   ├── ExecutionFeed.tsx
│   │   │   └── ConnectionStatus.tsx
│   │   ├── filters/
│   │   │   ├── DateRangePicker.tsx
│   │   │   ├── TimeframeSelector.tsx
│   │   │   ├── WorkspaceFilter.tsx
│   │   │   └── FilterBar.tsx
│   │   └── exports/
│   │       ├── ExportButton.tsx
│   │       ├── ExportModal.tsx
│   │       └── ReportGenerator.tsx
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts          # Axios instance
│   │   │   ├── endpoints.ts       # API endpoints
│   │   │   └── types.ts           # API types
│   │   ├── auth/
│   │   │   ├── auth.ts            # Auth utilities
│   │   │   └── token.ts           # Token management
│   │   ├── websocket/
│   │   │   ├── client.ts          # WS client
│   │   │   └── events.ts          # Event handlers
│   │   ├── utils/
│   │   │   ├── formatting.ts      # Number/date format
│   │   │   ├── calculations.ts    # Client-side calcs
│   │   │   └── constants.ts       # App constants
│   │   └── config.ts              # App configuration
│   ├── hooks/
│   │   ├── api/
│   │   │   ├── useMetrics.ts
│   │   │   ├── useAgents.ts
│   │   │   ├── useUsers.ts
│   │   │   └── useWorkspaces.ts
│   │   ├── useWebSocket.ts
│   │   ├── useAuth.ts
│   │   ├── useFilters.ts
│   │   └── useExport.ts
│   ├── styles/
│   │   ├── globals.css
│   │   └── components/
│   │       └── charts.css
│   └── types/
│       ├── metrics.ts
│       ├── agents.ts
│       ├── users.ts
│       └── common.ts
├── public/
│   ├── favicon.ico
│   └── images/
├── tests/
│   ├── unit/
│   └── e2e/
├── package.json
├── package-lock.json
├── tsconfig.json
├── next.config.js
├── tailwind.config.js
├── postcss.config.js
├── .env.local.example
├── .eslintrc.json
├── .prettierrc
└── Dockerfile
```

### Database Structure
```
database/
├── migrations/
│   ├── 001_create_analytics_schema.sql
│   ├── 002_create_base_tables.sql
│   ├── 003_create_materialized_views.sql
│   ├── 004_create_indexes.sql
│   ├── 005_create_functions.sql
│   └── 006_create_triggers.sql
├── seeds/
│   ├── development/
│   │   └── sample_data.sql
│   └── test/
│       └── test_data.sql
├── procedures/
│   ├── refresh_materialized_views.sql
│   ├── calculate_metrics.sql
│   └── cleanup_old_data.sql
└── README.md
```

### Jobs Structure
```
jobs/
├── aggregation/
│   ├── __init__.py
│   ├── hourly_rollup.py
│   ├── daily_rollup.py
│   ├── weekly_rollup.py
│   └── monthly_rollup.py
├── alerts/
│   ├── __init__.py
│   ├── threshold_checker.py
│   ├── anomaly_detector.py
│   └── notification_sender.py
├── maintenance/
│   ├── __init__.py
│   ├── cleanup.py
│   ├── optimize.py
│   └── backup.py
├── celeryconfig.py
├── requirements.txt
└── Dockerfile
```

### Docker Structure
```
docker/
├── nginx/
│   └── nginx.conf
├── redis/
│   └── redis.conf
└── postgres/
    └── init.sql
```

### GitHub Actions Structure
```
.github/
├── workflows/
│   ├── backend-ci.yml
│   ├── frontend-ci.yml
│   ├── deploy-production.yml
│   ├── deploy-staging.yml
│   └── database-migration.yml
├── ISSUE_TEMPLATE/
│   ├── bug_report.md
│   └── feature_request.md
└── pull_request_template.md
```

## File Naming Conventions
- Python files: `snake_case.py`
- TypeScript/React: `PascalCase.tsx` for components, `camelCase.ts` for utilities
- SQL files: `001_descriptive_name.sql` (numbered for order)
- Config files: `.lowercase` or `lowercase.config.ext`

## Dependencies

### Backend Dependencies
```txt
# requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
sqlalchemy==2.0.23
asyncpg==0.29.0
redis==5.0.1
celery==5.3.4
alembic==1.12.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
httpx==0.25.2
pandas==2.1.4
numpy==1.26.2
scipy==1.11.4
sentry-sdk==1.39.1
prometheus-client==0.19.0
```

### Frontend Dependencies
```json
// package.json dependencies
{
  "dependencies": {
    "next": "14.0.4",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "typescript": "5.3.3",
    "@tanstack/react-query": "5.13.4",
    "@tanstack/react-table": "8.10.7",
    "recharts": "2.10.3",
    "axios": "1.6.2",
    "date-fns": "3.0.6",
    "tailwindcss": "3.4.0",
    "lucide-react": "0.303.0",
    "clsx": "2.1.0",
    "zod": "3.22.4"
  }
}
```

## Testing Requirements
- Backend: 80% code coverage minimum
- Frontend: Component tests for all UI elements
- E2E tests for critical user flows
- Load testing for API endpoints

## Performance Targets
- Repository clone: <30 seconds
- Backend startup: <5 seconds
- Frontend build: <60 seconds
- Docker compose up: <2 minutes

## Security Considerations
- Never commit `.env` files
- Use `.env.example` for templates
- Separate configs for dev/staging/prod
- Secrets managed via environment variables

## Implementation Notes
1. Create repository with this exact structure
2. Initialize git with proper .gitignore
3. Set up pre-commit hooks for linting
4. Configure VSCode workspace settings
5. Add README with setup instructions