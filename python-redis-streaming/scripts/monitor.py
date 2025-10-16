"""Standalone monitoring script."""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from redis.asyncio import Redis
from asyncpg import create_pool
from src.config import Config
from src.monitor import StreamMonitor


async def run_monitor(interval: int = 5):
    """Run monitoring dashboard."""
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

    # Connect to Postgres
    try:
        pg_pool = await create_pool(dsn=config.postgres.dsn, min_size=2, max_size=5)
        print(f"Connected to Postgres at {config.postgres.host}:{config.postgres.port}")
    except Exception as e:
        print(f"Failed to connect to Postgres: {e}")
        await redis_client.close()
        return

    monitor = StreamMonitor(redis_client, pg_pool, config)

    print(f"\nStarting monitor (refreshing every {interval} seconds)")
    print("Press Ctrl+C to exit\n")

    try:
        await monitor.monitor_loop(interval_seconds=interval)
    except KeyboardInterrupt:
        print("\nStopping monitor...")
    finally:
        await redis_client.close()
        await pg_pool.close()


if __name__ == '__main__':
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    asyncio.run(run_monitor(interval))
