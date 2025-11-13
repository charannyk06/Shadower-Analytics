"""Report generation and management routes."""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import FileResponse
from datetime import datetime

from ...core.database import get_db
from ...services.reports import ReportService
from ...models.schemas.reports import (
    ReportConfigRequest,
    ReportJobResponse,
    ReportJobStatusResponse,
    TemplatesListResponse,
    CreateTemplateRequest,
    CreateTemplateResponse,
    CreateScheduleRequest,
    CreateScheduleResponse,
    SchedulesListResponse,
    ReportHistoryResponse,
    DataExportRequest,
    DataExportResponse,
    ShareReportRequest,
    ShareReportResponse,
    ReportAnalyticsResponse,
    WebhookRequest,
    WebhookResponse,
)
from ..dependencies.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


# ============================================================================
# Report Generation Endpoints
# ============================================================================

@router.post("/generate", response_model=ReportJobResponse)
async def generate_report(
    workspace_id: str = Query(..., description="Workspace ID"),
    config: ReportConfigRequest = ...,
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Generate a custom report.

    Creates a report generation job that processes asynchronously.
    The job can be tracked using the returned tracking URL.

    ## Parameters
    - **workspace_id**: ID of the workspace to generate report for
    - **config**: Report configuration including:
      - **name**: Report name
      - **template_id**: Optional template to use
      - **format**: Output format (pdf, excel, csv, json)
      - **sections**: Report sections to include
      - **date_range**: Date range for data
      - **filters**: Optional filters (agents, users, etc.)
      - **delivery**: Delivery configuration

    ## Returns
    - **job_id**: Unique job identifier
    - **status**: Current job status (queued)
    - **estimated_completion**: Estimated seconds until completion
    - **tracking_url**: URL to check job status

    ## Example
    ```json
    {
      "name": "Monthly Analytics Report",
      "template_id": "template_123",
      "format": "pdf",
      "sections": ["executive_summary", "user_analytics"],
      "date_range": {
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-31T23:59:59Z"
      },
      "filters": {
        "agents": ["agent_123"]
      },
      "delivery": {
        "method": "email",
        "recipients": ["admin@company.com"]
      }
    }
    ```
    """
    try:
        user_id = current_user.get("user_id")
        service = ReportService(db)

        result = await service.create_report_job(workspace_id, user_id, config)

        return ReportJobResponse(**result)

    except ValueError as e:
        logger.warning(f"Invalid report configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create report generation job"
        )


@router.get("/jobs/{job_id}", response_model=ReportJobStatusResponse)
async def get_report_job_status(
    job_id: str,
    workspace_id: str = Query(..., description="Workspace ID"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Check report generation job status.

    ## Parameters
    - **job_id**: Job ID from the generate_report response
    - **workspace_id**: Workspace ID for access control

    ## Returns
    - **job_id**: Job identifier
    - **status**: Current status (queued, processing, completed, failed)
    - **progress**: Progress percentage (0-100)
    - **current_section**: Section currently being processed
    - **completed_at**: Completion timestamp (if completed)
    - **download_url**: Download URL (if completed)
    - **error**: Error message (if failed)
    - **metadata**: Additional metadata (file size, page count, etc.)
    """
    try:
        service = ReportService(db)
        result = await service.get_report_job_status(job_id, workspace_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report job not found"
            )

        return ReportJobStatusResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job status"
        )


# ============================================================================
# Template Endpoints
# ============================================================================

