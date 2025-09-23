FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:/root/.cargo/bin:$PATH"

# Copy requirements
COPY requirements.txt .

# Install Python packages with uv
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8080

CMD ["marimo", "edit", "--host", "0.0.0.0", "--port", "8080", "notebooks/"]
