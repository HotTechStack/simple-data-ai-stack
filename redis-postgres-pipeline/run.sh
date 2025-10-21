#!/bin/bash

# Redis + Postgres Pipeline Runner
# Convenience script for common operations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env exists
check_env() {
    if [ ! -f .env ]; then
        warn ".env file not found. Copying from .env.example..."
        cp .env.example .env
        info "Created .env file. Please review and update if needed."
    fi
}

# Start infrastructure
start_infra() {
    info "Starting Postgres 18 and Redis..."
    docker compose up -d

    info "Waiting for services to be healthy..."
    sleep 5

    # Check Postgres
    until docker compose exec -T postgres pg_isready -U dataeng > /dev/null 2>&1; do
        warn "Waiting for Postgres..."
        sleep 2
    done
    info "Postgres is ready"

    # Check Redis
    until docker compose exec -T redis redis-cli ping > /dev/null 2>&1; do
        warn "Waiting for Redis..."
        sleep 2
    done
    info "Redis is ready"

    info "All services are up and healthy!"
    info "Access Redis UI at: http://localhost:8081"
}

# Stop infrastructure
stop_infra() {
    info "Stopping services..."
    docker compose down
}

# Setup Python environment
setup_python() {
    info "Setting up Python environment with uv..."

    if ! command -v uv &> /dev/null; then
        error "uv is not installed. Install from: https://github.com/astral-sh/uv"
        exit 1
    fi

    uv sync
    info "Python environment ready"
}

# Run CLI command
run_cli() {
    uv run python -m src.cli "$@"
}

# Full demo workflow
demo() {
    info "Running full pipeline demo..."

    # Ensure infrastructure is running
    start_infra

    info "Step 1: Initialize lookup cache"
    run_cli init-cache --all

    info "Step 2: Generate 10,000 sample orders"
    run_cli generate --count 10000 --duplicates 0.05

    info "Step 3: Process orders with 1 worker"
    run_cli process --workers 1 --iterations 5

    info "Step 4: Promote staging to production"
    run_cli promote

    info "Step 5: Display statistics"
    run_cli stats

    info "Demo complete! 🎉"
    info "Redis UI: http://localhost:8081"
}

# Run benchmark
benchmark() {
    local count=${1:-100000}

    info "Running benchmark with $count orders..."

    start_infra
    run_cli benchmark --total "$count" --batch-size 5000
}

# Show help
show_help() {
    cat << EOF
Redis + Postgres Pipeline Runner

Usage: ./run.sh <command> [options]

Commands:
    start           Start Postgres and Redis containers
    stop            Stop all containers
    setup           Setup Python environment
    demo            Run full pipeline demo
    benchmark [n]   Run benchmark (default: 100k orders)
    cli [args]      Run CLI command
    test            Run tests
    stats           Show pipeline statistics
    clean           Clean up all data and stop containers
    logs [service]  Show logs for service (postgres, redis, pgbouncer)
    help            Show this help

Examples:
    ./run.sh start                      # Start infrastructure
    ./run.sh demo                       # Run complete demo
    ./run.sh benchmark 500000           # Benchmark with 500k orders
    ./run.sh cli generate --count 5000  # Generate 5000 orders
    ./run.sh stats                      # Show current stats
    ./run.sh logs postgres              # Show Postgres logs

EOF
}

# Main command router
case "${1:-help}" in
    start)
        check_env
        start_infra
        ;;
    stop)
        stop_infra
        ;;
    setup)
        setup_python
        ;;
    demo)
        check_env
        setup_python
        demo
        ;;
    benchmark)
        check_env
        setup_python
        benchmark "${2:-100000}"
        ;;
    cli)
        shift
        run_cli "$@"
        ;;
    test)
        setup_python
        uv run pytest tests/ -v
        ;;
    stats)
        run_cli stats
        ;;
    clean)
        info "Cleaning up..."
        run_cli clear --all 2>/dev/null || true
        docker compose down -v
        info "Cleanup complete"
        ;;
    logs)
        service="${2:-postgres}"
        docker compose logs -f "$service"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
