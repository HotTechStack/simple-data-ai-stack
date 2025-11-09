"""
Incremental Postgres -> Parquet -> DuckDB sync powered by Polars.

The script follows the "Copying Postgres to DuckDB Without Losing Your Mind" blueprint:
- Postgres `updated_at` + trigger tracks row changes.
- Incremental batches pull rows newer than the last checkpoint.
- Each batch lands in Parquet, then loads into DuckDB with INSERT OR REPLACE.
- Checkpoints live in SQLite so restarts resume automatically.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import duckdb
import polars as pl
import psycopg
from psycopg import sql
from psycopg.rows import dict_row

UTC = timezone.utc
DEFAULT_LAST_SYNC = datetime(1970, 1, 1, tzinfo=UTC)

PG_TO_DUCK: Dict[str, str] = {
    "integer": "INTEGER",
    "bigint": "BIGINT",
    "smallint": "SMALLINT",
    "numeric": "DECIMAL(18,4)",
    "double precision": "DOUBLE",
    "real": "REAL",
    "text": "TEXT",
    "character varying": "VARCHAR",
    "timestamp without time zone": "TIMESTAMP",
    "timestamp with time zone": "TIMESTAMPTZ",
    "boolean": "BOOLEAN",
}


@dataclass
class Settings:
    pg_host: str = field(default_factory=lambda: os.getenv("POSTGRES_HOST", "localhost"))
    pg_port: int = field(default_factory=lambda: int(os.getenv("POSTGRES_PORT", "5432")))
    pg_db: str = field(default_factory=lambda: os.getenv("POSTGRES_DB", "analytics"))
    pg_user: str = field(default_factory=lambda: os.getenv("POSTGRES_USER", "analyst"))
    pg_password: str = field(default_factory=lambda: os.getenv("POSTGRES_PASSWORD", "analyst"))
    pg_schema: str = field(default_factory=lambda: os.getenv("POSTGRES_SCHEMA", "public"))
    pg_table: str = field(default_factory=lambda: os.getenv("POSTGRES_TABLE", "subscriptions"))
    primary_key: str = field(default_factory=lambda: os.getenv("POSTGRES_PRIMARY_KEY", "id"))
    batch_size: int = field(default_factory=lambda: int(os.getenv("BATCH_SIZE", "10000")))

    duckdb_path: Path = field(default_factory=lambda: Path(os.getenv("DUCKDB_PATH", "./lake/warehouse.duckdb")))
    duckdb_table: str = field(default_factory=lambda: os.getenv("DUCKDB_TABLE", "analytics_subscriptions"))

    parquet_dir: Path = field(default_factory=lambda: Path(os.getenv("PARQUET_DIR", "./parquet")))
    state_dir: Path = field(default_factory=lambda: Path(os.getenv("STATE_DIR", "./state")))
    checkpoint_db: Optional[Path] = field(default=None)
    bootstrap_flag: Optional[Path] = field(default=None)
    sync_interval_seconds: int = field(default_factory=lambda: int(os.getenv("SYNC_INTERVAL_SECONDS", "0")))

    def __post_init__(self) -> None:
        if not isinstance(self.duckdb_path, Path):
            self.duckdb_path = Path(self.duckdb_path)
        if not isinstance(self.parquet_dir, Path):
            self.parquet_dir = Path(self.parquet_dir)
        if not isinstance(self.state_dir, Path):
            self.state_dir = Path(self.state_dir)
        self.checkpoint_db = (
            Path(os.getenv("CHECKPOINT_DB"))
            if os.getenv("CHECKPOINT_DB")
            else self.state_dir / "checkpoints.db"
        )
        self.bootstrap_flag = (
            Path(os.getenv("BOOTSTRAP_FLAG"))
            if os.getenv("BOOTSTRAP_FLAG")
            else self.state_dir / "bootstrap.done"
        )

    def postgres_dsn(self) -> str:
        return (
            f"host={self.pg_host} port={self.pg_port} dbname={self.pg_db} "
            f"user={self.pg_user} password={self.pg_password}"
        )


class CheckpointStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    last_sync TEXT NOT NULL,
                    row_count INTEGER NOT NULL
                )
                """
            )

    def current(self) -> Tuple[datetime, int]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT last_sync, row_count FROM checkpoints ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if not row:
            return DEFAULT_LAST_SYNC, 0
        last_sync = datetime.fromisoformat(row[0])
        if last_sync.tzinfo is None:
            last_sync = last_sync.replace(tzinfo=UTC)
        return last_sync, row[1]

    def write(self, last_sync: datetime, row_count: int) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO checkpoints (last_sync, row_count) VALUES (?, ?)",
                (last_sync.isoformat(), row_count),
            )


