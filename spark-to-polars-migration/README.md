# Spark-to-Polars Migration Lab

Use this lab to practice rewriting a Spark batch job that relies on a Python UDF into optimized Polars and DuckDB pipelines that stay on a single machine—mirroring the migration strategy outlined in _"When You Don't Need Apache Spark Anymore"_.

## What You Get
- **Spark baseline** – `spark_job/spark_job.py` loads `data/orders.csv`, groups spend by customer, and applies a Python UDF to assign tiers. The job writes Parquet output to `output/spark/customer_spend/`.
- **Polars rewrite** – `polars_duckdb_job/polars_duckdb_job.py` runs the same aggregation lazily with Polars expressions (no UDF) and writes `output/polars/customer_spend.parquet`.
- **DuckDB SQL** – The same logic expressed as a single SQL statement against the CSV to demonstrate zero-copy Arrow execution and fast local analytics.
- **Dockerized workflow** – Dockerfiles pin dependencies; `docker-compose.yml` orchestrates repeatable runs and mounts shared `data/` and `output/` directories.

The sample dataset is intentionally small (<1 MB). Swap in a larger CSV/Parquet extract from an existing pipeline to measure wall-clock time and resource usage differences.

## Prerequisites
- Docker + Docker Compose v2
- ~2 GB RAM and a few hundred MB of free disk (more if you test with larger data)

## Run the Baseline Spark Job
```bash
cd spark-to-polars-migration
docker compose build spark-job
docker compose run --rm spark-job
```

The container executes Spark in local mode, logs the grouped output, and writes results to `output/spark/customer_spend/`. Note the startup time and total duration printed at the end—this is your baseline.

## Run the Polars & DuckDB Alternatives
```bash
docker compose build polars-job
docker compose run --rm polars-job
```

This single container executes both the Polars and DuckDB implementations back-to-back, printing their results and execution times. Outputs land in:
- `output/polars/customer_spend.parquet`
- `output/duckdb/customer_spend.parquet`

Compare the elapsed times with the Spark run to see the overhead avoided when you stay on a single machine.

## Inspect the Results
Use any Parquet-aware tool to open the outputs—for example, DuckDB from your host:
```bash
duckdb -c "SELECT * FROM 'output/polars/customer_spend.parquet' ORDER BY total_amount DESC;"
```

You should see identical rows across Spark, Polars, and DuckDB, confirming functional parity after removing the Python UDF.

## Customize the Experiment
- Replace `data/orders.csv` with a representative extract from one of your Spark jobs (CSV/Parquet/JSON). Update `ORDERS_PATH` in `docker-compose.yml` if the file name changes.
- Translate additional Spark UDFs into Polars expressions (`pl.when`, `pl.struct`, `pl.fold`) or DuckDB SQL CASE statements.
- Parameterize the tier thresholds via environment variables to mimic production config knobs.
- Integrate the containers with an orchestrator (Prefect, Airflow) to schedule micro-batch runs every minute, following the blog’s streaming recommendation.

## Troubleshooting
- **PySpark JVM errors**: Increase container memory (`docker run --memory`) or lower `spark.sql.shuffle.partitions`.
- **Parquet write failures**: Ensure the `output/` directory is writable; Docker Compose mounts it by default.
- **Performance parity**: If Spark and Polars finish in similar time, increase data volume or disable Spark caching to highlight startup overhead.

Once satisfied, measure for 2–4 weeks in parallel—log runtime, CPU, and failure rates—before retiring your Spark infrastructure for jobs that comfortably fit on a single node.
