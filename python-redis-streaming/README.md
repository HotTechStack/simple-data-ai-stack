# Python Redis Streaming

High-performance streaming pipeline using Python, Redis Streams, and Postgres. No Kafka needed.

## Why This Stack?

Everyone thinks you need Kafka for streaming. Not really.

**Python Can Handle Streaming — Here's How:**

- Python's asyncio is I/O-bound friendly — the GIL doesn't matter when you're waiting on network or disk
- Redis Streams + asyncpg give you persistence, consumer groups, and bulk inserts — all the primitives you need
- Most "real-time" workloads are under 10K events/sec — Python handles that on a single box without breaking a sweat

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│  Producers  │─────▶│ Redis Stream │─────▶│  Consumers  │
│   (async)   │      │   (buffer)   │      │  (5 workers)│
└─────────────┘      └──────────────┘      └──────┬──────┘
                                                   │
                                                   │ Batch Insert
                                                   │ (500 events or 2s)
                                                   ▼
                                            ┌─────────────┐
                                            │  Postgres   │
                                            │ (JSONB cols)│
                                            └─────────────┘
```

**Key Components:**

- **Docker Compose** with three services — Redis, Postgres, Python app running with uv
- **uv** syncs dependencies in 200ms — faster Docker builds, smaller images, no pip confusion
- **redis-py** with connection pooling — one connection per asyncio worker, reused across requests
- **Redis Streams** with XREADGROUP — consumer groups claim messages, no duplicate processing

## Scaling Logic

- `asyncio.create_task()` spawns your consumer pool — 5-10 workers per core is the sweet spot
- Each worker reads 100 events from Redis Stream — `XREADGROUP BLOCK 5000 COUNT 100`
- Batch accumulates until 500 records or 2 seconds — whichever comes first
- `asyncpg.executemany()` bulk inserts to Postgres — one round-trip beats 500 inserts

## Reliability

- **Backpressure** happens automatically — queue.put() blocking slows producers naturally
- **Dead letter queue** is another Redis Stream — just XADD to 'stream:dead' with error details
- **XACK** after Postgres insert — crash recovery replays unacknowledged messages for free
- **Postgres JSONB** columns store raw events — schema evolution doesn't break the pipeline

## Observability

- `XLEN` monitors stream depth — if it grows past 10K, fix consumers, not producers
- `pg_stat_statements` tracks insert latency — tune slowest queries first
- The entire engine is ~250 lines of Python — producer loop, consumer pool, batch inserter, that's it

**It runs 10K events/sec on one box.**

If it breaks, you've earned enough to hire a team for Kafka.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer

Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 1. Clone and Setup

```bash
cd python-redis-streaming
cp .env.example .env
```

### 2. Start Services

The `run.sh` script handles everything:

```bash
# Start Redis and Postgres
./run.sh

# Start the streaming engine
./run.sh start
```

### 3. Produce Sample Events

In another terminal:

```bash
# Produce 1000 sample events
./run.sh produce 1000

# Or produce 5000 events
./run.sh produce 5000
```

### 4. Monitor the Pipeline

In another terminal:

```bash
# Monitor with 5 second refresh
./run.sh monitor

# Or with 10 second refresh
./run.sh monitor 10
```

You'll see:
```
============================================================
STREAMING PIPELINE DASHBOARD
============================================================

Redis Streams:
  Stream Length: 1523
  Pending Messages: 0
  DLQ Length: 0

Postgres:
  Total Events: 8477
  Events (last minute): 1000
  DLQ Count: 0
  Table Size: 1256 kB

  Events by Type:
    order_placed: 1243
    user_created: 1189
    payment_processed: 1156
    product_viewed: 1098
    order_shipped: 1067

============================================================
```

## Running Tests

```bash
# Make sure services are running first
./run.sh

# Run tests
./run.sh test
```

## Benchmarking

Test the throughput:

```bash
# Run at 10K events/sec for 60 seconds
./run.sh benchmark 10000 60

# Run at 5K events/sec for 30 seconds
./run.sh benchmark 5000 30
```

Expected output:
```
============================================================
STREAMING BENCHMARK
============================================================
Target Rate: 10000 events/sec
Duration: 60 seconds
Expected Total: 600000 events
============================================================

Produced 1000 events...
Produced 2000 events...
...
Produced 600000 events...
Completed: 600000 total events produced

