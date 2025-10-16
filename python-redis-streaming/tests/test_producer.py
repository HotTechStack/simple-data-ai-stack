"""Tests for event producer."""
import pytest
import asyncio
from redis.asyncio import Redis
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

    # Clean up test stream
    await client.delete('test_stream')

    yield client

    # Cleanup
    await client.delete('test_stream')
    await client.close()


@pytest.fixture
def test_config():
    """Create test configuration."""
    config = Config.from_env()
    config.stream.stream_name = 'test_stream'
    return config


@pytest.mark.asyncio
async def test_produce_single_event(redis_client, test_config):
    """Test producing a single event."""
    producer = EventProducer(redis_client, test_config)

    event_id = await producer.produce(
        event_type='test_event',
        payload={'message': 'Hello World', 'count': 1}
    )

    assert event_id is not None

    # Verify event in stream
    stream_len = await redis_client.xlen('test_stream')
    assert stream_len == 1


@pytest.mark.asyncio
async def test_produce_batch(redis_client, test_config):
    """Test producing batch of events."""
    producer = EventProducer(redis_client, test_config)

    events = [
        ('event_type_1', {'data': f'Event {i}'})
        for i in range(10)
    ]

    event_ids = await producer.produce_batch(events)

    assert len(event_ids) == 10

    # Verify events in stream
    stream_len = await redis_client.xlen('test_stream')
    assert stream_len == 10


@pytest.mark.asyncio
async def test_produce_different_event_types(redis_client, test_config):
    """Test producing different event types."""
    producer = EventProducer(redis_client, test_config)

    await producer.produce('user_created', {'user_id': 123, 'email': 'test@example.com'})
    await producer.produce('order_placed', {'order_id': 456, 'amount': 99.99})
    await producer.produce('payment_processed', {'transaction_id': 'txn_789'})

    stream_len = await redis_client.xlen('test_stream')
    assert stream_len == 3


@pytest.mark.asyncio
async def test_produce_high_throughput(redis_client, test_config):
    """Test producing events at high throughput."""
    producer = EventProducer(redis_client, test_config)

    # Produce 1000 events
    events = [
        ('high_throughput_test', {'counter': i, 'data': f'Event {i}'})
        for i in range(1000)
    ]

    event_ids = await producer.produce_batch(events)
    assert len(event_ids) == 1000

    stream_len = await redis_client.xlen('test_stream')
    assert stream_len == 1000
