# Reports API Implementation - Code Examples

This file contains copy-paste ready code examples following the project's patterns.

---

## 1. Schema Models (Update common.py)

```python
"""Common shared schemas - Update/extend this"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, List, Any
from datetime import datetime, date
from enum import Enum


class ReportStatusEnum(str, Enum):
    """Report status enumeration."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportFormatEnum(str, Enum):
    """Report format enumeration."""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    HTML = "html"


class ReportFrequencyEnum(str, Enum):
    """Report scheduling frequency."""
    ONE_TIME = "one_time"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ReportConfig(BaseModel):
    """Report configuration."""
    
    model_config = ConfigDict(from_attributes=True)
    
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    
    # Metrics to include
    metric_types: List[str] = Field(
        default=["executions", "users", "agents"],
        description="Types of metrics to include"
    )
    
    # Time range
    time_range: Optional[Dict[str, date]] = Field(
        None,
        description="start_date and end_date for the report"
    )
    
    # Filters (flexible JSON)
    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional filters (workspace_id, agent_id, etc.)"
    )
    
    # Output format
    format: ReportFormatEnum = Field(default=ReportFormatEnum.JSON)
    
    # Scheduling
    frequency: ReportFrequencyEnum = Field(default=ReportFrequencyEnum.ONE_TIME)
    
    # Schedule details (for recurring reports)
    schedule_time: Optional[str] = Field(None, description="HH:MM format for daily/weekly/monthly")
    schedule_day: Optional[int] = Field(None, description="Day of month (1-31) or day of week (0-6)")


class ReportBase(BaseModel):
    """Base report model."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    workspace_id: str
    name: str
    description: Optional[str] = None
    config: Dict[str, Any]
    status: ReportStatusEnum
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class ReportCreate(BaseModel):
    """Request model for creating a report."""
    
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    config: ReportConfig


class ReportUpdate(BaseModel):
    """Request model for updating a report."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    config: Optional[ReportConfig] = None


class Report(ReportBase):
    """Complete report response model."""
    
    last_generated_at: Optional[datetime] = None
    last_generated_by: Optional[str] = None
    next_scheduled_run: Optional[datetime] = None


class ReportResultBase(BaseModel):
    """Base model for report results/execution."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    report_id: str
    workspace_id: str
    generated_at: datetime
    generated_by: str
    status: ReportStatusEnum
    file_path: Optional[str] = None
    download_url: Optional[str] = None


class ReportResult(ReportResultBase):
    """Complete report result/execution response."""
    
    execution_time_seconds: Optional[float] = None
    file_size_bytes: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None


class ReportListResponse(BaseModel):
    """Paginated list of reports."""
    
    total: int
    skip: int
    limit: int
    data: List[Report]
```

---

## 2. Database Model (Add to tables.py)

