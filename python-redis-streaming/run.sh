#!/bin/bash

# Main script to run the streaming engine

set -e

echo "=================================="
echo "Python Redis Streaming Engine"
echo "=================================="
echo ""

# Check if .env exists, if not copy from example
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
fi

# Function to check if services are ready
check_services() {
    echo "Checking if services are ready..."

    # Check Redis
    if ! docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo "Redis is not ready yet..."
        return 1
    fi

    # Check Postgres
    if ! docker-compose exec -T postgres pg_isready -U streaming_user -d streaming > /dev/null 2>&1; then
        echo "Postgres is not ready yet..."
        return 1
    fi

    echo "All services are ready!"
    return 0
}

# Start services
echo "Starting Docker services..."
docker-compose up -d redis postgres

# Wait for services to be ready
echo "Waiting for services to be ready..."
for i in {1..30}; do
    if check_services; then
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Services failed to start in time"
        exit 1
    fi
    sleep 2
done

echo ""
echo "Services are up and running!"
echo ""
echo "Available commands:"
echo "  ./run.sh start     - Start the streaming engine"
echo "  ./run.sh test      - Run tests"
echo "  ./run.sh produce   - Produce sample events"
echo "  ./run.sh monitor   - Monitor the pipeline"
echo "  ./run.sh benchmark - Run benchmark test"
echo "  ./run.sh stop      - Stop all services"
echo "  ./run.sh logs      - View logs"
echo ""

case "${1:-help}" in
    start)
        echo "Starting streaming engine..."
        docker-compose up streaming-app
        ;;
    test)
        echo "Running tests..."
        uv sync
        uv run pytest tests/ -v
        ;;
    produce)
        NUM_EVENTS=${2:-1000}
        echo "Producing $NUM_EVENTS sample events..."
        uv run python scripts/produce_sample.py $NUM_EVENTS
        ;;
    monitor)
        INTERVAL=${2:-5}
        echo "Starting monitor (refresh interval: ${INTERVAL}s)..."
        uv run python scripts/monitor.py $INTERVAL
        ;;
    benchmark)
        RATE=${2:-10000}
        DURATION=${3:-60}
        echo "Running benchmark: $RATE events/sec for $DURATION seconds..."
        uv run python scripts/benchmark.py $RATE $DURATION
        ;;
    stop)
        echo "Stopping all services..."
        docker-compose down
        ;;
    logs)
        SERVICE=${2:-streaming-app}
        docker-compose logs -f $SERVICE
        ;;
    clean)
        echo "Cleaning up Docker resources..."
        docker-compose down -v
        echo "Cleaned up!"
        ;;
    help|*)
        echo "Usage: ./run.sh [command] [args]"
        echo ""
        echo "Commands:"
        echo "  start              Start the streaming engine"
        echo "  test               Run tests"
        echo "  produce [n]        Produce n sample events (default: 1000)"
        echo "  monitor [interval] Monitor pipeline (default: 5s refresh)"
        echo "  benchmark [rate] [duration]  Run benchmark (default: 10000 events/sec for 60s)"
        echo "  stop               Stop all services"
        echo "  logs [service]     View logs (default: streaming-app)"
        echo "  clean              Clean up all Docker resources"
        echo ""
        ;;
esac
