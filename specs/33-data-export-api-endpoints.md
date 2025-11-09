# Specification: Data Export API Endpoints

## Overview
Define API endpoints for exporting analytics data in various formats with compression, scheduling, and delivery options.

## Technical Requirements

### Export Job Endpoints

#### POST `/api/v1/export/create`
```python
@router.post("/export/create")
async def create_export_job(
    export_config: ExportConfig,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Create data export job
    
    Request body:
    {
        "name": "Q1 2024 Analytics Export",
        "data_sources": [
            {
                "type": "user_activity",
                "filters": {
                    "date_range": {
                        "start": "2024-01-01",
                        "end": "2024-03-31"
                    },
                    "workspace_id": "ws_123"
                },
                "fields": ["user_id", "action", "timestamp", "credits"]
            },
            {
                "type": "agent_performance",
                "filters": {
                    "agent_ids": ["agent_123", "agent_456"]
                },
                "aggregation": "daily"
            }
        ],
        "format": "csv",  # csv, json, excel, parquet
        "compression": "gzip",  # none, gzip, zip, bz2
        "split_files": {
            "enabled": true,
            "max_size_mb": 100,
            "split_by": "month"  # month, week, size
        },
        "delivery": {
            "method": "download",  # download, email, s3, ftp
            "email_recipients": ["admin@company.com"],
            "s3_config": {
                "bucket": "analytics-exports",
                "prefix": "2024/Q1/"
            }
        },
        "encryption": {
            "enabled": true,
            "method": "AES256",
            "password_protected": true
        }
    }
    """
    # Validate export configuration
    validate_export_config(export_config)
    
    # Estimate export size and time
    estimate = await estimate_export(export_config)
    
    # Queue export job
    job = await queue_export_job(
        workspace_id=user.workspace_id,
        user_id=user.id,
        config=export_config,
        estimate=estimate
    )
    
    return {
        "job_id": job.id,
        "status": "queued",
        "estimated_size_mb": estimate.size_mb,
        "estimated_time_seconds": estimate.time_seconds,
        "estimated_rows": estimate.row_count,
        "tracking_url": f"/api/v1/export/status/{job.id}"
    }
```

#### GET `/api/v1/export/status/{job_id}`
```python
@router.get("/export/status/{job_id}")
async def get_export_status(
    job_id: str,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Get export job status
    """
    job = await get_export_job(job_id, user.id)
    
    return {
        "job_id": job_id,
        "status": job.status,  # queued, processing, completed, failed
        "progress": {
            "percentage": job.progress_percent,
            "rows_processed": job.rows_processed,
            "total_rows": job.total_rows,
            "current_table": job.current_table,
            "files_created": job.files_created
        },
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "files": [
            {
                "filename": "user_activity_2024_01.csv.gz",
                "size_mb": 45.2,
                "rows": 125000,
                "download_url": f"/api/v1/export/download/{job_id}/0",
                "checksum": "sha256:abcd1234..."
            }
        ] if job.status == "completed" else None,
        "error": job.error if job.status == "failed" else None
    }
```

#### GET `/api/v1/export/download/{job_id}/{file_index}`
```python
@router.get("/export/download/{job_id}/{file_index}")
async def download_export_file(
    job_id: str,
    file_index: int,
    user: User = Depends(get_current_user)
) -> FileResponse:
    """
    Download exported file
    """
    job = await get_export_job(job_id, user.id)
    
    if job.status != "completed":
        raise HTTPException(400, "Export not completed")
    
    file_info = job.files[file_index]
    
    # Check if password required
    if job.encryption.password_protected:
        password = request.headers.get("X-Export-Password")
        if not verify_export_password(job_id, password):
            raise HTTPException(401, "Invalid password")
    
    return FileResponse(
        path=file_info.path,
        filename=file_info.filename,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={file_info.filename}",
            "X-Checksum": file_info.checksum
        }
    )
```

### Export Templates

