# Polars + DuckDB Golden Customer Table

This repo turns the blog checklist "Creating One Clean Customer Table from 7 Conflicting Sources" into a fully executable, dockerized project. Running the pipeline spins up seven noisy inputs (CSV, Excel, JSON, and DuckDB extracts), normalizes them with Polars, validates them with Pandera, resolves conflicts with RapidFuzz + window functions, and materializes a master customer table in DuckDB.

## Requirements

- Python 3.11+
- Make (optional but handy)
- Docker (only if you want the containerized run)

All Python dependencies are captured in `requirements.txt`.

## How it mirrors the blog playbook

| Blog directive | Where it happens |
| --- | --- |
| Polars reads Excel/CSV/JSON/DB extracts | `mdm_pipeline.pipeline.load_sources` uses `scan_csv`, `scan_ndjson`, `read_excel`, and DuckDB connectors |
| Normalize column names with a mapping dict | `COLUMN_ALIASES` in `config.py` + `_normalize_schema` |
| Stack sources with a `source_system` column | `load_sources` keeps provenance + `source_record_id` |
| Validate the first 1000 rows with Pandera | `run_schema_validation` in `pipeline.py` |
| Standardize whitespace, emails, countries, phones | `standardize_values` |
| Add `data_quality_score` based on completeness + recency | `compute_data_quality` |
| Pick composite key early | `standardize_values` + `finalize_composite_keys` build `email|phone` fallback to `customer_id` |
| Dedupe with sorted window functions | `resolve_conflicts` ranks within `composite_key` partitions and keeps the best row |
| RapidFuzz fuzzy matching for names/addresses | `_fuzzy_updates` assigns missing keys when similarity ≥ 85 |
| Explicit conflict resolution w/ `source_priority` | `SOURCE_PRIORITIES` in `config.py` + `prefer_trusted` aggregator |
| Write golden table to DuckDB (`CREATE TABLE AS SELECT`) | `write_duckdb_table` |
| Add audit columns | `resolve_conflicts` adds `source_systems`, `conflict_rules_applied`, `created_at`, `last_updated_at` |
| Keep rules in git | All mapping + scoring logic lives in this repo |
| Automate before wiring Airflow | `Makefile` + Docker image keep runtime <5 minutes |

## Project layout

```
mdm-polars-duckdb/
├── Dockerfile
├── Makefile
├── requirements.txt
├── data_sources/        # auto-populated sample extracts
├── artifacts/           # DuckDB + CSV outputs land here
└── src/mdm_pipeline/
    ├── config.py        # column mappings, source priorities
    ├── data_generation.py
    ├── pipeline.py      # main orchestration script
    └── validators.py    # Pandera schema
```

## Run locally

```bash
cd mdm-polars-duckdb
uv venv --python 3.11
source .venv/bin/activate
UV_CACHE_DIR=.uv-cache uv pip install -r requirements.txt
make run
```

What you get:

- Synthetic versions of the seven conflicting systems in `data_sources/`
- Validation logs proving the schema check ran on the top 1,000 records
- A deduped `golden_customers` table in both `artifacts/golden_customers.duckdb` and CSV form

Inspect the result with DuckDB:

```bash
duckdb artifacts/golden_customers.duckdb "SELECT composite_key, customer_name, primary_source, data_quality_score FROM golden_customers ORDER BY data_quality_score DESC;"
```

## Run with Docker

```bash
cd mdm-polars-duckdb
make docker-run
```

The image bakes in all dependencies. `artifacts/` is volume-mounted so the DuckDB file and CSV remain on your host.

> **Heads up (macOS Accelerate bug)**  
> If the local run crashes during the Pandera import with a `Bus error` coming from NumPy, skip to the Docker flow above. That crash is Apple's Accelerate BLAS issue; the Linux container does not hit it.

## Extending the rules

- Adjust `SOURCE_PRIORITIES` in `config.py` when a new system joins the fray.
- Expand `ISO_COUNTRY_MAP`, phone normalizers, or quality scoring logic inside `pipeline.py` as your domain knowledge improves.
- Swap out `generate_sample_sources()` with real extract loaders when pointed at production feeds—the rest of the pipeline already follows the MDM best practices from the blog.

Everything that can drift (mappings, validation, conflict rules) lives in version-controlled Python so you can review diffs just like any other data engineering change.
