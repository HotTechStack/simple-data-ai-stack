from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict

import redis.asyncio as redis
from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel

from .config import load_settings
from .jobs import IngestionJob
from .logging_utils import get_logger, setup_logging


logger = get_logger(__name__)
app = FastAPI(title="Webhook Ingestion Gateway")
settings = load_settings()
setup_logging(settings.log_level)
redis_client = redis.from_url(settings.redis_url, decode_responses=True)


class WebhookPayload(BaseModel):
    event_type: str
    data: Dict[str, Any]


async def enqueue_job(job: IngestionJob) -> None:
    await redis_client.rpush(settings.redis_queue_name, job.to_json())


@app.post("/webhooks/{source}")
async def receive_webhook(source: str, payload: WebhookPayload, tasks: BackgroundTasks):
    job = IngestionJob(
        source_name=f"webhook_{source}",
        source_type="webhook_event",
        options={
            "payload": payload.model_dump(),
            "received_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    tasks.add_task(enqueue_job, job)
    logger.info("Accepted webhook for source %s", source)
    return {"status": "queued", "run_id": job.run_id}


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await redis_client.close()
