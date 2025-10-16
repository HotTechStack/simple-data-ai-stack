"""Main application entry point."""
import asyncio
import signal
from redis.asyncio import Redis, ConnectionPool
from asyncpg import create_pool
from src.config import Config
from src.producer import EventProducer
from src.consumer import EventConsumer
from src.monitor import StreamMonitor


class StreamingEngine:
    """Main streaming engine orchestrator."""

    def __init__(self):
        self.config = Config.from_env()
        self.redis_pool = None
        self.redis_client = None
        self.pg_pool = None
        self.consumers = []
        self.monitor = None
        self.tasks = []
        self.shutdown_event = asyncio.Event()

    async def setup(self):
        """Initialize Redis and Postgres connections."""
        print("Setting up streaming engine...")

        # Create Redis connection pool
        self.redis_pool = ConnectionPool(
            host=self.config.redis.host,
            port=self.config.redis.port,
            db=self.config.redis.db,
            decode_responses=False,
            max_connections=self.config.stream.num_workers + 5
        )
        self.redis_client = Redis(connection_pool=self.redis_pool)

        # Test Redis connection
        await self.redis_client.ping()
        print(f"Connected to Redis at {self.config.redis.host}:{self.config.redis.port}")

        # Create Postgres connection pool
        self.pg_pool = await create_pool(
            dsn=self.config.postgres.dsn,
            min_size=5,
            max_size=self.config.stream.num_workers + 5
        )
        print(f"Connected to Postgres at {self.config.postgres.host}:{self.config.postgres.port}")

        # Initialize monitor
        self.monitor = StreamMonitor(self.redis_client, self.pg_pool, self.config)
        print("Monitor initialized")

        # Create consumers
        for worker_id in range(self.config.stream.num_workers):
            consumer = EventConsumer(
                self.redis_client,
                self.pg_pool,
                self.config,
                worker_id
            )
            self.consumers.append(consumer)

        print(f"Created {len(self.consumers)} consumer workers")

    async def start_consumers(self):
        """Start all consumer workers."""
        print("Starting consumer workers...")

        for consumer in self.consumers:
            task = asyncio.create_task(consumer.consume())
            self.tasks.append(task)

        print(f"Started {len(self.tasks)} consumer tasks")

    async def start_monitor(self):
        """Start monitoring loop."""
        print("Starting monitor...")
        monitor_task = asyncio.create_task(self.monitor.monitor_loop(interval_seconds=10))
        self.tasks.append(monitor_task)

    async def run(self):
        """Run the streaming engine."""
        await self.setup()
        await self.start_consumers()
        await self.start_monitor()

        print("\nStreaming engine is running!")
        print("Press Ctrl+C to shutdown gracefully\n")

        # Wait for shutdown signal
        await self.shutdown_event.wait()

    async def shutdown(self):
        """Gracefully shutdown the engine."""
        print("\nShutting down streaming engine...")

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)

        # Close connections
        if self.redis_client:
            await self.redis_client.close()
        if self.redis_pool:
            await self.redis_pool.disconnect()
        if self.pg_pool:
            await self.pg_pool.close()

        print("Shutdown complete")

    def handle_shutdown_signal(self, sig):
        """Handle shutdown signals."""
        print(f"\nReceived signal {sig}")
        self.shutdown_event.set()


async def main():
    """Main entry point."""
    engine = StreamingEngine()

    # Setup signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda s=sig: engine.handle_shutdown_signal(s)
        )

    try:
        await engine.run()
    finally:
        await engine.shutdown()


if __name__ == '__main__':
    asyncio.run(main())
