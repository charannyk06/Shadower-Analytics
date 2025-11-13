"""Export Celery tasks."""

import logging
import asyncio
from datetime import datetime
from typing import Optional

from celery import Task
from src.celery_app import celery_app
from src.core.database import async_session_maker
from src.services.exports.export_processor import ExportProcessor
from src.core.config import settings

logger = logging.getLogger(__name__)


class AsyncDatabaseTask(Task):
    """Base task class that provides async database session handling."""

    def run_async(self, async_func, *args, **kwargs):
        """Run an async function synchronously with proper cleanup."""
        try:
            return asyncio.run(async_func(*args, **kwargs))
        except RuntimeError:
            # Fallback for edge cases
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(async_func(*args, **kwargs))
            finally:
                try:
                    loop.close()
                finally:
                    asyncio.set_event_loop(None)


@celery_app.task(
    name='tasks.exports.process_export_job',
    bind=True,
    base=AsyncDatabaseTask,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
    time_limit=3600,  # 1 hour hard limit
    soft_time_limit=3300,  # 55 minutes soft limit
)
def process_export_job(self, job_id: str, export_dir: Optional[str] = None):
    """Process export job.

    Args:
        job_id: Export job ID
        export_dir: Optional directory for export files
    """
    logger.info(f"Starting export job {job_id}")

    async def _process():
        async with async_session_maker() as session:
            processor = ExportProcessor(
                session,
                export_dir=export_dir or "/tmp/exports"
            )
            await processor.process_export(job_id)

    try:
        self.run_async(_process)
        logger.info(f"Export job {job_id} completed successfully")
    except Exception as exc:
        logger.error(f"Export job {job_id} failed: {exc}")
        # Retry the task
        raise self.retry(exc=exc)


@celery_app.task(
    name='tasks.exports.process_scheduled_export',
    bind=True,
    base=AsyncDatabaseTask,
    max_retries=2,
)
def process_scheduled_export(self, schedule_id: str):
    """Process scheduled export.

    Args:
        schedule_id: Export schedule ID
    """
    logger.info(f"Starting scheduled export {schedule_id}")

    async def _process():
        from src.models.database.exports import ExportSchedule, ExportTemplate, ExportJob
        from sqlalchemy import select
        import uuid

        async with async_session_maker() as session:
            # Get schedule
            result = await session.execute(
                select(ExportSchedule).where(ExportSchedule.id == uuid.UUID(schedule_id))
            )
            schedule = result.scalar_one_or_none()

            if not schedule or not schedule.is_active:
                logger.warning(f"Schedule {schedule_id} not found or not active")
                return

            # Get template
            result = await session.execute(
                select(ExportTemplate).where(ExportTemplate.id == schedule.template_id)
            )
            template = result.scalar_one_or_none()

            if not template:
                logger.error(f"Template {schedule.template_id} not found for schedule {schedule_id}")
                return

            # Create export job from template
            config = template.configuration
            job = ExportJob(
                name=f"{schedule.name} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                workspace_id=schedule.workspace_id,
                user_id=schedule.user_id,
                template_id=template.id,
                config=config,
                data_sources=config.get("data_sources", []),
                format=config.get("format", "csv"),
                compression=config.get("compression", "none"),
                delivery_method=config.get("delivery", {}).get("method", "download"),
                delivery_config=config.get("delivery"),
                encryption_enabled=config.get("encryption", {}).get("enabled", False),
                encryption_config=config.get("encryption"),
            )

            session.add(job)
            await session.commit()
            await session.refresh(job)

            # Update schedule
            schedule.last_run_at = datetime.utcnow()
            schedule.last_job_id = job.id
            schedule.run_count += 1

            # Calculate next run time (simplified)
            # In production, use a proper cron parser
            if schedule.frequency == "daily":
                from datetime import timedelta
                schedule.next_run_at = datetime.utcnow() + timedelta(days=1)
            elif schedule.frequency == "weekly":
                from datetime import timedelta
                schedule.next_run_at = datetime.utcnow() + timedelta(weeks=1)
            elif schedule.frequency == "monthly":
                from datetime import timedelta
                schedule.next_run_at = datetime.utcnow() + timedelta(days=30)

            await session.commit()

            # Queue export job processing
            process_export_job.delay(str(job.id))

            logger.info(f"Scheduled export {schedule_id} created job {job.id}")

    try:
        self.run_async(_process)
    except Exception as exc:
        logger.error(f"Scheduled export {schedule_id} failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(
    name='tasks.exports.cleanup_old_exports',
    bind=True,
    base=AsyncDatabaseTask,
)
def cleanup_old_exports(self, older_than_days: int = 90, keep_scheduled: bool = True):
    """Clean up old export files.

    Args:
        older_than_days: Delete exports older than this many days
        keep_scheduled: Keep exports created by schedules
    """
    logger.info(f"Starting cleanup of exports older than {older_than_days} days")

    async def _cleanup():
        from src.models.database.exports import ExportJob, ExportFile
        from sqlalchemy import select, delete
        from datetime import timedelta
        import os

        async with async_session_maker() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)

            # Build query
            query = select(ExportJob).where(
                ExportJob.created_at < cutoff_date,
                ExportJob.status.in_(["completed", "failed", "cancelled"])
            )

            if keep_scheduled:
                query = query.where(ExportJob.template_id.is_(None))

            result = await session.execute(query)
            jobs_to_delete = result.scalars().all()

            deleted_count = 0
            space_freed = 0

            for job in jobs_to_delete:
                # Get files
                result = await session.execute(
                    select(ExportFile).where(ExportFile.job_id == job.id)
                )
                files = result.scalars().all()

                # Delete physical files
                for file in files:
                    try:
                        if os.path.exists(file.file_path):
                            os.remove(file.file_path)
                            space_freed += file.size_mb
                    except Exception as e:
                        logger.warning(f"Failed to delete file {file.file_path}: {e}")

                # Delete database records
                await session.execute(
                    delete(ExportFile).where(ExportFile.job_id == job.id)
                )
                await session.delete(job)
                deleted_count += 1

            await session.commit()

            logger.info(
                f"Cleanup completed: {deleted_count} exports deleted, "
                f"{space_freed:.2f} MB freed"
            )

            return {"deleted_count": deleted_count, "space_freed_mb": space_freed}

    try:
        result = self.run_async(_cleanup)
        return result
    except Exception as exc:
        logger.error(f"Cleanup failed: {exc}")
        raise


