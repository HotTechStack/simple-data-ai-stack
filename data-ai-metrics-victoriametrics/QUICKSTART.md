# ⚡ Quick Start Guide

Get the VictoriaMetrics Data Pipeline Observability demo running in **under 5 minutes**.

## 🎯 Goal

By the end of this guide, you'll have:
- A running Polars ETL pipeline processing 10k+ rows
- Live metrics in VictoriaMetrics
- Beautiful Grafana dashboards showing pipeline performance
- Working understanding of modern data observability

## 📋 Prerequisites Check

```bash
# Docker (required)
docker --version
# Should show: Docker version 20.x or higher

# Docker Compose (required)
docker compose version
# Should show: Docker Compose version 2.x or higher

# Python (required)
python --version
# Should show: Python 3.11 or higher

# uv package manager (recommended but optional)
uv --version
# If not installed: curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 🚀 5-Step Setup

### Step 1: Configuration (30 seconds)

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI key (optional - only needed for LLM features)
nano .env  # or use your favorite editor
```

**Minimum .env content:**
```bash
OPENAI_API_KEY=sk-your-key-here  # Optional - skip if not using LLM features
```

### Step 2: Start Infrastructure (1 minute)

```bash
# Start all services
docker compose up -d

# Wait for services to be ready (about 10-15 seconds)
sleep 15

# Check services are running
docker compose ps
```

**What's starting:**
- VictoriaMetrics (metrics database)
- vmagent (metrics scraper)
- Grafana (dashboards)
- VictoriaLogs (log storage)
- VictoriaTraces (trace storage)

### Step 3: Install Dependencies (1 minute)

```bash
# Install Python dependencies
uv sync

# OR if you don't have uv:
pip install -e .
```

### Step 4: Setup Grafana (2 minutes)

1. **Open Grafana**: http://localhost:3000
2. **Login**: admin / admin (skip password change)
3. **Add VictoriaMetrics Datasource**:
   - Click Configuration (⚙️) → Data sources → Add data source
   - Search for "VictoriaMetrics"
   - Fill in:
     - Name: `VictoriaMetrics`
     - URL: `http://victoriametrics:8428`
   - Click **Save & Test** → Should show green ✅
   - Toggle **Default** ON at the top

4. **Import Dashboard**:
   - Go to Dashboards (四) → Import
   - Click "Upload JSON file"
   - Select `grafana/dashboards/pipeline-observability.json`
   - Click **Import**

### Step 5: Run the Pipeline (30 seconds)

```bash
# Start the ETL pipeline
uv run python polars_pipeline.py

# OR without uv:
python polars_pipeline.py
```

**Expected output:**
```
INFO - Starting Prometheus metrics server on port 8000...
INFO - Metrics available at http://localhost:8000/metrics
INFO - Starting ETL pipeline: etl_pipeline
INFO - [EXTRACT] Extracted 10000 rows
INFO - [TRANSFORM] Transformed 7542 rows
INFO - [QUALITY_CHECK] Quality Score: 98.45/100
INFO - [LOAD] Loaded 7542 rows to output/data.parquet
INFO - Pipeline completed successfully in 2.34s
```

**Keep this running!**

## 🎨 View Your Dashboard

### Open Grafana Dashboard

**URL:** http://localhost:3000/d/pipeline-observability

**What you should see (after 30-60 seconds):**
- ✅ Total rows processed (increasing number)
- ✅ Data quality score (90-100%)
- ✅ Throughput graphs (rows/second)
- ✅ Stage duration charts
- ✅ Error counts (should be 0)

**Note:** Wait 30-60 seconds for vmagent to scrape metrics for the first time.

## 🧪 Try Other Features

### DuckDB Analytics
Query VictoriaMetrics from SQL:

```bash
# Open new terminal (keep pipeline running)
uv run python duckdb_analytics.py
```

**You'll see:**
- Pipeline summary reports
- Stage performance analysis
- Data quality trends
- SQL analytics on metrics
- Parquet export demo

### LLM Natural Language Queries
Ask questions in plain English:

```bash
uv run python llm_metrics_query.py --interactive

# Try asking:
# "How many rows have been processed?"
# "What's the data quality score?"
# "Show me throughput by stage"
```

