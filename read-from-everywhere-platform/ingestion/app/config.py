from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    redis_url: str
    redis_queue_name: str
    max_job_attempts: int
    backoff_base_seconds: float
    backoff_cap_seconds: float
    schedule_interval_seconds: int

    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    postgres_db: str

    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_region: str
    minio_secure: bool
    minio_raw_bucket: str
    minio_processed_bucket: str
    minio_dead_letter_bucket: str

    log_level: str

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def s3_config(self) -> dict[str, Optional[str]]:
        return {
            "endpoint_url": self.minio_endpoint,
            "aws_access_key_id": self.minio_access_key,
            "aws_secret_access_key": self.minio_secret_key,
            "region_name": self.minio_region or None,
        }


def getenv(key: str, default: Optional[str] = None) -> str:
    value = os.getenv(key, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


def load_settings() -> Settings:
    return Settings(
        redis_url=getenv("REDIS_URL", "redis://redis:6379/0"),
        redis_queue_name=getenv("REDIS_QUEUE_NAME", "ingestion-jobs"),
        max_job_attempts=int(getenv("MAX_JOB_ATTEMPTS", "4")),
        backoff_base_seconds=float(getenv("BACKOFF_BASE_SECONDS", "2")),
        backoff_cap_seconds=float(getenv("BACKOFF_CAP_SECONDS", "60")),
        schedule_interval_seconds=int(getenv("SCHEDULE_INTERVAL_SECONDS", "300")),
        postgres_host=getenv("POSTGRES_HOST", "postgres"),
        postgres_port=int(getenv("POSTGRES_PORT", "5433")),
        postgres_user=getenv("POSTGRES_USER", "metadata"),
        postgres_password=getenv("POSTGRES_PASSWORD", "metadata"),
        postgres_db=getenv("POSTGRES_DB", "metadata"),
        minio_endpoint=getenv("MINIO_ENDPOINT", "http://minio:9000"),
        minio_access_key=getenv("MINIO_ACCESS_KEY", "minioadmin"),
        minio_secret_key=getenv("MINIO_SECRET_KEY", "minioadmin"),
        minio_region=getenv("MINIO_REGION", "us-east-1"),
        minio_secure=getenv("MINIO_SECURE", "false").lower() == "true",
        minio_raw_bucket=getenv("MINIO_RAW_BUCKET", "raw"),
        minio_processed_bucket=getenv("MINIO_PROCESSED_BUCKET", "processed"),
        minio_dead_letter_bucket=getenv("MINIO_DEAD_LETTER_BUCKET", "dead-letter"),
        log_level=getenv("LOG_LEVEL", "INFO"),
    )


__all__ = ["Settings", "load_settings"]
