"""JSON export functionality."""

import json
import gzip
import zipfile
import bz2
from typing import Dict, List, Any, Optional, BinaryIO
from datetime import datetime, date
from pathlib import Path


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""

    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def export_to_json(
    data: Any,
    pretty: bool = True,
    output_path: Optional[str] = None,
    compression: str = "none"
) -> str:
    """Export data to JSON format.

    Args:
        data: Data to export (dict, list, etc.)
        pretty: Whether to format JSON with indentation
        output_path: Optional file path to write to
        compression: Compression type (none, gzip, zip, bz2)

    Returns:
        JSON string or file path if output_path is provided
    """
    if pretty:
        json_content = json.dumps(data, cls=DateTimeEncoder, indent=2, sort_keys=True)
    else:
        json_content = json.dumps(data, cls=DateTimeEncoder)

    # If no output path, return string
    if output_path is None:
        return json_content

    # Write to file with optional compression
    json_bytes = json_content.encode('utf-8')

    if compression == "gzip":
        with gzip.open(output_path, 'wb') as f:
            f.write(json_bytes)
    elif compression == "zip":
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            filename = Path(output_path).stem + '.json'
            zf.writestr(filename, json_bytes)
    elif compression == "bz2":
        with bz2.open(output_path, 'wb') as f:
            f.write(json_bytes)
    else:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_content)

    return output_path


def export_metrics_to_json(metrics: Dict) -> str:
    """Export metrics data to JSON."""
    return export_to_json(metrics)


def stream_to_json(
    data_generator,
    output_file: BinaryIO,
    compression: str = "none"
) -> int:
    """Stream data to JSON Lines file (JSONL format).

    Args:
        data_generator: Generator that yields dictionaries
        output_file: Binary file object to write to
        compression: Compression type

    Returns:
        Number of rows written
    """
    row_count = 0
    buffer_size = 1000
    buffer = []

    for row in data_generator:
        json_line = json.dumps(row, cls=DateTimeEncoder) + '\n'
        buffer.append(json_line)
        row_count += 1

        if len(buffer) >= buffer_size:
            _flush_json_buffer(buffer, output_file, compression)
            buffer.clear()

    # Write remaining buffer
    if buffer:
        _flush_json_buffer(buffer, output_file, compression)

    return row_count


def _flush_json_buffer(
    buffer: List[str],
    output_file: BinaryIO,
    compression: str
):
    """Flush JSON buffer to file with compression."""
    content = ''.join(buffer)
    content_bytes = content.encode('utf-8')

    if compression == "gzip":
        content_bytes = gzip.compress(content_bytes)
    elif compression == "bz2":
        content_bytes = bz2.compress(content_bytes)

    output_file.write(content_bytes)
