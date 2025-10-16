# Quick Start Guide

Get the streaming engine running in under 2 minutes.

## Prerequisites

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Ensure Docker is running
docker --version
```

## Step 1: Setup

```bash
# Copy environment file
cp .env.example .env

# Install dependencies (takes ~200ms with uv!)
uv sync --extra dev
```

## Step 2: Start Services

```bash
# Start Redis and Postgres
./run.sh
```

This will:
- Start Redis on port 6379
- Start Postgres on port 5432
- Initialize database schema
- Wait for services to be healthy

## Step 3: Run Tests

```bash
# Run all tests to verify everything works
./run.sh test
```

Expected output:
```
============================= test session starts ==============================
...
======================== 9 passed in 5.44s =========================
```

## Step 4: Start the Streaming Engine

In one terminal:
```bash
# Start the engine (monitors every 10 seconds)
./run.sh start
```

You'll see:
```
Setting up streaming engine...
Connected to Redis at localhost:6379
Connected to Postgres at localhost:5432
Created 5 consumer workers
Streaming engine is running!
```

## Step 5: Produce Events

In another terminal:
```bash
# Produce 1000 sample events
./run.sh produce 1000
```

Watch the first terminal to see:
- Events being consumed in batches
- Real-time dashboard updates
- Throughput statistics

## Step 6: Monitor the Pipeline

In a third terminal:
```bash
# Monitor with 5-second refresh
./run.sh monitor 5
```

You'll see a live dashboard:
```
============================================================
STREAMING PIPELINE DASHBOARD
============================================================

Redis Streams:
  Stream Length: 523
  Pending Messages: 0
  DLQ Length: 0

Postgres:
  Total Events: 1000
  Events (last minute): 1000
  DLQ Count: 0
  Table Size: 528 kB

  Events by Type:
    order_placed: 145
    user_created: 132
    payment_processed: 121
    ...
============================================================
```

## Quick Commands Reference

```bash
# Produce events
./run.sh produce 100        # 100 events
./run.sh produce 10000      # 10K events

# Monitor
./run.sh monitor 5          # 5 second refresh
./run.sh monitor 10         # 10 second refresh

# Benchmark
./run.sh benchmark 10000 60 # 10K events/sec for 60s
./run.sh benchmark 5000 30  # 5K events/sec for 30s

# View logs
./run.sh logs               # streaming-app logs
./run.sh logs redis         # redis logs
./run.sh logs postgres      # postgres logs

# Stop everything
./run.sh stop

# Clean up (removes all data)
./run.sh clean
```

## Troubleshooting

### Services won't start
```bash
# Check if ports are in use
lsof -i :6379  # Redis
lsof -i :5432  # Postgres

# Clean up and restart
./run.sh clean
./run.sh
```

### Stream keeps growing
```bash
# Check if consumers are running
./run.sh logs | grep "Worker"

# Increase workers in .env
NUM_WORKERS=10
```

### Test the connection manually
```bash
# Test Redis
docker-compose exec redis redis-cli ping

# Test Postgres
docker-compose exec postgres psql -U streaming_user -d streaming -c "SELECT COUNT(*) FROM events;"
```

## What's Next?

1. **Read the Architecture**: Check [README.md](README.md) for detailed architecture
2. **Explore the Code**: Start with `src/main.py` - it's only ~100 lines
3. **Customize Events**: Edit `scripts/produce_sample.py` for your event types
4. **Tune Performance**: Adjust `BATCH_SIZE` and `NUM_WORKERS` in `.env`

## Production Checklist

Before deploying to production:

- [ ] Update `.env` with production credentials
- [ ] Set up proper monitoring (Prometheus/Grafana)
- [ ] Configure Redis persistence settings
- [ ] Tune Postgres for your workload
- [ ] Set up backup/recovery procedures
- [ ] Load test at your expected throughput
- [ ] Set up alerts for stream depth > 10K
- [ ] Monitor DLQ regularly

## Support

- Issues: Check [README.md](README.md) troubleshooting section
- Performance: The engine handles 10K events/sec on a single box
- Scaling: If you need more, consider adding more workers or horizontal scaling

Happy streaming!
