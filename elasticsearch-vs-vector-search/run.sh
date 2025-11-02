#!/bin/bash

# Elasticsearch vs Vector Search - Quick Start Script

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Elasticsearch vs Vector Search Demo                          ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"

# Function to check if services are healthy
check_services() {
    echo -e "\n${YELLOW}Checking service health...${NC}"

    # Wait for Elasticsearch
    echo -n "Waiting for Elasticsearch..."
    for i in {1..30}; do
        if curl -s http://localhost:9200/_cluster/health > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done

    # Wait for PostgreSQL
    echo -n "Waiting for PostgreSQL..."
    for i in {1..30}; do
        if docker compose exec -T postgres pg_isready -U searchuser -d searchdb > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
}

# Parse command
case "$1" in
    start)
        echo -e "\n${YELLOW}Starting services...${NC}"
        docker compose up -d
        check_services
        echo -e "\n${GREEN}✓ Services started successfully!${NC}"
        echo -e "\nNext steps:"
        echo -e "  ./run.sh setup    # Generate and load data"
        echo -e "  ./run.sh demo     # Run comprehensive demo"
        ;;

    setup)
        echo -e "\n${YELLOW}Setting up data...${NC}"

        echo -e "\n${YELLOW}Step 1: Generating sample data...${NC}"
        docker compose exec demo-api python scripts/generate_data.py

        echo -e "\n${YELLOW}Step 2: Loading data into Elasticsearch and pgvector...${NC}"
        echo -e "${YELLOW}Watch the performance difference! (ES vs Vector pipeline)${NC}\n"
        docker compose exec demo-api python scripts/load_data.py

        echo -e "\n${GREEN}✓ Setup complete!${NC}"
        echo -e "\nNext step:"
        echo -e "  ./run.sh demo     # Run comprehensive demo"
        ;;

    demo)
        echo -e "\n${YELLOW}Running comprehensive demo...${NC}\n"
        docker compose exec demo-api python scripts/demo.py
        ;;

    keyword)
        echo -e "\n${YELLOW}Running keyword search demo...${NC}\n"
        docker compose exec demo-api python scripts/keyword_search.py
        ;;

    vector)
        echo -e "\n${YELLOW}Running vector search demo...${NC}\n"
        docker compose exec demo-api python scripts/vector_search.py
        ;;

    hybrid)
        echo -e "\n${YELLOW}Running hybrid search demo...${NC}\n"
        docker compose exec demo-api python scripts/hybrid_search.py
        ;;

    logs)
        docker compose logs -f
        ;;

    status)
        echo -e "\n${YELLOW}Service Status:${NC}\n"
        docker compose ps

        echo -e "\n${YELLOW}Elasticsearch Health:${NC}"
        curl -s http://localhost:9200/_cluster/health?pretty | grep -E "cluster_name|status|number_of_nodes"

        echo -e "\n${YELLOW}Product Count:${NC}"
        docker compose exec -T postgres psql -U searchuser -d searchdb -c "SELECT COUNT(*) as product_count FROM products;"
        ;;

    stop)
        echo -e "\n${YELLOW}Stopping services...${NC}"
        docker compose stop
        echo -e "${GREEN}✓ Services stopped${NC}"
        ;;

    clean)
        echo -e "\n${YELLOW}Removing all containers and volumes...${NC}"
        docker compose down -v
        echo -e "${GREEN}✓ Cleanup complete${NC}"
        ;;

    shell)
        echo -e "\n${YELLOW}Starting Python shell with search modules loaded...${NC}\n"
        docker compose exec demo-api python -i -c "
from keyword_search import KeywordSearch
from vector_search import VectorSearch
from hybrid_search import HybridSearch

print('Available searchers:')
print('  keyword_searcher = KeywordSearch()')
print('  vector_searcher = VectorSearch()')
print('  hybrid_searcher = HybridSearch()')
print()
print('Try: keyword_searcher.search_by_sku(\"ELEC-000001\")')
"
        ;;

    *)
        echo -e "\nUsage: ./run.sh {command}"
        echo -e "\nCommands:"
        echo -e "  ${GREEN}start${NC}      Start all services"
        echo -e "  ${GREEN}setup${NC}      Generate and load sample data"
        echo -e "  ${GREEN}demo${NC}       Run comprehensive demo (all scenarios)"
        echo -e "  ${GREEN}keyword${NC}    Run keyword search demo only"
        echo -e "  ${GREEN}vector${NC}     Run vector search demo only"
        echo -e "  ${GREEN}hybrid${NC}     Run hybrid search demo only"
        echo -e "  ${GREEN}shell${NC}      Interactive Python shell with search modules"
        echo -e "  ${GREEN}status${NC}     Check service status and data counts"
        echo -e "  ${GREEN}logs${NC}       View service logs"
        echo -e "  ${GREEN}stop${NC}       Stop all services"
        echo -e "  ${GREEN}clean${NC}      Remove all containers and data"
        echo -e "\nQuick start:"
        echo -e "  ${YELLOW}./run.sh start${NC}   # Start services"
        echo -e "  ${YELLOW}./run.sh setup${NC}   # Load data"
        echo -e "  ${YELLOW}./run.sh demo${NC}    # Run demo"
        ;;
esac
