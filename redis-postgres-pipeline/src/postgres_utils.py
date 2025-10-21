"""Postgres utilities for pipeline operations.

This module demonstrates Postgres patterns from the blog:
- Connection pooling with PgBouncer (800 workers -> 25 connections)
- UNLOGGED tables for staging (3x faster writes)
- Materialized views for pre-computed aggregations
- Async I/O in Postgres 18 for mixed workloads
- Bulk operations with COPY for performance
"""

from typing import Any, Dict, List, Optional
import psycopg
from psycopg.rows import dict_row
from psycopg import sql
import polars as pl
from io import StringIO
from .config import postgres_config, pgbouncer_config


class PostgresConnection:
    """Wrapper for Postgres connections with best practices."""

    def __init__(self, use_pgbouncer: bool = True):
        """Initialize connection.

        Args:
            use_pgbouncer: If True, use PgBouncer pooling (recommended for workers)
        """
        self.config = pgbouncer_config if use_pgbouncer else postgres_config
        self.conn: Optional[psycopg.Connection] = None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def connect(self) -> psycopg.Connection:
        """Establish database connection."""
        self.conn = psycopg.connect(
            self.config.connection_string,
            row_factory=dict_row,
            autocommit=False,
        )
        return self.conn

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute(self, query: str, params: Optional[tuple] = None) -> None:
        """Execute a query without returning results."""
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            self.conn.commit()

    def fetchone(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """Fetch single row as dictionary."""
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()

    def fetchall(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Fetch all rows as list of dictionaries."""
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()


class StagingTable:
    """UNLOGGED table operations for fast staging.

    UNLOGGED tables skip WAL, giving 3x faster writes:
    - Perfect for temporary data that gets validated
    - Data is promoted to durable tables or discarded
    - Lost on crash, but that's acceptable for staging
    """

    def __init__(self, conn: PostgresConnection, table_name: str = "orders_staging"):
        self.conn = conn
        self.table_name = table_name

    def bulk_insert(self, df: pl.DataFrame) -> int:
        """Bulk insert DataFrame using COPY (fastest method)."""
        # Convert DataFrame to CSV in memory
        csv_buffer = StringIO()
        df.write_csv(csv_buffer)
        csv_buffer.seek(0)

        # Get column list from CSV header
        header = csv_buffer.readline().strip()
        columns = header

        # Use COPY for maximum performance with specific columns
        with self.conn.conn.cursor() as cur:
            with cur.copy(
                f"COPY {self.table_name}({columns}) FROM STDIN WITH (FORMAT CSV)"
            ) as copy:
                while data := csv_buffer.read(8192):
                    copy.write(data)

            self.conn.conn.commit()

        return len(df)

    def insert_batch(self, records: List[Dict[str, Any]]) -> int:
        """Insert batch of records using execute_values."""
        if not records:
            return 0

        # Build column names from first record
        columns = list(records[0].keys())
        values = [[r.get(col) for col in columns] for r in records]

        # Build INSERT query
        query = sql.SQL("INSERT INTO {table} ({fields}) VALUES ({placeholders})").format(
            table=sql.Identifier(self.table_name),
            fields=sql.SQL(', ').join(map(sql.Identifier, columns)),
            placeholders=sql.SQL(', ').join(sql.Placeholder() * len(columns))
        )

        with self.conn.conn.cursor() as cur:
            # Use executemany for batch insert
            cur.executemany(query, values)
            self.conn.conn.commit()

        return len(records)

    def count(self) -> int:
        """Get count of records in staging."""
        result = self.conn.fetchone(f"SELECT COUNT(*) as count FROM {self.table_name}")
        return result['count'] if result else 0

    def truncate(self) -> None:
        """Truncate staging table."""
        self.conn.execute(f"TRUNCATE {self.table_name}")

    def promote_to_production(self) -> int:
        """Promote staging data to production tables using stored procedure."""
        result = self.conn.fetchone("SELECT * FROM promote_staging_to_production()")
        return result['inserted_count'] if result else 0


class MaterializedViewManager:
    """Manage materialized views for pre-computed aggregations.

    Materialized views stop dashboards from hammering live queries:
    - Pre-compute expensive aggregations
    - Refresh on schedule or on-demand
    - Concurrent refresh allows queries during refresh
    """

    def __init__(self, conn: PostgresConnection):
        self.conn = conn

    def refresh_all(self) -> None:
        """Refresh all materialized views using helper function."""
        self.conn.execute("SELECT refresh_all_materialized_views()")

    def refresh_view(self, view_name: str, concurrent: bool = True) -> None:
        """Refresh single materialized view.

        Args:
            view_name: Name of the materialized view
            concurrent: If True, allows queries during refresh (requires unique index)
        """
        concurrent_clause = "CONCURRENTLY" if concurrent else ""
        self.conn.execute(f"REFRESH MATERIALIZED VIEW {concurrent_clause} {view_name}")

    def get_view_stats(self, view_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics about a materialized view."""
        query = """
            SELECT
                schemaname,
                matviewname,
                matviewowner,
                tablespace,
                hasindexes,
                ispopulated,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||matviewname)) as size
            FROM pg_matviews
            WHERE matviewname = %s
        """
        return self.conn.fetchone(query, (view_name,))

    def list_views(self) -> List[Dict[str, Any]]:
        """List all materialized views."""
        query = """
            SELECT
                matviewname,
                ispopulated,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||matviewname)) as size
            FROM pg_matviews
            WHERE schemaname = 'public'
            ORDER BY matviewname
        """
        return self.conn.fetchall(query)


class BulkLoader:
    """Efficient bulk loading using Polars and COPY.

    Demonstrates the pattern:
    1. One query pulls 500k rows
    2. Transform in-memory with Polars (6x faster than Pandas)
    3. Bulk write back with COPY in seconds
    """

    def __init__(self, conn: PostgresConnection):
        self.conn = conn

    def read_to_polars(
        self,
        query: str,
        params: Optional[tuple] = None,
        batch_size: int = 50000
    ) -> pl.DataFrame:
        """Read query results into Polars DataFrame.

        Uses server-side cursors for memory efficiency with large datasets.
        """
        with self.conn.conn.cursor(name='bulk_cursor') as cur:
            cur.execute(query, params)

            # Fetch in batches and build DataFrame
            dataframes = []
            while True:
                rows = cur.fetchmany(batch_size)
                if not rows:
                    break

                # Convert to Polars DataFrame
                if rows:
                    df_batch = pl.DataFrame(rows)
                    dataframes.append(df_batch)

            # Concatenate all batches
            if dataframes:
                return pl.concat(dataframes)
            else:
                return pl.DataFrame()

    def write_from_polars(
        self,
        df: pl.DataFrame,
        table_name: str,
        if_exists: str = 'append'
    ) -> int:
        """Write Polars DataFrame to table using COPY.

        Args:
            df: Polars DataFrame to write
            table_name: Target table name
            if_exists: 'append' or 'replace'
        """
        if if_exists == 'replace':
            self.conn.execute(f"TRUNCATE {table_name}")

        # Convert to CSV in memory
        csv_buffer = StringIO()
        df.write_csv(csv_buffer)
        csv_buffer.seek(0)

        # Skip header
        csv_buffer.readline()

        # COPY for maximum speed
        with self.conn.conn.cursor() as cur:
            with cur.copy(
                f"COPY {table_name} FROM STDIN WITH (FORMAT CSV)"
            ) as copy:
                while data := csv_buffer.read(8192):
                    copy.write(data)

            self.conn.conn.commit()

        return len(df)

    def transform_and_load(
        self,
        source_query: str,
        target_table: str,
        transform_fn,
        batch_size: int = 50000
    ) -> int:
        """Read, transform, and write in one operation.

        Args:
            source_query: SQL query to read source data
            target_table: Target table name
            transform_fn: Function that takes and returns Polars DataFrame
            batch_size: Batch size for reading

        Returns:
            Number of rows written
        """
        # Read data
        df = self.read_to_polars(source_query, batch_size=batch_size)

        if len(df) == 0:
            return 0

        # Transform with Polars
        df_transformed = transform_fn(df)

        # Write back
        return self.write_from_polars(df_transformed, target_table)


class LookupTableCache:
    """Load reference tables into memory/Redis.

    Small lookup tables (products, zip codes, currency rates)
    should be cached to avoid repeated joins.
    """

    def __init__(self, conn: PostgresConnection):
        self.conn = conn

    def load_products(self) -> pl.DataFrame:
        """Load product catalog into Polars DataFrame."""
        query = "SELECT * FROM product_catalog"
        with self.conn.conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            return pl.DataFrame(rows)

    def load_currency_rates(self) -> pl.DataFrame:
        """Load currency rates into Polars DataFrame."""
        query = "SELECT * FROM currency_rates"
        with self.conn.conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            return pl.DataFrame(rows)

    def load_zip_codes(self) -> pl.DataFrame:
        """Load zip code zones into Polars DataFrame."""
        query = "SELECT * FROM zip_code_zones"
        with self.conn.conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            return pl.DataFrame(rows)

    def load_all_to_dict(self) -> Dict[str, pl.DataFrame]:
        """Load all lookup tables into a dictionary."""
        return {
            'products': self.load_products(),
            'currency_rates': self.load_currency_rates(),
            'zip_codes': self.load_zip_codes(),
        }


def get_postgres_connection(use_pgbouncer: bool = True) -> PostgresConnection:
    """Get a Postgres connection.

    Args:
        use_pgbouncer: If True, connect through PgBouncer pool (recommended)
    """
    return PostgresConnection(use_pgbouncer=use_pgbouncer)
