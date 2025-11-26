#!/bin/bash

# VictoriaMetrics Data Pipeline Observability Demo
# This script sets up and runs the complete demonstration

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}"
echo "=========================================="
echo "VictoriaMetrics Data Pipeline Demo"
echo "=========================================="
echo -e "${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    echo "Please start Docker and try again"
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env and add your OPENAI_API_KEY${NC}"
    echo "Then run this script again"
    exit 1
fi

# Start Docker Compose services
echo -e "\n${GREEN}[1/5] Starting infrastructure (VictoriaMetrics, Grafana, vmagent...)${NC}"
docker compose up -d

# Wait for services to be ready
echo -e "\n${GREEN}[2/5] Waiting for services to be ready...${NC}"
sleep 5

# Check if VictoriaMetrics is ready
echo "Checking VictoriaMetrics..."
for i in {1..30}; do
    if curl -s http://localhost:8428/metrics > /dev/null; then
        echo -e "${GREEN}✓ VictoriaMetrics is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ VictoriaMetrics failed to start${NC}"
        exit 1
    fi
    sleep 1
done

# Check if Grafana is ready
echo "Checking Grafana..."
for i in {1..30}; do
    if curl -s http://localhost:3000/api/health > /dev/null; then
        echo -e "${GREEN}✓ Grafana is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ Grafana failed to start${NC}"
        exit 1
    fi
    sleep 1
done

# Install Python dependencies
echo -e "\n${GREEN}[3/5] Installing Python dependencies...${NC}"
if command -v uv &> /dev/null; then
    uv sync
else
    echo -e "${YELLOW}uv not found, using pip...${NC}"
    pip install -e .
fi

# Display access information
echo -e "\n${GREEN}[4/5] Services are ready!${NC}"
echo -e "\n📊 Access URLs:"
echo "  • Grafana Dashboard:    http://localhost:3000 (admin/admin)"
echo "  • VictoriaMetrics:      http://localhost:8428"
echo "  • vmagent:              http://localhost:8429"
echo "  • Pipeline Metrics:     http://localhost:8000/metrics (after starting pipeline)"

# Ask user what to run
echo -e "\n${GREEN}[5/5] Choose what to run:${NC}"
echo "  1) Start Polars ETL Pipeline (recommended first)"
echo "  2) Run DuckDB Analytics Demo"
echo "  3) Run LLM Query Demo (requires OPENAI_API_KEY)"
echo "  4) Run LLM Interactive Mode"
echo "  5) Run OpenAI Tracing Example"
echo "  6) Show all logs"
echo "  7) Exit"

read -p "Enter choice (1-7): " choice

case $choice in
    1)
        echo -e "\n${GREEN}Starting Polars ETL Pipeline...${NC}"
        echo -e "${YELLOW}Pipeline will run continuously. Press Ctrl+C to stop.${NC}"
        echo -e "${YELLOW}Open Grafana at http://localhost:3000 to see metrics!${NC}\n"
        sleep 2
        if command -v uv &> /dev/null; then
            uv run python polars_pipeline.py
        else
            python polars_pipeline.py
        fi
        ;;
    2)
        echo -e "\n${GREEN}Running DuckDB Analytics Demo...${NC}"
        if command -v uv &> /dev/null; then
            uv run python duckdb_analytics.py
        else
            python duckdb_analytics.py
        fi
        ;;
    3)
        echo -e "\n${GREEN}Running LLM Query Demo...${NC}"
        if command -v uv &> /dev/null; then
            uv run python llm_metrics_query.py
        else
            python llm_metrics_query.py
        fi
        ;;
    4)
        echo -e "\n${GREEN}Starting LLM Interactive Mode...${NC}"
        if command -v uv &> /dev/null; then
            uv run python llm_metrics_query.py --interactive
        else
            python llm_metrics_query.py --interactive
        fi
        ;;
    5)
        echo -e "\n${GREEN}Running OpenAI Tracing Example...${NC}"
        echo -e "${YELLOW}This will generate random jokes and trace them.${NC}"
        echo -e "${YELLOW}Press Ctrl+C to stop.${NC}\n"
        sleep 2
        if command -v uv &> /dev/null; then
            uv run python openai_conn.py
        else
            python openai_conn.py
        fi
        ;;
    6)
        echo -e "\n${GREEN}Showing Docker Compose logs...${NC}"
        echo -e "${YELLOW}Press Ctrl+C to stop.${NC}\n"
        sleep 2
        docker compose logs -f
        ;;
    7)
        echo -e "\n${GREEN}Goodbye!${NC}"
        echo -e "To stop services: ${YELLOW}docker compose down${NC}\n"
        exit 0
        ;;
    *)
        echo -e "\n${RED}Invalid choice${NC}"
        exit 1
        ;;
esac
