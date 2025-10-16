"""Observability and monitoring utilities."""
import asyncio
from typing import Dict, Any
from redis.asyncio import Redis
from asyncpg import Pool
from src.config import Config


class StreamMonitor:
    """Monitor streaming pipeline health and performance."""

    def __init__(self, redis_client: Redis, pg_pool: Pool, config: Config):
        self.redis = redis_client
        self.pg_pool = pg_pool
        self.config = config
        self.stream_name = config.stream.stream_name
        self.dlq_stream = config.stream.dlq_stream_name

    async def get_stream_length(self, stream_name: str = None) -> int:
        """Get current stream length (XLEN)."""
        if stream_name is None:
            stream_name = self.stream_name

        try:
            length = await self.redis.xlen(stream_name)
            return length
        except Exception as e:
            print(f"Error getting stream length: {e}")
            return -1

    async def get_dlq_length(self) -> int:
        """Get dead letter queue length."""
        return await self.get_stream_length(self.dlq_stream)

    async def get_consumer_group_info(self) -> Dict[str, Any]:
        """Get consumer group information."""
        try:
            groups = await self.redis.xinfo_groups(self.stream_name)

            group_info = []
            for group in groups:
                decoded_group = {}
                for key, value in group.items():
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    value_str = value.decode('utf-8') if isinstance(value, bytes) else value
                    decoded_group[key_str] = value_str

                group_info.append(decoded_group)

            return {
                'groups': group_info,
                'count': len(group_info)
            }
        except Exception as e:
            print(f"Error getting consumer group info: {e}")
            return {'groups': [], 'count': 0}

    async def get_pending_messages(self) -> int:
        """Get count of pending (unacknowledged) messages."""
        try:
            pending = await self.redis.xpending(
                self.stream_name,
                self.config.stream.consumer_group
            )

            if pending:
                # pending returns [count, min_id, max_id, consumers]
                return pending[0] if isinstance(pending, list) else 0

            return 0
        except Exception as e:
            print(f"Error getting pending messages: {e}")
            return -1

    async def get_postgres_stats(self) -> Dict[str, Any]:
        """Get Postgres statistics."""
        try:
            async with self.pg_pool.acquire() as conn:
                # Get total event count
                total_events = await conn.fetchval(
                    "SELECT COUNT(*) FROM events"
                )

                # Get events by type
                events_by_type = await conn.fetch(
                    """
                    SELECT event_type, COUNT(*) as count
                    FROM events
                    GROUP BY event_type
                    ORDER BY count DESC
                    """
                )

                # Get recent events rate
                recent_events = await conn.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM events
                    WHERE created_at > NOW() - INTERVAL '1 minute'
                    """
                )

                # Get DLQ count
                dlq_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM dead_letter_queue"
                )

                # Get table size
                table_size = await conn.fetchval(
                    """
                    SELECT pg_size_pretty(pg_total_relation_size('events'))
                    """
                )

                return {
                    'total_events': total_events,
                    'events_by_type': [
                        {'type': row['event_type'], 'count': row['count']}
                        for row in events_by_type
                    ],
                    'events_last_minute': recent_events,
                    'dlq_count': dlq_count,
                    'table_size': table_size
                }

        except Exception as e:
            print(f"Error getting Postgres stats: {e}")
            return {}

    async def get_insert_latency(self) -> Dict[str, Any]:
        """Get insert query performance stats using pg_stat_statements."""
        try:
            async with self.pg_pool.acquire() as conn:
                # Check if pg_stat_statements is available
                has_pg_stat = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                    )
                    """
                )

                if not has_pg_stat:
                    return {'available': False, 'message': 'pg_stat_statements not installed'}

                # Get stats for INSERT queries on events table
                stats = await conn.fetch(
                    """
                    SELECT
                        calls,
                        mean_exec_time,
                        max_exec_time,
                        total_exec_time
                    FROM pg_stat_statements
                    WHERE query LIKE '%INSERT INTO events%'
                    ORDER BY calls DESC
                    LIMIT 1
                    """
                )

                if not stats:
                    return {'available': True, 'stats': None}

                stat = stats[0]
                return {
                    'available': True,
                    'calls': stat['calls'],
                    'mean_ms': round(stat['mean_exec_time'], 2),
                    'max_ms': round(stat['max_exec_time'], 2),
                    'total_ms': round(stat['total_exec_time'], 2)
                }

        except Exception as e:
            print(f"Error getting insert latency: {e}")
            return {'available': False, 'error': str(e)}

    async def print_dashboard(self):
        """Print monitoring dashboard."""
        stream_len = await self.get_stream_length()
        dlq_len = await self.get_dlq_length()
        pending = await self.get_pending_messages()
        pg_stats = await self.get_postgres_stats()
        insert_latency = await self.get_insert_latency()

        print("\n" + "="*60)
        print("STREAMING PIPELINE DASHBOARD")
        print("="*60)

        print("\nRedis Streams:")
        print(f"  Stream Length: {stream_len}")
        print(f"  Pending Messages: {pending}")
        print(f"  DLQ Length: {dlq_len}")

        if pg_stats:
            print("\nPostgres:")
            print(f"  Total Events: {pg_stats.get('total_events', 'N/A')}")
            print(f"  Events (last minute): {pg_stats.get('events_last_minute', 'N/A')}")
            print(f"  DLQ Count: {pg_stats.get('dlq_count', 'N/A')}")
            print(f"  Table Size: {pg_stats.get('table_size', 'N/A')}")

            if pg_stats.get('events_by_type'):
                print("\n  Events by Type:")
                for event_type in pg_stats['events_by_type'][:5]:
                    print(f"    {event_type['type']}: {event_type['count']}")

        if insert_latency.get('available') and insert_latency.get('stats') is not None:
            print("\nInsert Performance:")
            print(f"  Calls: {insert_latency.get('calls', 'N/A')}")
            print(f"  Mean Latency: {insert_latency.get('mean_ms', 'N/A')} ms")
            print(f"  Max Latency: {insert_latency.get('max_ms', 'N/A')} ms")

        print("\n" + "="*60 + "\n")

    async def monitor_loop(self, interval_seconds: int = 10):
        """Continuously monitor and print dashboard."""
        print(f"Starting monitor loop (interval: {interval_seconds}s)")

        while True:
            try:
                await self.print_dashboard()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                print("Monitor loop shutting down...")
                break
            except Exception as e:
                print(f"Error in monitor loop: {e}")
                await asyncio.sleep(interval_seconds)
