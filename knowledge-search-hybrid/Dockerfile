# Single-container hybrid search stack: FastAPI + Tantivy + HNSW + local embeddings
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS base

WORKDIR /app

# System deps for Tantivy wheels + scientific stack
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libomp-dev && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY config ./config
COPY data ./data
COPY src ./src

ENV UV_SYSTEM_PYTHON=1 \
    PYTHONPATH=/app/src

RUN uv sync --no-dev

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "app.main"]
