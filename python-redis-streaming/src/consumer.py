"""Event consumer with consumer groups and batch processing."""
import asyncio
import json
import time
from typing import Dict, Any, Optional
from redis.asyncio import Redis
from asyncpg import Pool
from src.config import Config


class EventConsumer:
    """
    Consumes events from Redis Stream using consumer groups.
    Implements batching and dead letter queue for failed messages.
    """

    def __init__(
        self,
        redis_client: Redis,
        pg_pool: Pool,
        config: Config,
        worker_id: int
    ):
        self.redis = redis_client
        self.pg_pool = pg_pool
        self.config = config
        self.worker_id = worker_id
        self.consumer_name = f"{config.stream.consumer_name}-{worker_id}"
        self.stream_name = config.stream.stream_name
        self.group_name = config.stream.consumer_group
        self.dlq_stream = config.stream.dlq_stream_name

        # Batch configuration
        self.batch_size = config.stream.batch_size
        self.batch_timeout = config.stream.batch_timeout_seconds
        self.xread_count = config.stream.xread_count
        self.xread_block = config.stream.xread_block_ms

        # Batch accumulator
        self.batch: list[tuple[str, Dict[str, Any]]] = []
        self.last_batch_time = time.time()

        # Stats
        self.processed_count = 0
        self.error_count = 0

    async def ensure_consumer_group(self):
        """Create consumer group if it doesn't exist."""
        try:
            await self.redis.xgroup_create(
                self.stream_name,
                self.group_name,
                id='0',
                mkstream=True
            )
            print(f"Consumer group '{self.group_name}' created")
        except Exception as e:
            if 'BUSYGROUP' not in str(e):
                print(f"Error creating consumer group: {e}")

    async def read_events(self) -> list[tuple[str, Dict[str, Any]]]:
        """
        Read events from Redis Stream using XREADGROUP.

        Returns:
            List of (event_id, event_data) tuples
        """
        try:
            # XREADGROUP BLOCK 5000 COUNT 100 GROUP processors consumer-1 STREAMS events >
            messages = await self.redis.xreadgroup(
                groupname=self.group_name,
                consumername=self.consumer_name,
                streams={self.stream_name: '>'},
                count=self.xread_count,
                block=self.xread_block
            )

            if not messages:
                return []

            events = []
            for stream_name, stream_messages in messages:
                for message_id, message_data in stream_messages:
                    event_id = message_id.decode('utf-8') if isinstance(message_id, bytes) else message_id

                    # Decode message data
                    decoded_data = {}
                    for key, value in message_data.items():
                        key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                        value_str = value.decode('utf-8') if isinstance(value, bytes) else value
                        decoded_data[key_str] = value_str

                    events.append((event_id, decoded_data))

            return events

        except Exception as e:
            print(f"Worker {self.worker_id}: Error reading from stream: {e}")
            return []

    async def process_batch(self):
        """Insert batch to Postgres using executemany for efficiency."""
        if not self.batch:
            return

        try:
            # Prepare batch data for insertion
            records = []
            event_ids = []

            for event_id, event_data in self.batch:
                event_type = event_data.get('event_type', 'unknown')
                payload_str = event_data.get('payload', '{}')

                try:
                    payload = json.loads(payload_str)
                except json.JSONDecodeError:
                    payload = {'raw': payload_str}

                records.append((event_id, event_type, json.dumps(payload)))
                event_ids.append(event_id)

            # Bulk insert using executemany
            async with self.pg_pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO events (event_id, event_type, payload)
                    VALUES ($1, $2, $3::jsonb)
                    """,
                    records
                )

            # Acknowledge all messages after successful insert
            pipeline = self.redis.pipeline()
            for event_id in event_ids:
                pipeline.xack(self.stream_name, self.group_name, event_id)
            await pipeline.execute()

            self.processed_count += len(self.batch)
            print(f"Worker {self.worker_id}: Processed batch of {len(self.batch)} events (total: {self.processed_count})")

        except Exception as e:
            print(f"Worker {self.worker_id}: Error processing batch: {e}")
            self.error_count += len(self.batch)

            # Send failed events to DLQ
            await self.send_to_dlq(self.batch, str(e))

        finally:
            # Clear batch
            self.batch.clear()
            self.last_batch_time = time.time()

    async def send_to_dlq(self, events: list[tuple[str, Dict[str, Any]]], error_message: str):
        """Send failed events to dead letter queue."""
        try:
            pipeline = self.redis.pipeline()

            for event_id, event_data in events:
                dlq_data = {
                    'original_event_id': event_id,
                    'event_type': event_data.get('event_type', 'unknown'),
                    'payload': event_data.get('payload', '{}'),
                    'error': error_message,
                    'failed_at': str(time.time())
                }
                pipeline.xadd(self.dlq_stream, dlq_data)

                # Also insert to postgres DLQ table
                try:
                    async with self.pg_pool.acquire() as conn:
                        await conn.execute(
                            """
                            INSERT INTO dead_letter_queue (event_id, event_type, payload, error_message)
                            VALUES ($1, $2, $3::jsonb, $4)
                            """,
                            event_id,
                            event_data.get('event_type', 'unknown'),
                            event_data.get('payload', '{}'),
                            error_message
                        )
                except Exception as dlq_error:
                    print(f"Worker {self.worker_id}: Error inserting to DLQ table: {dlq_error}")

            await pipeline.execute()
            print(f"Worker {self.worker_id}: Sent {len(events)} events to DLQ")

        except Exception as e:
            print(f"Worker {self.worker_id}: Error sending to DLQ: {e}")

    async def should_flush_batch(self) -> bool:
        """Check if batch should be flushed based on size or timeout."""
        if len(self.batch) >= self.batch_size:
            return True

        if time.time() - self.last_batch_time >= self.batch_timeout:
            return True

        return False

    async def consume(self):
        """Main consumer loop."""
        await self.ensure_consumer_group()
        print(f"Worker {self.worker_id}: Starting consumer loop")

        while True:
            try:
                # Read events from stream
                events = await self.read_events()

                # Add to batch
                self.batch.extend(events)

                # Flush batch if needed
                if await self.should_flush_batch():
                    await self.process_batch()

            except asyncio.CancelledError:
                print(f"Worker {self.worker_id}: Shutting down...")
                # Process remaining batch
                if self.batch:
                    await self.process_batch()
                break
            except Exception as e:
                print(f"Worker {self.worker_id}: Unexpected error: {e}")
                await asyncio.sleep(1)

    async def get_stats(self) -> Dict[str, int]:
        """Get consumer statistics."""
        return {
            'worker_id': self.worker_id,
            'processed': self.processed_count,
            'errors': self.error_count,
            'current_batch_size': len(self.batch)
        }
