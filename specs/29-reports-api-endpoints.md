# Specification: Reports API Endpoints

## Overview
Define API endpoints for report generation, scheduling, templates, and export functionality.

## Technical Requirements

### Report Generation Endpoints

#### POST `/api/v1/reports/generate`
```python
@router.post("/reports/generate")
async def generate_report(
    workspace_id: str,
    report_config: ReportConfig,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Generate a custom report
    
    Request body:
    {
        "name": "Monthly Analytics Report",
        "template_id": "template_123",
        "format": "pdf",  # pdf, excel, csv, json
        "sections": [
            "executive_summary",
            "user_analytics",
            "agent_performance",
            "financial_metrics"
        ],
        "date_range": {
            "start": "2024-01-01",
            "end": "2024-01-31"
        },
        "filters": {
            "agents": ["agent_123", "agent_456"],
            "users": null  # all users
        },
        "delivery": {
            "method": "email",  # email, download, webhook
            "recipients": ["admin@company.com"]
        }
    }
    """
    report_job = await queue_report_generation(workspace_id, report_config)
    
    return {
        "job_id": report_job.id,
        "status": "queued",
        "estimated_completion": 120,  # seconds
        "tracking_url": f"/api/v1/reports/jobs/{report_job.id}"
    }
```

#### GET `/api/v1/reports/jobs/{job_id}`
```python
@router.get("/reports/jobs/{job_id}")
async def get_report_job_status(
    job_id: str,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Check report generation job status
    """
    job = await get_report_job(job_id)
    
    return {
        "job_id": job_id,
        "status": job.status,  # queued, processing, completed, failed
        "progress": job.progress,  # 0-100
        "current_section": job.current_section,
        "completed_at": job.completed_at,
        "download_url": job.download_url if job.status == "completed" else None,
        "error": job.error if job.status == "failed" else None,
        "metadata": {
            "page_count": job.page_count,
            "file_size": job.file_size,
            "generation_time": job.generation_time
        }
    }
```

### Report Templates Endpoints

#### GET `/api/v1/reports/templates`
```python
@router.get("/reports/templates")
async def get_report_templates(
    workspace_id: Optional[str] = None,
    category: Optional[str] = None,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    List available report templates
    """
    templates = await get_templates(workspace_id, category)
    
    return {
        "templates": [
            {
                "id": "template_123",
                "name": "Executive Summary",
                "description": "High-level KPIs and trends",
                "category": "executive",
                "sections": ["kpis", "trends", "predictions"],
                "formats": ["pdf", "pptx"],
                "is_custom": False,
                "preview_url": "/api/v1/reports/templates/template_123/preview"
            }
        ]
    }
```

#### POST `/api/v1/reports/templates`
```python
@router.post("/reports/templates")
async def create_custom_template(
    workspace_id: str,
    template_config: TemplateConfig,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Create custom report template
    
    Request body:
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
            },
            {
                "type": "text",
                "title": "Summary",
                "template": "This week saw {{change}}% growth..."
            }
        ],
        "layout": {
            "orientation": "portrait",
            "margins": {"top": 1, "bottom": 1, "left": 1, "right": 1}
        }
    }
    """
    template_id = await create_template(workspace_id, template_config)
    
    return {
        "template_id": template_id,
        "status": "created"
    }
```

### Scheduled Reports Endpoints

#### GET `/api/v1/reports/scheduled`
```python
@router.get("/reports/scheduled")
async def get_scheduled_reports(
    workspace_id: str,
    is_active: Optional[bool] = None,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    List scheduled reports for workspace
    """
    schedules = await get_report_schedules(workspace_id, is_active)
    
    return {
        "schedules": [
            {
                "id": "schedule_123",
                "name": "Weekly Performance Report",
                "template_id": "template_456",
                "frequency": "weekly",
                "schedule": {
                    "day_of_week": "monday",
                    "time": "09:00",
                    "timezone": "America/New_York"
                },
                "recipients": ["team@company.com"],
                "is_active": True,
                "last_run": "2024-01-15T09:00:00Z",
                "next_run": "2024-01-22T09:00:00Z"
            }
        ]
    }
```

#### POST `/api/v1/reports/scheduled`
```python
@router.post("/reports/scheduled")
async def create_scheduled_report(
    workspace_id: str,
    schedule_config: ScheduleConfig,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Create scheduled report
    
    Request body:
    {
        "name": "Daily Analytics Digest",
        "template_id": "template_daily",
        "frequency": "daily",  # daily, weekly, monthly, quarterly
        "schedule": {
            "time": "08:00",
            "timezone": "UTC",
            "day_of_week": null,  # for weekly
            "day_of_month": null  # for monthly
        },
        "recipients": {
            "emails": ["admin@company.com"],
            "slack_channels": ["#analytics"],
            "webhooks": ["https://api.company.com/reports"]
        },
        "filters": {
            "include_weekends": false
        }
    }
    """
    schedule_id = await create_schedule(workspace_id, schedule_config)
    
    return {
        "schedule_id": schedule_id,
        "status": "active",
        "next_run": calculate_next_run(schedule_config)
    }
```

### Report History Endpoints

