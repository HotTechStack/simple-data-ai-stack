"""Polars data transformation tools."""

import tempfile
from pathlib import Path
from uuid import uuid4
import polars as pl
from ..types import Artifact, SessionContext


async def run_polars(
    input_uri: str,
    operations: str,
    output_uri: str = None,
    session_context: SessionContext = None
) -> Artifact:
    """
    Run Polars transformation on a dataset.

    Args:
        input_uri: Path to input file (parquet, csv, json)
        operations: Polars operations as string (e.g., "filter(pl.col('revenue') > 100).select(['product', 'revenue'])")
        output_uri: Path to output file (auto-generated if not provided)
        session_context: Session context

    Returns:
        Artifact with transformation results

    Example:
        await run_polars(
            input_uri="/tmp/sales.parquet",
            operations="filter(pl.col('revenue') > 100).group_by('region').agg(pl.col('revenue').sum())",
            output_uri="/tmp/regional_sales.parquet"
        )
    """
    # Determine input format
    if input_uri.endswith('.parquet'):
        df = pl.read_parquet(input_uri)
    elif input_uri.endswith('.csv'):
        df = pl.read_csv(input_uri)
    elif input_uri.endswith('.json'):
        df = pl.read_json(input_uri)
    else:
        raise ValueError(f"Unsupported file format: {input_uri}")

    # Apply transformations
    # NOTE: Using eval for simplicity - in production, use AST parsing or predefined transforms
    try:
        result = eval(f"df.{operations}")
    except Exception as e:
        raise ValueError(f"Polars operation failed: {e}\nOperation: {operations}")

    # Auto-generate output path if not provided
    if not output_uri:
        output_uri = str(Path(tempfile.gettempdir()) / f"polars_{uuid4()}.parquet")

    # Write output
    result.write_parquet(output_uri)

    return Artifact(
        uri=output_uri,
        format="parquet",
        schema={col: str(dtype) for col, dtype in result.schema.items()},
        lineage={
            "tool": "run_polars",
            "input": input_uri,
            "operations": operations
        },
        row_count=len(result)
    )


async def transform_csv(
    input_csv: str,
    output_parquet: str = None,
    filter_expr: str = None,
    select_cols: list = None,
    session_context: SessionContext = None
) -> Artifact:
    """
    Transform CSV to Parquet with optional filtering and column selection.

    Args:
        input_csv: Path to input CSV file
        output_parquet: Path to output Parquet file (auto-generated if not provided)
        filter_expr: Filter expression (e.g., "pl.col('revenue') > 100")
        select_cols: List of columns to select
        session_context: Session context

    Returns:
        Artifact with transformed data

    Example:
        await transform_csv(
            input_csv="/data/sales.csv",
            filter_expr="pl.col('revenue') > 1000",
            select_cols=["product", "revenue", "region"]
        )
    """
    df = pl.read_csv(input_csv)

    # Apply filter
    if filter_expr:
        try:
            df = eval(f"df.filter({filter_expr})")
        except Exception as e:
            raise ValueError(f"Filter failed: {e}\nExpression: {filter_expr}")

    # Select columns
    if select_cols:
        df = df.select(select_cols)

    # Auto-generate output path
    if not output_parquet:
        output_parquet = str(Path(tempfile.gettempdir()) / f"transformed_{uuid4()}.parquet")

    # Write parquet
    df.write_parquet(output_parquet)

    return Artifact(
        uri=output_parquet,
        format="parquet",
        schema={col: str(dtype) for col, dtype in df.schema.items()},
        lineage={
            "tool": "transform_csv",
            "input": input_csv,
            "filter": filter_expr,
            "columns": select_cols
        },
        row_count=len(df)
    )


async def join_datasets(
    left_uri: str,
    right_uri: str,
    on: str,
    how: str = "inner",
    output_uri: str = None,
    session_context: SessionContext = None
) -> Artifact:
    """
    Join two datasets.

    Args:
        left_uri: Path to left dataset (parquet/csv)
        right_uri: Path to right dataset (parquet/csv)
        on: Column name to join on
        how: Join type ("inner", "left", "outer", "cross")
        output_uri: Path to output file
        session_context: Session context

    Returns:
        Artifact with joined data

    Example:
        await join_datasets(
            left_uri="/tmp/sales.parquet",
            right_uri="/tmp/products.parquet",
            on="product_id",
            how="left"
        )
    """
    # Read datasets
    if left_uri.endswith('.parquet'):
        left_df = pl.read_parquet(left_uri)
    else:
        left_df = pl.read_csv(left_uri)

    if right_uri.endswith('.parquet'):
        right_df = pl.read_parquet(right_uri)
    else:
        right_df = pl.read_csv(right_uri)

    # Join
    result = left_df.join(right_df, on=on, how=how)

    # Auto-generate output path
    if not output_uri:
        output_uri = str(Path(tempfile.gettempdir()) / f"joined_{uuid4()}.parquet")

    # Write output
    result.write_parquet(output_uri)

    return Artifact(
        uri=output_uri,
        format="parquet",
        schema={col: str(dtype) for col, dtype in result.schema.items()},
        lineage={
            "tool": "join_datasets",
            "left": left_uri,
            "right": right_uri,
            "on": on,
            "how": how
        },
        row_count=len(result)
    )


async def aggregate_data(
    input_uri: str,
    group_by: list,
    aggregations: dict,
    output_uri: str = None,
    session_context: SessionContext = None
) -> Artifact:
    """
    Aggregate data with group by.

    Args:
        input_uri: Path to input file
        group_by: List of columns to group by
        aggregations: Dict of column -> aggregation function
                     e.g., {"revenue": "sum", "orders": "count"}
        output_uri: Path to output file
        session_context: Session context

    Returns:
        Artifact with aggregated data

    Example:
        await aggregate_data(
            input_uri="/tmp/sales.parquet",
            group_by=["region", "product"],
            aggregations={"revenue": "sum", "quantity": "mean"}
        )
    """
    # Read data
    if input_uri.endswith('.parquet'):
        df = pl.read_parquet(input_uri)
    else:
        df = pl.read_csv(input_uri)

    # Build aggregation expressions
    agg_exprs = []
    for col, func in aggregations.items():
        if func == "sum":
            agg_exprs.append(pl.col(col).sum().alias(f"{col}_{func}"))
        elif func == "mean":
            agg_exprs.append(pl.col(col).mean().alias(f"{col}_{func}"))
        elif func == "count":
            agg_exprs.append(pl.col(col).count().alias(f"{col}_{func}"))
        elif func == "min":
            agg_exprs.append(pl.col(col).min().alias(f"{col}_{func}"))
        elif func == "max":
            agg_exprs.append(pl.col(col).max().alias(f"{col}_{func}"))
        else:
            raise ValueError(f"Unsupported aggregation: {func}")

    # Group by and aggregate
    result = df.group_by(group_by).agg(agg_exprs)

    # Auto-generate output path
    if not output_uri:
        output_uri = str(Path(tempfile.gettempdir()) / f"aggregated_{uuid4()}.parquet")

    # Write output
    result.write_parquet(output_uri)

    return Artifact(
        uri=output_uri,
        format="parquet",
        schema={col: str(dtype) for col, dtype in result.schema.items()},
        lineage={
            "tool": "aggregate_data",
            "input": input_uri,
            "group_by": group_by,
            "aggregations": aggregations
        },
        row_count=len(result)
    )
