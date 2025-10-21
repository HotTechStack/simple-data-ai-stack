"""Configuration management for the pipeline."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class PostgresConfig:
    """Postgres connection configuration."""

    host: str = os.getenv("POSTGRES_HOST", "localhost")
    port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    user: str = os.getenv("POSTGRES_USER", "dataeng")
    password: str = os.getenv("POSTGRES_PASSWORD", "dataeng_secret")
    database: str = os.getenv("POSTGRES_DB", "orders_pipeline")

    @property
    def connection_string(self) -> str:
        """Get psycopg connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class PgBouncerConfig:
    """PgBouncer connection configuration."""

    host: str = os.getenv("POSTGRES_HOST", "localhost")
    port: int = int(os.getenv("PGBOUNCER_PORT", "6432"))
    user: str = os.getenv("POSTGRES_USER", "dataeng")
    password: str = os.getenv("POSTGRES_PASSWORD", "dataeng_secret")
    database: str = os.getenv("POSTGRES_DB", "orders_pipeline")

    @property
    def connection_string(self) -> str:
        """Get psycopg connection string for PgBouncer."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class RedisConfig:
    """Redis connection configuration."""

    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = int(os.getenv("REDIS_PORT", "6379"))
    password: str = os.getenv("REDIS_PASSWORD", "")
    db: int = int(os.getenv("REDIS_DB", "0"))


@dataclass
class PipelineConfig:
    """Pipeline execution configuration."""

    worker_count: int = int(os.getenv("WORKER_COUNT", "4"))
    batch_size: int = int(os.getenv("BATCH_SIZE", "5000"))
    dedup_window_seconds: int = int(os.getenv("DEDUP_WINDOW_SECONDS", "3600"))
    max_queue_depth: int = int(os.getenv("MAX_QUEUE_DEPTH", "100000"))


# Global config instances
postgres_config = PostgresConfig()
pgbouncer_config = PgBouncerConfig()
redis_config = RedisConfig()
pipeline_config = PipelineConfig()
