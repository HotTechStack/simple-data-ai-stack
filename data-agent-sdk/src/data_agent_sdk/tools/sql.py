"""SQL tools."""

import tempfile
from pathlib import Path
from uuid import uuid4
import duckdb
from ..types import Artifact, SessionContext


async def run_sql(sql: str, session_context: SessionContext = None) -> Artifact:
    """Execute SQL query."""
    # Extract database path from session context
    database = ":memory:"
    if session_context and session_context.warehouse:
        warehouse = session_context.warehouse
        if warehouse.startswith("duckdb://"):
            database = warehouse.replace("duckdb://", "")

    conn = duckdb.connect(database)
    try:
        result = conn.execute(sql).pl()
        path = Path(tempfile.gettempdir()) / f"query_{uuid4()}.parquet"
        result.write_parquet(path)

        return Artifact(
            uri=str(path),
            format="parquet",
            schema={col: str(dtype) for col, dtype in result.schema.items()},
            lineage={"query": sql, "tool": "run_sql"},
            row_count=len(result),
        )
    finally:
        conn.close()


async def read_metadata(table: str, session_context: SessionContext = None):
    """Read table metadata."""
    # Extract database path from session context
    database = ":memory:"
    if session_context and session_context.warehouse:
        warehouse = session_context.warehouse
        if warehouse.startswith("duckdb://"):
            database = warehouse.replace("duckdb://", "")

    conn = duckdb.connect(database)
    try:
        schema = conn.execute(f"DESCRIBE {table}").fetchall()
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        return {
            "table": table,
            "schema": {row[0]: row[1] for row in schema},
            "row_count": count,
        }
    finally:
        conn.close()
