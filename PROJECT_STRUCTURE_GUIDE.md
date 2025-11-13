# Shadower Analytics - Project Structure & Implementation Guide

## Project Overview

This is a FastAPI-based analytics platform with:
- **Backend**: FastAPI service with async database operations
- **Database**: PostgreSQL with SQLAlchemy ORM (async)
- **Task Queue**: Celery for background jobs
- **Caching**: Redis with custom cache service
- **Authentication**: JWT-based with Supabase integration

---

## 1. API STRUCTURE

### Location: `/backend/src/api/`

**Key Files:**
- `main.py` - FastAPI application setup with all routers registered
- `routes/` - Individual endpoint modules for each feature
- `dependencies/` - Shared dependency functions (auth, db, cache)
- `middleware/` - Global and feature-specific middleware
- `websocket/` - Real-time WebSocket support

### Router Pattern
```python
# Location: backend/src/api/routes/[feature].py
from fastapi import APIRouter, Depends, Query, Body
from ...core.database import get_db
from ..dependencies.auth import get_current_user

router = APIRouter(prefix="/api/v1/[feature]", tags=["[feature]"])

@router.get("/")
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db=Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Endpoint description."""
    # Implementation
    return {}
```

### Current Routes
- `/api/v1/agents` - Agent analytics
- `/api/v1/metrics` - General metrics
- `/api/v1/exports` - Data export (CSV, PDF, JSON)
- `/api/v1/reports` - **Custom reports** (currently skeleton)
- `/api/v1/funnels` - Funnel analysis
- `/api/v1/anomalies` - Anomaly detection
- `/api/v1/leaderboards` - Rankings
- `/api/v1/executive` - Executive dashboard
- And more...

---

## 2. MODELS & SCHEMAS

### Database Models
**Location**: `/backend/src/models/database/tables.py`

Key tables for Reports implementation:
```python
class ExecutionLog(Base):
    """Contains execution details with filters and metadata"""
    agent_id, user_id, workspace_id, status, duration, credits_used, metadata

class ExecutionMetricsDaily(Base):
    """Daily aggregated metrics"""
    workspace_id, date, total_executions, success_rate, etc.

class ExecutionMetricsHourly(Base):
    """Hourly aggregated metrics"""
    Similar to daily but at hourly granularity

class AnomalyDetection(Base):
    """Anomaly detection data"""
    workspace_id, metric_type, severity, context, etc.
```

### Pydantic Schemas (Request/Response)
**Location**: `/backend/src/models/schemas/`

Current schemas:
- `common.py` - Contains basic `Report` and `ReportConfig` schemas (incomplete)
- `metrics.py` - Metric-related schemas (TimeRange, ExecutionMetrics, UserMetrics, etc.)
- `agent_analytics.py` - Agent-specific analytics schemas
- `anomalies.py` - Anomaly detection schemas

### Schema Pattern
```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ReportSchema(BaseModel):
    """Report response model."""
    id: str
    workspace_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True  # For SQLAlchemy models
```

---

## 3. AUTHENTICATION & DEPENDENCIES

### Authentication Flow
**Location**: `/backend/src/api/dependencies/auth.py` & `/backend/src/api/middleware/auth.py`

```python
# JWT-based authentication using HTTPBearer
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Returns: user_id, email, workspace_id, workspaces, role, permissions"""

async def get_current_active_user(
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Checks if user is active"""

async def require_admin(
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Requires admin or owner role"""

async def require_owner_or_admin(
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Requires owner or admin role"""
```

### Token Structure
```python
{
    "sub": "user_id",
    "email": "user@example.com",
    "workspaceId": "workspace_uuid",
    "workspaces": ["ws1", "ws2"],
    "role": "owner|admin|member",
    "permissions": ["read:reports", "write:reports"],
    "exp": expiration_timestamp
}
```

### Database Dependency
```python
from ...core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Async database session with auto-rollback on error"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Workspace Validation
```python
from ...middleware.workspace import WorkspaceAccess

# In routes:
await WorkspaceAccess.validate_workspace_access(current_user, workspace_id)
# OR
workspace_access=Depends(validate_workspace_access)  # Direct dependency
```

---

## 4. JOB QUEUES & ASYNC TASKS

### Celery Configuration
**Location**: `/backend/src/celery_app.py`

```python
celery_app = Celery(
    'shadower_analytics',
    broker=settings.CELERY_BROKER_URL,  # Redis
    backend=settings.CELERY_RESULT_BACKEND,  # Redis
    include=['src.tasks.aggregation', 'src.tasks.maintenance']
)
```

### Task Pattern
**Location**: `/backend/src/tasks/aggregation.py`

```python
from src.celery_app import celery_app
from src.core.database import async_session_maker