#### GET `/api/v1/export/templates`
```python
@router.get("/export/templates")
async def get_export_templates(
    workspace_id: str,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    List available export templates
    """
    templates = await get_workspace_export_templates(workspace_id)
    
    return {
        "templates": [
            {
                "id": "template_123",
                "name": "Monthly User Report",
                "description": "Complete user activity for a month",
                "data_sources": ["user_activity", "user_sessions"],
                "format": "excel",
                "estimated_size_mb": 50,
                "last_used": "2024-01-15T10:00:00Z",
                "created_by": "admin@company.com"
            }
        ]
    }
```

#### POST `/api/v1/export/templates`
```python
@router.post("/export/templates")
async def create_export_template(
    template_config: ExportTemplateConfig,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Save export configuration as template
    
    Request body:
    {
        "name": "Weekly Analytics Package",
        "description": "Standard weekly analytics export",
        "configuration": {
            "data_sources": [...],
            "format": "excel",
            "compression": "zip"
        },
        "is_public": false,
        "schedule": {
            "enabled": true,
            "frequency": "weekly",
            "day_of_week": "monday",
            "time": "08:00"
        }
    }
    """
    template = await create_template(
        workspace_id=user.workspace_id,
        user_id=user.id,
        config=template_config
    )
    
    return {
        "template_id": template.id,
        "created": True
    }
```

### Scheduled Exports

#### GET `/api/v1/export/scheduled`
```python
@router.get("/export/scheduled")
async def get_scheduled_exports(
    workspace_id: str,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    List scheduled exports
    """
    schedules = await get_export_schedules(workspace_id)
    
    return {
        "schedules": [
            {
                "id": "schedule_123",
                "name": "Daily Activity Export",
                "template_id": "template_456",
                "frequency": "daily",
                "next_run": "2024-01-16T00:00:00Z",
                "last_run": "2024-01-15T00:00:00Z",
                "is_active": True,
                "delivery": {
                    "method": "s3",
                    "auto_delete_after_days": 30
                }
            }
        ]
    }
```

#### POST `/api/v1/export/scheduled`
```python
@router.post("/export/scheduled")
async def create_scheduled_export(
    schedule_config: ExportScheduleConfig,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Create scheduled export
    
    Request body:
    {
        "name": "Weekly Performance Export",
        "template_id": "template_123",
        "frequency": "weekly",
        "schedule": {
            "day_of_week": "sunday",
            "time": "23:00",
            "timezone": "UTC"
        },
        "retention": {
            "keep_exports_days": 90,
            "auto_cleanup": true
        }
    }
    """
    schedule = await create_export_schedule(
        workspace_id=user.workspace_id,
        config=schedule_config
    )
    
    return {
        "schedule_id": schedule.id,
        "next_run": schedule.next_run
    }
```

### Bulk Export Operations

#### POST `/api/v1/export/bulk`
```python
@router.post("/export/bulk")
async def create_bulk_export(
    bulk_config: BulkExportConfig,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Export complete workspace data
    
    Request body:
    {
        "export_type": "full_backup",  # full_backup, migration, audit
        "include_deleted": false,
        "point_in_time": "2024-01-15T00:00:00Z",
        "tables": [
            "user_activity",
            "agent_performance",
            "credit_consumption",
            "error_logs"
        ],
        "format": "parquet",
        "partitioning": {
            "by": "month",
            "parallel_jobs": 4
        }
    }
    """
    jobs = await create_bulk_export_jobs(
        workspace_id=user.workspace_id,
        config=bulk_config
    )
    
    return {
        "batch_id": jobs.batch_id,
        "job_ids": jobs.job_ids,
        "total_tables": len(bulk_config.tables),
        "estimated_total_size_gb": jobs.estimated_size_gb
    }
```

### Export Format Converters

#### POST `/api/v1/export/convert`
```python
@router.post("/export/convert")
async def convert_export_format(
    conversion_config: ConversionConfig,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Convert existing export to different format
    
    Request body:
    {
        "source_job_id": "job_123",
        "target_format": "parquet",  # csv, json, excel, parquet
        "options": {
            "excel_sheets": true,
            "json_pretty": true,
            "parquet_compression": "snappy"
        }
    }
    """
    conversion_job = await queue_format_conversion(
        source_job_id=conversion_config.source_job_id,
        target_format=conversion_config.target_format,
        options=conversion_config.options
    )
    
    return {
        "conversion_job_id": conversion_job.id,
        "status": "processing"
    }
```

