# Hybrid Knowledge Search (No Vector-DB Theater)

Lightweight, config-driven lexical + semantic search in one container. Inspired by “Building Knowledge Search Without Vector-DB Theater,” this stack keeps everything local: Polars ETL pulls JSONL drops, Tantivy (Lucene) handles BM25, FastEmbed + HNSW deliver semantic recall, and a FastAPI endpoint fuses results, autocomplete, and RAG-style answers.

## Why this repo
- **One config** (`config/search_config.yaml`) captures schemas, analyzers, embedding model, and fusion knobs—treat search like code, not tribal memory.  
- **Pull-based indexing**: drop CSVs/JSONL in `data/raw`, run Polars ETL → `data/processed/docs.jsonl`, rebuild indexes.  
- **Single container**: local embeddings (ONNX via FastEmbed), BM25 from Lucene/Tantivy, HNSW vectors, RAG answer synthesis on the same API.  
- **Resilient storage**: disk-backed indexes in `data/index`; swap folders or mount S3 for zero-downtime rollbacks.  
- **Deterministic hybrid**: lexical + semantic in one request using reciprocal-rank fusion; autocomplete reuses the same index.

## Layout
- `config/search_config.yaml` — field types, analyzers, embedding model, fusion weights, autocomplete fields.  
- `data/raw/` — sample Confluence, GitHub, and Slack CSV inputs.  
- `data/processed/docs.jsonl` — Polars-normalized corpus; the indexer reads from here.  
- `data/index/` — Tantivy schema + HNSW vectors + doc store.  
- `src/app/` — FastAPI app, ETL, indexer, hybrid search, and RAG helper.  
- `scripts/refresh.sh` — run ETL + indexing in one command during development.

## Quickstart (local, uv)
```bash
cd knowledge-search-hybrid
export PYTHONPATH=src
uv run python -m app.etl         # Polars ETL → data/processed/docs.jsonl
uv run python -m app.indexer     # Build lexical + vector indexes
uv run python -m app.main        # Start API at http://localhost:8000
```
Endpoints:  
- `GET /health` — status + index readiness.  
- `GET /search?q=payment` — hybrid BM25 + semantic with rank fusion.  
- `GET /autocomplete?prefix=pay` — search-as-you-type driven by the same index.  
- `GET /rag?q=...` — pulls top docs and streams them through a local LLM (Ollama if set) or a deterministic extractive summary.

## Docker
```bash
docker compose up --build
# Inside the container, seed data and indexes:
docker compose exec knowledge-search uv run python -m app.etl
docker compose exec knowledge-search uv run python -m app.indexer
```
Port `8000` is exposed; mount `./data` to keep indexes between restarts. Set `OLLAMA_MODEL` if you want local LLM answers.

## How it maps to the blog claims
- **Hybrid in one node**: Tantivy BM25 + HNSW vectors live together; handles ~100k docs comfortably on a laptop.  
- **Local embeddings**: FastEmbed uses ONNX models locally—no per-token costs or external latency.  
- **Strong schema**: field types, stored flags, and analyzers live in config; the indexer enforces them every rebuild.  
- **Boring ingestion**: Polars ETL reads CSV drops and writes JSONL; the indexer consumes files, not POST storms.  
- **Rank fusion**: reciprocal-rank fusion with adjustable lexical/semantic weights gives deterministic ordering.  
- **Autocomplete & RAG**: autocomplete reuses the same text fields; RAG happens on the search API, no extra service.  
- **Stateless node**: all state lives under `data/index`; point another container at it or swap directories for rollbacks.

## Running your own corpus
1) Add new CSV/JSONL files under `data/raw/`.  
2) Update `config/search_config.yaml` if you introduce new fields or tags.  
3) `uv run python -m app.etl && uv run python -m app.indexer` to refresh.  
4) Keep `./data/index` on disk or S3; swap the folder to roll forward/back.

## Notes
- The FastEmbed model downloads on first run; pre-warm it or bake into your image for air-gapped envs.  
- Use `config.hybrid` knobs to tune BM25/semantic balance or increase `k` for broader recall.  
- For production, mount `./data` to durable storage and add a cron/CI job that runs `scripts/refresh.sh`.