### OpenAI Tracing
See LLM calls traced in VictoriaTraces:

```bash
uv run python openai_conn.py
```

Then in Grafana:
- Go to Explore
- Select datasource: VictoriaTraces
- Service: random_joke_generator

## 📊 Understanding the Flow

### Pipeline Flow
```
Generate Data (Faker)
    ↓
Extract → metrics tracked
    ↓
Transform → metrics tracked
    ↓
Quality Checks → scores tracked
    ↓
Load to Parquet → size tracked
```

### Metrics Collection
```
polars_pipeline.py (port 8000)
    ↓ exposes /metrics
vmagent (port 8429) - scrapes every 30s
    ↓ pushes metrics
VictoriaMetrics (port 8428) - stores data
    ↓ query API
Grafana (port 3000) - visualizes
```

## 🐛 Common Issues & Solutions

### Dashboard Shows "Datasource not found"

**Problem:** Dashboard can't find VictoriaMetrics datasource.

**Solution:**
1. Make sure datasource is named exactly `VictoriaMetrics`
2. Check it's set as default datasource
3. Re-import dashboard

### Dashboard is Empty (No Data)

**Check these in order:**

```bash
# 1. Is pipeline exposing metrics?
curl http://localhost:8000/metrics | grep pipeline_rows

# 2. Does VictoriaMetrics have data?
curl 'http://localhost:8428/api/v1/query?query=pipeline_rows_processed_total'

# 3. Wait 60 seconds and refresh dashboard
```

If still no data:
```bash
# Check vmagent logs
docker compose logs vmagent | grep -i error
```

### "Connection Refused" Errors

**Pipeline can't start on port 8000:**
```bash
# Check what's using port 8000
lsof -i :8000

# Kill it or change port in polars_pipeline.py
```

**Can't connect to Grafana:**
```bash
# Check if Grafana is running
docker compose ps grafana

# View logs
docker compose logs grafana
```

### DuckDB Analytics Fails

**Missing pandas:**
```bash
uv sync  # reinstall all dependencies
```

## ✅ Success Checklist

You're done when you can:
- [x] Start services with one command
- [x] See pipeline processing data in terminal
- [x] View live metrics in Grafana dashboard
- [x] Query metrics via VictoriaMetrics API
- [x] Run DuckDB analytics successfully

**Congratulations!** 🎉 You now have a working data pipeline observability stack!

## 🎓 What's Next?

### Beginner (You are here!)
- [x] Get system running
- [ ] Explore Grafana dashboard - click around!
- [ ] Watch metrics update in real-time
- [ ] Check raw metrics: `curl http://localhost:8000/metrics`
- [ ] Read the full README.md

### Intermediate
- [ ] Read `polars_pipeline.py` - see how metrics are instrumented
- [ ] Modify pipeline to process more/less data
- [ ] Add your own custom metrics
- [ ] Create a custom Grafana panel

### Advanced
- [ ] Set up alerting rules in Grafana
- [ ] Integrate with your own data sources
- [ ] Add stream aggregation for storage optimization
- [ ] Deploy to production environment

## 📚 Learn More

- **Full Documentation**: [README.md](README.md)
- **Troubleshooting**: See README.md troubleshooting section
- **VictoriaMetrics Docs**: https://docs.victoriametrics.com/

## 💡 Pro Tips

**View Raw Metrics:**
```bash
# See all metrics
curl http://localhost:8000/metrics

# Filter specific metric
curl http://localhost:8000/metrics | grep pipeline_rows_processed

# Query VictoriaMetrics directly
curl 'http://localhost:8428/api/v1/query?query=pipeline_rows_processed_total{stage="extract"}'
```

**Watch Metrics Update Live:**
```bash
watch -n 2 'curl -s http://localhost:8428/api/v1/query?query=sum\(pipeline_rows_processed_total\) | jq .data.result[0].value[1]'
```

**Quick Cleanup:**
```bash
# Stop everything
docker compose down

# Remove all data
docker compose down -v
```

---

**Need help?** Check the [README.md](README.md) or run `./verify_setup.py` for diagnostics.

**Ready for more?** Try `uv run python llm_metrics_query.py --interactive` to query metrics with natural language! 🚀
