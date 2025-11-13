"""CSV export functionality."""

import csv
import gzip
import zipfile
import bz2
import io
from typing import List, Dict, Optional, BinaryIO
from pathlib import Path


def export_to_csv(
    data: List[Dict],
    columns: Optional[List[str]] = None,
    output_path: Optional[str] = None,
    compression: str = "none"
) -> str:
    """Export data to CSV format.

    Args:
        data: List of dictionaries to export
        columns: Optional list of column names to include
        output_path: Optional file path to write to
        compression: Compression type (none, gzip, zip, bz2)

    Returns:
        CSV string or file path if output_path is provided
    """
    if not data:
        return ""

    # Determine columns
    if columns is None and len(data) > 0:
        columns = list(data[0].keys())

    # Create CSV content
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()

    for row in data:
        writer.writerow({k: row.get(k, "") for k in columns})

    csv_content = output.getvalue()

    # If no output path, return string
    if output_path is None:
        return csv_content

    # Write to file with optional compression
    csv_bytes = csv_content.encode('utf-8')

    if compression == "gzip":
        with gzip.open(output_path, 'wb') as f:
            f.write(csv_bytes)
    elif compression == "zip":
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Extract filename from path
            filename = Path(output_path).stem + '.csv'
            zf.writestr(filename, csv_bytes)
    elif compression == "bz2":
        with bz2.open(output_path, 'wb') as f:
            f.write(csv_bytes)
    else:
        # No compression
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)

    return output_path


def export_metrics_to_csv(metrics: List[Dict]) -> str:
    """Export metrics data to CSV."""
    return export_to_csv(metrics)


def stream_to_csv(
    data_generator,
    columns: List[str],
    output_file: BinaryIO,
    compression: str = "none"
) -> int:
    """Stream data to CSV file.

    Args:
        data_generator: Generator that yields dictionaries
        columns: Column names
        output_file: Binary file object to write to
        compression: Compression type

    Returns:
        Number of rows written
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()

    row_count = 0
    buffer_size = 1000
    buffer = []

    for row in data_generator:
        buffer.append(row)
        row_count += 1

        if len(buffer) >= buffer_size:
            _write_buffer_to_csv(writer, buffer, output)
            _flush_to_file(output, output_file, compression)
            buffer.clear()
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=columns)

    # Write remaining buffer
    if buffer:
        _write_buffer_to_csv(writer, buffer, output)
        _flush_to_file(output, output_file, compression)

    return row_count


def _write_buffer_to_csv(writer, buffer: List[Dict], output: io.StringIO):
    """Write buffer to CSV writer."""
    for row in buffer:
        writer.writerow(row)


def _flush_to_file(
    output: io.StringIO,
    output_file: BinaryIO,
    compression: str
):
    """Flush string buffer to file with compression."""
    content = output.getvalue()
    if content:
        content_bytes = content.encode('utf-8')
        if compression == "gzip":
            content_bytes = gzip.compress(content_bytes)
        elif compression == "bz2":
            content_bytes = bz2.compress(content_bytes)
        output_file.write(content_bytes)
