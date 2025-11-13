"""Parquet export functionality."""

from typing import List, Dict, Optional
from datetime import datetime, date


def export_to_parquet(
    data: List[Dict],
    output_path: str,
    columns: Optional[List[str]] = None,
    compression: str = "snappy"
) -> str:
    """Export data to Parquet format.

    Args:
        data: List of dictionaries to export
        output_path: File path to write to
        columns: Optional list of column names to include
        compression: Compression algorithm (snappy, gzip, brotli, zstd, none)

    Returns:
        File path

    Note:
        This requires pyarrow or fastparquet to be installed:
        - pip install pyarrow (recommended)
        - pip install fastparquet
    """
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        raise ImportError(
            "pyarrow is required for Parquet export. "
            "Install it with: pip install pyarrow"
        )

    if not data:
        return output_path

    # Determine columns
    if columns is None:
        columns = list(data[0].keys())

    # Convert data to Arrow table
    # Create dict of lists for each column
    table_data = {col: [] for col in columns}

    for row in data:
        for col in columns:
            value = row.get(col)
            # Convert datetime objects to timestamp
            if isinstance(value, (datetime, date)):
                value = value
            table_data[col].append(value)

    # Create Arrow table
    table = pa.Table.from_pydict(table_data)

    # Write to Parquet file
    pq.write_table(
        table,
        output_path,
        compression=compression if compression != "none" else None
    )

    return output_path


def stream_to_parquet(
    data_generator,
    output_path: str,
    columns: List[str],
    compression: str = "snappy",
    batch_size: int = 10000
) -> int:
    """Stream data to Parquet file in batches.

    Args:
        data_generator: Generator that yields dictionaries
        output_path: File path to write to
        columns: Column names
        compression: Compression algorithm
        batch_size: Number of rows per batch

    Returns:
        Number of rows written
    """
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        raise ImportError(
            "pyarrow is required for Parquet export. "
            "Install it with: pip install pyarrow"
        )

    row_count = 0
    batch_data = {col: [] for col in columns}
    writer = None
    schema = None

    for row in data_generator:
        for col in columns:
            value = row.get(col)
            batch_data[col].append(value)

        row_count += 1

        if len(batch_data[columns[0]]) >= batch_size:
            # Create table from batch
            table = pa.Table.from_pydict(batch_data)

            if writer is None:
                # Initialize writer with schema from first batch
                schema = table.schema
                writer = pq.ParquetWriter(
                    output_path,
                    schema,
                    compression=compression if compression != "none" else None
                )

            writer.write_table(table)

            # Clear batch
            batch_data = {col: [] for col in columns}

    # Write remaining data
    if batch_data[columns[0]]:
        table = pa.Table.from_pydict(batch_data)

        if writer is None:
            schema = table.schema
            writer = pq.ParquetWriter(
                output_path,
                schema,
                compression=compression if compression != "none" else None
            )

        writer.write_table(table)

    if writer:
        writer.close()

    return row_count


def export_to_parquet_partitioned(
    data: List[Dict],
    output_dir: str,
    partition_cols: List[str],
    compression: str = "snappy"
) -> str:
    """Export data to partitioned Parquet files.

    Args:
        data: List of dictionaries to export
        output_dir: Directory path to write partitioned files
        partition_cols: Columns to partition by (e.g., ['year', 'month'])
        compression: Compression algorithm

    Returns:
        Output directory path
    """
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        raise ImportError(
            "pyarrow is required for Parquet export. "
            "Install it with: pip install pyarrow"
        )

    if not data:
        return output_dir

    # Convert to Arrow table
    columns = list(data[0].keys())
    table_data = {col: [] for col in columns}

    for row in data:
        for col in columns:
            table_data[col].append(row.get(col))

    table = pa.Table.from_pydict(table_data)

    # Write partitioned dataset
    pq.write_to_dataset(
        table,
        root_path=output_dir,
        partition_cols=partition_cols,
        compression=compression if compression != "none" else None
    )

    return output_dir


def read_parquet(file_path: str) -> List[Dict]:
    """Read Parquet file into list of dictionaries.

    Args:
        file_path: Path to Parquet file

    Returns:
        List of dictionaries
    """
    try:
        import pyarrow.parquet as pq
    except ImportError:
        raise ImportError(
            "pyarrow is required for Parquet export. "
            "Install it with: pip install pyarrow"
        )

    table = pq.read_table(file_path)
    return table.to_pylist()