============================================================
BENCHMARK RESULTS
============================================================
Total Events: 600000
Elapsed Time: 60.02 seconds
Actual Rate: 9996.67 events/sec
Target Rate: 10000 events/sec
Accuracy: 99.97%
============================================================
```

## Project Structure

```
python-redis-streaming/
├── src/
│   ├── config.py       # Configuration management
│   ├── producer.py     # Event producer
│   ├── consumer.py     # Event consumer with batching
│   ├── monitor.py      # Observability utilities
│   └── main.py         # Main application
├── tests/
│   ├── test_producer.py
│   └── test_consumer.py
├── scripts/
│   ├── produce_sample.py  # Produce sample events
│   ├── monitor.py         # Standalone monitoring
│   └── benchmark.py       # Benchmark script
├── docker-compose.yml
├── Dockerfile
├── init.sql            # Postgres schema
├── pyproject.toml
├── run.sh              # Main entry script
└── README.md
```

## Configuration

Edit `.env` to customize:

```bash
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=streaming
POSTGRES_USER=streaming_user
POSTGRES_PASSWORD=streaming_pass

# Streaming config
NUM_WORKERS=5              # Consumer workers
BATCH_SIZE=500             # Events per batch
BATCH_TIMEOUT_SECONDS=2    # Max wait time for batch
XREAD_COUNT=100            # Events to read per XREADGROUP
XREAD_BLOCK_MS=5000        # Block time for XREADGROUP
```

## How It Works

### Producer

```python
# Produce single event
await producer.produce('user_created', {
    'user_id': 123,
    'email': 'user@example.com'
})

# Produce batch
events = [
    ('order_placed', {'order_id': 'ORD-123', 'amount': 99.99}),
    ('payment_processed', {'txn_id': 'TXN-456'})
]
await producer.produce_batch(events)
```

### Consumer

Consumers automatically:
1. Read from Redis Stream using consumer groups
2. Accumulate events into batches
3. Bulk insert to Postgres when batch is full or timeout expires
4. Acknowledge messages after successful insert
5. Send failed messages to dead letter queue

### Monitoring

```python
# Get stream length
stream_len = await monitor.get_stream_length()

# Get pending messages
pending = await monitor.get_pending_messages()

# Get Postgres stats
stats = await monitor.get_postgres_stats()
```

## Advanced Usage

### Docker Compose Only

```bash
# Start everything with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f streaming-app

# Stop everything
docker-compose down
```

### Local Development

```bash
# Install dependencies
uv sync

# Start Redis and Postgres only
docker-compose up -d redis postgres

# Run locally
uv run python -m src.main

# Run tests
uv run pytest tests/ -v
```

### Useful Commands

```bash
# Check Redis stream length
docker-compose exec redis redis-cli XLEN events

# Check Postgres data
docker-compose exec postgres psql -U streaming_user -d streaming -c "SELECT COUNT(*) FROM events;"

# View consumer groups
docker-compose exec redis redis-cli XINFO GROUPS events

# Clear all data
./run.sh clean
```

## Performance Tips

1. **Tune batch size**: Larger batches = better throughput, higher latency
2. **Add more workers**: Scale horizontally by increasing NUM_WORKERS
3. **Connection pooling**: Already configured optimally
4. **Postgres tuning**: Use JSONB indexes for query optimization
5. **Monitor XLEN**: If stream grows, add more consumers

## Troubleshooting

### Stream keeps growing

Consumers can't keep up with producers. Solutions:
- Increase NUM_WORKERS
- Increase BATCH_SIZE
- Check Postgres insert latency

### High insert latency

Check Postgres performance:
```sql
SELECT * FROM pg_stat_statements
WHERE query LIKE '%INSERT INTO events%';
```

### Messages in DLQ

Check dead letter queue:
```bash
docker-compose exec postgres psql -U streaming_user -d streaming -c "SELECT * FROM dead_letter_queue ORDER BY failed_at DESC LIMIT 10;"
```

## License

MIT

## Contributing

PRs welcome! This is a learning project showing how Python can handle streaming workloads.

## Learn More

- [Redis Streams](https://redis.io/docs/data-types/streams/)
- [asyncpg](https://github.com/MagicStack/asyncpg)
- [uv](https://github.com/astral-sh/uv)
