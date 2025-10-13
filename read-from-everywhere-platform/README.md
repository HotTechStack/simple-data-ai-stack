# Read-From-Everywhere Data Platform

This stack turns the ideas in **“Building a Data Platform That Reads From Everywhere”** into running code. One `docker compose up` launches polyglot ingestion with Polars, raw object storage via MinIO, metadata tracking in Postgres, and ad‑hoc analytics in DuckDB.

## What You Get
- **Polars ingestion workers** pull batch CSVs, Parquet files, REST APIs, synthetic "stream" events, and webhook payloads through a single asyncio loop.
- **Redis-backed queue** handles both batch schedules and streaming/webhook traffic without separate infrastructure.
- **Retry with exponential backoff** keeps noisy APIs under control; exhausted jobs land safely in a MinIO-backed dead letter queue and Postgres log.
- **Immutable blob storage** in MinIO mirrors production S3 semantics so write failures surface locally before AWS bills do.
- **Metadata registry** in Postgres tracks source freshness, schema versions, and row counts for every ingestion run.
- **DuckDB query service** runs directly on Parquet in MinIO—no warehouse cluster required.

## Stack Layout
```
read-from-everywhere-platform/
├── docker-compose.yml          # One file, one command
├── data/seeds/                 # Demo CSV seeds (Parquet generated on first run)
├── ingestion/                  # Polars worker, scheduler, webhook gateway
│   └── app/
│       ├── worker.py           # Async ingestion loop with retries + DLQ
│       ├── scheduler.py        # Enqueues batch jobs on Redis
│       ├── webhook.py          # Accepts webhooks, responds 200 immediately
│       ├── storage.py          # MinIO helpers + schema hashing
│       ├── database.py         # Postgres metadata store
│       └── ...
├── mock_api/                   # FastAPI service that simulates upstream APIs
├── postgres/init.sql           # Metadata tables & views
└── scripts/duckdb_query.sql    # Sample DuckDB queries over MinIO
```

## Quick Start
1. **Build & launch everything**
   ```bash
   docker compose up --build
   ```
   Services: Postgres, Redis, MinIO (+ console on :9001), mock REST API, Polars scheduler & worker, webhook gateway (:8080), and a ready-to-use DuckDB CLI container.

2. **Watch ingestion run**
   ```bash
   docker compose logs -f ingestion-worker
   ```
   You’ll see four job types succeed: REST API (`customers_api`), CSV (`finance_csv`), Parquet (`orders_parquet` – generated on first run), and synthetic stream events (`synthetic_stream`). Each run lands raw + processed Parquet in MinIO and updates Postgres metadata.

3. **Inspect metadata**
   ```bash
   docker compose exec postgres psql -U metadata -d metadata -c "SELECT source_name, row_count, succeeded_at FROM ingestion_run_summary;"
   docker compose exec postgres psql -U metadata -d metadata -c "SELECT source_name, error, attempt FROM ingestion_failures;"
   ```

4. **Query everything with DuckDB**
   ```bash
   docker compose exec duckdb duckdb -f /scripts/duckdb_query.sql
   ```
   DuckDB reads Parquet straight from MinIO (via httpfs + S3 endpoint), joining batch files and API outputs without copying data.

5. **Trigger a webhook**
   ```bash
   curl -X POST http://localhost:8080/webhooks/zendesk \
     -H 'Content-Type: application/json' \
     -d '{"event_type":"ticket_created","data":{"ticket_id":987,"priority":"high"}}'
   ```
   The gateway returns `200` immediately; the worker picks up the payload from the same Redis queue as scheduled jobs and stores it alongside other sources.

## Design Notes Mapped to the Blog Post
- **One docker-compose up** starts ingestion workers, blob storage, metadata DB, mock APIs, Redis queue, webhook gateway, and DuckDB query node.
- **Polars reads from anywhere** — handlers cover REST, CSV, Parquet, synthetic streaming events, and webhook payloads, all turned into lazy Polars frames.
- **No separate batch vs. streaming infra** — both the periodic scheduler and real-time webhook feed the same `redis` queue.
- **Asyncio + Redis over Kafka** — `redis.blpop` powers the fetch loop; this scales to most “streaming” workloads before Kafka is necessary.
- **Retries with exponential backoff** — configurable attempts/backoff; exhausted jobs are persisted to a MinIO dead-letter bucket and logged in Postgres.
- **MinIO mirrors S3** — raw, processed, and dead-letter data live in dedicated buckets so local testing matches production semantics.
- **Metadata in Postgres** — `ingestion_runs`, `ingestion_schemas`, and `ingestion_failures` give audit trails, schema versioning, and simple health metrics.
- **Polars > Spark for medium data** — lazy transforms add lineage columns and timestamping without spinning up clusters; Parquet outputs are query-ready forever.
- **DuckDB queries everything** — the provided SQL sample shows millisecond joins across API + CSV ingest results directly in object storage.
- **Schema drift ready** — schema hashes & versioning detect changes; Polars handles missing columns without killing the pipeline.
- **Webhooks respond fast** — FastAPI gateway returns HTTP 200 instantly while pushing the heavy work onto the async worker.
- **Batch API calls** — mock API honours `limit` parameters and the scheduler requests data in configurable chunks.
- **Dead letter review** — failures surface in Postgres and land in `s3://dead-letter/...` for replay after analysis.

## Configuration
Key environment variables (override via `.env` or Compose):
- `REDIS_QUEUE_NAME` – shared queue for all ingestion types.
- `SCHEDULE_INTERVAL_SECONDS` – scheduler frequency (default 5 minutes).
- `MAX_JOB_ATTEMPTS`, `BACKOFF_BASE_SECONDS`, `BACKOFF_CAP_SECONDS` – retry controls.
- `MINIO_*` – endpoint & bucket names; defaults align with the compose file.

Buckets (`raw`, `processed`, `dead-letter`) are auto-created on startup. The worker also seeds a demo Parquet file if `data/seeds/orders.parquet` is missing, so the Parquet path works out of the box.

## Operational Playbook
- **Check health**: `docker compose exec postgres psql -U metadata -d metadata -c "SELECT * FROM ingestion_failures ORDER BY created_at DESC LIMIT 5;"`
- **Replay dead letters**: fetch the JSON from `dead-letter/` in MinIO, fix the upstream issue, and POST it to `/webhooks/replay` (or enqueue manually).
- **Scale workers**: add `replicas` or another `ingestion-worker` service in Compose—no new code paths needed.
- **Extend sources**: drop another handler in `ingestion/app/worker.py` (e.g., Kafka consumer) and register it in the scheduler.

## Tear Down
Stop everything when you are done:
```bash
docker compose down -v
```
This removes containers and persistent MinIO/Postgres volumes so the next run starts clean.

Happy ingesting—add real sources, crank up the data volume, and you’ll know exactly when you truly need Kafka, Airflow, or Spark.
