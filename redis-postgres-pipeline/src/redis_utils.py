"""Redis utilities for pipeline operations.

This module demonstrates all the Redis patterns mentioned in the blog:
- Lists as job queues (LPUSH/BRPOP replacing Kafka)
- Hashes for deduplication windows
- Snapshots of lookup tables
- Pub/sub for event notification
- Sorted sets for time-windowed processing
- Counters for backpressure
- Automatic TTL-based cleanup
"""

import json
import time
from typing import Any, Dict, List, Optional, Set
from redis import Redis
from .config import redis_config


class RedisQueue:
    """Redis list-based job queue.

    Replaces Kafka for simple job queuing:
    - LPUSH for adding jobs (producer side)
    - BRPOP for consuming jobs (worker side)
    - Handles 100k+ jobs/day without configuration
    """

    def __init__(self, redis_client: Redis, queue_name: str):
        self.redis = redis_client
        self.queue_name = queue_name
        self.counter_key = f"{queue_name}:counter"

    def push(self, job_data: Dict[str, Any]) -> None:
        """Add job to queue (producer)."""
        self.redis.lpush(self.queue_name, json.dumps(job_data))
        self.redis.incr(self.counter_key)

    def push_batch(self, jobs: List[Dict[str, Any]]) -> None:
        """Add multiple jobs atomically."""
        if not jobs:
            return
        serialized = [json.dumps(job) for job in jobs]
        pipe = self.redis.pipeline()
        pipe.lpush(self.queue_name, *serialized)
        pipe.incrby(self.counter_key, len(jobs))
        pipe.execute()

    def pop(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """Block until job available (worker)."""
        result = self.redis.brpop(self.queue_name, timeout=timeout)
        if result:
            _, job_data = result
            self.redis.decr(self.counter_key)
            return json.loads(job_data)
        return None

    def size(self) -> int:
        """Get current queue depth (for backpressure monitoring)."""
        return self.redis.llen(self.queue_name)

    def counter(self) -> int:
        """Get total jobs processed counter."""
        value = self.redis.get(self.counter_key)
        return int(value) if value else 0

    def clear(self) -> None:
        """Clear the queue."""
        self.redis.delete(self.queue_name, self.counter_key)


class RedisDeduplicator:
    """Redis hash-based deduplication window.

    Tracks record IDs in a time window to catch duplicates:
    - Stores millions of record IDs efficiently
    - Automatic TTL cleanup
    - Prevents duplicate data poisoning Postgres
    """

    def __init__(self, redis_client: Redis, window_name: str, ttl_seconds: int = 3600):
        self.redis = redis_client
        self.window_name = window_name
        self.ttl_seconds = ttl_seconds

    def is_duplicate(self, record_id: str) -> bool:
        """Check if record_id seen in current window."""
        return self.redis.hexists(self.window_name, record_id)

    def mark_seen(self, record_id: str) -> bool:
        """Mark record as seen. Returns True if new, False if duplicate."""
        timestamp = int(time.time())
        # HSETNX returns 1 if new, 0 if exists
        is_new = self.redis.hsetnx(self.window_name, record_id, timestamp)

        # Set TTL on first insert
        if self.redis.hlen(self.window_name) == 1:
            self.redis.expire(self.window_name, self.ttl_seconds)

        return bool(is_new)

    def mark_batch(self, record_ids: List[str]) -> int:
        """Mark multiple records. Returns count of new records."""
        if not record_ids:
            return 0

        timestamp = int(time.time())
        pipe = self.redis.pipeline()

        for record_id in record_ids:
            pipe.hsetnx(self.window_name, record_id, timestamp)

        # Set TTL on the hash
        pipe.expire(self.window_name, self.ttl_seconds)

        results = pipe.execute()
        # Count how many were new (HSETNX returns 1 for new)
        return sum(results[:-1])  # Exclude the EXPIRE result

    def count_seen(self) -> int:
        """Get count of records in current window."""
        return self.redis.hlen(self.window_name)

    def clear(self) -> None:
        """Clear deduplication window."""
        self.redis.delete(self.window_name)


class RedisCache:
    """Redis cache for lookup tables.

    Snapshots small reference data (zip codes, currency rates, SKUs):
    - Stops joining Postgres 10k times per run
    - Hash structure for efficient key-value lookups
    - Optional TTL for automatic refresh
    """

    def __init__(self, redis_client: Redis, cache_name: str):
        self.redis = redis_client
        self.cache_name = cache_name

    def get(self, key: str) -> Optional[str]:
        """Get single value from cache."""
        value = self.redis.hget(self.cache_name, key)
        return value.decode('utf-8') if value else None

    def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON value from cache."""
        value = self.get(key)
        return json.loads(value) if value else None

    def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> None:
        """Set single value in cache."""
        self.redis.hset(self.cache_name, key, value)
        if ttl_seconds:
            self.redis.expire(self.cache_name, ttl_seconds)

    def set_json(self, key: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
        """Set JSON value in cache."""
        self.set(key, json.dumps(value), ttl_seconds)

    def set_batch(self, mapping: Dict[str, str], ttl_seconds: Optional[int] = None) -> None:
        """Set multiple key-value pairs."""
        if not mapping:
            return

        pipe = self.redis.pipeline()
        pipe.hset(self.cache_name, mapping=mapping)
        if ttl_seconds:
            pipe.expire(self.cache_name, ttl_seconds)
        pipe.execute()

    def get_all(self) -> Dict[str, str]:
        """Get all cached values."""
        result = self.redis.hgetall(self.cache_name)
        return {k.decode('utf-8'): v.decode('utf-8') for k, v in result.items()}

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return self.redis.hexists(self.cache_name, key)

    def delete(self, key: str) -> None:
        """Delete key from cache."""
        self.redis.hdel(self.cache_name, key)

    def clear(self) -> None:
        """Clear entire cache."""
        self.redis.delete(self.cache_name)

    def size(self) -> int:
        """Get number of items in cache."""
        return self.redis.hlen(self.cache_name)


class RedisPubSub:
    """Redis pub/sub for pipeline coordination.

    Replaces polling logic:
    - Upstream signals completion
    - Downstream picks up instantly
    - Deletes 'check every 30 seconds' cron jobs
    """

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.pubsub = redis_client.pubsub()

    def publish(self, channel: str, message: Dict[str, Any]) -> None:
        """Publish message to channel."""
        self.redis.publish(channel, json.dumps(message))

    def subscribe(self, channels: List[str]) -> None:
        """Subscribe to channels."""
        self.pubsub.subscribe(*channels)

    def listen(self, timeout: Optional[float] = None):
        """Listen for messages."""
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                yield message['channel'].decode('utf-8'), data

    def get_message(self, timeout: float = 1.0) -> Optional[tuple]:
        """Get single message with timeout."""
        message = self.pubsub.get_message(timeout=timeout)
        if message and message['type'] == 'message':
            channel = message['channel'].decode('utf-8')
            data = json.loads(message['data'])
            return channel, data
        return None

    def unsubscribe(self) -> None:
        """Unsubscribe from all channels."""
        self.pubsub.unsubscribe()

    def close(self) -> None:
        """Close pub/sub connection."""
        self.pubsub.close()


class RedisSortedSet:
    """Redis sorted set for time-windowed processing.

    Makes sliding windows trivial:
    - Score by timestamp
    - Process chunks by range
    - No custom windowing code needed
    """

    def __init__(self, redis_client: Redis, set_name: str):
        self.redis = redis_client
        self.set_name = set_name

    def add(self, member: str, score: float) -> None:
        """Add member with score (typically timestamp)."""
        self.redis.zadd(self.set_name, {member: score})

    def add_batch(self, members: Dict[str, float]) -> None:
        """Add multiple members with scores."""
        if members:
            self.redis.zadd(self.set_name, members)

    def get_range_by_score(self, min_score: float, max_score: float) -> List[str]:
        """Get members in score range."""
        result = self.redis.zrangebyscore(self.set_name, min_score, max_score)
        return [m.decode('utf-8') for m in result]

    def remove_range_by_score(self, min_score: float, max_score: float) -> int:
        """Remove members in score range. Returns count removed."""
        return self.redis.zremrangebyscore(self.set_name, min_score, max_score)

    def count_range(self, min_score: float, max_score: float) -> int:
        """Count members in score range."""
        return self.redis.zcount(self.set_name, min_score, max_score)

    def size(self) -> int:
        """Get total members in set."""
        return self.redis.zcard(self.set_name)

    def clear(self) -> None:
        """Clear entire sorted set."""
        self.redis.delete(self.set_name)


class RedisBackpressure:
    """Redis counters for backpressure monitoring.

    Track queue depth in real-time:
    - Throttle upstream when downstream lags
    - Prevents memory explosions
    - Simple counter-based logic
    """

    def __init__(self, redis_client: Redis, namespace: str = "backpressure"):
        self.redis = redis_client
        self.namespace = namespace

    def increment(self, queue_name: str, amount: int = 1) -> int:
        """Increment queue counter. Returns new value."""
        key = f"{self.namespace}:{queue_name}"
        return self.redis.incrby(key, amount)

    def decrement(self, queue_name: str, amount: int = 1) -> int:
        """Decrement queue counter. Returns new value."""
        key = f"{self.namespace}:{queue_name}"
        return self.redis.decrby(key, amount)

    def get_depth(self, queue_name: str) -> int:
        """Get current queue depth."""
        key = f"{self.namespace}:{queue_name}"
        value = self.redis.get(key)
        return int(value) if value else 0

    def should_throttle(self, queue_name: str, max_depth: int) -> bool:
        """Check if upstream should throttle."""
        return self.get_depth(queue_name) >= max_depth

    def reset(self, queue_name: str) -> None:
        """Reset queue counter."""
        key = f"{self.namespace}:{queue_name}"
        self.redis.delete(key)


def get_redis_client() -> Redis:
    """Get configured Redis client."""
    return Redis(
        host=redis_config.host,
        port=redis_config.port,
        password=redis_config.password if redis_config.password else None,
        db=redis_config.db,
        decode_responses=False,
    )
