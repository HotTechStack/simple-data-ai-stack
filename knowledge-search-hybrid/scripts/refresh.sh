#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${PYTHONPATH:-$ROOT_DIR/src}"

echo "Running Polars ETL..."
uv run python -m app.etl

echo "Rebuilding lexical + vector indexes..."
uv run python -m app.indexer

echo "Done. Start the API with: uv run python -m app.main"