@router.get("/templates", response_model=TemplatesListResponse)
async def get_report_templates(
    workspace_id: Optional[str] = Query(None, description="Workspace ID for custom templates"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    List available report templates.

    Returns both global templates and workspace-specific custom templates.

    ## Parameters
    - **workspace_id**: Optional workspace ID to include custom templates
    - **category**: Optional category filter (executive, operational, technical, financial)

    ## Returns
    List of templates with:
    - **id**: Template ID
    - **name**: Template name
    - **description**: Template description
    - **category**: Template category
    - **sections**: Available sections
    - **formats**: Supported output formats
    - **is_custom**: Whether it's a custom template
    - **preview_url**: URL to preview the template
    """
    try:
        service = ReportService(db)
        templates = await service.get_templates(workspace_id, category)

        return TemplatesListResponse(templates=templates)

    except Exception as e:
        logger.error(f"Error getting templates: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve templates"
        )


@router.post("/templates", response_model=CreateTemplateResponse)
async def create_custom_template(
    workspace_id: str = Query(..., description="Workspace ID"),
    template_config: CreateTemplateRequest = ...,
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Create custom report template.

    ## Parameters
    - **workspace_id**: Workspace ID
    - **template_config**: Template configuration including:
      - **name**: Template name
      - **description**: Optional description
      - **sections**: Array of section definitions
      - **layout**: Optional layout configuration

    ## Example
    ```json
    {
      "name": "Custom Weekly Report",
      "description": "Weekly performance metrics",
      "sections": [
        {
          "type": "chart",
          "title": "User Growth",
          "metric": "active_users",
          "visualization": "line_chart"
        },
        {
          "type": "table",
          "title": "Top Agents",
          "data_source": "agent_performance",
          "columns": ["name", "executions", "success_rate"]
        }
      ],
      "layout": {
        "orientation": "portrait",
        "margins": {"top": 1, "bottom": 1, "left": 1, "right": 1}
      }
    }
    ```
    """
    try:
        user_id = current_user.get("user_id")
        service = ReportService(db)

        template_id = await service.create_template(workspace_id, user_id, template_config)

        return CreateTemplateResponse(template_id=template_id, status="created")

    except ValueError as e:
        logger.warning(f"Invalid template configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating template: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create template"
        )


# ============================================================================
# Scheduled Reports Endpoints
# ============================================================================

@router.get("/scheduled", response_model=SchedulesListResponse)
async def get_scheduled_reports(
    workspace_id: str = Query(..., description="Workspace ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    List scheduled reports for workspace.

    ## Parameters
    - **workspace_id**: Workspace ID
    - **is_active**: Optional filter for active/inactive schedules

    ## Returns
    List of scheduled reports with:
    - **id**: Schedule ID
    - **name**: Schedule name
    - **template_id**: Template being used
    - **frequency**: Schedule frequency (daily, weekly, monthly, quarterly)
    - **schedule**: Schedule configuration (time, timezone, etc.)
    - **recipients**: List of recipients
    - **is_active**: Whether schedule is active
    - **last_run**: Last execution timestamp
    - **next_run**: Next scheduled execution
    """
    try:
        service = ReportService(db)
        schedules = await service.get_schedules(workspace_id, is_active)

        return SchedulesListResponse(schedules=schedules)

    except Exception as e:
        logger.error(f"Error getting schedules: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve schedules"
        )


@router.post("/scheduled", response_model=CreateScheduleResponse)
async def create_scheduled_report(
    workspace_id: str = Query(..., description="Workspace ID"),
    schedule_config: CreateScheduleRequest = ...,
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Create scheduled report.

    ## Parameters
    - **workspace_id**: Workspace ID
    - **schedule_config**: Schedule configuration including:
      - **name**: Schedule name
      - **template_id**: Template to use
      - **frequency**: Frequency (daily, weekly, monthly, quarterly)
      - **schedule**: Schedule details (time, timezone, etc.)
      - **recipients**: Recipients configuration
      - **filters**: Optional data filters

    ## Example
    ```json
    {
      "name": "Daily Analytics Digest",
      "template_id": "template_daily",
      "frequency": "daily",
      "schedule": {
        "time": "08:00",
        "timezone": "UTC"
      },
      "recipients": {
        "emails": ["admin@company.com"],
        "slack_channels": ["#analytics"]
      }
    }
    ```
    """
    try:
        user_id = current_user.get("user_id")
        service = ReportService(db)

        result = await service.create_schedule(workspace_id, user_id, schedule_config)

        return CreateScheduleResponse(**result)

    except ValueError as e:
        logger.warning(f"Invalid schedule configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating schedule: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create schedule"
        )


# ============================================================================
# Report History Endpoints
# ============================================================================

@router.get("/history", response_model=ReportHistoryResponse)
async def get_report_history(
    workspace_id: str = Query(..., description="Workspace ID"),
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Pagination limit"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get historical reports.

    ## Parameters
    - **workspace_id**: Workspace ID
    - **report_type**: Optional type filter (scheduled, manual, ad-hoc)
    - **start_date**: Optional start date filter
    - **end_date**: Optional end date filter
    - **skip**: Pagination offset
    - **limit**: Pagination limit (max 1000)

    ## Returns
    Paginated list of historical reports with:
    - **id**: Report ID
    - **name**: Report name
    - **type**: Report type
    - **generated_at**: Generation timestamp
    - **generated_by**: User who generated the report
    - **format**: File format
    - **file_size**: File size in bytes
    - **page_count**: Number of pages
    - **download_url**: URL to download the report
    - **expires_at**: Expiration timestamp
    """
    try:
        service = ReportService(db)
        result = await service.get_report_history(
            workspace_id, report_type, start_date, end_date, skip, limit
        )

        return ReportHistoryResponse(**result)

    except Exception as e:
        logger.error(f"Error getting report history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve report history"
        )


# ============================================================================
# Export Endpoints
# ============================================================================

@router.post("/export/data", response_model=DataExportResponse)
async def export_raw_data(
    workspace_id: str = Query(..., description="Workspace ID"),
    export_config: DataExportRequest = ...,
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Export raw data for external analysis.

    ## Parameters
    - **workspace_id**: Workspace ID
    - **export_config**: Export configuration including:
      - **data_sources**: Data sources to export
      - **format**: Export format (csv, json, parquet)
      - **date_range**: Date range for data
      - **compression**: Compression type (none, gzip, zip)
      - **include_metadata**: Whether to include metadata

    ## Example
    ```json
    {
      "data_sources": [
        "user_activity",
        "agent_performance",
        "credit_consumption"
      ],
      "format": "csv",
      "date_range": {
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-31T23:59:59Z"
      },
      "compression": "gzip",
      "include_metadata": true
    }
    ```
    """
    try:
        user_id = current_user.get("user_id")
        service = ReportService(db)

        result = await service.create_data_export_job(workspace_id, user_id, export_config)

        return DataExportResponse(**result)

    except ValueError as e:
        logger.warning(f"Invalid export configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating export job: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create export job"
        )


@router.get("/download/{report_id}")
async def download_report(
    report_id: str,
    workspace_id: str = Query(..., description="Workspace ID"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Download generated report file.

    ## Parameters
    - **report_id**: Report ID
    - **workspace_id**: Workspace ID for access control

    ## Returns
    File download response with appropriate headers

    ## Errors
    - **403**: Access denied
    - **404**: Report not found
    - **410**: Report has expired
    """
    try:
        service = ReportService(db)
        report = await service.get_report_for_download(report_id, workspace_id)

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found or has expired"
            )

        # In production, this would return the actual file
        # For now, return a placeholder response
        return {
            "message": "Download endpoint - would return file",
            "report_id": report_id,
            "file_path": report.get("file_path")
        }

        # Actual implementation would be:
        # return FileResponse(
        #     path=report["file_path"],
        #     filename=report["filename"],
        #     media_type=report["content_type"],
        #     headers={"Content-Disposition": f"attachment; filename={report['filename']}"}
        # )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download report"
        )


# ============================================================================
# Report Sharing Endpoints
# ============================================================================

@router.post("/{report_id}/share", response_model=ShareReportResponse)
async def share_report(
    report_id: str,
    workspace_id: str = Query(..., description="Workspace ID"),
    share_config: ShareReportRequest = ...,
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Share report with external users.

    ## Parameters
    - **report_id**: Report ID to share
    - **workspace_id**: Workspace ID
    - **share_config**: Share configuration including:
      - **recipients**: List of email addresses
      - **message**: Optional message
      - **expiration_days**: Days until link expires (1-90)
      - **require_password**: Whether to require password
      - **allow_download**: Whether to allow downloads

    ## Example
    ```json
    {
      "recipients": ["external@client.com"],
      "message": "Please find attached the monthly report",
      "expiration_days": 7,
      "require_password": true,
      "allow_download": true
    }
    ```
    """
    try:
        user_id = current_user.get("user_id")
        service = ReportService(db)

        result = await service.create_share_link(report_id, workspace_id, user_id, share_config)

        return ShareReportResponse(**result)

    except ValueError as e:
        logger.warning(f"Invalid share configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error sharing report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create share link"
        )


# ============================================================================
# Report Analytics Endpoints
# ============================================================================

@router.get("/analytics", response_model=ReportAnalyticsResponse)
async def get_report_analytics(
    workspace_id: str = Query(..., description="Workspace ID"),
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Analytics about report usage.

    ## Parameters
    - **workspace_id**: Workspace ID
    - **start_date**: Start date for analytics period
    - **end_date**: End date for analytics period

    ## Returns
    Report usage analytics including:
    - **total_generated**: Total reports generated
    - **total_views**: Total report views
    - **total_downloads**: Total downloads
    - **avg_generation_time**: Average generation time in seconds
    - **most_popular**: Most popular templates
    - **by_format**: Usage breakdown by format
    - **by_user**: Usage breakdown by user
    """
    try:
        service = ReportService(db)
        result = await service.get_report_analytics(workspace_id, start_date, end_date)

        return ReportAnalyticsResponse(**result)

    except Exception as e:
        logger.error(f"Error getting report analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics"
        )


# ============================================================================
# Webhook Endpoints
# ============================================================================

@router.post("/webhooks", response_model=WebhookResponse)
async def register_report_webhook(
    workspace_id: str = Query(..., description="Workspace ID"),
    webhook_config: WebhookRequest = ...,
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Register webhook for report events.

    ## Parameters
    - **workspace_id**: Workspace ID
    - **webhook_config**: Webhook configuration including:
      - **url**: Webhook URL (must be https)
      - **events**: List of events to subscribe to
      - **secret**: Optional secret for signature verification
      - **is_active**: Whether webhook is active

    ## Events
    - `report.generated`: Report generation completed
    - `report.failed`: Report generation failed
    - `report.downloaded`: Report was downloaded
    - `report.shared`: Report was shared

    ## Example
    ```json
    {
      "url": "https://api.company.com/reports/webhook",
      "events": ["report.generated", "report.failed"],
      "secret": "webhook_secret_key",
      "is_active": true
    }
    ```
    """
    try:
        user_id = current_user.get("user_id")
        service = ReportService(db)

        webhook_id = await service.register_webhook(workspace_id, user_id, webhook_config)

        return WebhookResponse(webhook_id=webhook_id, status="registered")

    except ValueError as e:
        logger.warning(f"Invalid webhook configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error registering webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register webhook"
        )


@router.get("/webhooks")
async def get_webhooks(
    workspace_id: str = Query(..., description="Workspace ID"),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get registered webhooks for workspace.

    ## Parameters
    - **workspace_id**: Workspace ID

    ## Returns
    List of webhooks with:
    - **id**: Webhook ID
    - **url**: Webhook URL
    - **events**: Subscribed events
    - **is_active**: Active status
    - **total_deliveries**: Total delivery attempts
    - **successful_deliveries**: Successful deliveries
    - **failed_deliveries**: Failed deliveries
    - **last_delivery_at**: Last delivery timestamp
    - **created_at**: Creation timestamp
    """
    try:
        service = ReportService(db)
        webhooks = await service.get_webhooks(workspace_id)

        return {"webhooks": webhooks}

    except Exception as e:
        logger.error(f"Error getting webhooks: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve webhooks"
        )
