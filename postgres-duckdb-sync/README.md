# Copying Postgres to DuckDB Without Losing Your Mind (Hands-On Stack)

This directory turns the blog playbook into a reproducible project. Spin up Postgres + DuckDB + a 150-line Polars script, then continuously sync live rows from Postgres into DuckDB without Kafka, Debezium, or Airflow.

## Why this stack?
- **Realistic demo:** Postgres table with `updated_at` trigger, soft deletes (`deleted_at`), and fake SaaS data ready on container start.
- **Minimal moving parts:** A single Python process batsched rows to Parquet, loads them into DuckDB via `INSERT OR REPLACE`, and tracks checkpoints in SQLite.
- **Crash safe:** Last sync timestamp + row count live in SQLite. When the container restarts, the loop resumes exactly where it stopped.
- **Schema aware:** New Postgres columns are detected automatically and added to DuckDB before inserts land.
- **Docker native:** `docker compose up -d --build` launches the full environment; helpers show how to seed changes and inspect DuckDB.

## Stack layout
```
postgres-duckdb-sync/
├── docker-compose.yml          # Postgres + syncer service
├── app/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── src/sync.py             # 150-line incremental sync script
│   └── scripts/seed_changes.py # Helper to simulate live inserts/updates/deletes
├── postgres/init/              # Schema, trigger, seed rows
├── lake/                       # DuckDB file volume (warehouse.duckdb)
├── parquet/                    # Rolling Parquet drops for each batch
└── state/                      # SQLite checkpoint + bootstrap flag
```

## Quick start
1. **Build + launch**
   ```bash
   cd postgres-duckdb-sync
   docker compose up -d --build
   ```
   - Postgres listens on `localhost:5437` with user/password `analyst`.
   - The syncer container loops every 30 seconds (`SYNC_INTERVAL_SECONDS`).

2. **Watch the sync loop**
   ```bash
   docker compose logs -f syncer
   ```
   First run performs the bootstrap (`SELECT *` dump → Parquet → DuckDB). Subsequent loops only copy rows with `updated_at` newer than the last checkpoint.

3. **Generate live change events**
   ```bash
   docker compose exec syncer python scripts/seed_changes.py
   ```
   This inserts one row, updates one, and soft-deletes another with `deleted_at = NOW()`. The sync loop picks up the delta on the next interval.

4. **Query DuckDB**
   ```bash
   docker compose exec syncer python - <<'PY'
   import duckdb
   con = duckdb.connect('/app/lake/warehouse.duckdb')
   print(con.sql("SELECT id, email, plan, lifetime_value FROM analytics_subscriptions WHERE deleted_at IS NULL ORDER BY updated_at DESC LIMIT 5"))
   PY
   ```
   DuckDB stays <100 ms on millions of rows because it only appends columnar Parquet batches.

## How it implements the blog checklist
- **Timestamp column + trigger:** `postgres/init/01_schema.sql` adds `updated_at TIMESTAMPTZ DEFAULT NOW()` and a trigger that touches it on every update. `deleted_at` turns hard deletes into tombstones that analytics can filter out.
- **Incremental queries:** `app/src/sync.py` pulls `WHERE updated_at > :last_sync` in 10k-row chunks (`BATCH_SIZE`). Batch size is configurable via env.
- **Parquet or bust:** Each chunk becomes a Parquet file inside `parquet/`. DuckDB ingests via `INSERT OR REPLACE ... read_parquet(?)`, so re-running the same batch is idempotent.
- **Checkpoints in SQLite:** `state/checkpoints.db` stores `(last_sync_ts, cumulative_row_count)`. Crashes at 3 AM resume on the next loop with no manual fixups.
- **Soft deletes:** Because Postgres keeps tombstones, DuckDB always knows which rows are active. Analytics queries simply filter `WHERE deleted_at IS NULL`.
- **Schema drift guardrails:** Before each insert, the sync script compares `information_schema.columns` against DuckDB’s `pragma_table_info`; missing columns trigger `ALTER TABLE ... ADD COLUMN` inside DuckDB.
- **Bootstrap vs incremental:** The presence of `state/bootstrap.done` toggles the mode. Bootstrap streams `SELECT * FROM schema.table ORDER BY updated_at` through Polars, drops one Parquet file, loads it once, and then switches to incremental forever.
- **Polars + DuckDB speed:** Polars streams the Postgres cursor straight into columnar batches (no pandas). DuckDB ingests Parquet directly—no CSV/JSON to slow things down.
- **Idempotent loads:** DuckDB table `analytics_subscriptions` declares `PRIMARY KEY(id)` so `INSERT OR REPLACE` handles reruns and duplicates gracefully.
- **No orchestration sprawl:** Everything runs as a single long-lived process inside the `syncer` container. Swap the entrypoint for `cron` if you’d rather schedule exact start times.

## Environment variables
Adjustable via `docker-compose.yml` or `env` files:

| Variable | Description | Default |
| --- | --- | --- |
| `POSTGRES_*` | Connection details + table/schema names | `analyst` / `analytics` / `subscriptions` |
| `POSTGRES_PRIMARY_KEY` | Column used for `INSERT OR REPLACE` | `id` |
| `BATCH_SIZE` | Rows per incremental query | `10000` |
| `DUCKDB_PATH` | Where the DuckDB file lives inside the container | `/app/lake/warehouse.duckdb` |
| `DUCKDB_TABLE` | Target table name inside DuckDB | `analytics_subscriptions` |
| `PARQUET_DIR` | Parquet drop zone | `/app/parquet` |
| `STATE_DIR` | Checkpoint + bootstrap flag | `/app/state` |
| `SYNC_INTERVAL_SECONDS` | How often the loop reruns when `--loop` is enabled | `30` |

## Cleaning up / rerunning
```bash
docker compose down -v  # remove containers + Postgres volume
docker compose up -d --build
```
Deleting the `state/` directory resets checkpoints so the next run performs a fresh bootstrap.

## Extending the pattern
- Replace the seed data with your production table by pointing `POSTGRES_*` at your database.
- Batch export Parquet files to S3/MinIO for cheap backups—the sync already writes them.
- Integrate with DuckDB’s `read_parquet('parquet/*.parquet')` to replay history or validate row counts.
- Add a second cron/compose service that runs `python src/sync.py` on a schedule instead of looping forever.

Ten minutes, zero message queues, and you can demo a resilient Postgres → DuckDB sync end to end.
