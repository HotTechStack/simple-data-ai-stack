"""Tests for event consumer."""
import pytest
import asyncio
import json
from redis.asyncio import Redis
from asyncpg import create_pool
from src.consumer import EventConsumer
from src.producer import EventProducer
from src.config import Config


@pytest.fixture
async def redis_client():
    """Create Redis client for testing."""
    config = Config.from_env()
    client = Redis(
        host=config.redis.host,
        port=config.redis.port,
        db=config.redis.db,
        decode_responses=False
    )

    # Clean up test streams
    await client.delete('test_consumer_stream')
    await client.delete('test_consumer_stream:dead')

    # Delete consumer groups
    try:
        await client.xgroup_destroy('test_consumer_stream', 'test_group')
    except:
        pass

    yield client

    # Cleanup
    await client.delete('test_consumer_stream')
    await client.delete('test_consumer_stream:dead')
    try:
        await client.xgroup_destroy('test_consumer_stream', 'test_group')
    except:
        pass

    await client.close()


@pytest.fixture
async def pg_pool():
    """Create Postgres connection pool for testing."""
    config = Config.from_env()
    pool = await create_pool(dsn=config.postgres.dsn, min_size=2, max_size=5)

    # Clean up test data
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM events WHERE event_type LIKE 'test_%'")
        await conn.execute("DELETE FROM dead_letter_queue WHERE event_type LIKE 'test_%'")

    yield pool

    # Cleanup
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM events WHERE event_type LIKE 'test_%'")
        await conn.execute("DELETE FROM dead_letter_queue WHERE event_type LIKE 'test_%'")

    await pool.close()


@pytest.fixture
def test_config():
    """Create test configuration."""
    config = Config.from_env()
    config.stream.stream_name = 'test_consumer_stream'
    config.stream.consumer_group = 'test_group'
    config.stream.consumer_name = 'test_consumer'
    config.stream.dlq_stream_name = 'test_consumer_stream:dead'
    config.stream.batch_size = 10
    config.stream.batch_timeout_seconds = 1
    return config


@pytest.mark.asyncio
async def test_consumer_group_creation(redis_client, pg_pool, test_config):
    """Test consumer group is created properly."""
    consumer = EventConsumer(redis_client, pg_pool, test_config, worker_id=0)
    await consumer.ensure_consumer_group()

    # Check group exists
    groups = await redis_client.xinfo_groups('test_consumer_stream')
    assert len(groups) == 1


@pytest.mark.asyncio
async def test_consume_and_process_events(redis_client, pg_pool, test_config):
    """Test consuming and processing events."""
    # Produce some events
    producer = EventProducer(redis_client, test_config)
    for i in range(5):
        await producer.produce(
            event_type='test_consume',
            payload={'counter': i, 'message': f'Test event {i}'}
        )

    # Create consumer and process
    consumer = EventConsumer(redis_client, pg_pool, test_config, worker_id=0)
    await consumer.ensure_consumer_group()

    # Read and accumulate events
    events = await consumer.read_events()
    consumer.batch.extend(events)

    # Process batch
    await consumer.process_batch()

    # Verify events in database
    async with pg_pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM events WHERE event_type = 'test_consume'"
        )
        assert count == 5


@pytest.mark.asyncio
async def test_batch_accumulation(redis_client, pg_pool, test_config):
    """Test batch accumulation logic."""
    import time
    consumer = EventConsumer(redis_client, pg_pool, test_config, worker_id=0)

    # Test batch size trigger
    consumer.batch = [(f'id-{i}', {'test': 'data'}) for i in range(10)]
    assert await consumer.should_flush_batch() == True

    # Test timeout trigger
    consumer.batch = [(f'id-{i}', {'test': 'data'}) for i in range(5)]
    consumer.last_batch_time = time.time() - 2
    assert await consumer.should_flush_batch() == True

    # Test no trigger
    consumer.batch = [(f'id-{i}', {'test': 'data'}) for i in range(5)]
    consumer.last_batch_time = time.time()
    assert await consumer.should_flush_batch() == False


@pytest.mark.asyncio
async def test_consumer_stats(redis_client, pg_pool, test_config):
    """Test consumer statistics tracking."""
    consumer = EventConsumer(redis_client, pg_pool, test_config, worker_id=0)

    # Produce and consume events
    producer = EventProducer(redis_client, test_config)
    await producer.produce_batch([
        ('test_stats', {'data': f'Event {i}'})
        for i in range(20)
    ])

    await consumer.ensure_consumer_group()
    events = await consumer.read_events()
    consumer.batch.extend(events)
    await consumer.process_batch()

    stats = await consumer.get_stats()
    assert stats['worker_id'] == 0
    assert stats['processed'] == 20
    assert stats['current_batch_size'] == 0


@pytest.mark.asyncio
async def test_high_throughput_consumption(redis_client, pg_pool, test_config):
    """Test consuming high volume of events."""
    # Produce 500 events
    producer = EventProducer(redis_client, test_config)
    events = [
        ('test_throughput', {'counter': i, 'data': f'Event {i}'})
        for i in range(500)
    ]
    await producer.produce_batch(events)

    # Consume all events
    consumer = EventConsumer(redis_client, pg_pool, test_config, worker_id=0)
    await consumer.ensure_consumer_group()

    # Process in multiple batches
    total_processed = 0
    for _ in range(10):  # Max 10 iterations to prevent infinite loop
        events = await consumer.read_events()
        if not events:
            break

        consumer.batch.extend(events)

        if await consumer.should_flush_batch():
            await consumer.process_batch()

        total_processed += len(events)

    # Process remaining
    if consumer.batch:
        await consumer.process_batch()

    # Verify all events in database
    async with pg_pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM events WHERE event_type = 'test_throughput'"
        )
        assert count == 500