### Export Metadata

#### GET `/api/v1/export/metadata/{job_id}`
```python
@router.get("/export/metadata/{job_id}")
async def get_export_metadata(
    job_id: str,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Get detailed export metadata
    """
    metadata = await get_export_metadata_details(job_id)
    
    return {
        "job_id": job_id,
        "metadata": {
            "schema": {
                "tables": [
                    {
                        "name": "user_activity",
                        "columns": [
                            {"name": "user_id", "type": "UUID"},
                            {"name": "action", "type": "VARCHAR"},
                            {"name": "timestamp", "type": "TIMESTAMP"}
                        ],
                        "row_count": 125000
                    }
                ]
            },
            "statistics": {
                "total_rows": 450000,
                "total_columns": 45,
                "date_range": {
                    "start": "2024-01-01",
                    "end": "2024-01-31"
                }
            },
            "lineage": {
                "source_database": "analytics",
                "export_timestamp": "2024-01-15T14:30:00Z",
                "filters_applied": ["workspace_id = 'ws_123'"]
            }
        }
    }
```

### Export Validation

#### POST `/api/v1/export/validate`
```python
@router.post("/export/validate")
async def validate_export(
    validation_config: ValidationConfig,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Validate export file integrity
    
    Request body:
    {
        "job_id": "job_123",
        "validation_type": "full",  # checksum, schema, full
        "sample_rows": 100
    }
    """
    validation_result = await validate_export_files(
        job_id=validation_config.job_id,
        validation_type=validation_config.validation_type
    )
    
    return {
        "valid": validation_result.is_valid,
        "checks": {
            "checksum_valid": validation_result.checksum_valid,
            "schema_valid": validation_result.schema_valid,
            "row_count_match": validation_result.row_count_match,
            "no_corruption": validation_result.no_corruption
        },
        "sample_data": validation_result.sample_data if validation_config.sample_rows else None
    }
```

### Export Cleanup

#### DELETE `/api/v1/export/{job_id}`
```python
@router.delete("/export/{job_id}")
async def delete_export(
    job_id: str,
    user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Delete export files
    """
    await delete_export_files(job_id, user.id)
    
    return {
        "job_id": job_id,
        "deleted": True,
        "files_removed": 5,
        "space_freed_mb": 234.5
    }
```

#### POST `/api/v1/export/cleanup`
```python
@router.post("/export/cleanup")
async def cleanup_old_exports(
    cleanup_config: CleanupConfig,
    user: User = Depends(require_admin)
) -> APIResponse:
    """
    Clean up old exports
    
    Request body:
    {
        "older_than_days": 90,
        "keep_scheduled": true,
        "dry_run": false
    }
    """
    cleanup_result = await cleanup_exports(
        workspace_id=user.workspace_id,
        config=cleanup_config
    )
    
    return {
        "exports_deleted": cleanup_result.deleted_count,
        "space_freed_gb": cleanup_result.space_freed_gb,
        "dry_run": cleanup_config.dry_run
    }
```

## Export Processing Pipeline

```python
class ExportProcessor:
    async def process_export(self, job_id: str):
        """Main export processing pipeline"""
        job = await get_job(job_id)
        
        try:
            # 1. Initialize export
            await self.initialize_export(job)
            
            # 2. Extract data
            for source in job.data_sources:
                data = await self.extract_data(source)
                
                # 3. Transform data
                transformed = await self.transform_data(data, job.format)
                
                # 4. Write to file
                await self.write_to_file(transformed, job)
                
                # 5. Update progress
                await self.update_progress(job)
            
            # 6. Finalize export
            await self.finalize_export(job)
            
            # 7. Deliver export
            await self.deliver_export(job)
            
        except Exception as e:
            await self.handle_export_error(job, e)
```

## Implementation Priority
1. Basic export creation and download
2. Multiple format support
3. Scheduled exports
4. Bulk export operations
5. Advanced validation and cleanup

## Success Metrics
- Export success rate > 99%
- Average export time < 5 minutes for < 1GB
- Format conversion accuracy 100%
- Scheduled export reliability > 99.9%