"""Event producer for Redis Streams."""
import asyncio
import json
import time
from typing import Dict, Any
from redis.asyncio import Redis
from src.config import Config


class EventProducer:
    """Produces events to Redis Stream with connection pooling."""

    def __init__(self, redis_client: Redis, config: Config):
        self.redis = redis_client
        self.config = config
        self.stream_name = config.stream.stream_name

    async def produce(self, event_type: str, payload: Dict[str, Any]) -> str:
        """
        Produce a single event to Redis Stream.

        Args:
            event_type: Type of the event
            payload: Event payload data

        Returns:
            Event ID from Redis Stream
        """
        event_data = {
            'event_type': event_type,
            'payload': json.dumps(payload),
            'timestamp': str(time.time())
        }

        event_id = await self.redis.xadd(
            self.stream_name,
            event_data
        )

        return event_id.decode('utf-8') if isinstance(event_id, bytes) else event_id

    async def produce_batch(self, events: list[tuple[str, Dict[str, Any]]]) -> list[str]:
        """
        Produce multiple events efficiently using pipeline.

        Args:
            events: List of (event_type, payload) tuples

        Returns:
            List of event IDs
        """
        pipeline = self.redis.pipeline()

        for event_type, payload in events:
            event_data = {
                'event_type': event_type,
                'payload': json.dumps(payload),
                'timestamp': str(time.time())
            }
            pipeline.xadd(self.stream_name, event_data)

        results = await pipeline.execute()
        return [
            result.decode('utf-8') if isinstance(result, bytes) else result
            for result in results
        ]

    async def produce_continuous(
        self,
        event_type: str,
        rate_per_second: int,
        duration_seconds: int = 60
    ) -> int:
        """
        Produce events continuously at a specified rate.
        Used for testing and benchmarking.

        Args:
            event_type: Type of events to produce
            rate_per_second: Target events per second
            duration_seconds: How long to produce events

        Returns:
            Total number of events produced
        """
        total_produced = 0
        interval = 1.0 / rate_per_second
        end_time = time.time() + duration_seconds

        print(f"Starting continuous production: {rate_per_second} events/sec for {duration_seconds}s")

        while time.time() < end_time:
            payload = {
                'counter': total_produced,
                'timestamp': time.time(),
                'data': f'Event number {total_produced}'
            }

            await self.produce(event_type, payload)
            total_produced += 1

            if total_produced % 1000 == 0:
                print(f"Produced {total_produced} events...")

            await asyncio.sleep(interval)

        print(f"Completed: {total_produced} total events produced")
        return total_produced
