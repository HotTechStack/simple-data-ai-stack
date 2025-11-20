# Simple Data AI Stack

Build and demo modern data and AI platforms without waiting on infrastructure tickets. This repository collects curated, dockerized blueprints that let data engineers, ML teams, and platform builders spin up end-to-end environments—data lake foundations, pipeline orchestration, observability, and AI-friendly tooling—in a few commands.

---

## The Vision
- **Accelerate experimentation:** Stand up realistic data/AI environments locally or on a single VM, then iterate on pipelines, models, and dashboards with production-inspired defaults.
- **Stay modular:** Each stack is self-contained and composable—pick the lakehouse, orchestration, or monitoring pieces you need today and combine them as your platform grows.
- **Promote best practices:** Included services cover security, backups, health checks, and resource monitoring so teams focus on insights, not plumbing.
- **Bridge personas:** Empower data engineers, AI engineers, analytics developers, and operators to collaborate against the same sandbox with role-aligned interfaces.


---

## Repository Guide
| Directory                           | Focus                            | Highlights | Docs                                                                                                                      |
|-------------------------------------|----------------------------------| --- |---------------------------------------------------------------------------------------------------------------------------|
| `data-Infrastructure/`              | Platform foundations             | Opinionated essays covering the why behind stack choices—start with hidden pitfalls that derail data platforms before they scale | [The Hidden Problems in Data Infrastructure](data-Infrastructure/The%20Hidden%20Problems%20in%20Data%20Infrastructure.md) |
| `datalake/`                         | Data infrastructure              | PostgreSQL-based lake with connection pooling, Redis cache, no-code access, backups, and uptime monitoring | [Postgres Lake README](datalake/postgres_datalake/README.md)                                                              |
| `data_pipeline_orchestration/`      | Data & AI engineering            | Apache Airflow bundle with MinIO object storage, customizable ETL worker, resource monitoring, and helper scripts | [Airflow Stack README](data_pipeline_orchestration/README.md)                                                             |
| `ducklake-ai-platform/`             | Lakehouse + AI workspace         | DuckDB + DuckLake core with Marimo notebooks, MinIO object storage, Postgres metadata, and vector search-ready defaults | [DuckLake README](ducklake-ai-platform/README.md)                                                                         |
| `dataengineering-dashboard-vision/` | Observability agent              | Conversational Grafana + Prometheus assistant delivers root-cause context and anomaly summaries via chat | [Dashboard Agent README](dataengineering-dashboard-vision/README.md)                                                      |
| `dwh-rag-framework/`                | Warehouse-first RAG lab          | DuckDB snapshots feeding LightRAG indexing with Marimo notebooks and Cronicle automation for agent validation | [RAG Framework README](dwh-rag-framework/README.md)                                                                       |
| `n8n-data-ai-orchestration/`        | AI-powered job orchestration     | Customer retention workflow that blends SQL, enrichment, OpenAI strategy generation, Slack/email reporting, and failure alerting in n8n | [n8n Flow README](n8n-data-ai-orchestration/README.md)                                                                    |
| `mcp-data-server/`                  | Universal data loader MCP        | Format-agnostic FastAPI server with auto-detect parsers, DuckDB SQL querying, and REST endpoints for instant file-to-query workflows | [MCP Data Server README](mcp-data-server/README.md)                                                                       |
| `data-agent-sdk/`                   | Data engineering agent SDK       | Minimal SDK for building data agents with SQL/Polars tools, governance hooks, lineage tracking, and MCP server support in ~2,000 lines | [Data Agent SDK README](data-agent-sdk/README.md)                                                                         |
| `python-redis-streaming/`           | Streaming ingestion engine       | Async Python + Redis Streams + Postgres stack with uv tooling, DLQ handling, and CLI helpers for monitoring and benchmarks | [Python Redis Streaming README](python-redis-streaming/README.md)                                                         |
| `redis-postgres-pipeline/`          | High-performance pipeline        | Production-ready data pipeline with Redis queues, dedup, caching, Postgres 18 async I/O, UNLOGGED staging, materialized views, and Polars — handles 500M records without Spark | [Redis Postgres Pipeline README](redis-postgres-pipeline/README.md)                                                       |
| `postgres-duckdb-sync/`             | Postgres → DuckDB sync lab       | 150-line Polars loop that copies live Postgres rows to DuckDB via Parquet, SQLite checkpoints, schema drift detection, and soft-delete support — exactly what the “Copying Postgres to DuckDB” post prescribes | [Postgres → DuckDB Sync README](postgres-duckdb-sync/README.md)                                                           |
| `spark-to-polars-migration/`        | Spark-to-single-node rewrite lab | Side-by-side Spark UDF baseline with Polars and DuckDB replacements, Dockerized for benchmarking single-node performance | [Spark-to-Polars README](spark-to-polars-migration/README.md)                                                             |
| `data-pipeline-security/`           | Data Pipeline Security           | Secrets & Identity | [Data-pipeline-security README](data-pipeline-security/README.md)                                                         |
| `elasticsearch-vs-vector-search/`   | Search architecture lab          | Hands-on comparison of Elasticsearch keyword search vs pgvector semantic search with hybrid approach, performance benchmarks, and production decision framework | [Elasticsearch vs Vector Search README](elasticsearch-vs-vector-search/README.md)                                         |
| `knowledge-search-hybrid/`          | Local hybrid search stack        | Config-driven Lucene BM25 + local embeddings + HNSW kNN + RAG answers in one container; Polars ETL on JSONL drops, autocomplete, and disk-backed indexes | [Hybrid Knowledge Search README](knowledge-search-hybrid/README.md)                                                        |
| `mdm-polars-duckdb/`                | MDM golden customer table        | Implements “Creating One Clean Customer Table from 7 Conflicting Sources” with Polars, Pandera, RapidFuzz, and DuckDB; includes synthetic messy inputs, uv workflow, and Docker image for five-minute runs | [Polars + DuckDB Golden Table README](mdm-polars-duckdb/README.md)                                                        |

