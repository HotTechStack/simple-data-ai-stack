.PHONY: help setup start stop logs clean agent examples dev-install

help:
	@echo "CUA Dashboard Agent - Quick Commands"
	@echo ""
	@echo "  make setup       - Create .env file and directories"
	@echo "  make dev-install - Install with uv for local development"
	@echo "  make start       - Start all services"
	@echo "  make stop        - Stop all services"
	@echo "  make logs        - View logs"
	@echo "  make agent       - Run agent in interactive mode"
	@echo "  make examples    - Run example scenarios"
	@echo "  make clean       - Remove all containers and volumes"
	@echo ""

setup:
	@echo "Setting up CUA Dashboard Agent..."
	@cp -n .env.example .env || true
	@mkdir -p agent outputs grafana-dashboards
	@echo "✓ Created .env and directories"
	@echo ""
	@echo "⚠️  Edit .env and add your ANTHROPIC_API_KEY"
	@echo ""

dev-install:
	@echo "Installing dependencies with uv (fast!)..."
	@command -v uv >/dev/null 2>&1 || { echo "Installing uv..."; curl -LsSf https://astral.sh/uv/install.sh | sh; }
	uv venv
	@echo "✓ Virtual environment created"
	@echo ""
	@echo "Activate with: source .venv/bin/activate"
	@echo "Then run: uv pip install -r requirements.txt"

start:
	@echo "Starting services..."
	docker-compose up -d
	@echo ""
	@echo "✓ Services started"
	@echo ""
	@echo "Grafana: http://localhost:3000 (admin/admin)"
	@echo "Prometheus: http://localhost:9090"
	@echo "CUA Desktop: http://localhost:6080 (password: password)"
	@echo ""
	@echo "Run 'make agent' to start asking questions"

stop:
	docker-compose down

logs:
	docker-compose logs -f

agent:
	docker-compose run --rm cua-agent

examples:
	docker-compose run --rm -e MODE=examples cua-agent

clean:
	docker-compose down -v
	@echo "✓ Cleaned up containers and volumes"