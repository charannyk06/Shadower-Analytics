"""Export processor service for data extraction and transformation."""

import os
import hashlib
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import uuid

from ...models.database.exports import (
    ExportJob,
    ExportFile,
    ExportMetadata,
    ExportStatus,
    ExportFormat,
)
from ...models.schemas.exports import DataSourceConfig, ExportConfig
from . import csv_export, json_export, excel_export, parquet_export


logger = logging.getLogger(__name__)


class ExportProcessor:
    """Main export processing pipeline."""

    def __init__(self, db_session: AsyncSession, export_dir: str = "/tmp/exports"):
        """Initialize export processor.

        Args:
            db_session: Database session
            export_dir: Directory to store export files
        """
        self.db = db_session
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    async def process_export(self, job_id: str) -> None:
        """Main export processing pipeline.

        Args:
            job_id: Export job ID
        """
        job = await self._get_job(job_id)

        try:
            # 1. Initialize export
            await self._initialize_export(job)

            # 2. Extract and process data
            files_created = []
            for source_idx, source in enumerate(job.data_sources):
                logger.info(f"Processing data source {source_idx + 1}/{len(job.data_sources)}")

                # Extract data
                data_generator = self._extract_data(source, job.workspace_id)

                # Transform and write to file
                file_info = await self._process_data_source(
                    job,
                    source,
                    data_generator,
                    source_idx
                )

                if file_info:
                    files_created.append(file_info)

            # 3. Finalize export
            await self._finalize_export(job, files_created)

            # 4. Deliver export (if configured)
            if job.delivery_method != "download":
                await self._deliver_export(job)

        except Exception as e:
            await self._handle_export_error(job, e)
            raise

    async def _get_job(self, job_id: str) -> ExportJob:
        """Get export job by ID."""
        result = await self.db.execute(
            select(ExportJob).where(ExportJob.id == uuid.UUID(job_id))
        )
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError(f"Export job {job_id} not found")
        return job

    async def _initialize_export(self, job: ExportJob) -> None:
        """Initialize export job."""
        job.status = ExportStatus.PROCESSING
        job.started_at = datetime.utcnow()
        job.progress_percent = 0.0

        await self.db.commit()
        logger.info(f"Initialized export job {job.id}")

    async def _extract_data(
        self,
        source: Dict[str, Any],
        workspace_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Extract data from source.

        Args:
            source: Data source configuration
            workspace_id: Workspace ID for filtering

        Yields:
            Data rows as dictionaries
        """
        source_type = source.get("type")
        filters = source.get("filters", {})
        fields = source.get("fields")

        # Build query based on source type
        query = self._build_query(source_type, workspace_id, filters, fields)

        # Execute query and yield results
        result = await self.db.execute(text(query))

        for row in result:
            # Convert row to dictionary
            yield dict(row._mapping)

    def _build_query(
        self,
        source_type: str,
        workspace_id: str,
        filters: Dict[str, Any],
        fields: Optional[List[str]]
    ) -> str:
        """Build SQL query for data extraction.

        Args:
            source_type: Type of data source
            workspace_id: Workspace ID
            filters: Additional filters
            fields: Fields to select

        Returns:
            SQL query string
        """
        # Map source types to table names
        table_map = {
            "user_activity": "user_activity_logs",
            "agent_performance": "agent_metrics",
            "credit_consumption": "credit_usage",
            "error_logs": "error_tracking",
            "execution_logs": "execution_logs",
        }

        table_name = table_map.get(source_type, source_type)

        # Build SELECT clause
        if fields:
            select_clause = ", ".join(fields)
        else:
            select_clause = "*"

        # Build WHERE clause
        where_clauses = [f"workspace_id = '{workspace_id}'"]

        # Add date range filter
        date_range = filters.get("date_range")
        if date_range:
            start_date = date_range.get("start")
            end_date = date_range.get("end")
            if start_date:
                where_clauses.append(f"created_at >= '{start_date}'")
            if end_date:
                where_clauses.append(f"created_at <= '{end_date}'")

        # Add agent IDs filter
        agent_ids = filters.get("agent_ids")
        if agent_ids:
            agent_ids_str = "', '".join(agent_ids)
            where_clauses.append(f"agent_id IN ('{agent_ids_str}')")

        # Add user IDs filter
        user_ids = filters.get("user_ids")
        if user_ids:
            user_ids_str = "', '".join(user_ids)
            where_clauses.append(f"user_id IN ('{user_ids_str}')")

        where_clause = " AND ".join(where_clauses)

        # Build full query
        query = f"SELECT {select_clause} FROM {table_name} WHERE {where_clause}"

        # Add aggregation if specified
        aggregation = filters.get("aggregation")
        if aggregation:
            # This is a simplified example
            # In production, you'd want more sophisticated aggregation logic
            if aggregation == "daily":
                query += " GROUP BY DATE(created_at)"

        return query

    async def _process_data_source(
        self,
        job: ExportJob,
        source: Dict[str, Any],
        data_generator: AsyncGenerator,
        source_idx: int
    ) -> Optional[Dict[str, Any]]:
        """Process data source and write to file.

        Args:
            job: Export job
            source: Data source configuration
            data_generator: Generator yielding data rows
            source_idx: Index of this data source

        Returns:
            File information dictionary
        """
        # Generate filename
        source_type = source.get("type", "data")
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{job.name}_{source_type}_{timestamp}_{source_idx}"

        # Get format extension
        format_ext = self._get_format_extension(job.format)
        compression_ext = self._get_compression_extension(job.compression)

        filename = f"{base_filename}.{format_ext}{compression_ext}"
        file_path = self.export_dir / str(job.id) / filename

        # Create job directory
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write data to file
        fields = source.get("fields")
        row_count = await self._write_data_to_file(
            data_generator,
            str(file_path),
            job.format,
            job.compression,
            fields
        )

        if row_count == 0:
            return None

        # Calculate file size and checksum
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        checksum = self._calculate_checksum(str(file_path))

        # Create export file record
        export_file = ExportFile(
            job_id=job.id,
            filename=filename,
            file_path=str(file_path),
            file_index=source_idx,
            size_mb=file_size_mb,
            row_count=row_count,
            checksum=f"sha256:{checksum}",
        )

        self.db.add(export_file)
        await self.db.commit()

        # Update job progress
        job.files_created += 1
        job.rows_processed += row_count
        job.progress_percent = (source_idx + 1) / len(job.data_sources) * 100
        await self.db.commit()

        return {
            "filename": filename,
            "size_mb": file_size_mb,
            "rows": row_count,
            "checksum": f"sha256:{checksum}",
        }

    async def _write_data_to_file(
        self,
        data_generator: AsyncGenerator,
        file_path: str,
        format: str,
        compression: str,
        fields: Optional[List[str]] = None
    ) -> int:
        """Write data to file in specified format.

        Args:
            data_generator: Generator yielding data rows
            file_path: Path to output file
            format: Export format
            compression: Compression type
            fields: Optional list of field names

        Returns:
            Number of rows written
        """
        # Collect data (in production, you'd want to stream this)
        data = []
        async for row in data_generator:
            data.append(row)

        if not data:
            return 0

        # Determine fields if not provided
        if fields is None and len(data) > 0:
            fields = list(data[0].keys())

        # Write based on format
        if format == ExportFormat.CSV.value:
            csv_export.export_to_csv(
                data,
                columns=fields,
                output_path=file_path,
                compression=compression
            )
        elif format == ExportFormat.JSON.value:
            json_export.export_to_json(
                data,
                output_path=file_path,
                compression=compression
            )
        elif format == ExportFormat.EXCEL.value:
            excel_export.export_to_excel(
                data,
                output_path=file_path,
                columns=fields
            )
        elif format == ExportFormat.PARQUET.value:
            parquet_export.export_to_parquet(
                data,
                output_path=file_path,
                columns=fields,
                compression=compression if compression != "none" else "snappy"
            )

        return len(data)

    def _get_format_extension(self, format: str) -> str:
        """Get file extension for format."""
        extensions = {
            "csv": "csv",
            "json": "json",
            "excel": "xlsx",
            "parquet": "parquet",
        }
        return extensions.get(format, "dat")

    def _get_compression_extension(self, compression: str) -> str:
        """Get file extension for compression."""
        if compression == "none":
            return ""
        extensions = {
            "gzip": ".gz",
            "zip": ".zip",
            "bz2": ".bz2",
        }
        return extensions.get(compression, "")

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    async def _finalize_export(
        self,
        job: ExportJob,
        files_created: List[Dict[str, Any]]
    ) -> None:
        """Finalize export job.

        Args:
            job: Export job
            files_created: List of file information dictionaries
        """
        job.status = ExportStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.progress_percent = 100.0
        job.files = files_created

        # Calculate total size
        total_size = sum(f["size_mb"] for f in files_created)
        job.total_size_mb = total_size

        await self.db.commit()
        logger.info(f"Finalized export job {job.id}: {len(files_created)} files, {total_size:.2f} MB")

    async def _deliver_export(self, job: ExportJob) -> None:
        """Deliver export files based on delivery configuration.

        Args:
            job: Export job
        """
        # Placeholder for delivery implementation
        # In production, you would implement:
        # - Email delivery
        # - S3 upload
        # - FTP upload
        logger.info(f"Delivery method '{job.delivery_method}' not yet implemented")
        pass

    async def _handle_export_error(self, job: ExportJob, error: Exception) -> None:
        """Handle export error.

        Args:
            job: Export job
            error: Exception that occurred
        """
        job.status = ExportStatus.FAILED
        job.error_message = str(error)
        job.completed_at = datetime.utcnow()

        await self.db.commit()
        logger.error(f"Export job {job.id} failed: {error}")

    async def estimate_export(self, config: ExportConfig, workspace_id: str) -> Dict[str, Any]:
        """Estimate export size and time.

        Args:
            config: Export configuration
            workspace_id: Workspace ID

        Returns:
            Dictionary with estimates
        """
        total_rows = 0
        total_size_mb = 0.0

        for source in config.data_sources:
            # Estimate row count
            count_query = self._build_count_query(
                source.type,
                workspace_id,
                source.filters.dict() if source.filters else {}
            )
            result = await self.db.execute(text(count_query))
            row_count = result.scalar() or 0
            total_rows += row_count

            # Estimate size (rough estimate: 1KB per row)
            estimated_size_mb = (row_count * 1024) / (1024 * 1024)
            total_size_mb += estimated_size_mb

        # Estimate time (rough estimate: 100,000 rows per minute)
        estimated_time_seconds = int(total_rows / 100000 * 60)
        if estimated_time_seconds < 1:
            estimated_time_seconds = 1

        return {
            "size_mb": round(total_size_mb, 2),
            "time_seconds": estimated_time_seconds,
            "row_count": total_rows,
        }

    def _build_count_query(
        self,
        source_type: str,
        workspace_id: str,
        filters: Dict[str, Any]
    ) -> str:
        """Build count query for estimation."""
        table_map = {
            "user_activity": "user_activity_logs",
            "agent_performance": "agent_metrics",
            "credit_consumption": "credit_usage",
            "error_logs": "error_tracking",
            "execution_logs": "execution_logs",
        }

        table_name = table_map.get(source_type, source_type)
        where_clauses = [f"workspace_id = '{workspace_id}'"]

        # Add filters (simplified)
        date_range = filters.get("date_range")
        if date_range:
            start = date_range.get("start")
            end = date_range.get("end")
            if start:
                where_clauses.append(f"created_at >= '{start}'")
            if end:
                where_clauses.append(f"created_at <= '{end}'")

        where_clause = " AND ".join(where_clauses)
        return f"SELECT COUNT(*) FROM {table_name} WHERE {where_clause}"