#### GET `/api/v1/reports/history`
```python
@router.get("/reports/history")
async def get_report_history(
    workspace_id: str,
    report_type: Optional[str] = None,
    date_range: Optional[DateRange] = None,
    pagination: PaginationParams = Depends(),
    user: User = Depends(get_current_user)
) -> PaginatedResponse:
    """
    Get historical reports
    """
    reports = await get_historical_reports(
        workspace_id, report_type, date_range, pagination
    )
    
    return {
        "reports": [
            {
                "id": "report_789",
                "name": "Q1 2024 Analytics",
                "type": "quarterly",
                "generated_at": "2024-04-01T00:00:00Z",
                "generated_by": "user_123",
                "format": "pdf",
                "file_size": 2457600,
                "page_count": 42,
                "download_url": "/api/v1/reports/download/report_789",
                "expires_at": "2024-05-01T00:00:00Z"
            }
        ],
        **pagination.dict()
    }
```

### Export Endpoints

#### POST `/api/v1/reports/export/data`
```python
@router.post("/reports/export/data")
async def export_raw_data(
    workspace_id: str,
    export_config: DataExportConfig,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Export raw data for external analysis
    
    Request body:
    {
        "data_sources": [
            "user_activity",
            "agent_performance",
            "credit_consumption"
        ],
        "format": "csv",  # csv, json, parquet
        "date_range": {
            "start": "2024-01-01",
            "end": "2024-01-31"
        },
        "compression": "gzip",  # none, gzip, zip
        "include_metadata": true
    }
    """
    export_job = await queue_data_export(workspace_id, export_config)
    
    return {
        "job_id": export_job.id,
        "estimated_size": export_job.estimated_size,
        "estimated_time": export_job.estimated_time
    }
```

#### GET `/api/v1/reports/download/{report_id}`
```python
@router.get("/reports/download/{report_id}")
async def download_report(
    report_id: str,
    user: User = Depends(get_current_user)
) -> FileResponse:
    """
    Download generated report file
    """
    report = await get_report(report_id)
    
    # Verify access
    if not has_access(user, report):
        raise HTTPException(403, "Access denied")
    
    # Check expiration
    if report.is_expired():
        raise HTTPException(410, "Report has expired")
    
    return FileResponse(
        path=report.file_path,
        filename=report.filename,
        media_type=report.content_type,
        headers={
            "Content-Disposition": f"attachment; filename={report.filename}"
        }
    )
```

### Report Sharing Endpoints

#### POST `/api/v1/reports/{report_id}/share`
```python
@router.post("/reports/{report_id}/share")
async def share_report(
    report_id: str,
    share_config: ShareConfig,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Share report with external users
    
    Request body:
    {
        "recipients": ["external@client.com"],
        "message": "Please find attached the monthly report",
        "expiration_days": 7,
        "require_password": true,
        "allow_download": true
    }
    """
    share_link = await create_share_link(report_id, share_config)
    
    return {
        "share_url": share_link.url,
        "password": share_link.password if share_config.require_password else None,
        "expires_at": share_link.expires_at
    }
```

### Report Analytics Endpoints

#### GET `/api/v1/reports/analytics`
```python
@router.get("/reports/analytics")
async def get_report_analytics(
    workspace_id: str,
    date_range: DateRange,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Analytics about report usage
    """
    analytics = await get_report_usage_analytics(workspace_id, date_range)
    
    return {
        "report_analytics": {
            "total_generated": 145,
            "total_views": 892,
            "total_downloads": 234,
            "avg_generation_time": 45.2,
            "most_popular": [
                {"template": "Executive Summary", "count": 42},
                {"template": "Weekly Performance", "count": 38}
            ],
            "by_format": {
                "pdf": 89,
                "excel": 34,
                "csv": 22
            },
            "by_user": [
                {"user": "admin@company.com", "count": 67}
            ]
        }
    }
```

### Webhook Endpoints

#### POST `/api/v1/reports/webhooks`
```python
@router.post("/reports/webhooks")
async def register_report_webhook(
    workspace_id: str,
    webhook_config: WebhookConfig,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Register webhook for report events
    
    Request body:
    {
        "url": "https://api.company.com/reports/webhook",
        "events": ["report.generated", "report.failed"],
        "secret": "webhook_secret_key",
        "is_active": true
    }
    """
    webhook_id = await register_webhook(workspace_id, webhook_config)
    
    return {
        "webhook_id": webhook_id,
        "status": "registered"
    }
```

## Report Generation Pipeline

```python
class ReportGenerator:
    async def generate(self, config: ReportConfig):
        """Main report generation pipeline"""
        # 1. Validate configuration
        await self.validate_config(config)
        
        # 2. Fetch data
        data = await self.fetch_report_data(config)
        
        # 3. Process and aggregate
        processed = await self.process_data(data)
        
        # 4. Render report
        rendered = await self.render_report(processed, config.template)
        
        # 5. Convert to format
        output = await self.convert_format(rendered, config.format)
        
        # 6. Deliver report
        await self.deliver_report(output, config.delivery)
        
        return output
```

## Implementation Priority
1. Basic report generation
2. Report templates
3. Scheduled reports
4. Export functionality
5. Report sharing and analytics

## Success Metrics
- Report generation success rate > 99%
- Average generation time < 2 minutes
- Template satisfaction score > 4.0/5.0
- Scheduled report reliability > 99.9%