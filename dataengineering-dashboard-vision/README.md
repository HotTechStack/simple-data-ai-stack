# AI Agents Reading Your Data Dashboards

**Conversational data validation with CUA + Grafana**

Ask questions about your metrics. Get answers with context. No dashboard clicking required.

## What This Does

- CUA reads your Grafana dashboards like a senior data engineer
- Ask: "Any pipeline failures in the last 24 hours?" → get root cause analysis
- Ask: "Why did the ETL run take 3x longer today?" → get correlation across metrics
- Ask: "Which table hasn't been updated?" → get freshness validation

**10× faster root cause analysis. Zero dashboards opened. All insights in chat.**

## Stack

```
docker-compose.yml
├── Grafana (dashboards)
├── Prometheus (metrics)
├── Node Exporter (system metrics)
├── CUA Ubuntu (browser container)
└── CUA Agent (AI that reads dashboards)
    └── uv for fast package management
```

## Quick Start

### 1. Prerequisites

- Docker Desktop or Docker Engine
- Anthropic API key (get from https://console.anthropic.com)
- 4GB RAM minimum
- uv (optional for local development): `curl -LsSf https://astral.sh/uv/install.sh | sh`

### 2. Setup

```bash
# Clone or create project directory
mkdir cua-dashboard-agent && cd cua-dashboard-agent

# Copy all files from the artifact

# Create .env file
make setup

# Add your API key
# Edit .env and add: ANTHROPIC_API_KEY=your-key-here
```

### 3. Run (Docker - Production)

```bash
# Start the entire stack (uses uv inside containers)
docker-compose up -d

# Wait 30 seconds for services to start

# Check services are running
docker-compose ps

# Run the agent in interactive mode
make agent
```

### 4. Run (Local Development - Faster)

```bash
# Install dependencies with uv (much faster than pip)
make dev-install
source .venv/bin/activate
uv pip install -r requirements.txt

# Start only Grafana/Prometheus
docker-compose up -d grafana prometheus node-exporter

# Run agent locally
python agent/dashboard_agent.py
```

### 4. Access Grafana

Open browser to http://localhost:3000

- Username: `admin`
- Password: `admin`

You'll see basic system metrics from Node Exporter.

## Usage

### Interactive Mode (Default)

```bash
docker-compose run --rm cua-agent

# Then ask questions:
Your question: What metrics are currently being collected?
Your question: Show me CPU usage over the last hour
Your question: Any memory spikes or anomalies?
```

### Example Scenarios Mode

```bash
# Run pre-configured scenarios
docker-compose run --rm -e MODE=examples cua-agent
```

### Point at Your Own Dashboards

Edit `.env`:

```bash
# Point to your existing Grafana
GRAFANA_URL=http://your-grafana-url:3000
GRAFANA_USER=your-username
GRAFANA_PASSWORD=your-password
```

Then run:

```bash
docker-compose up -d grafana prometheus  # Skip if using external Grafana
docker-compose run --rm cua-agent
```

## How It Works

1. **CUA Container** — Ubuntu desktop in Docker, runs Firefox
2. **Agent** — Claude 3.5 Sonnet controls the browser, reads dashboards
3. **Computer Interface** — Takes screenshots, clicks, types, navigates
4. **Reasoning Loop** — Analyzes metrics, correlates patterns, reports findings

**No Grafana API integration needed. Agent reads what you read.**

## Example Questions

```
"Any compute spikes in the last 24 hours?"
"Is RAM utilization concerning?"
"Which namespace looks unhealthy?"
"Why did disk I/O spike at 2:15am?"
"Compare CPU usage today vs yesterday"
"List all dashboards and their status"
"Show me the 3 most concerning metrics right now"
```

## Output

Answers are:
- Printed to console in real-time
- Saved to `outputs/analysis_TIMESTAMP.txt`
- Include screenshots (future feature)

## Architecture

```
You → Question
  ↓
CUA Agent (Claude 3.5 Sonnet)
  ↓
CUA Computer (Ubuntu container)
  ↓
Firefox → Grafana Dashboard
  ↓
Screenshots → Analysis
  ↓
Answer with Context
```

## Validate Locally Before Prod

- Point agent at localhost Grafana first
- Test with synthetic metrics (Node Exporter)
- Verify agent catches anomalies
- Then point at production dashboards

**If it doesn't work on localhost, it won't work in prod.**

## Extending

### Local Development with uv

For faster local development:

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install deps (much faster than pip)
uv venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
uv pip install -r requirements.txt

# Run agent locally
python agent/dashboard_agent.py
```

### Add Custom Metrics

Edit `prometheus.yml` to scrape your services:

```yaml
scrape_configs:
  - job_name: 'your-app'
    static_configs:
      - targets: ['your-app:8080']
```

### Use Different Models

Edit `agent/dashboard_agent.py`:

```python
# Use OpenAI instead of Anthropic
agent = ComputerAgent(
    model="openai/gpt-4o",
    tools=[computer],
)

# Use local model with Ollama
agent = ComputerAgent(
    model="omniparser+ollama_chat/llama3.2:latest",
    tools=[computer],
)
```

### Add More Dashboards

Import dashboards in Grafana:
- Go to http://localhost:3000
- Dashboards → Import
- Use ID from https://grafana.com/grafana/dashboards/

Agent will automatically read them.

## Costs

- Anthropic Claude 3.5 Sonnet: ~$0.01-0.05 per question (depends on complexity)
- OpenAI GPT-4o: ~$0.02-0.10 per question
- Local models (Ollama): Free, but slower

Budget limit: Set `max_trajectory_budget` in code (default: $5.00)

## Troubleshooting

**Services won't start:**
```bash
docker-compose down -v
docker-compose up -d
docker-compose logs -f
```

**CUA container can't connect:**
```bash
# Check if running on ARM (M1/M2 Mac)
# CUA requires amd64 platform
docker pull --platform=linux/amd64 trycua/cua-ubuntu:latest
```

**Agent errors:**
```bash
# Verify API key is set
echo $ANTHROPIC_API_KEY

# Check agent logs
docker-compose logs cua-agent
```

**Grafana won't load:**
```bash
# Wait longer (first startup takes 60s)
docker-compose ps

# Check Grafana logs
docker-compose logs grafana
```

## Next Steps

1. Point at your production Grafana
2. Test with real dashboards (Kubernetes, Airflow, Postgres)
3. Schedule periodic checks (cron + docker-compose run)
4. Build custom dashboards for your data pipelines
5. Integrate with Slack (send analysis to channels)

## Why This Works

- **Browser automation beats APIs** — screenshots are universal, APIs change
- **Local first** — validate on localhost before pointing at prod
- **Docker-compose** — entire stack in one command
- **Conversational** — ask questions instead of reading 47 panels

**From dashboards to dialogue. This is Data + AI Engineering 2026.**

## Resources

- CUA Docs: https://docs.cua.ai
- CUA GitHub: https://github.com/trycua/cua
- Grafana Dashboards: https://grafana.com/grafana/dashboards/
- Blog Post: [Link to your blog]

## License

MIT

---

**Questions? Issues? Improvements?**

Open an issue or contribute to make this better.