```python
"""Add to models/database/tables.py"""

from uuid import uuid4
from sqlalchemy import Column, String, Integer, DateTime, JSON, Enum, Index, Boolean, Float
from sqlalchemy.sql import func


class Report(Base):
    """Reports table."""
    
    __tablename__ = "reports"
    __table_args__ = (
        Index('idx_reports_workspace', 'workspace_id'),
        Index('idx_reports_created_by', 'created_by'),
        Index('idx_reports_status', 'status'),
        Index('idx_reports_workspace_created', 'workspace_id', 'created_at'),
        {'schema': 'analytics'}
    )
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    workspace_id = Column(String, index=True, nullable=False)
    
    # Report metadata
    name = Column(String(255), nullable=False)
    description = Column(String)
    status = Column(String(20), nullable=False, default='draft')  # draft, scheduled, running, completed, failed
    
    # Configuration stored as JSON
    config = Column(JSON, nullable=False)
    
    # Scheduling information
    frequency = Column(String(20), default='one_time')  # one_time, daily, weekly, monthly
    schedule_time = Column(String(5))  # HH:MM format
    schedule_day = Column(Integer)  # Day of month or day of week
    next_scheduled_run = Column(DateTime)
    
    # Tracking
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    last_generated_at = Column(DateTime)
    last_generated_by = Column(String)


class ReportResult(Base):
    """Report generation results/execution history."""
    
    __tablename__ = "report_results"
    __table_args__ = (
        Index('idx_report_results_report', 'report_id'),
        Index('idx_report_results_workspace', 'workspace_id'),
        Index('idx_report_results_generated', 'generated_at'),
        Index('idx_report_results_status', 'status'),
        Index('idx_report_results_workspace_time', 'workspace_id', 'generated_at'),
        {'schema': 'analytics'}
    )
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    report_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)
    
    # Generation details
    generated_at = Column(DateTime, default=func.now())
    generated_by = Column(String, nullable=False)
    status = Column(String(20), nullable=False)  # completed, failed, expired
    
    # File information
    file_path = Column(String)  # S3 path or local path
    download_url = Column(String)
    file_format = Column(String(10), nullable=False)  # json, csv, pdf, html
    file_size_bytes = Column(Integer)
    
    # Execution metrics
    execution_time_seconds = Column(Float)
    
    # Error tracking
    error_message = Column(String)
    
    # Additional metadata
    metadata = Column(JSON)  # Any additional data about generation
    
    # Expiration
    expires_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
```

---

## 3. Service Implementation

