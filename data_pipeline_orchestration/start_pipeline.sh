#!/bin/bash
set -e

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()   { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"; }
warn()  { echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"; }
error() { echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"; }
info()  { echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"; }

COMPOSE="docker-compose -f docker-compose.airflow.yml -f docker-compose.override.yml --profile flower --profile extras"

# Fixed wait function with proper health checks
wait_for_service() {
    local service=$1 port=$2
    local max_attempts=30 attempt=1
    info "Waiting for $service on port $port..."
    
    while [ $attempt -le $max_attempts ]; do
        case $service in
            "MinIO")
                # MinIO health check - try the health endpoint first, fallback to API
                if curl -f -s http://localhost:$port/minio/health/live > /dev/null 2>&1 || \
                   curl -f -s http://localhost:$port/minio/health/ready > /dev/null 2>&1; then
                    log "$service is ready!"
                    return 0
                fi
                ;;
            "Airflow")
                # Airflow health check
                if curl -f -s http://localhost:$port/health > /dev/null 2>&1 || \
                   curl -f -s http://localhost:$port/ > /dev/null 2>&1; then
                    log "$service is ready!"
                    return 0
                fi
                ;;
            "DuckDB")
                # DuckDB Service (if you have a FastAPI wrapper)
                if curl -f -s http://localhost:$port/ > /dev/null 2>&1 || \
                   curl -f -s http://localhost:$port/health > /dev/null 2>&1; then
                    log "$service is ready!"
                    return 0
                fi
                ;;
            "Beszel")
                # Beszel health check
                if curl -f -s http://localhost:$port/ > /dev/null 2>&1; then
                    log "$service is ready!"
                    return 0
                fi
                ;;
        esac
        
        info "Attempt $attempt/$max_attempts: $service not ready yet..."
        sleep 5
        ((attempt++))
    done
    warn "$service may not be ready yet, but continuing..."
    return 1
}

# Check if container is running (for services without HTTP ports)
check_container_running() {
    local service=$1
    info "Checking if $service container is running..."
    
    # Simple check - if we can get container ID, it exists
    if $COMPOSE ps -q "$service" >/dev/null 2>&1; then
        log "$service container found and should be running!"
        return 0
    else
        warn "$service container not found"
        return 1
    fi
}