@celery_app.task(
    name='tasks.exports.validate_export_files',
    bind=True,
    base=AsyncDatabaseTask,
)
def validate_export_files(self, job_id: str):
    """Validate export files.

    Args:
        job_id: Export job ID
    """
    logger.info(f"Validating export files for job {job_id}")

    async def _validate():
        from src.models.database.exports import ExportJob, ExportFile
        from sqlalchemy import select
        import uuid
        import os
        import hashlib

        async with async_session_maker() as session:
            # Get job
            result = await session.execute(
                select(ExportJob).where(ExportJob.id == uuid.UUID(job_id))
            )
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Export job {job_id} not found")

            # Get files
            result = await session.execute(
                select(ExportFile).where(ExportFile.job_id == job.id)
            )
            files = result.scalars().all()

            validation_results = []

            for file in files:
                # Check file exists
                file_exists = os.path.exists(file.file_path)

                # Validate checksum if file exists
                checksum_valid = False
                if file_exists:
                    sha256_hash = hashlib.sha256()
                    with open(file.file_path, "rb") as f:
                        for byte_block in iter(lambda: f.read(4096), b""):
                            sha256_hash.update(byte_block)
                    current_checksum = f"sha256:{sha256_hash.hexdigest()}"
                    checksum_valid = current_checksum == file.checksum

                validation_results.append({
                    "filename": file.filename,
                    "file_exists": file_exists,
                    "checksum_valid": checksum_valid,
                })

            all_valid = all(
                r["file_exists"] and r["checksum_valid"]
                for r in validation_results
            )

            logger.info(
                f"Validation for job {job_id}: "
                f"{'passed' if all_valid else 'failed'}"
            )

            return {
                "valid": all_valid,
                "files": validation_results,
            }

    try:
        result = self.run_async(_validate)
        return result
    except Exception as exc:
        logger.error(f"Validation failed for job {job_id}: {exc}")
        raise
