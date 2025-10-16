FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Copy dependency files
COPY pyproject.toml .

# Install dependencies with uv
RUN uv sync --frozen

# Copy application code
COPY src ./src

# Run the application
CMD ["uv", "run", "python", "-m", "src.main"]
