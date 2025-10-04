.PHONY: install test run-simple run-mcp run-polars clean

install:
	uv pip install -e ".[dev]"

test:
	pytest tests/ -v

run-simple:
	uv run python simple_example.py

run-mcp:
	uv run python mcp_example.py

run-polars:
	uv run python polars_pipeline_example.py

run: run-simple

clean:
	rm -rf build/ dist/ *.egg-info __pycache__ .pytest_cache
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
