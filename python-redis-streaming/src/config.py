"""Configuration management for streaming engine."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class RedisConfig:
    """Redis connection configuration."""
    host: str
    port: int
    db: int

    @classmethod
    def from_env(cls) -> 'RedisConfig':
        return cls(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0'))
        )


@dataclass
class PostgresConfig:
    """Postgres connection configuration."""
    host: str
    port: int
    database: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> 'PostgresConfig':
        return cls(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', '5432')),
            database=os.getenv('POSTGRES_DB', 'streaming'),
            user=os.getenv('POSTGRES_USER', 'streaming_user'),
            password=os.getenv('POSTGRES_PASSWORD', 'streaming_pass')
        )

    @property
    def dsn(self) -> str:
        """Generate PostgreSQL DSN."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class StreamConfig:
    """Streaming configuration."""
    stream_name: str
    consumer_group: str
    consumer_name: str
    dlq_stream_name: str
    num_workers: int
    batch_size: int
    batch_timeout_seconds: float
    xread_count: int
    xread_block_ms: int

    @classmethod
    def from_env(cls) -> 'StreamConfig':
        return cls(
            stream_name=os.getenv('STREAM_NAME', 'events'),
            consumer_group=os.getenv('CONSUMER_GROUP', 'processors'),
            consumer_name=os.getenv('CONSUMER_NAME', 'consumer-1'),
            dlq_stream_name=os.getenv('DLQ_STREAM_NAME', 'events:dead'),
            num_workers=int(os.getenv('NUM_WORKERS', '5')),
            batch_size=int(os.getenv('BATCH_SIZE', '500')),
            batch_timeout_seconds=float(os.getenv('BATCH_TIMEOUT_SECONDS', '2')),
            xread_count=int(os.getenv('XREAD_COUNT', '100')),
            xread_block_ms=int(os.getenv('XREAD_BLOCK_MS', '5000'))
        )


@dataclass
class Config:
    """Main configuration container."""
    redis: RedisConfig
    postgres: PostgresConfig
    stream: StreamConfig

    @classmethod
    def from_env(cls) -> 'Config':
        return cls(
            redis=RedisConfig.from_env(),
            postgres=PostgresConfig.from_env(),
            stream=StreamConfig.from_env()
        )