```python
"""Create new file: services/analytics/reports_service.py"""

import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ReportService:
    """Service for managing custom reports."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_report(
        self,
        workspace_id: str,
        name: str,
        config: Dict[str, Any],
        created_by: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new report definition.
        
        Args:
            workspace_id: Workspace ID
            name: Report name
            config: Report configuration dict
            created_by: User ID who created the report
            description: Optional description
            
        Returns:
            Created report as dict
            
        Raises:
            ValueError: If validation fails
        """
        # Validate inputs
        if not workspace_id or not name or not created_by:
            raise ValueError("Missing required fields")
        
        try:
            from ...models.database.tables import Report
            
            report = Report(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                name=name,
                description=description,
                config=config,
                status='draft',
                created_by=created_by,
                frequency=config.get('frequency', 'one_time'),
                schedule_time=config.get('schedule_time'),
                schedule_day=config.get('schedule_day'),
            )
            
            self.db.add(report)
            await self.db.flush()
            await self.db.refresh(report)
            
            logger.info(f"Created report {report.id} in workspace {workspace_id}")
            
            return self._to_dict(report)
        
        except Exception as e:
            logger.error(f"Error creating report: {str(e)}", exc_info=True)
            await self.db.rollback()
            raise
    
    async def get_report(
        self,
        report_id: str,
        workspace_id: str,
    ) -> Dict[str, Any]:
        """Get a specific report by ID.
        
        Args:
            report_id: Report ID
            workspace_id: Workspace ID for authorization
            
        Returns:
            Report as dict
            
        Raises:
            ValueError: If report not found
        """
        from ...models.database.tables import Report
        
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
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List reports in a workspace.
        
        Args:
            workspace_id: Workspace ID
            skip: Number of results to skip
            limit: Maximum number of results
            status: Optional filter by status
            
        Returns:
            Paginated list of reports
        """
        from ...models.database.tables import Report
        
        # Count query
        count_query = select(func.count(Report.id)).where(
            Report.workspace_id == workspace_id
        )
        
        if status:
            count_query = count_query.where(Report.status == status)
        
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        # Data query
        data_query = (
            select(Report)
            .where(Report.workspace_id == workspace_id)
            .order_by(desc(Report.created_at))
            .offset(skip)
            .limit(limit)
        )
        
        if status:
            data_query = data_query.where(Report.status == status)
        
        result = await self.db.execute(data_query)
        reports = result.scalars().all()
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": [self._to_dict(r) for r in reports]
        }
    
    async def update_report(
        self,
        report_id: str,
        workspace_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a report.
        
        Args:
            report_id: Report ID
            workspace_id: Workspace ID for authorization
            name: Optional new name
            description: Optional new description
            config: Optional new config
            status: Optional new status
            
        Returns:
            Updated report as dict
            
        Raises:
            ValueError: If report not found
        """
        from ...models.database.tables import Report
        
        result = await self.db.execute(
            select(Report)
            .where(Report.id == report_id)
            .where(Report.workspace_id == workspace_id)
        )
        
        report = result.scalar_one_or_none()
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        # Update fields
        if name is not None:
            report.name = name
        if description is not None:
            report.description = description
        if config is not None:
            report.config = config
            report.frequency = config.get('frequency', report.frequency)
            report.schedule_time = config.get('schedule_time', report.schedule_time)
            report.schedule_day = config.get('schedule_day', report.schedule_day)
        if status is not None:
            report.status = status
        
        report.updated_at = datetime.utcnow()
        
        await self.db.flush()
        await self.db.refresh(report)
        
        logger.info(f"Updated report {report_id}")
        
        return self._to_dict(report)
    
    async def delete_report(
        self,
        report_id: str,
        workspace_id: str,
    ) -> bool:
        """Delete a report.
        
        Args:
            report_id: Report ID
            workspace_id: Workspace ID for authorization
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If report not found
        """
        from ...models.database.tables import Report, ReportResult
        
        result = await self.db.execute(
            select(Report)
            .where(Report.id == report_id)
            .where(Report.workspace_id == workspace_id)
        )
        
        report = result.scalar_one_or_none()
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        # Delete related results
        await self.db.execute(
            delete(ReportResult).where(ReportResult.report_id == report_id)
        )
        
        # Delete report
        await self.db.delete(report)
        await self.db.flush()
        
        logger.info(f"Deleted report {report_id}")
        
        return True
    
    async def generate_report(
        self,
        report_id: str,
        workspace_id: str,
        generated_by: str,
    ) -> Dict[str, Any]:
        """Generate/execute a report.
        
        This method orchestrates report generation:
        1. Fetch report definition
        2. Query required metrics
        3. Format data
        4. Generate output
        5. Store result
        
        Args:
            report_id: Report ID
            workspace_id: Workspace ID
            generated_by: User ID who triggered generation
            
        Returns:
            Report result as dict
            
        Raises:
            ValueError: If report not found
        """
        from ...models.database.tables import Report, ReportResult
        
        try:
            # Get report definition
            report = await self.get_report(report_id, workspace_id)
            
            # Fetch data based on report config
            report_data = await self._fetch_report_data(workspace_id, report['config'])
            
            # Generate output file based on format
            file_format = report['config'].get('format', 'json')
            file_content = await self._generate_output(file_format, report_data)
            
            # Store result
            result = ReportResult(
                id=str(uuid.uuid4()),
                report_id=report_id,
                workspace_id=workspace_id,
                generated_by=generated_by,
                status='completed',
                file_format=file_format,
                file_size_bytes=len(file_content.encode()) if isinstance(file_content, str) else len(file_content),
                metadata={"metrics_included": report['config'].get('metric_types', [])}
            )
            
            # Update report's last_generated fields
            db_report = await self.db.execute(
                select(Report).where(Report.id == report_id)
            )
            db_report_obj = db_report.scalar_one()
            db_report_obj.last_generated_at = datetime.utcnow()
            db_report_obj.last_generated_by = generated_by
            
            self.db.add(result)
            await self.db.flush()
            await self.db.refresh(result)
            
            logger.info(f"Generated report {report_id}")
            
            return self._result_to_dict(result)
        
        except Exception as e:
            logger.error(f"Error generating report {report_id}: {str(e)}", exc_info=True)
            # TODO: Store error result in database
            raise
    
    async def _fetch_report_data(
        self,
        workspace_id: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Fetch data for report based on configuration.
        
        This method queries the database for metrics specified in config.
        """
        from ...models.database.tables import ExecutionMetricsDaily, ExecutionLog
        
        metric_types = config.get('metric_types', [])
        time_range = config.get('time_range', {})
        filters = config.get('filters', {})
        
        start_date = time_range.get('start_date', date.today() - timedelta(days=30))
        end_date = time_range.get('end_date', date.today())
        
        data = {}
        
        # Query daily execution metrics
        if 'executions' in metric_types:
            result = await self.db.execute(
                select(ExecutionMetricsDaily)
                .where(ExecutionMetricsDaily.workspace_id == workspace_id)
                .where(ExecutionMetricsDaily.date >= start_date)
                .where(ExecutionMetricsDaily.date <= end_date)
                .order_by(ExecutionMetricsDaily.date)
            )
            
            metrics = result.scalars().all()
            data['executions'] = [
                {
                    'date': m.date,
                    'total_executions': m.total_executions,
                    'successful_executions': m.successful_executions,
                    'failed_executions': m.failed_executions,
                    'success_rate': m.total_executions and (m.successful_executions / m.total_executions * 100),
                    'avg_runtime': m.avg_runtime,
                }
                for m in metrics
            ]
        
        # TODO: Add more metric types (users, agents, etc.)
        
        return data
    
    async def _generate_output(
        self,
        format: str,
        data: Dict[str, Any],
    ) -> Any:
        """Generate output in specified format.
        
        Args:
            format: Output format (json, csv, pdf, html)
            data: Data to format
            
        Returns:
            Formatted output (str for text, bytes for binary)
        """
        if format == 'json':
            import json
            return json.dumps(data, default=str)
        
        elif format == 'csv':
            from ...services.exports.csv_export import export_to_csv
            # Flatten data for CSV
            rows = []
            for metric_type, values in data.items():
                if isinstance(values, list):
                    rows.extend(values)
            return export_to_csv(rows)
        
        elif format == 'pdf':
            from ...services.exports.pdf_export import generate_pdf_report
            return await generate_pdf_report(data, template='default')
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _to_dict(self, report) -> Dict[str, Any]:
        """Convert Report ORM to dict."""
        return {
            "id": report.id,
            "workspace_id": report.workspace_id,
            "name": report.name,
            "description": report.description,
            "config": report.config,
            "status": report.status,
            "created_by": report.created_by,
            "created_at": report.created_at,
            "updated_at": report.updated_at,
            "last_generated_at": report.last_generated_at,
            "last_generated_by": report.last_generated_by,
        }
    
    def _result_to_dict(self, result) -> Dict[str, Any]:
        """Convert ReportResult ORM to dict."""
        return {
            "id": result.id,
            "report_id": result.report_id,
            "workspace_id": result.workspace_id,
            "generated_at": result.generated_at,
            "generated_by": result.generated_by,
            "status": result.status,
            "file_path": result.file_path,
            "download_url": result.download_url,
            "file_format": result.file_format,
            "file_size_bytes": result.file_size_bytes,
            "execution_time_seconds": result.execution_time_seconds,
            "error_message": result.error_message,
            "metadata": result.metadata,
        }
```

