"""Produce sample events for testing."""
import asyncio
import sys
import random
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from redis.asyncio import Redis
from src.config import Config
from src.producer import EventProducer


SAMPLE_EVENT_TYPES = [
    'user_created',
    'user_updated',
    'order_placed',
    'order_shipped',
    'order_delivered',
    'payment_processed',
    'payment_failed',
    'inventory_updated',
    'product_viewed',
    'cart_updated'
]


async def produce_samples(num_events: int = 100):
    """Produce sample events."""
    config = Config.from_env()

    redis_client = Redis(
        host=config.redis.host,
        port=config.redis.port,
        db=config.redis.db,
        decode_responses=False
    )

    try:
        await redis_client.ping()
        print(f"Connected to Redis at {config.redis.host}:{config.redis.port}")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        return

    producer = EventProducer(redis_client, config)

    print(f"\nProducing {num_events} sample events...")

    events = []
    for i in range(num_events):
        event_type = random.choice(SAMPLE_EVENT_TYPES)

        # Generate realistic payloads based on event type
        if 'user' in event_type:
            payload = {
                'user_id': random.randint(1000, 9999),
                'email': f'user{random.randint(1, 1000)}@example.com',
                'timestamp': asyncio.get_event_loop().time()
            }
        elif 'order' in event_type:
            payload = {
                'order_id': f'ORD-{random.randint(10000, 99999)}',
                'user_id': random.randint(1000, 9999),
                'amount': round(random.uniform(10, 500), 2),
                'items_count': random.randint(1, 10),
                'timestamp': asyncio.get_event_loop().time()
            }
        elif 'payment' in event_type:
            payload = {
                'transaction_id': f'TXN-{random.randint(100000, 999999)}',
                'amount': round(random.uniform(10, 500), 2),
                'method': random.choice(['credit_card', 'debit_card', 'paypal', 'crypto']),
                'timestamp': asyncio.get_event_loop().time()
            }
        else:
            payload = {
                'id': random.randint(1, 10000),
                'data': f'Sample data {i}',
                'timestamp': asyncio.get_event_loop().time()
            }

        events.append((event_type, payload))

    # Produce in batches of 100
    batch_size = 100
    for i in range(0, len(events), batch_size):
        batch = events[i:i+batch_size]
        await producer.produce_batch(batch)
        print(f"Produced {min(i+batch_size, len(events))}/{len(events)} events...")

    print(f"\nSuccessfully produced {num_events} events!")

    # Show stream length
    stream_len = await redis_client.xlen(config.stream.stream_name)
    print(f"Current stream length: {stream_len}")

    await redis_client.close()


if __name__ == '__main__':
    num_events = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    asyncio.run(produce_samples(num_events))
