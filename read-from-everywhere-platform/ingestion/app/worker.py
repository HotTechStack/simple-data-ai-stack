from __future__ import annotations

import asyncio
import json
import os
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import aiohttp
import polars as pl
import redis.asyncio as redis

from .config import load_settings
from .database import MetadataStore
from .jobs import IngestionJob
from .logging_utils import get_logger, setup_logging
from .storage import ObjectStorage, describe_schema


logger = get_logger(__name__)


class IngestionWorker:
    def __init__(self) -> None:
        self.settings = load_settings()
        setup_logging(self.settings.log_level)
        self.redis = redis.from_url(self.settings.redis_url, decode_responses=True)
        self.storage = ObjectStorage(self.settings)
        self.metadata_store = MetadataStore(self.settings.postgres_dsn)
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        await self.metadata_store.connect()
        await self.storage.ensure_buckets()
        timeout = aiohttp.ClientTimeout(total=60, connect=5)
        self._http_session = aiohttp.ClientSession(timeout=timeout)
        logger.info("Worker ready: waiting for ingestion jobs")
        try:
            await self._consume_loop()
        finally:
            await self.stop()

    async def stop(self) -> None:
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()
        await self.metadata_store.close()
        await self.redis.close()
        self._shutdown_event.set()

    async def _consume_loop(self) -> None:
        queue_name = self.settings.redis_queue_name
        while not self._shutdown_event.is_set():
            try:
                item = await self.redis.blpop(queue_name, timeout=5)
                if not item:
                    continue
                _, raw_job = item
                job = IngestionJob.from_json(raw_job)
                await self._handle_job(job)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Unexpected error while consuming queue")
                await asyncio.sleep(1)

    async def _handle_job(self, job: IngestionJob) -> None:
        logger.info("Processing job %s (attempt %s)", job.run_id, job.attempt)
        assert self._http_session is not None
        try:
            frame = await self._fetch_source(job, self._http_session)
            if frame.is_empty():
                logger.warning("Job %s returned an empty frame", job.run_id)

            raw_key = self._build_object_key(job, prefix="raw")
            raw_uri = await self.storage.write_dataframe(
                self.settings.minio_raw_bucket,
                raw_key,
                frame,
            )

            processed_frame = self._transform_frame(job, frame)
            processed_key = self._build_object_key(job, prefix="processed")
            processed_uri = await self.storage.write_dataframe(
                self.settings.minio_processed_bucket,
                processed_key,
                processed_frame,
            )

            schema = describe_schema(processed_frame)
            await self.metadata_store.record_success(
                source_name=job.source_name,
                source_type=job.source_type,
                run_id=job.run_id,
                raw_object_key=raw_uri,
                processed_object_key=processed_uri,
                row_count=processed_frame.height,
                schema=schema,
            )

            logger.info(
                "Job %s succeeded (rows=%s)", job.run_id, processed_frame.height
            )
        except Exception as exc:
            await self._handle_failure(job, exc)

    async def _handle_failure(self, job: IngestionJob, exc: Exception) -> None:
        error_message = f"{type(exc).__name__}: {exc}"
        logger.error(
            "Job %s failed on attempt %s: %s", job.run_id, job.attempt, error_message
        )
        logger.debug("Stack trace:\n%s", traceback.format_exc())

        if job.attempt >= self.settings.max_job_attempts:
            payload = json.loads(job.to_json())
            payload["error"] = error_message
            await self.metadata_store.record_failure(
                source_name=job.source_name,
                source_type=job.source_type,
                run_id=job.run_id,
                attempt=job.attempt,
                error=error_message,
                payload=payload,
            )
            dead_letter_uri = await self.storage.write_dead_letter(
                job=payload,
                error=error_message,
            )
            logger.error(
                "Job %s moved to dead letter queue at %s",
                job.run_id,
                dead_letter_uri,
            )
            return

        delay = min(
            self.settings.backoff_cap_seconds,
            self.settings.backoff_base_seconds * (2 ** (job.attempt - 1)),
        )
        logger.info(
            "Re-enqueueing job %s after %.1f seconds (attempt %s)",
            job.run_id,
            delay,
            job.attempt + 1,
        )
        await self._requeue_job(job, delay)

    async def _requeue_job(self, job: IngestionJob, delay: float) -> None:
        async def _enqueue_later() -> None:
            await asyncio.sleep(delay)
            await self.redis.rpush(
                self.settings.redis_queue_name, job.next_attempt().to_json()
            )

        asyncio.create_task(_enqueue_later())

    async def _fetch_source(
        self, job: IngestionJob, session: aiohttp.ClientSession
    ) -> pl.DataFrame:
        source_type = job.source_type
        if source_type == "rest_api":
            return await self._fetch_rest_api(job, session)
        if source_type == "csv_file":
            return await asyncio.to_thread(
                pl.read_csv, job.options["path"], try_parse_dates=True
            )
        if source_type == "parquet_file":
            path = job.options["path"]
            if not os.path.exists(path):
                await asyncio.to_thread(self._create_sample_parquet, path)
            return await asyncio.to_thread(pl.read_parquet, path)
        if source_type == "synthetic_stream":
            return self._generate_synthetic_events(job.options)
        if source_type == "minio_blob":
            return await self._load_from_minio(job.options)
        if source_type == "webhook_event":
            payload = job.options.get("payload")
            if not isinstance(payload, dict):
                raise ValueError("Webhook payload must be a dict")
            record = payload | {"received_at": job.options.get("received_at")}
            return pl.DataFrame([record])
        raise ValueError(f"Unsupported source type: {source_type}")

    async def _fetch_rest_api(
        self, job: IngestionJob, session: aiohttp.ClientSession
    ) -> pl.DataFrame:
        options = job.options
        url = options["url"]
        params = options.get("params", {})
        batch_param = options.get("batch_param", "limit")
        batch_size = options.get("batch_size", 1000)
        params[batch_param] = batch_size
        all_rows: list[Dict[str, Any]] = []
        next_url: Optional[str] = url
        while next_url:
            async with session.get(next_url, params=params) as response:
                response.raise_for_status()
                payload = await response.json()
            data = payload.get("data", payload)
            if isinstance(data, dict):
                data = [data]
            if not isinstance(data, list):
                raise ValueError("REST API payload must be a list or dict")
            all_rows.extend(data)
            next_url = payload.get("next") if options.get("paginate", False) else None
        return pl.DataFrame(all_rows, infer_schema_length=1000)

    def _generate_synthetic_events(self, options: Dict[str, Any]) -> pl.DataFrame:
        import random

        rows = options.get("rows", 500)
        event_type = options.get("event_type", "page_view")
        tenant = options.get("tenant", "demo")
        now = datetime.now(timezone.utc)
        data = []
        for i in range(rows):
            data.append(
                {
                    "event_id": f"{event_type}-{tenant}-{i}",
                    "event_type": event_type,
                    "customer_id": random.randint(1000, 9999),
                    "value": round(random.random() * 100, 2),
                    "emitted_at": (now).isoformat(),
                }
            )
        return pl.DataFrame(data)

    async def _load_from_minio(self, options: Dict[str, Any]) -> pl.DataFrame:
        # Placeholder to show MinIO to MinIO processing; not used by default schedule.
        raise NotImplementedError("MinIO source ingestion not yet implemented")

    def _transform_frame(self, job: IngestionJob, frame: pl.DataFrame) -> pl.DataFrame:
        lazy_frame = frame.lazy().with_columns(
            pl.lit(datetime.now(timezone.utc).isoformat()).alias("processed_at"),
            pl.lit(job.source_name).alias("source_name"),
        )
        if job.source_type == "rest_api" and "created_at" in frame.columns:
            lazy_frame = lazy_frame.with_columns(
                pl.col("created_at").str.strptime(pl.Datetime, strict=False)
            )
        if "emitted_at" in frame.columns:
            lazy_frame = lazy_frame.with_columns(
                pl.col("emitted_at").str.strptime(pl.Datetime, strict=False)
            )
        processed = lazy_frame.collect()
        return processed

    def _build_object_key(self, job: IngestionJob, prefix: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        return f"{prefix}/{job.source_name}/{timestamp}/{job.run_id}.parquet"

    def _create_sample_parquet(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        frame = pl.DataFrame(
            {
                "order_id": [101, 102, 103, 104],
                "customer_id": [1, 2, 3, 4],
                "status": ["paid", "pending", "refunded", "paid"],
                "total": [199.0, 49.0, 25.0, 310.0],
                "order_ts": [
                    datetime(2024, 5, 1, 9, 0, 0, tzinfo=timezone.utc),
                    datetime(2024, 5, 1, 10, 30, 0, tzinfo=timezone.utc),
                    datetime(2024, 5, 2, 14, 45, 0, tzinfo=timezone.utc),
                    datetime(2024, 5, 3, 16, 0, 0, tzinfo=timezone.utc),
                ],
            }
        )
        frame.write_parquet(path)
        logger.info("Created sample parquet seed at %s", path)


async def main() -> None:
    worker = IngestionWorker()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
