# Simple Data AI Stack – Data Pipeline Orchestration

This project bundles a resource-aware analytics stack—Airflow, MinIO, a custom ETL worker (Polars + DuckDB + Pandas), and Beszel monitoring—into a single-node environment. The `start_pipeline.sh` script provisions everything with Docker Compose and gives you helper commands to run, observe, and optimize the ETL workloads.

## Prerequisites
- A machine/VM with **≥16 GB RAM** and **≥200 GB** free disk, as the ETL jobs cache data locally.
- Docker and Docker Compose (v2) installed and running.
- `bash`, `curl`, and `chmod` available (default on macOS/Linux).

## Repository Layout
- `start_pipeline.sh` – entrypoint script that sets up and controls the stack.
- `docker-compose.airflow.yml` – official Airflow Docker stack (downloaded automatically if missing).
- `docker-compose.override.yml` – adds MinIO, Beszel, and the custom ETL worker.
- `scripts/etl_pipeline.py` – the core ETL job (extract from MinIO, transform with Polars/DuckDB, load back to MinIO).
- `scripts/generate_sample_data.py` – utility to seed MinIO with CSV data.
- `dags/` – Airflow DAGs, including `etl_pipeline` to orchestrate the Python ETL script.

## One-time Setup
```bash
chmod +x start_pipeline.sh
```

## Step-by-step: `./start_pipeline.sh start`
The `start` command calls the `start_pipeline` function inside the script. Each sub-step below includes a quick validation tip.

1. **Prepare project folders**
   - Creates `dags`, `logs`, `plugins`, `data`, `scripts`, and `config` if they do not exist.
   - Writes `.env` with your `AIRFLOW_UID` so Airflow containers run as your user.
   - Ensures `scripts/monitor.py` exists and is executable.
   - _Validate_: `ls dags logs plugins data scripts config` should show populated directories; `.env` should contain `AIRFLOW_UID=...`.

2. **Fetch the Airflow Compose bundle (idempotent)**
   - Downloads `docker-compose.airflow.yml` from the Apache Airflow docs site when the file is absent.
   - _Validate_: `ls docker-compose.airflow.yml` or view the first lines with `head`.

3. **Pull container images**
   - Runs `docker-compose -f docker-compose.airflow.yml -f docker-compose.override.yml --profile flower --profile extras pull` to grab all Airflow/MinIO/Beszel/ETL images.
   - _Validate_: Docker reports the image digests; reruns skip already cached layers.

4. **Initialize the Airflow metadatabase**
   - Starts the transient `airflow-init` container to set up the PostgreSQL metadata DB and create the admin user.
   - _Validate_: `docker compose ... ps airflow-init` should finish with `Exit 0`; logs show `Airflow is ready`.

5. **Start all services in the background**
   - Brings up Airflow (API server, scheduler, workers, triggerer, flower), Postgres, Redis, MinIO (plus bucket bootstrapper), Beszel, and the `etl-worker` container.
   - _Validate_: `./start_pipeline.sh status` (or the full `docker-compose ... ps`) lists every container as `Up`.

6. **Check core service health**
   - Polls the HTTP health endpoints for Airflow (http://localhost:8080), MinIO (http://localhost:9000/minio/health/live), and Beszel (http://localhost:8090).
   - _Validate_: You can also run the same `curl` commands manually or open the URLs in a browser.

7. **Display quick reference output**
   - Prints service URLs, default credentials, and helpful ETL commands once everything is ready.
   - _Validate_: Look for `Pipeline ready ✅` in your terminal output.

## Core Commands
```bash
./start_pipeline.sh start        # provision + start everything
./start_pipeline.sh status       # show container state and URLs
./start_pipeline.sh logs <svc>   # tail logs (e.g., airflow-scheduler, etl-worker)
./start_pipeline.sh etl [chunk]  # run ETL manually with optional row chunk size
./start_pipeline.sh shell <svc>  # get an interactive shell inside a container
./start_pipeline.sh stop         # stop containers but keep volumes/data
./start_pipeline.sh cleanup      # stop and remove containers, networks, volumes
```

## Accessing the Services
- Airflow Web UI: http://localhost:8080 (default credentials: `admin` / `admin`)
- Airflow Flower (Celery monitoring): http://localhost:5555
- MinIO Console: http://localhost:9001 (default credentials: `minioadmin` / `minioadmin123`)
- Beszel Monitor: http://localhost:8090

> Tip: Once the Airflow UI is up, unpause the `etl_pipeline` DAG and trigger it manually to schedule ETL runs.

## Running the ETL Job
The ETL pipeline extracts CSV files from the `raw-data` MinIO bucket, enriches them with Polars/DuckDB, and writes Parquet + summary JSON back to `processed-data`.

### Seed sample data
```bash
./start_pipeline.sh shell etl-worker
python /app/scripts/generate_sample_data.py --records 5000
exit
```
This stores a `sales_data_5000.csv` file in the `raw-data` bucket.

### Run ad-hoc ETL
```bash
./start_pipeline.sh etl               # default chunk size from ETL_CHUNK_SIZE
./start_pipeline.sh etl 25000         # override chunk size for large files
```
Success emits `ETL Pipeline completed successfully` in the logs and pushes processed Parquet + JSON summary files to `processed-data`.

### Trigger via Airflow
1. Open Airflow UI → DAGs.
2. Locate `etl_pipeline`, flip the toggle to **On**.
3. Trigger `Run` (⚡ icon) to execute the DAG: `run_etl_pipeline` → `cleanup_temp_data` → `system_health_check`.
4. Inspect task logs directly in Airflow.

## Monitoring and Optimization
- Beszel captures CPU, RAM, and I/O metrics per container; watch it during heavy ETL runs.
- Resource guardrails:
  - **RAM > 70%** → reduce `--chunk-size` or break the DAG into more granular tasks.
  - **CPU > 80%** → parallelize transforms or stagger DAG schedules.
  - **Disk I/O > 75%** → optimize DuckDB SQL, limit temp outputs, or leverage Parquet pushdowns.
- Scale by uploading larger datasets to MinIO (`--large 500` produces ~500 MB). Rerun the ETL and iterate on chunk size or DAG timing to maximize throughput without exhausting the single node.

## Troubleshooting
- **Health check warnings**: If the script warns a service is slow to start, re-run `./start_pipeline.sh status` and inspect logs (`./start_pipeline.sh logs airflow-scheduler`).
- **MinIO authentication errors**: Ensure buckets exist (`createbuckets` container runs on start) and credentials match the override file.
- **ETL failures**: Use `./start_pipeline.sh logs etl-worker` for stack traces. Files remain in `/tmp` until the `cleanup_temp_data` task runs.
- **Port conflicts**: Stop any services already using 8080, 9000/9001, 8090, or 5555 before starting the stack.

## Next Steps
1. Customize `scripts/etl_pipeline.py` with domain-specific transforms.
2. Add more Airflow DAGs and stagger schedules to balance resource usage.
3. Plug in alerting (email, Slack) based on Beszel or Airflow events.