Pair the conceptual deep dives with the hands-on stack READMEs: skim `data-Infrastructure/` to understand the platform philosophy, then jump into the stack directory that matches your next experiment for deployment steps and credentials.

---

## Getting Started
1. **Install prerequisites**: Docker + Docker Compose v2 on a machine with adequate CPU, RAM, and disk (see stack-specific READMEs for sizing).
2. **Clone the repo**:
   ```bash
   git clone https://github.com/hottechstack/simple-data-ai-stack.git
   cd simple-data-ai-stack
   ```
3. **Choose a stack**: Browse the directories above and open the corresponding README for detailed instructions.
4. **Launch locally**: Most stacks run with a single command (`docker compose up -d`, `./start_pipeline.sh start`, etc.). Scripts expose health checks, sample data loaders, and log helpers to keep you moving.
5. **Compose your platform**: Run stacks side-by-side for a fuller platform—pipe object storage into the SQL lake, orchestrate model feature jobs, or layer BI tooling on top.

---

## Typical Use Cases
- Prototype a lakehouse with production-grade components before committing to cloud services.
- Trial ETL & AI feature pipelines with real datasets and observe resource footprints.
- Provide analysts and business users a sandbox with self-service interfaces (NocoDB, pgAdmin, dashboards).
- Validate monitoring/backup strategies in isolation before promoting to shared environments.

---

## Opinionated Workflow
1. **Land** structured/unstructured data via MinIO or direct DB ingestion.
2. **Transform** using Airflow-managed ETL jobs powered by DuckDB and Polars.
3. **Serve & explore** through PostgreSQL, NocoDB, BI tools, or custom APIs.
4. **Observe** everything with built-in uptime checks, metrics dashboards, and automated backups.

The stacks are designed to connect: object storage flows into transformation jobs, refined outputs land back into the data lake, and monitoring tools keep the feedback loop tight.

---

## Roadmap Inspiration
- ✅ Vector databases + search architecture comparison (see `elasticsearch-vs-vector-search/`)
- Streaming ingestion profile (Kafka/Redpanda + stream processing + materialized views).
- Notebook & model experimentation workspace with GPU-ready containers.
- Terraform modules to mirror these blueprints in managed cloud environments.

Have an idea or internal stack you want to share? Contributions are welcome—open an issue or PR to propose a new module or enhancement.

---

## Contributing
1. Fork the repository and work inside a dedicated directory for your stack.
2. Document your stack thoroughly (architecture, environment variables, health checks, teardown steps).
3. Reuse existing patterns for Docker Compose profiles, scripts, and monitoring hooks to keep experiences consistent.
4. Submit a PR describing the use case, prerequisites, and any sample data included.

---

## License
Unless otherwise stated in a subdirectory, content is provided as-is for educational and production experimentation. Review upstream container licenses before deploying in regulated environments.
