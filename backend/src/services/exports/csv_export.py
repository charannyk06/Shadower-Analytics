"""CSV export functionality."""

import csv
import io
from typing import List, Dict


def export_to_csv(data: List[Dict], columns: List[str] = None) -> str:
    """Export data to CSV format.

    Args:
        data: List of dictionaries to export
        columns: Optional list of column names to include

    Returns:
        CSV string
    """
    if not data:
        return ""

    output = io.StringIO()

    # Determine columns
    if columns is None:
        columns = list(data[0].keys())

    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()

    for row in data:
        writer.writerow({k: row.get(k, "") for k in columns})

    return output.getvalue()


def export_metrics_to_csv(metrics: List[Dict]) -> str:
    """Export metrics data to CSV."""
    return export_to_csv(metrics)
