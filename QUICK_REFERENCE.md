# Quick File Reference for Reports API Implementation

## Essential Files to Review

### 1. API Routes (Best Examples)
- `/home/user/Shadower-Analytics/backend/src/api/routes/reports.py` - **SKELETON TO IMPLEMENT**
- `/home/user/Shadower-Analytics/backend/src/api/routes/funnels.py` - Modern route pattern (100 lines shown)
- `/home/user/Shadower-Analytics/backend/src/api/routes/agents.py` - Agent analytics with service usage
- `/home/user/Shadower-Analytics/backend/src/api/routes/exports.py` - Export pattern (CSV, PDF, JSON)

### 2. Authentication & Dependencies
- `/home/user/Shadower-Analytics/backend/src/api/dependencies/auth.py` - get_current_user, require_admin, etc.
- `/home/user/Shadower-Analytics/backend/src/api/dependencies/database.py` - get_db session management
- `/home/user/Shadower-Analytics/backend/src/api/middleware/auth.py` - JWT token handling
- `/home/user/Shadower-Analytics/backend/src/api/middleware/workspace.py` - WorkspaceAccess validation

### 3. Schemas & Models
- `/home/user/Shadower-Analytics/backend/src/models/schemas/common.py` - Report & ReportConfig (incomplete)
- `/home/user/Shadower-Analytics/backend/src/models/schemas/metrics.py` - Metric schemas examples
- `/home/user/Shadower-Analytics/backend/src/models/schemas/agent_analytics.py` - Complex schema example
- `/home/user/Shadower-Analytics/backend/src/models/database/tables.py` - All database models

### 4. Services (Business Logic Pattern)
- `/home/user/Shadower-Analytics/backend/src/services/analytics/agent_analytics_service.py` - Full service example
- `/home/user/Shadower-Analytics/backend/src/services/analytics/funnel_analysis.py` - Complex service
- `/home/user/Shadower-Analytics/backend/src/services/exports/csv_export.py` - Export service
- `/home/user/Shadower-Analytics/backend/src/services/exports/pdf_export.py` - PDF generation

### 5. Tasks & Jobs
- `/home/user/Shadower-Analytics/backend/src/celery_app.py` - Celery configuration
- `/home/user/Shadower-Analytics/backend/src/tasks/aggregation.py` - Async task pattern
- `/home/user/Shadower-Analytics/backend/src/tasks/maintenance.py` - Maintenance tasks

### 6. Caching
- `/home/user/Shadower-Analytics/backend/src/services/cache/__init__.py` - Cache exports
- `/home/user/Shadower-Analytics/backend/src/services/cache/redis_cache.py` - Cache service
- `/home/user/Shadower-Analytics/backend/src/services/cache/keys.py` - Cache key patterns

### 7. Utilities & Config
- `/home/user/Shadower-Analytics/backend/src/utils/validators.py` - Input validation patterns
- `/home/user/Shadower-Analytics/backend/src/core/config.py` - Settings & environment
- `/home/user/Shadower-Analytics/backend/src/core/database.py` - Database setup

### 8. Main Application
- `/home/user/Shadower-Analytics/backend/src/api/main.py` - FastAPI app registration

---

## Architecture at a Glance

```
HTTP Request
    ↓
@router.endpoint() [reports.py]
    ↓
Depends(get_current_user) → JWT validation
    ↓
Depends(get_db) → AsyncSession
    ↓
Service(db) → Business logic [reports_service.py]
    ↓
Database Query (ExecutionLog, ExecutionMetricsDaily, etc.)
    ↓
Format Response (Pydantic schema) → Return JSON
```

## Key Technologies Used

- **FastAPI**: Web framework with async support
- **SQLAlchemy**: ORM with async driver (asyncpg)
- **PostgreSQL**: Primary database
- **Redis**: Caching & Celery broker
- **Celery**: Task queue for async jobs
- **Pydantic**: Request/response validation
- **JWT**: Authentication tokens

## Common Patterns

1. **Route Pattern**: Endpoint → Service → Repository (DB)
2. **Auth Pattern**: HTTPBearer → JWT decode → User dict
3. **Database Pattern**: async_session → SQLAlchemy query → scalar/scalars
4. **Error Pattern**: Try/except → HTTPException with status code
5. **Pagination Pattern**: skip/limit queries → offset/limit
6. **Cache Pattern**: @cached decorator or CacheService.set/get
7. **Task Pattern**: @celery_app.task → AsyncDatabaseTask → asyncio.run()

---

## For Reports Implementation, You'll Need:

1. **Schemas**: Update/create comprehensive Report & ReportConfig in `common.py`
2. **Database**: Consider if you need a new `Report` table or use existing tables
3. **Service**: Create `services/reports_service.py` with:
   - create_report()
   - get_report()
   - list_reports()
   - update_report()
   - delete_report()
   - execute_report() or run_report()
4. **Routes**: Implement endpoints in `reports.py` using the service
5. **Tasks**: Optionally create `tasks/reports.py` for async report generation
6. **Exports**: Leverage existing export services for PDF/CSV generation

