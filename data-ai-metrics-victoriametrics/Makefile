.PHONY: help setup up down restart logs pipeline analytics llm-demo llm-chat openai-trace clean test

# Default target
help:
	@echo "VictoriaMetrics Data Pipeline Observability - Available Commands"
	@echo ""
	@echo "Setup & Infrastructure:"
	@echo "  make setup          - Initial setup (create .env, install deps)"
	@echo "  make up             - Start all Docker services"
	@echo "  make down           - Stop all Docker services"
	@echo "  make restart        - Restart all Docker services"
	@echo "  make logs           - Show Docker logs (follow mode)"
	@echo ""
	@echo "Run Demos:"
	@echo "  make pipeline       - Start Polars ETL pipeline (continuous)"
	@echo "  make analytics      - Run DuckDB analytics demo"
	@echo "  make llm-demo       - Run LLM query demo (example questions)"
	@echo "  make llm-chat       - Run LLM interactive chat mode"
	@echo "  make openai-trace   - Run OpenAI tracing example"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean          - Clean generated files"
	@echo "  make test           - Run basic health checks"
	@echo "  make grafana        - Open Grafana in browser"
	@echo "  make vm             - Open VictoriaMetrics in browser"
	@echo ""
	@echo "Quick Start: make setup && make up && make pipeline"

# Initial setup
setup:
	@echo "Setting up project..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✓ Created .env file (please add OPENAI_API_KEY)"; \
	else \
		echo "✓ .env file already exists"; \
	fi
	@if command -v uv >/dev/null 2>&1; then \
		echo "Installing dependencies with uv..."; \
		uv sync; \
	else \
		echo "Installing dependencies with pip..."; \
		pip install -e .; \
	fi
	@echo "✓ Setup complete!"

# Docker management
up:
	@echo "Starting Docker services..."
	docker compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo ""
	@echo "Services running:"
	@docker compose ps
	@echo ""
	@echo "Access URLs:"
	@echo "  Grafana:         http://localhost:3000 (admin/admin)"
	@echo "  VictoriaMetrics: http://localhost:8428"
	@echo "  vmagent:         http://localhost:8429"

down:
	@echo "Stopping Docker services..."
	docker compose down

restart:
	@echo "Restarting Docker services..."
	docker compose restart

logs:
	docker compose logs -f

# Run demos
pipeline:
	@echo "Starting Polars ETL Pipeline..."
	@echo "Metrics will be available at http://localhost:8000/metrics"
	@echo "Open Grafana at http://localhost:3000 to visualize"
	@echo ""
	@if command -v uv >/dev/null 2>&1; then \
		uv run python polars_pipeline.py; \
	else \
		python polars_pipeline.py; \
	fi

analytics:
	@echo "Running DuckDB Analytics Demo..."
	@if command -v uv >/dev/null 2>&1; then \
		uv run python duckdb_analytics.py; \
	else \
		python duckdb_analytics.py; \
	fi

llm-demo:
	@echo "Running LLM Query Demo..."
	@if command -v uv >/dev/null 2>&1; then \
		uv run python llm_metrics_query.py; \
	else \
		python llm_metrics_query.py; \
	fi

llm-chat:
	@echo "Starting LLM Interactive Chat..."
	@if command -v uv >/dev/null 2>&1; then \
		uv run python llm_metrics_query.py --interactive; \
	else \
		python llm_metrics_query.py --interactive; \
	fi

openai-trace:
	@echo "Running OpenAI Tracing Example..."
	@if command -v uv >/dev/null 2>&1; then \
		uv run python openai_conn.py; \
	else \
		python openai_conn.py; \
	fi

# Utilities
clean:
	@echo "Cleaning generated files..."
	rm -rf output/
	rm -rf __pycache__/
	rm -rf *.pyc
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	@echo "✓ Clean complete"

test:
	@echo "Running health checks..."
	@echo ""
	@echo "1. Checking VictoriaMetrics..."
	@curl -sf http://localhost:8428/metrics > /dev/null && echo "  ✓ VictoriaMetrics is healthy" || echo "  ✗ VictoriaMetrics is not responding"
	@echo ""
	@echo "2. Checking vmagent..."
	@curl -sf http://localhost:8429/metrics > /dev/null && echo "  ✓ vmagent is healthy" || echo "  ✗ vmagent is not responding"
	@echo ""
	@echo "3. Checking Grafana..."
	@curl -sf http://localhost:3000/api/health > /dev/null && echo "  ✓ Grafana is healthy" || echo "  ✗ Grafana is not responding"
	@echo ""
	@echo "4. Checking Python environment..."
	@if command -v uv >/dev/null 2>&1; then \
		echo "  ✓ uv is installed"; \
	else \
		echo "  ℹ uv not found (using pip)"; \
	fi

grafana:
	@echo "Opening Grafana in browser..."
	@open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 2>/dev/null || echo "Please open http://localhost:3000 manually"

vm:
	@echo "Opening VictoriaMetrics in browser..."
	@open http://localhost:8428 2>/dev/null || xdg-open http://localhost:8428 2>/dev/null || echo "Please open http://localhost:8428 manually"

# All-in-one demo
demo: up
	@echo ""
	@echo "Starting complete demo..."
	@echo "1. Services are starting up..."
	@sleep 10
	@echo "2. Opening Grafana..."
	@make grafana
	@echo "3. Starting pipeline in 5 seconds..."
	@echo "   (Press Ctrl+C to stop the pipeline)"
	@sleep 5
	@make pipeline