@celery_app.task(
    name='tasks.aggregation.hourly_rollup',
    bind=True,
    base=AsyncDatabaseTask,
    max_retries=3,
    default_retry_delay=300,
)
def hourly_rollup_task(self, target_hour: Optional[str] = None) -> Dict:
    """Celery task for periodic aggregation.
    
    Args:
        target_hour: ISO format datetime string (optional)
    
    Returns:
        Dictionary with task results
    """
    try:
        async def run_rollup():
            async with async_session_maker() as db:
                return await hourly_rollup(db, target_datetime)
        
        result = self.run_async(run_rollup)
        return result
    except Exception as exc:
        raise self.retry(exc=exc)
```

### Periodic Tasks (Beat Schedule)
```python
celery_app.conf.beat_schedule = {
    'hourly-rollup': {
        'task': 'tasks.aggregation.hourly_rollup',
        'schedule': crontab(minute=5),  # 5 minutes past each hour
        'options': {'expires': 3600}
    },
    'daily-rollup': {
        'task': 'tasks.aggregation.daily_rollup',
        'schedule': crontab(hour=1, minute=0),  # 1 AM daily
        'options': {'expires': 7200}
    },
    # ... more scheduled tasks
}
```

### Background Tasks in Routes
```python
from fastapi import BackgroundTasks

@router.post("/generate")
async def generate_report(
    report_id: str,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
):
    """Trigger async report generation."""
    background_tasks.add_task(
        generate_pdf_report,
        report_id=report_id,
        db=db
    )
    return {"report_id": report_id, "status": "processing"}
```

---

## 5. FILE STORAGE & EXPORTS

### Export Service Pattern
**Location**: `/backend/src/services/exports/`

**CSV Export**:
```python
def export_to_csv(data: List[Dict], columns: List[str] = None) -> str:
    """Returns CSV string (can stream to file)"""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for row in data:
        writer.writerow(...)
    return output.getvalue()
```

**PDF Export**:
```python
async def generate_pdf_report(
    report_data: Dict,
    template: str = "default",
) -> bytes:
    """Returns PDF bytes (can be saved to disk or S3)"""
    # Implementation uses reportlab or weasyprint
    return pdf_bytes
```

**JSON Export**:
```python
async def export_to_json(...) -> Dict:
    """Returns JSON-serializable data"""
```

### Suggested Implementation
- **S3/Cloud Storage**: For generated reports (PDFs, large exports)
- **Redis**: For temporary export status tracking
- **File System**: Local storage during development
- **Streaming**: For large CSV exports (StreamingResponse)

---

## 6. CACHING STRATEGY

### Redis Cache Service
**Location**: `/backend/src/services/cache/`

```python
from ...services.cache import cached, CacheKeys

# Using cache decorator
@cached(key_generator=CacheKeys.agent_metrics, ttl=3600)
async def get_agent_metrics(agent_id: str, workspace_id: str):
    """Automatically cached for 1 hour"""
    return metrics

# Or manual cache
from ...core.redis import RedisClient

cache_service = CacheService(redis_client)
await cache_service.set("key", value, ttl=3600)
value = await cache_service.get("key")
```

### Cache Invalidation
```python
from ...services.cache import invalidate_pattern, invalidate_metric_cache

# Invalidate specific patterns
await invalidate_pattern("metrics:*")
await invalidate_metric_cache(metric_type="executions")
```

---

## 7. SERVICE LAYER PATTERN

### Service Class Structure
**Location**: `/backend/src/services/[category]/[feature]_service.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Any

class ReportService:
    """Business logic for reports."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_report(
        self,
        workspace_id: str,
        name: str,
        config: Dict[str, Any],
        created_by: str,
    ) -> Dict[str, Any]:
        """Create a new report definition."""
        # Validation
        if not workspace_id or not name:
            raise ValueError("Missing required fields")
        
        # Database operations
        report = Report(
            workspace_id=workspace_id,
            name=name,
            config=config,
            created_by=created_by,
        )
        self.db.add(report)
        await self.db.flush()
        await self.db.refresh(report)
        
        return {
            "id": report.id,
            "workspace_id": report.workspace_id,
            "name": report.name,
            # ... more fields
        }
    
    async def get_report(self, report_id: str, workspace_id: str) -> Dict:
        """Fetch a report by ID."""
        result = await self.db.execute(
            select(Report)
            .where(Report.id == report_id)
            .where(Report.workspace_id == workspace_id)
        )
        report = result.scalar_one_or_none()
        if not report:
            raise ValueError(f"Report {report_id} not found")
        return self._to_dict(report)
    
    async def list_reports(
        self,
        workspace_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """List reports with pagination."""
        # Query and return paginated results
        pass
    
    async def delete_report(self, report_id: str, workspace_id: str) -> bool:
        """Delete a report."""
        pass
    
    def _to_dict(self, report: Report) -> Dict:
        """Convert ORM model to dictionary."""
        return {
            "id": report.id,
            "workspace_id": report.workspace_id,
            "name": report.name,
            "created_at": report.created_at,
            # ... more fields
        }
```

### Service Usage in Routes
```python
@router.post("/", response_model=ReportSchema)
async def create_report(
    workspace_id: str = Query(...),
    config: ReportConfigSchema = Body(...),
    db=Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Create a new report."""
    service = ReportService(db)
    
    report = await service.create_report(
        workspace_id=workspace_id,
        name=config.name,
        config=config.dict(),
        created_by=current_user["user_id"],
    )
    
    return report
