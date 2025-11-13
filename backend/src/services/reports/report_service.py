"""Report generation and management service."""

import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4

from sqlalchemy import select, and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database.tables import (
    ReportJob,
    ReportTemplate,
    ReportSchedule,
    GeneratedReport,
    ReportShare,
    ReportWebhook,
    ExecutionLog,
    ExecutionMetricsDaily,
)
from src.models.schemas.reports import (
    ReportConfigRequest,
    ReportFormat,
    ReportStatus,
    CreateTemplateRequest,
    CreateScheduleRequest,
    ShareReportRequest,
    DataExportRequest,
    WebhookRequest,
)
from src.utils.datetime import utc_now

logger = logging.getLogger(__name__)


class ReportService:
    """Service for handling report operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Report Generation
    # ========================================================================

    async def create_report_job(
        self,
        workspace_id: str,
        user_id: str,
        config: ReportConfigRequest
    ) -> Dict[str, Any]:
        """Create a new report generation job.

        Args:
            workspace_id: Workspace ID
            user_id: User ID
            config: Report configuration

        Returns:
            Job information
        """
        try:
            # Create job record
            job_id = str(uuid4())
            job = ReportJob(
                id=job_id,
                workspace_id=workspace_id,
                user_id=user_id,
                report_name=config.name,
                template_id=config.template_id,
                report_format=config.format.value,
                sections=[s.value for s in config.sections],
                date_range={
                    "start": config.date_range.start.isoformat(),
                    "end": config.date_range.end.isoformat()
                },
                filters=config.filters.dict() if config.filters else {},
                delivery_config=config.delivery.dict(),
                status=ReportStatus.QUEUED.value,
                progress=0,
                expires_at=utc_now() + timedelta(days=30)
            )

            self.db.add(job)
            await self.db.commit()

            # TODO: Queue Celery task for async generation
            # from src.tasks.reports import generate_report_task
            # generate_report_task.delay(job_id)

            logger.info(f"Created report job {job_id} for workspace {workspace_id}")

            return {
                "job_id": job_id,
                "status": ReportStatus.QUEUED.value,
                "estimated_completion": 120,  # 2 minutes estimate
                "tracking_url": f"/api/v1/reports/jobs/{job_id}"
            }

        except Exception as e:
            logger.error(f"Error creating report job: {str(e)}", exc_info=True)
            await self.db.rollback()
            raise

    async def get_report_job_status(
        self,
        job_id: str,
        workspace_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get report job status.

        Args:
            job_id: Job ID
            workspace_id: Workspace ID for access control

        Returns:
            Job status information or None if not found
        """
        try:
            query = select(ReportJob).where(
                and_(
                    ReportJob.id == job_id,
                    ReportJob.workspace_id == workspace_id
                )
            )
            result = await self.db.execute(query)
            job = result.scalar_one_or_none()

            if not job:
                return None

            metadata = {}
            if job.status == ReportStatus.COMPLETED.value:
                metadata = {
                    "page_count": job.page_count,
                    "file_size": job.file_size,
                    "generation_time": job.generation_time
                }

            return {
                "job_id": job.id,
                "status": job.status,
                "progress": job.progress,
                "current_section": job.current_section,
                "completed_at": job.completed_at,
                "download_url": job.download_url if job.status == ReportStatus.COMPLETED.value else None,
                "error": job.error_message if job.status == ReportStatus.FAILED.value else None,
                "metadata": metadata
            }

        except Exception as e:
            logger.error(f"Error getting job status: {str(e)}", exc_info=True)
            raise

    # ========================================================================
    # Templates
    # ========================================================================

    async def get_templates(
        self,
        workspace_id: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get report templates.

        Args:
            workspace_id: Workspace ID (optional, for custom templates)
            category: Template category filter

        Returns:
            List of templates
        """
        try:
            # Build query for global and workspace templates
            conditions = [ReportTemplate.is_active == True]

            if workspace_id:
                conditions.append(
                    or_(
                        ReportTemplate.workspace_id == workspace_id,
                        ReportTemplate.workspace_id.is_(None)
                    )
                )
            else:
                conditions.append(ReportTemplate.workspace_id.is_(None))

            if category:
                conditions.append(ReportTemplate.category == category)

            query = select(ReportTemplate).where(and_(*conditions))
            result = await self.db.execute(query)
            templates = result.scalars().all()

            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "category": t.category,
                    "sections": [s.get("type", "") for s in t.sections] if t.sections else [],
                    "formats": t.supported_formats or ["pdf", "excel"],
                    "is_custom": t.is_custom,
                    "preview_url": f"/api/v1/reports/templates/{t.id}/preview" if t.id else None,
                    "usage_count": t.usage_count or 0
                }
                for t in templates
            ]

        except Exception as e:
            logger.error(f"Error getting templates: {str(e)}", exc_info=True)
            raise

    async def create_template(
        self,
        workspace_id: str,
        user_id: str,
        config: CreateTemplateRequest
    ) -> str:
        """Create custom report template.

        Args:
            workspace_id: Workspace ID
            user_id: User ID
            config: Template configuration

        Returns:
            Template ID
        """
        try:
            template_id = str(uuid4())
            template = ReportTemplate(
                id=template_id,
                workspace_id=workspace_id,
                name=config.name,
                description=config.description,
                category=config.category.value,
                is_custom=True,
                sections=[s.dict() for s in config.sections],
                layout=config.layout.dict() if config.layout else {},
                supported_formats=["pdf", "excel", "csv"],
                created_by=user_id
            )

            self.db.add(template)
            await self.db.commit()

            logger.info(f"Created template {template_id} for workspace {workspace_id}")
            return template_id

        except Exception as e:
            logger.error(f"Error creating template: {str(e)}", exc_info=True)
            await self.db.rollback()
            raise

    # ========================================================================
    # Scheduled Reports
    # ========================================================================

    async def get_schedules(
        self,
        workspace_id: str,
        is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """Get scheduled reports for workspace.

        Args:
            workspace_id: Workspace ID
            is_active: Filter by active status

        Returns:
            List of schedules
        """
        try:
            conditions = [ReportSchedule.workspace_id == workspace_id]
            if is_active is not None:
                conditions.append(ReportSchedule.is_active == is_active)

            query = select(ReportSchedule).where(and_(*conditions))
            result = await self.db.execute(query)
            schedules = result.scalars().all()

            return [
                {
                    "id": s.id,
                    "name": s.name,
                    "template_id": s.template_id,
                    "frequency": s.frequency,
                    "schedule": s.schedule_config or {},
                    "recipients": self._flatten_recipients(s.recipients),
                    "is_active": s.is_active,
                    "last_run": s.last_run_at,
                    "next_run": s.next_run_at,
                    "successful_runs": s.successful_runs or 0,
                    "failed_runs": s.failed_runs or 0
                }
                for s in schedules
            ]

        except Exception as e:
            logger.error(f"Error getting schedules: {str(e)}", exc_info=True)
            raise

    def _flatten_recipients(self, recipients: Dict[str, Any]) -> List[str]:
        """Flatten recipients dict to list of emails."""
        if not recipients:
            return []
        emails = recipients.get("emails", [])
        slack = recipients.get("slack_channels", [])
        webhooks = recipients.get("webhooks", [])
        return emails + slack + webhooks

    async def create_schedule(
        self,
        workspace_id: str,
        user_id: str,
        config: CreateScheduleRequest
    ) -> Dict[str, Any]:
        """Create scheduled report.

        Args:
            workspace_id: Workspace ID
            user_id: User ID
            config: Schedule configuration

        Returns:
            Schedule information
        """
        try:
            schedule_id = str(uuid4())
            next_run = self._calculate_next_run(config.frequency.value, config.schedule.dict())

            schedule = ReportSchedule(
                id=schedule_id,
                workspace_id=workspace_id,
                name=config.name,
                template_id=config.template_id,
                frequency=config.frequency.value,
                schedule_config=config.schedule.dict(),
                recipients=config.recipients.dict(),
                filters=config.filters.dict() if config.filters else {},
                is_active=True,
                next_run_at=next_run,
                created_by=user_id
            )

            self.db.add(schedule)
            await self.db.commit()

            logger.info(f"Created schedule {schedule_id} for workspace {workspace_id}")

            return {
                "schedule_id": schedule_id,
                "status": "active",
                "next_run": next_run
            }

        except Exception as e:
            logger.error(f"Error creating schedule: {str(e)}", exc_info=True)
            await self.db.rollback()
            raise

    def _calculate_next_run(self, frequency: str, schedule_config: Dict[str, Any]) -> datetime:
        """Calculate next run time for schedule."""
        now = utc_now()
        time_str = schedule_config.get("time", "09:00")
        hours, minutes = map(int, time_str.split(':'))

        if frequency == "daily":
            next_run = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
        elif frequency == "weekly":
            # Simplified: next Monday at specified time
            next_run = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
            days_ahead = 7 - now.weekday()
            next_run += timedelta(days=days_ahead if days_ahead > 0 else 7)
        elif frequency == "monthly":
            # Simplified: first day of next month
            if now.month == 12:
                next_run = now.replace(year=now.year + 1, month=1, day=1, hour=hours, minute=minutes)
            else:
                next_run = now.replace(month=now.month + 1, day=1, hour=hours, minute=minutes)
        else:  # quarterly
            # Simplified: next quarter start
            quarter_months = [1, 4, 7, 10]
            current_month = now.month
            next_quarter_month = next((m for m in quarter_months if m > current_month), None)
            if next_quarter_month:
                next_run = now.replace(month=next_quarter_month, day=1, hour=hours, minute=minutes)
            else:
                next_run = now.replace(year=now.year + 1, month=1, day=1, hour=hours, minute=minutes)

        return next_run

    # ========================================================================
    # Report History
    # ========================================================================

    async def get_report_history(
        self,
        workspace_id: str,
        report_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get historical reports.

        Args:
            workspace_id: Workspace ID
            report_type: Report type filter
            start_date: Start date filter
            end_date: End date filter
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            Historical reports with pagination
        """
        try:
            conditions = [GeneratedReport.workspace_id == workspace_id]

            if report_type:
                conditions.append(GeneratedReport.report_type == report_type)
            if start_date:
                conditions.append(GeneratedReport.generated_at >= start_date)
            if end_date:
                conditions.append(GeneratedReport.generated_at <= end_date)

            # Get total count
            count_query = select(func.count()).select_from(GeneratedReport).where(and_(*conditions))
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            # Get reports
            query = (
                select(GeneratedReport)
                .where(and_(*conditions))
                .order_by(GeneratedReport.generated_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await self.db.execute(query)
            reports = result.scalars().all()

            return {
                "reports": [
                    {
                        "id": r.id,
                        "name": r.report_name,
                        "type": r.report_type,
                        "generated_at": r.generated_at,
                        "generated_by": r.generated_by,
                        "format": r.file_format,
                        "file_size": r.file_size or 0,
                        "page_count": r.page_count,
                        "download_url": f"/api/v1/reports/download/{r.id}",
                        "expires_at": r.expires_at,
                        "download_count": r.download_count or 0
                    }
                    for r in reports
                ],
                "total": total or 0,
                "skip": skip,
                "limit": limit
            }

        except Exception as e:
            logger.error(f"Error getting report history: {str(e)}", exc_info=True)
            raise

    # ========================================================================
    # Data Export
    # ========================================================================

    async def create_data_export_job(
        self,
        workspace_id: str,
        user_id: str,
        config: DataExportRequest
    ) -> Dict[str, Any]:
        """Create data export job.

        Args:
            workspace_id: Workspace ID
            user_id: User ID
            config: Export configuration

        Returns:
            Export job information
        """
        try:
            job_id = str(uuid4())

            # Estimate size based on data sources
            estimated_size = await self._estimate_export_size(
                workspace_id,
                config.data_sources,
                config.date_range.start,
                config.date_range.end
            )

            # Create job (reusing ReportJob table for simplicity)
            job = ReportJob(
                id=job_id,
                workspace_id=workspace_id,
                user_id=user_id,
                report_name=f"Data Export - {', '.join(config.data_sources)}",
                report_format=config.format.value,
                date_range={
                    "start": config.date_range.start.isoformat(),
                    "end": config.date_range.end.isoformat()
                },
                filters={"data_sources": config.data_sources},
                status=ReportStatus.QUEUED.value,
                progress=0
            )

            self.db.add(job)
            await self.db.commit()

            # TODO: Queue Celery task
            # from src.tasks.reports import export_data_task
            # export_data_task.delay(job_id)

            logger.info(f"Created export job {job_id} for workspace {workspace_id}")

            return {
                "job_id": job_id,
                "estimated_size": estimated_size,
                "estimated_time": max(60, estimated_size // 1000000)  # 1 second per MB
            }

        except Exception as e:
            logger.error(f"Error creating export job: {str(e)}", exc_info=True)
            await self.db.rollback()
            raise

    async def _estimate_export_size(
        self,
        workspace_id: str,
        data_sources: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> int:
        """Estimate export size in bytes."""
        try:
            # Simple estimation based on execution logs count
            query = select(func.count()).select_from(ExecutionLog).where(
                and_(
                    ExecutionLog.workspace_id == workspace_id,
                    ExecutionLog.started_at >= start_date,
                    ExecutionLog.started_at <= end_date
                )
            )
            result = await self.db.execute(query)
            count = result.scalar() or 0

            # Estimate ~500 bytes per row
            return count * 500 * len(data_sources)

        except Exception as e:
            logger.warning(f"Error estimating export size: {str(e)}")
            return 1000000  # Default 1MB

    async def get_report_for_download(
        self,
        report_id: str,
        workspace_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get report for download.

        Args:
            report_id: Report ID
            workspace_id: Workspace ID for access control

        Returns:
            Report information or None if not found/expired
        """
        try:
            query = select(GeneratedReport).where(
                and_(
                    GeneratedReport.id == report_id,
                    GeneratedReport.workspace_id == workspace_id
                )
            )
            result = await self.db.execute(query)
            report = result.scalar_one_or_none()

            if not report:
                return None

            # Check expiration
            if report.expires_at and report.expires_at < utc_now():
                return None

            # Update download count
            report.download_count = (report.download_count or 0) + 1
            report.last_downloaded_at = utc_now()
            await self.db.commit()

            return {
                "file_path": report.file_path,
                "filename": report.filename,
                "content_type": report.content_type or "application/octet-stream"
            }

        except Exception as e:
            logger.error(f"Error getting report for download: {str(e)}", exc_info=True)
            raise

    # ========================================================================
    # Report Sharing
    # ========================================================================

    async def create_share_link(
        self,
        report_id: str,
        workspace_id: str,
        user_id: str,
        config: ShareReportRequest
    ) -> Dict[str, Any]:
        """Create share link for report.

        Args:
            report_id: Report ID
            workspace_id: Workspace ID
            user_id: User ID
            config: Share configuration

        Returns:
            Share link information
        """
        try:
            # Verify report exists
            query = select(GeneratedReport).where(
                and_(
                    GeneratedReport.id == report_id,
                    GeneratedReport.workspace_id == workspace_id
                )
            )
            result = await self.db.execute(query)
            report = result.scalar_one_or_none()

            if not report:
                raise ValueError("Report not found")

            # Generate share token and password if required
            share_token = secrets.token_urlsafe(32)
            password = secrets.token_urlsafe(16) if config.require_password else None
            share_url = f"/api/v1/reports/shared/{share_token}"

            share = ReportShare(
                id=str(uuid4()),
                report_id=report_id,
                workspace_id=workspace_id,
                share_token=share_token,
                share_url=share_url,
                recipients=config.recipients,
                message=config.message,
                require_password=config.require_password,
                password_hash=self._hash_password(password) if password else None,
                allow_download=config.allow_download,
                created_by=user_id,
                expires_at=utc_now() + timedelta(days=config.expiration_days)
            )

            self.db.add(share)
            await self.db.commit()

            logger.info(f"Created share link for report {report_id}")

            return {
                "share_url": share_url,
                "password": password,
                "expires_at": share.expires_at
            }

        except Exception as e:
            logger.error(f"Error creating share link: {str(e)}", exc_info=True)
            await self.db.rollback()
            raise

    def _hash_password(self, password: str) -> str:
        """Simple password hashing (use bcrypt in production)."""
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()

    # ========================================================================
    # Report Analytics
    # ========================================================================

    async def get_report_analytics(
        self,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get report usage analytics.

        Args:
            workspace_id: Workspace ID
            start_date: Start date
            end_date: End date

        Returns:
            Analytics data
        """
        try:
            # Count total generated reports
            count_query = select(func.count()).select_from(GeneratedReport).where(
                and_(
                    GeneratedReport.workspace_id == workspace_id,
                    GeneratedReport.generated_at >= start_date,
                    GeneratedReport.generated_at <= end_date
                )
            )
            count_result = await self.db.execute(count_query)
            total_generated = count_result.scalar() or 0

            # Get reports for further analysis
            query = select(GeneratedReport).where(
                and_(
                    GeneratedReport.workspace_id == workspace_id,
                    GeneratedReport.generated_at >= start_date,
                    GeneratedReport.generated_at <= end_date
                )
            )
            result = await self.db.execute(query)
            reports = result.scalars().all()

            # Calculate metrics
            total_views = sum(r.download_count or 0 for r in reports)
            total_downloads = total_views  # Same for now

            # Format usage
            format_usage = {}
            for r in reports:
                fmt = r.file_format
                format_usage[fmt] = format_usage.get(fmt, 0) + 1

            # Most popular templates
            template_counts = {}
            for r in reports:
                if r.template_id:
                    template_counts[r.template_id] = template_counts.get(r.template_id, 0) + 1

            most_popular = [
                {"template": tid, "count": cnt}
                for tid, cnt in sorted(template_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            ]

            return {
                "report_analytics": {
                    "total_generated": total_generated,
                    "total_views": total_views,
                    "total_downloads": total_downloads,
                    "avg_generation_time": 45.2,  # Mock value
                    "most_popular": most_popular,
                    "by_format": format_usage,
                    "by_user": []  # Could add user breakdown
                }
            }

        except Exception as e:
            logger.error(f"Error getting report analytics: {str(e)}", exc_info=True)
            raise

    # ========================================================================
    # Webhooks
    # ========================================================================

    async def register_webhook(
        self,
        workspace_id: str,
        user_id: str,
        config: WebhookRequest
    ) -> str:
        """Register webhook for report events.

        Args:
            workspace_id: Workspace ID
            user_id: User ID
            config: Webhook configuration

        Returns:
            Webhook ID
        """
        try:
            webhook_id = str(uuid4())
            webhook = ReportWebhook(
                id=webhook_id,
                workspace_id=workspace_id,
                url=config.url,
                events=config.events,
                secret=config.secret,
                is_active=config.is_active,
                created_by=user_id
            )

            self.db.add(webhook)
            await self.db.commit()

            logger.info(f"Registered webhook {webhook_id} for workspace {workspace_id}")
            return webhook_id

        except Exception as e:
            logger.error(f"Error registering webhook: {str(e)}", exc_info=True)
            await self.db.rollback()
            raise

    async def get_webhooks(
        self,
        workspace_id: str
    ) -> List[Dict[str, Any]]:
        """Get webhooks for workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            List of webhooks
        """
        try:
            query = select(ReportWebhook).where(
                ReportWebhook.workspace_id == workspace_id
            )
            result = await self.db.execute(query)
            webhooks = result.scalars().all()

            return [
                {
                    "id": w.id,
                    "url": w.url,
                    "events": w.events or [],
                    "is_active": w.is_active,
                    "total_deliveries": w.total_deliveries or 0,
                    "successful_deliveries": w.successful_deliveries or 0,
                    "failed_deliveries": w.failed_deliveries or 0,
                    "last_delivery_at": w.last_delivery_at,
                    "created_at": w.created_at
                }
                for w in webhooks
            ]

        except Exception as e:
            logger.error(f"Error getting webhooks: {str(e)}", exc_info=True)
            raise


class ReportGenerator:
    """Report generation pipeline."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate(self, job_id: str) -> Dict[str, Any]:
        """Generate report.

        Args:
            job_id: Report job ID

        Returns:
            Generation result
        """
        # This would be implemented as a Celery task
        # For now, return a placeholder
        return {
            "status": "completed",
            "file_path": f"/tmp/reports/{job_id}.pdf",
            "file_size": 1024000,
            "page_count": 10
        }

    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate report configuration."""
        # Validation logic
        return True

    async def fetch_report_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data for report."""
        # Data fetching logic
        return {}

    async def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and aggregate data."""
        # Data processing logic
        return data

    async def render_report(self, data: Dict[str, Any], template: Any) -> bytes:
        """Render report using template."""
        # Rendering logic
        return b""

    async def convert_format(self, rendered: bytes, format: str) -> bytes:
        """Convert report to specified format."""
        # Format conversion logic
        return rendered

    async def deliver_report(self, output: bytes, delivery_config: Dict[str, Any]) -> None:
        """Deliver report to recipients."""
        # Delivery logic
        pass