@contextmanager
def postgres_connection(settings: Settings):
    with psycopg.connect(settings.postgres_dsn(), autocommit=True, row_factory=dict_row) as conn:
        yield conn


def log(message: str) -> None:
    timestamp = datetime.now(tz=UTC).isoformat()
    print(f"[sync] {timestamp} {message}", flush=True)


def get_postgres_columns(conn, settings: Settings) -> List[Tuple[str, str]]:
    query = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
    """
    with conn.cursor() as cur:
        cur.execute(query, (settings.pg_schema, settings.pg_table))
        rows = cur.fetchall()
    return [(row["column_name"], row["data_type"]) for row in rows]


def ensure_duckdb_schema(
    conn: duckdb.DuckDBPyConnection, settings: Settings, pg_columns: Sequence[Tuple[str, str]]
) -> None:
    table_exists = conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [settings.duckdb_table],
    ).fetchone()[0]

    if not table_exists:
        column_sql = []
        for name, pg_type in pg_columns:
            duck_type = PG_TO_DUCK.get(pg_type, "VARCHAR")
            column_sql.append(f"{name} {duck_type}")
        pk_clause = f", PRIMARY KEY({settings.primary_key})" if settings.primary_key else ""
        ddl = f"CREATE TABLE {settings.duckdb_table} ({', '.join(column_sql)}{pk_clause})"
        log(f"Creating DuckDB table {settings.duckdb_table}")
        conn.execute(ddl)
        return

    duck_columns = {
        row[1]: row[2]
        for row in conn.execute(f"PRAGMA table_info('{settings.duckdb_table}')").fetchall()
    }
    for name, pg_type in pg_columns:
        if name in duck_columns:
            continue
        duck_type = PG_TO_DUCK.get(pg_type, "VARCHAR")
        log(f"Schema drift detected. Adding column {name} {duck_type} to DuckDB")
        conn.execute(
            f"ALTER TABLE {settings.duckdb_table} ADD COLUMN {name} {duck_type}"
        )


def write_parquet(df: pl.DataFrame, directory: Path, prefix: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%S%f")
    file_path = directory / f"{prefix}_{timestamp}.parquet"
    df.write_parquet(file_path)
    return file_path


def load_parquet_into_duckdb(
    parquet_path: Path, settings: Settings, pg_columns: Sequence[Tuple[str, str]]
) -> int:
    conn = duckdb.connect(str(settings.duckdb_path))
    try:
        ensure_duckdb_schema(conn, settings, pg_columns)
        row_count = conn.execute(
            "SELECT COUNT(*) FROM read_parquet(?)", [str(parquet_path)]
        ).fetchone()[0]
        log(f"Inserting {parquet_path.name} into DuckDB with INSERT OR REPLACE")
        conn.execute(
            f"""
            INSERT OR REPLACE INTO {settings.duckdb_table}
            SELECT * FROM read_parquet(?)
            """,
            [str(parquet_path)],
        )
        return row_count
    finally:
        conn.close()


def copy_full_table_to_parquet(
    conn, settings: Settings, parquet_dir: Path
) -> Tuple[Optional[Path], Optional[pl.DataFrame]]:
    parquet_dir.mkdir(parents=True, exist_ok=True)
    query = sql.SQL(
        "SELECT * FROM {}.{} ORDER BY updated_at"
    ).format(sql.Identifier(settings.pg_schema), sql.Identifier(settings.pg_table))
    with conn.cursor() as cur:
        log("Running SELECT * for bootstrap load")
        cur.execute(query)
        rows = cur.fetchall()

    if not rows:
        log("Bootstrap query returned no rows")
        return None, None

    df = pl.DataFrame(rows)
    for column in ("updated_at", "deleted_at"):
        if column in df.columns:
            df = df.with_columns(
                pl.col(column).cast(pl.Datetime(time_zone="UTC"), strict=False)
            )
    parquet_path = write_parquet(df, parquet_dir, "bootstrap")
    return parquet_path, df


def fetch_incremental_batch(conn, settings: Settings, last_sync: datetime) -> pl.DataFrame:
    query = sql.SQL(
        """
        SELECT *
        FROM {}.{}
        WHERE updated_at > %s
        ORDER BY updated_at
        LIMIT %s
        """
    ).format(sql.Identifier(settings.pg_schema), sql.Identifier(settings.pg_table))
    with conn.cursor() as cur:
        cur.execute(query, (last_sync, settings.batch_size))
        rows = cur.fetchall()
    if not rows:
        return pl.DataFrame()
    return pl.DataFrame(rows)


def normalize_timestamp(value) -> datetime:
    if value is None:
        return DEFAULT_LAST_SYNC
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(str(value))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def run_bootstrap(
    conn, settings: Settings, checkpoints: CheckpointStore, pg_columns: Sequence[Tuple[str, str]]
) -> None:
    parquet_path, df = copy_full_table_to_parquet(conn, settings, settings.parquet_dir)
    if not parquet_path or df is None:
        log("Skipping bootstrap load (no data)")
        settings.bootstrap_flag.touch()
        checkpoints.write(DEFAULT_LAST_SYNC, 0)
        return
    load_parquet_into_duckdb(parquet_path, settings, pg_columns)
    last_sync = normalize_timestamp(df["updated_at"].max())
    checkpoints.write(last_sync, df.height)
    settings.bootstrap_flag.touch()
    log(
        f"Bootstrap finished: {df.height} rows copied, last_sync={last_sync.isoformat()}"
    )


def run_incremental_sync(
    conn, settings: Settings, checkpoints: CheckpointStore, pg_columns: Sequence[Tuple[str, str]]
) -> None:
    last_sync, total_rows = checkpoints.current()
    log(f"Starting incremental sync from {last_sync.isoformat()} (rows synced={total_rows})")
    pg_columns = list(pg_columns)
    batch_count = 0
    while True:
        df = fetch_incremental_batch(conn, settings, last_sync)
        if df.is_empty():
            if batch_count == 0:
                log("No new rows to sync.")
            break
        for column in ("updated_at", "deleted_at"):
            if column in df.columns:
                df = df.with_columns(
                    pl.col(column).cast(pl.Datetime(time_zone="UTC"), strict=False)
                )
        pg_column_names = {name for name, _ in pg_columns}
        if missing := [col for col in df.columns if col not in pg_column_names]:
            log(f"Detected new columns {missing}. Refreshing DuckDB schema metadata.")
            pg_columns = get_postgres_columns(conn, settings)
        parquet_path = write_parquet(df, settings.parquet_dir, "incremental")
        upserted = load_parquet_into_duckdb(parquet_path, settings, pg_columns)
        last_sync = normalize_timestamp(df["updated_at"].max())
        total_rows += upserted
        checkpoints.write(last_sync, total_rows)
        batch_count += 1
        log(
            f"Batch {batch_count}: {upserted} rows synced. last_sync={last_sync.isoformat()}"
        )
        if df.height < settings.batch_size:
            break


def run_once(settings: Settings) -> None:
    settings.parquet_dir.mkdir(parents=True, exist_ok=True)
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    settings.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoints = CheckpointStore(settings.checkpoint_db)

    with postgres_connection(settings) as conn:
        pg_columns = get_postgres_columns(conn, settings)
        if not settings.bootstrap_flag.exists():
            run_bootstrap(conn, settings, checkpoints, pg_columns)
        run_incremental_sync(conn, settings, checkpoints, pg_columns)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Incremental Postgres → DuckDB sync orchestrated by Parquet checkpoints."
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Keep the process running and rerun the sync every SYNC_INTERVAL_SECONDS.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = Settings()
    if args.loop:
        interval = max(settings.sync_interval_seconds, 10)
        log(f"Entering daemon mode. Interval={interval}s")
        while True:
            try:
                run_once(settings)
            except Exception as exc:  # pragma: no cover
                log(f"Sync failed: {exc}")
            time.sleep(interval)
    else:
        run_once(settings)


if __name__ == "__main__":
    main()