# Setup project structure
setup_project() {
    log "Setting up project structure..."
    
    # Create required directories
    mkdir -p {dags,logs,plugins,data,scripts,config}
    
    # Create .env file with proper permissions
    export AIRFLOW_UID=$(id -u)
    echo "AIRFLOW_UID=${AIRFLOW_UID}" > .env
    
    # Create config directory placeholder
    touch config/.gitkeep
    
    # Create monitor.py if it doesn't exist
    if [ ! -f scripts/monitor.py ]; then
        info "Creating monitor.py placeholder..."
        cat > scripts/monitor.py << 'EOF'
#!/usr/bin/env python3
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("ETL Worker ready - use 'docker-compose exec etl-worker python /app/scripts/etl_pipeline.py'")
    while True:
        logger.info("ETL Worker heartbeat")
        time.sleep(3600)  # Log every hour

if __name__ == "__main__":
    main()
EOF
    fi
    
    # Set proper permissions
    chmod +x scripts/*.py 2>/dev/null || true
    
    log "Project structure ready!"
}

# Cleanup
cleanup() {
    log "Cleaning up..."
    $COMPOSE down -v
    docker system prune -f
}

# Stop
stop_pipeline() {
    log "Stopping pipeline..."
    $COMPOSE down
}

# Start
start_pipeline() {
    log "Starting pipeline..."

    # Setup project first
    setup_project

    # Download Airflow compose if missing
    if [ ! -f docker-compose.airflow.yml ]; then
        info "Downloading Airflow docker-compose.yml..."
        curl -Lf 'https://airflow.apache.org/docs/apache-airflow/3.0.6/docker-compose.yaml' -o docker-compose.airflow.yml
        log "Downloaded official Airflow docker-compose.yml"
    fi

    # Pull all images first
    info "Pulling Docker images..."
    $COMPOSE pull

    # Init Airflow DB
    info "Initializing Airflow database..."
    $COMPOSE up airflow-init

    # Start all services
    info "Starting all services..."
    $COMPOSE up -d

    # Wait for critical services with HTTP endpoints
    log "Checking service health..."
    wait_for_service "Airflow" 8080

    # Check services with HTTP endpoints
    info "Checking additional HTTP services..."
    wait_for_service "MinIO" 9000
    wait_for_service "Beszel" 8090

    # ETL worker doesn't need a health check - it's working if you see logs
    info "ETL worker should be running (check logs: ./start.sh logs etl-worker)"

    log "Pipeline ready ✅"
    show_urls
    show_etl_commands
}

# Run ETL Pipeline
run_etl() {
    local chunk_size=${2:-50000}
    log "Running ETL Pipeline with chunk size: $chunk_size"
    
    if [ ! -f scripts/etl_pipeline.py ]; then
        error "etl_pipeline.py not found in scripts/ directory!"
        info "Please copy your ETL script to scripts/etl_pipeline.py"
        return 1
    fi
    
    # Check if etl-worker container is running
    if ! check_container_running "etl-worker"; then
        error "ETL worker container is not running. Start the pipeline first with: ./start.sh start"
        return 1
    fi
    
    $COMPOSE exec etl-worker python /app/scripts/etl_pipeline.py --chunk-size "$chunk_size"
}

# Show URLs and status
show_urls() {
    echo ""
    echo "=== SERVICE URLS ==="
    echo "Airflow Web UI:   http://localhost:8080 (admin/admin)"
    echo "Airflow Flower:   http://localhost:5555"
    echo "MinIO Console:    http://localhost:9001 (minioadmin/minioadmin123)"
    echo "Beszel Monitor:   http://localhost:8090"
    # echo "DuckDB Service:   http://localhost:3000  # Uncomment if you have DuckDB HTTP service"
    echo ""
}

# Show ETL commands
show_etl_commands() {
    echo "=== ETL COMMANDS ==="
    echo "Run ETL Pipeline:     ./start.sh etl"
    echo "Run ETL (custom):     ./start.sh etl 25000"
    echo "ETL Shell Access:     ./start.sh shell etl-worker"
    echo "View ETL Logs:        ./start.sh logs etl-worker"
    echo ""
    echo "=== QUICK STATUS ==="
    $COMPOSE ps
    echo ""
}

# Show help
show_help() {
    echo "Usage: $0 {start|stop|restart|cleanup|logs|status|etl|shell|help}"
    echo ""
    echo "Commands:"
    echo "  start              Start all services"
    echo "  stop               Stop all services"
    echo "  restart            Restart all services"
    echo "  cleanup            Stop and remove all containers/volumes"
    echo "  logs [service]     Show logs for service (default: all)"
    echo "  status             Show container status"
    echo "  etl [chunk_size]   Run ETL pipeline (default chunk: 50000)"
    echo "  shell [service]    Access container shell (default: etl-worker)"
    echo "  help               Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 etl 25000"
    echo "  $0 logs etl-worker"
    echo "  $0 shell etl-worker"
}

# Main command handling
cmd="${1:-start}"
case "$cmd" in
    start) 
        start_pipeline 
        ;;
    stop) 
        stop_pipeline 
        ;;
    cleanup) 
        cleanup 
        ;;
    restart) 
        stop_pipeline
        sleep 5
        start_pipeline 
        ;;
    logs) 
        $COMPOSE logs -f "${2:-}" 
        ;;
    status) 
        $COMPOSE ps 
        echo ""
        show_urls
        ;;
    etl)
        run_etl "$@"
        ;;
    shell) 
        service=${2:-etl-worker}
        $COMPOSE exec "$service" /bin/bash 
        ;;
    help|--help|-h)
        show_help
        ;;
    *) 
        error "Unknown command: $cmd"
        show_help
        exit 1
        ;;
esac