---

## 4. Route Implementation

```python
"""Update backend/src/api/routes/reports.py"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Body, HTTPException, status
from datetime import date
import logging

from ...core.database import get_db
from ...models.schemas.common import (
    Report,
    ReportCreate,
    ReportUpdate,
    ReportListResponse,
    ReportResult,
    ReportStatusEnum,
)
from ...services.analytics.reports_service import ReportService
from ..dependencies.auth import get_current_user, require_admin
from ...utils.validators import validate_workspace_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/", response_model=ReportListResponse)
async def list_reports(
    workspace_id: str = Query(..., description="Workspace ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="Filter by status"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List all reports in a workspace.
    
    Requires authentication.
    """
    try:
        # Validate workspace ID
        validated_workspace_id = validate_workspace_id(workspace_id)
        
        logger.info(
            f"Listing reports for workspace {validated_workspace_id} "
            f"(user: {current_user.get('user_id')})"
        )
        
        service = ReportService(db)
        result = await service.list_reports(
            workspace_id=validated_workspace_id,
            skip=skip,
            limit=limit,
            status=status,
        )
        
        return result
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error listing reports: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list reports",
        )


@router.post("/", response_model=Report)
async def create_report(
    workspace_id: str = Query(...),
    report_data: ReportCreate = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a new custom report.
    
    Requires authentication.
    """
    try:
        validated_workspace_id = validate_workspace_id(workspace_id)
        
        logger.info(
            f"Creating report '{report_data.name}' in workspace {validated_workspace_id} "
            f"(user: {current_user.get('user_id')})"
        )
        
        service = ReportService(db)
        report = await service.create_report(
            workspace_id=validated_workspace_id,
            name=report_data.name,
            description=report_data.description,
            config=report_data.config.dict(),
            created_by=current_user.get("user_id"),
        )
        
        return report
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create report",
        )


@router.get("/{report_id}", response_model=Report)
async def get_report(
    report_id: str,
    workspace_id: str = Query(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get a specific report.
    
    Requires authentication.
    """
    try:
        validated_workspace_id = validate_workspace_id(workspace_id)
        
        logger.info(
            f"Fetching report {report_id} in workspace {validated_workspace_id} "
            f"(user: {current_user.get('user_id')})"
        )
        
        service = ReportService(db)
        report = await service.get_report(
            report_id=report_id,
            workspace_id=validated_workspace_id,
        )
        
        return report
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error fetching report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch report",
        )


@router.put("/{report_id}", response_model=Report)
async def update_report(
    report_id: str,
    workspace_id: str = Query(...),
    report_data: ReportUpdate = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update a report configuration.
    
    Requires authentication.
    """
    try:
        validated_workspace_id = validate_workspace_id(workspace_id)
        
        logger.info(
            f"Updating report {report_id} in workspace {validated_workspace_id} "
            f"(user: {current_user.get('user_id')})"
        )
        
        service = ReportService(db)
        report = await service.update_report(
            report_id=report_id,
            workspace_id=validated_workspace_id,
            name=report_data.name,
            description=report_data.description,
            config=report_data.config.dict() if report_data.config else None,
        )
        
        return report
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update report",
        )


@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    workspace_id: str = Query(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete a report.
    
    Requires authentication.
    """
    try:
        validated_workspace_id = validate_workspace_id(workspace_id)
        
        logger.info(
            f"Deleting report {report_id} in workspace {validated_workspace_id} "
            f"(user: {current_user.get('user_id')})"
        )
        
        service = ReportService(db)
        await service.delete_report(
            report_id=report_id,
            workspace_id=validated_workspace_id,
        )
        
        return {"success": True, "message": "Report deleted successfully"}
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error deleting report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete report",
        )


@router.post("/{report_id}/generate", response_model=ReportResult)
async def generate_report(
    report_id: str,
    workspace_id: str = Query(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Execute/generate a report and get results.
    
    Requires authentication. For long-running reports, consider using
    a background task or Celery job and returning a task ID.
    """
    try:
        validated_workspace_id = validate_workspace_id(workspace_id)
        
        logger.info(
            f"Generating report {report_id} in workspace {validated_workspace_id} "
            f"(user: {current_user.get('user_id')})"
        )
        
        service = ReportService(db)
        result = await service.generate_report(
            report_id=report_id,
            workspace_id=validated_workspace_id,
            generated_by=current_user.get("user_id"),
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report",
        )
```

---

## Summary

This implementation provides:

1. **Schemas**: Comprehensive Pydantic models for requests/responses
2. **Database Models**: Tables for reports and results with proper indexing
3. **Service Layer**: Business logic with error handling and logging
4. **API Routes**: Full CRUD endpoints with authentication and validation

Key patterns followed:
- Async/await for all I/O operations
- Dependency injection for database and auth
- Structured error handling with HTTPException
- Input validation using validators
- Comprehensive logging
- Service layer separation from routes
- Type hints throughout

Next steps:
1. Add database migration using Alembic
2. Implement Celery tasks for async report generation
3. Add caching for frequently accessed reports
4. Implement file storage (S3 or local filesystem)
5. Add tests for all endpoints
6. Consider webhook notifications for report completion

