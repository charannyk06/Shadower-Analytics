"""Export functionality routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime
import uuid
import os

from ...core.database import get_db
from ...api.dependencies.auth import get_current_user, require_admin
from ...models.database.exports import (
    ExportJob,
    ExportTemplate,
    ExportSchedule,
    ExportFile,
    ExportMetadata,
    ExportStatus,
)
from ...models.schemas.exports import (
    ExportConfig,
    CreateExportResponse,
    ExportStatusResponse,
    ExportProgress,
    ExportFileInfo,
    ExportTemplateConfig,
    CreateTemplateResponse,
    ExportTemplatesResponse,
    ExportScheduleConfig,
    CreateScheduleResponse,
    ExportSchedulesResponse,
    BulkExportConfig,
    CreateBulkExportResponse,
    ConversionConfig,
    ConvertFormatResponse,
    ExportMetadataResponse,
    ValidationConfig,
    ValidationResponse,
    CleanupConfig,
    CleanupResponse,
    DeleteExportResponse,
)
from ...services.exports.export_processor import ExportProcessor
from ...tasks.exports import process_export_job, cleanup_old_exports

router = APIRouter(prefix="/api/v1/export", tags=["exports"])


# ============================================================================
# Export Job Endpoints
# ============================================================================


@router.post("/create", response_model=CreateExportResponse)
async def create_export_job(
    export_config: ExportConfig,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create data export job.

    This endpoint queues a new export job with the specified configuration.
    The export will be processed asynchronously in the background.
    """
    workspace_id = user.get("workspace_id")
    user_id = user.get("user_id")

    # Validate export configuration
    if not export_config.data_sources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one data source is required"
        )

    # Estimate export size and time
    processor = ExportProcessor(db)
    estimate = await processor.estimate_export(export_config, workspace_id)

    # Create export job
    job = ExportJob(
        name=export_config.name,
        workspace_id=workspace_id,
        user_id=user_id,
        config=export_config.dict(),
        data_sources=[ds.dict() for ds in export_config.data_sources],
        format=export_config.format.value,
        compression=export_config.compression.value,
        delivery_method=export_config.delivery.method.value if export_config.delivery else "download",
        delivery_config=export_config.delivery.dict() if export_config.delivery else None,
        encryption_enabled=export_config.encryption.enabled if export_config.encryption else False,
        encryption_config=export_config.encryption.dict() if export_config.encryption else None,
        estimated_size_mb=estimate["size_mb"],
        estimated_time_seconds=estimate["time_seconds"],
        estimated_rows=estimate["row_count"],
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Queue export job for processing
    celery_task = process_export_job.delay(str(job.id))
    job.celery_task_id = celery_task.id
    await db.commit()

    return CreateExportResponse(
        job_id=str(job.id),
        status=job.status,
        estimated_size_mb=estimate["size_mb"],
        estimated_time_seconds=estimate["time_seconds"],
        estimated_rows=estimate["row_count"],
        tracking_url=f"/api/v1/export/status/{job.id}"
    )


@router.get("/status/{job_id}", response_model=ExportStatusResponse)
async def get_export_status(
    job_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get export job status.

    Returns the current status, progress, and results (if completed) of an export job.
    """
    result = await db.execute(
        select(ExportJob).where(
            ExportJob.id == uuid.UUID(job_id),
            ExportJob.workspace_id == user.get("workspace_id")
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found"
        )

    # Build progress information
    progress = ExportProgress(
        percentage=job.progress_percent or 0.0,
        rows_processed=job.rows_processed or 0,
        total_rows=job.total_rows or job.estimated_rows or 0,
        current_table=job.current_table,
        files_created=job.files_created or 0,
    )

    # Build file information if completed
    files = None
    if job.status == ExportStatus.COMPLETED and job.files:
        files = [
            ExportFileInfo(
                filename=f["filename"],
                size_mb=f["size_mb"],
                rows=f["rows"],
                download_url=f"/api/v1/export/download/{job_id}/{i}",
                checksum=f["checksum"],
            )
            for i, f in enumerate(job.files)
        ]

    return ExportStatusResponse(
        job_id=str(job.id),
        status=job.status,
        progress=progress,
        started_at=job.started_at,
        completed_at=job.completed_at,
        files=files,
        error=job.error_message if job.status == ExportStatus.FAILED else None,
    )


@router.get("/download/{job_id}/{file_index}")
async def download_export_file(
    job_id: str,
    file_index: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download exported file.

    Downloads a specific file from a completed export job.
    """
    # Get job
    result = await db.execute(
        select(ExportJob).where(
            ExportJob.id == uuid.UUID(job_id),
            ExportJob.workspace_id == user.get("workspace_id")
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found"
        )

    if job.status != ExportStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Export not completed"
        )

    # Get file
    result = await db.execute(
        select(ExportFile).where(
            ExportFile.job_id == job.id,
            ExportFile.file_index == file_index
        )
    )
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Check if file exists
    if not os.path.exists(file.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk"
        )

    # Update download counter
    file.downloaded_count += 1
    file.last_downloaded_at = datetime.utcnow()
    await db.commit()

    return FileResponse(
        path=file.file_path,
        filename=file.filename,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={file.filename}",
            "X-Checksum": file.checksum,
        }
    )


# ============================================================================
# Export Template Endpoints
# ============================================================================


@router.get("/templates", response_model=ExportTemplatesResponse)
async def get_export_templates(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List available export templates.

    Returns all templates accessible to the current user.
    """
    workspace_id = user.get("workspace_id")

    result = await db.execute(
        select(ExportTemplate).where(
            (ExportTemplate.workspace_id == workspace_id) |
            (ExportTemplate.is_public == True)
        ).order_by(ExportTemplate.last_used_at.desc().nullsfirst())
    )
    templates = result.scalars().all()

    from ...models.schemas.exports import ExportTemplate as ExportTemplateSchema

    template_list = [
        ExportTemplateSchema(
            id=str(t.id),
            name=t.name,
            description=t.description,
            data_sources=[ds.get("type") for ds in t.configuration.get("data_sources", [])],
            format=t.configuration.get("format", "csv"),
            estimated_size_mb=50.0,  # Placeholder
            last_used=t.last_used_at,
            created_by=str(t.user_id),
        )
        for t in templates
    ]

    return ExportTemplatesResponse(templates=template_list)


@router.post("/templates", response_model=CreateTemplateResponse)
async def create_export_template(
    template_config: ExportTemplateConfig,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Save export configuration as template.

    Creates a reusable template for export configurations.
    """
    workspace_id = user.get("workspace_id")
    user_id = user.get("user_id")

    template = ExportTemplate(
        workspace_id=workspace_id,
        user_id=user_id,
        name=template_config.name,
        description=template_config.description,
        configuration=template_config.configuration.dict(),
        is_public=template_config.is_public,
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    return CreateTemplateResponse(
        template_id=str(template.id),
        created=True
    )


# ============================================================================
# Scheduled Export Endpoints
# ============================================================================


@router.get("/scheduled", response_model=ExportSchedulesResponse)
async def get_scheduled_exports(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List scheduled exports.

    Returns all active schedules for the current workspace.
    """
    workspace_id = user.get("workspace_id")

    result = await db.execute(
        select(ExportSchedule).where(
            ExportSchedule.workspace_id == workspace_id
        ).order_by(ExportSchedule.next_run_at)
    )
    schedules = result.scalars().all()

    from ...models.schemas.exports import ExportScheduleInfo, DeliveryConfig, DeliveryMethodEnum

    schedule_list = [
        ExportScheduleInfo(
            id=str(s.id),
            name=s.name,
            template_id=str(s.template_id),
            frequency=s.frequency,
            next_run=s.next_run_at,
            last_run=s.last_run_at,
            is_active=s.is_active,
            delivery=DeliveryConfig(method=DeliveryMethodEnum.DOWNLOAD),  # Placeholder
        )
        for s in schedules
    ]

    return ExportSchedulesResponse(schedules=schedule_list)


@router.post("/scheduled", response_model=CreateScheduleResponse)
async def create_scheduled_export(
    schedule_config: ExportScheduleConfig,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Create scheduled export.

    Sets up automatic recurring exports based on a template.
    """
    workspace_id = user.get("workspace_id")
    user_id = user.get("user_id")

    # Verify template exists
    result = await db.execute(
        select(ExportTemplate).where(
            ExportTemplate.id == uuid.UUID(schedule_config.template_id),
            ExportTemplate.workspace_id == workspace_id
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Calculate next run time (simplified)
    from datetime import timedelta
    if schedule_config.frequency == "daily":
        next_run = datetime.utcnow() + timedelta(days=1)
    elif schedule_config.frequency == "weekly":
        next_run = datetime.utcnow() + timedelta(weeks=1)
    elif schedule_config.frequency == "monthly":
        next_run = datetime.utcnow() + timedelta(days=30)
    else:
        next_run = datetime.utcnow() + timedelta(days=1)

    schedule = ExportSchedule(
        workspace_id=workspace_id,
        user_id=user_id,
        name=schedule_config.name,
        template_id=template.id,
        frequency=schedule_config.frequency,
        schedule_config=schedule_config.schedule.dict(),
        retention_config=schedule_config.retention.dict() if schedule_config.retention else None,
        next_run_at=next_run,
    )

    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    return CreateScheduleResponse(
        schedule_id=str(schedule.id),
        next_run=next_run
    )


# ============================================================================
# Bulk Export and Utility Endpoints
# ============================================================================


@router.post("/bulk", response_model=CreateBulkExportResponse)
async def create_bulk_export(
    bulk_config: BulkExportConfig,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Export complete workspace data.

    Creates multiple export jobs for backing up or migrating workspace data.
    """
    workspace_id = user.get("workspace_id")
    user_id = user.get("user_id")

    batch_id = str(uuid.uuid4())
    job_ids = []
    estimated_total_size_gb = 0.0

    # Create a job for each table
    for table in bulk_config.tables:
        job_name = f"{bulk_config.export_type.value}_{table}_{datetime.utcnow().strftime('%Y%m%d')}"

        job = ExportJob(
            name=job_name,
            workspace_id=workspace_id,
            user_id=user_id,
            config=bulk_config.dict(),
            data_sources=[{"type": table, "filters": {}}],
            format=bulk_config.format.value,
            compression="gzip",
        )

        db.add(job)
        await db.flush()
        job_ids.append(str(job.id))

        # Queue job
        process_export_job.delay(str(job.id))

        estimated_total_size_gb += 0.1  # Placeholder estimate

    await db.commit()

    return CreateBulkExportResponse(
        batch_id=batch_id,
        job_ids=job_ids,
        total_tables=len(bulk_config.tables),
        estimated_total_size_gb=estimated_total_size_gb
    )


@router.post("/convert", response_model=ConvertFormatResponse)
async def convert_export_format(
    conversion_config: ConversionConfig,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Convert existing export to different format.

    Creates a new export job that converts an existing export to a different format.
    """
    # Get source job
    result = await db.execute(
        select(ExportJob).where(
            ExportJob.id == uuid.UUID(conversion_config.source_job_id),
            ExportJob.workspace_id == user.get("workspace_id")
        )
    )
    source_job = result.scalar_one_or_none()

    if not source_job or source_job.status != ExportStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source job not found or not completed"
        )

    # Create conversion job
    conversion_job = ExportJob(
        name=f"Conversion of {source_job.name}",
        workspace_id=source_job.workspace_id,
        user_id=source_job.user_id,
        config=source_job.config,
        data_sources=source_job.data_sources,
        format=conversion_config.target_format.value,
        compression="none",
    )

    db.add(conversion_job)
    await db.commit()
    await db.refresh(conversion_job)

    # Queue conversion (would use the same export task)
    process_export_job.delay(str(conversion_job.id))

    return ConvertFormatResponse(
        conversion_job_id=str(conversion_job.id),
        status=ExportStatus.QUEUED
    )


@router.get("/metadata/{job_id}", response_model=ExportMetadataResponse)
async def get_export_metadata(
    job_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed export metadata.

    Returns schema, statistics, and lineage information for an export.
    """
    # Get job
    result = await db.execute(
        select(ExportJob).where(
            ExportJob.id == uuid.UUID(job_id),
            ExportJob.workspace_id == user.get("workspace_id")
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found"
        )

    # Get or create metadata
    result = await db.execute(
        select(ExportMetadata).where(ExportMetadata.job_id == job.id)
    )
    metadata = result.scalar_one_or_none()

    if not metadata:
        # Create placeholder metadata
        from ...models.schemas.exports import (
            ExportMetadataInfo,
            SchemaInfo,
            ExportStatistics,
            ExportLineage,
        )

        metadata_info = ExportMetadataInfo(
            schema=SchemaInfo(tables=[]),
            statistics=ExportStatistics(
                total_rows=job.rows_processed or 0,
                total_columns=0,
            ),
            lineage=ExportLineage(
                source_database="analytics",
                export_timestamp=job.created_at or datetime.utcnow(),
                filters_applied=[],
            )
        )
    else:
        from ...models.schemas.exports import ExportMetadataInfo
        metadata_info = ExportMetadataInfo(**metadata.schema_info)

    return ExportMetadataResponse(
        job_id=str(job.id),
        metadata=metadata_info
    )


@router.post("/validate", response_model=ValidationResponse)
async def validate_export(
    validation_config: ValidationConfig,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Validate export file integrity.

    Checks checksums, schema, and data integrity of export files.
    """
    from ...tasks.exports import validate_export_files
    from ...models.schemas.exports import ValidationChecks

    # Queue validation task
    task = validate_export_files.delay(validation_config.job_id)
    result = task.get(timeout=30)  # Wait for validation

    checks = ValidationChecks(
        checksum_valid=result["valid"],
        schema_valid=result["valid"],
        row_count_match=result["valid"],
        no_corruption=result["valid"],
    )

    return ValidationResponse(
        valid=result["valid"],
        checks=checks,
        sample_data=None
    )


@router.delete("/{job_id}", response_model=DeleteExportResponse)
async def delete_export(
    job_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete export files.

    Removes export job and associated files from the system.
    """
    # Get job
    result = await db.execute(
        select(ExportJob).where(
            ExportJob.id == uuid.UUID(job_id),
            ExportJob.workspace_id == user.get("workspace_id")
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found"
        )

    # Get files
    result = await db.execute(
        select(ExportFile).where(ExportFile.job_id == job.id)
    )
    files = result.scalars().all()

    # Delete physical files
    files_removed = 0
    space_freed_mb = 0.0

    for file in files:
        if os.path.exists(file.file_path):
            try:
                os.remove(file.file_path)
                files_removed += 1
                space_freed_mb += file.size_mb
            except Exception as e:
                pass  # Continue even if deletion fails

    # Delete database records
    await db.execute(delete(ExportFile).where(ExportFile.job_id == job.id))
    await db.delete(job)
    await db.commit()

    return DeleteExportResponse(
        job_id=str(job_id),
        deleted=True,
        files_removed=files_removed,
        space_freed_mb=space_freed_mb
    )


@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_old_exports(
    cleanup_config: CleanupConfig,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Clean up old exports.

    Removes old export files based on age and other criteria.
    """
    if cleanup_config.dry_run:
        # Just return estimates without deleting
        return CleanupResponse(
            exports_deleted=0,
            space_freed_gb=0.0,
            dry_run=True
        )

    # Queue cleanup task
    task = cleanup_old_exports.delay(
        older_than_days=cleanup_config.older_than_days,
        keep_scheduled=cleanup_config.keep_scheduled
    )
    result = task.get(timeout=60)

    return CleanupResponse(
        exports_deleted=result["deleted_count"],
        space_freed_gb=result["space_freed_mb"] / 1024,
        dry_run=False
    )
