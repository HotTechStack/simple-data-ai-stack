"""Benchmark script to test streaming throughput."""
import asyncio
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from redis.asyncio import Redis
from src.config import Config
from src.producer import EventProducer


async def benchmark(rate_per_second: int = 10000, duration_seconds: int = 60):
    """
    Run benchmark test.

    Args:
        rate_per_second: Target events per second
        duration_seconds: How long to run the test
    """
    config = Config.from_env()

    # Connect to Redis
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

    print("\n" + "="*60)
    print("STREAMING BENCHMARK")
    print("="*60)
    print(f"Target Rate: {rate_per_second} events/sec")
    print(f"Duration: {duration_seconds} seconds")
    print(f"Expected Total: {rate_per_second * duration_seconds} events")
    print("="*60 + "\n")

    start_time = time.time()

    # Run benchmark
    total_produced = await producer.produce_continuous(
        event_type='benchmark_event',
        rate_per_second=rate_per_second,
        duration_seconds=duration_seconds
    )

    elapsed = time.time() - start_time
    actual_rate = total_produced / elapsed

    print("\n" + "="*60)
    print("BENCHMARK RESULTS")
    print("="*60)
    print(f"Total Events: {total_produced}")
    print(f"Elapsed Time: {elapsed:.2f} seconds")
    print(f"Actual Rate: {actual_rate:.2f} events/sec")
    print(f"Target Rate: {rate_per_second} events/sec")
    print(f"Accuracy: {(actual_rate/rate_per_second)*100:.2f}%")
    print("="*60 + "\n")

    await redis_client.close()


if __name__ == '__main__':
    # Default: 10K events/sec for 60 seconds
    rate = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60

    asyncio.run(benchmark(rate, duration))
