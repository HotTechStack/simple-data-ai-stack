from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import redis.asyncio as redis

from .config import load_settings
from .jobs import IngestionJob
from .logging_utils import get_logger, setup_logging


logger = get_logger(__name__)

SCHEDULED_SOURCES = [
    IngestionJob(
        source_name="customers_api",
        source_type="rest_api",
        options={
            "url": "http://mock-api:8000/customers",
            "batch_size": 1000,
            "batch_param": "limit",
            "paginate": False,
        },
    ),
    IngestionJob(
        source_name="finance_csv",
        source_type="csv_file",
        options={
            "path": "/app/data/seeds/finance_transactions.csv",
        },
    ),
    IngestionJob(
        source_name="orders_parquet",
        source_type="parquet_file",
        options={
            "path": "/app/data/seeds/orders.parquet",
        },
    ),
    IngestionJob(
        source_name="synthetic_stream",
        source_type="synthetic_stream",
        options={
            "rows": 250,
            "event_type": "webhook_event",
            "tenant": "demo",
        },
    ),
]


class Scheduler:
    def __init__(self) -> None:
        self.settings = load_settings()
        setup_logging(self.settings.log_level)
        self.redis = redis.from_url(self.settings.redis_url, decode_responses=True)

    async def start(self) -> None:
        logger.info(
            "Scheduler active — pushing jobs every %s seconds",
            self.settings.schedule_interval_seconds,
        )
        try:
            while True:
                await self._emit_cycle()
                await asyncio.sleep(self.settings.schedule_interval_seconds)
        finally:
            await self.redis.close()

    async def _emit_cycle(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        for job in SCHEDULED_SOURCES:
            enriched = IngestionJob(
                source_name=job.source_name,
                source_type=job.source_type,
                options=job.options | {"scheduled_at": now},
            )
            await self.redis.rpush(
                self.settings.redis_queue_name,
                enriched.to_json(),
            )
            logger.info("Enqueued %s", job.source_name)


async def main() -> None:
    scheduler = Scheduler()
    await scheduler.start()


if __name__ == "__main__":
    asyncio.run(main())
