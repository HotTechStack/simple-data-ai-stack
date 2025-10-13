from __future__ import annotations

import asyncio
import hashlib
import io
import json
from datetime import datetime, timezone
from typing import Any, Dict

import polars as pl
from botocore.config import Config
import boto3

from .config import Settings


class ObjectStorage:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = boto3.client(
            "s3",
            **settings.s3_config,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
        self._ensured_buckets: set[str] = set()

    async def ensure_bucket(self, bucket: str) -> None:
        if bucket in self._ensured_buckets:
            return

        async def _ensure() -> None:
            existing = await asyncio.to_thread(self._client.list_buckets)
            names = {item["Name"] for item in existing.get("Buckets", [])}
            if bucket in names:
                return
            create_kwargs: Dict[str, Any] = {"Bucket": bucket}
            if self._settings.minio_region and self._settings.minio_region != "us-east-1":
                create_kwargs["CreateBucketConfiguration"] = {
                    "LocationConstraint": self._settings.minio_region
                }
            await asyncio.to_thread(self._client.create_bucket, **create_kwargs)

        await _ensure()
        self._ensured_buckets.add(bucket)

    async def ensure_buckets(self) -> None:
        await asyncio.gather(
            self.ensure_bucket(self._settings.minio_raw_bucket),
            self.ensure_bucket(self._settings.minio_processed_bucket),
            self.ensure_bucket(self._settings.minio_dead_letter_bucket),
        )

    async def write_dataframe(self, bucket: str, key: str, frame: pl.DataFrame) -> str:
        await self.ensure_bucket(bucket)
        buffer = io.BytesIO()
        await asyncio.to_thread(frame.write_parquet, buffer)
        buffer.seek(0)
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=bucket,
            Key=key,
            Body=buffer.getvalue(),
            ContentType="application/octet-stream",
        )
        return f"s3://{bucket}/{key}"

    async def write_dead_letter(self, *, job: Dict[str, Any], error: str) -> str:
        payload = {
            "job": job,
            "error": error,
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }
        key = f"dead-letter/{job['source_name']}/{job['run_id']}.json"
        await self.ensure_bucket(self._settings.minio_dead_letter_bucket)
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._settings.minio_dead_letter_bucket,
            Key=key,
            Body=json.dumps(payload).encode("utf-8"),
            ContentType="application/json",
        )
        return f"s3://{self._settings.minio_dead_letter_bucket}/{key}"


def describe_schema(frame: pl.DataFrame) -> Dict[str, Any]:
    columns = []
    for name, dtype in zip(frame.columns, frame.dtypes):
        columns.append({"name": name, "dtype": str(dtype)})
    serialized = json.dumps(columns, sort_keys=True).encode("utf-8")
    schema_hash = hashlib.sha256(serialized).hexdigest()
    return {
        "columns": columns,
        "hash": schema_hash,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
