# Source Guide

- `app/config.py` — loads YAML to typed settings (schema, embedding, fusion).  
- `app/etl.py` — Polars pull-based ETL from `data/raw/` to JSONL for indexing.  
- `app/indexer.py` — builds Tantivy (BM25) lexical index + HNSW vector store with local embeddings; persists doc store.  
- `app/search.py` — hybrid searcher with reciprocal-rank fusion and autocomplete helpers.  
- `app/rag.py` — RAG-style answer synthesis: uses Ollama if available, otherwise deterministic extractive summaries.  
- `app/main.py` — FastAPI wiring: health, ETL+index trigger, search, autocomplete, and RAG endpoints.