```

---

## 8. EXISTING REPORT SKELETON

### Current State
**Location**: `/backend/src/api/routes/reports.py`

```python
router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

@router.get("/")  # List reports
@router.post("/")  # Create report
@router.get("/{report_id}")  # Get report
@router.put("/{report_id}")  # Update report
@router.delete("/{report_id}")  # Delete report
@router.post("/{report_id}/run")  # Execute/generate report
```

**Schemas**: Located in `/backend/src/models/schemas/common.py`
- `Report` - Report model
- `ReportConfig` - Report configuration

---

## 9. INPUT VALIDATION

### Validators
**Location**: `/backend/src/utils/validators.py`

```python
# Validate IDs
validate_workspace_id(workspace_id: str) -> str
validate_agent_id(agent_id: str) -> str
validate_user_id(user_id: str) -> str

# Validate date ranges
validate_date_range(start_date: date, end_date: date) -> bool

# Validate timeframes
validate_timeframe(timeframe: str) -> bool  # 7d, 30d, 90d, 1y

# HTML sanitization
sanitize_html_content(content: str, max_length: int) -> str

# Pagination
validate_pagination(skip: int, limit: int) -> bool
```

---

## 10. CONFIGURATION

### Settings
**Location**: `/backend/src/core/config.py`

```python
class Settings(BaseSettings):
    # Database
    DATABASE_URL: str  # PostgreSQL async connection string
    DB_POOL_SIZE: int = 20
    
    # Redis/Celery
    REDIS_URL: str  # Must be set in environment
    CELERY_BROKER_URL: str  # Usually Redis
    CELERY_RESULT_BACKEND: str  # Usually Redis
    
    # JWT/Auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # Feature Flags
    ENABLE_REALTIME: bool = True
    ENABLE_ALERTS: bool = True
    ENABLE_EXPORTS: bool = True
    
    # Aggregation
    HOURLY_ROLLUP_ENABLED: bool = True
    DAILY_ROLLUP_ENABLED: bool = True
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
```

---

## 11. KEY DESIGN PATTERNS

### 1. Dependency Injection
```python
async def endpoint(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    pass
```

### 2. Async-First
- All database operations are async (async_session_maker)
- All I/O is async (await)
- Task queue uses async tasks with proper event loop handling

### 3. Error Handling
```python
from fastapi import HTTPException
from sqlalchemy import select

try:
    result = await db.execute(query)
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=404,
            detail="Item not found"
        )
except Exception as e:
    logger.error(f"Error: {str(e)}", exc_info=True)
    raise HTTPException(
        status_code=500,
        detail="Internal server error"
    )
```

### 4. Pagination
```python
skip: int = Query(0, ge=0)
limit: int = Query(100, ge=1, le=1000)

results = await db.execute(
    select(Model)
    .offset(skip)
    .limit(limit)
)
```

### 5. Query Patterns
```python
# Single result
result = await db.execute(
    select(Model).where(Model.id == id)
)
item = result.scalar_one_or_none()

# Multiple results
result = await db.execute(
    select(Model)
    .where(Model.workspace_id == workspace_id)
    .order_by(Model.created_at.desc())
)
items = result.scalars().all()

# With aggregations
result = await db.execute(
    select(func.count(Model.id))
    .where(Model.status == "success")
)
count = result.scalar()
```

---

## 12. RECOMMENDED IMPLEMENTATION STRUCTURE

For implementing the Reports API endpoints:

```
backend/src/
├── api/
│   └── routes/
│       └── reports.py  ← Main endpoints
├── models/
│   ├── database/
│   │   └── tables.py  ← Add Report table if needed
│   └── schemas/
│       └── common.py  ← Update Report schemas
├── services/
│   └── [new folder]/
│       └── reports_service.py  ← Business logic
├── tasks/
│   └── [new if needed]/
│       └── reports.py  ← Celery tasks
└── utils/
    └── [add validators if needed]
```

---

## 13. DATABASE CONNECTION EXAMPLE

```python
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ...models.database.tables import ExecutionLog

async def get_execution_summary(
    db: AsyncSession,
    workspace_id: str,
    start_date: datetime,
    end_date: datetime,
):
    """Example: Query execution logs."""
    result = await db.execute(
        select(
            func.count(ExecutionLog.id).label("total"),
            func.sum(ExecutionLog.credits_used).label("credits"),
            func.avg(ExecutionLog.duration).label("avg_duration"),
        )
        .where(ExecutionLog.workspace_id == workspace_id)
        .where(ExecutionLog.started_at >= start_date)
        .where(ExecutionLog.started_at <= end_date)
    )
    
    row = result.first()
    return {
        "total_executions": row.total or 0,
        "total_credits": row.credits or 0,
        "avg_duration": float(row.avg_duration) if row.avg_duration else 0,
    }
```

