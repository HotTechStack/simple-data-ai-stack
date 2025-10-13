from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, Query

app = FastAPI(title="Mock Data API")


CUSTOMERS = [
    {
        "id": 1,
        "email": "alice@example.com",
        "segment": "enterprise",
        "created_at": datetime(2023, 11, 1, tzinfo=timezone.utc).isoformat(),
    },
    {
        "id": 2,
        "email": "bob@example.com",
        "segment": "starter",
        "created_at": datetime(2023, 12, 18, tzinfo=timezone.utc).isoformat(),
    },
    {
        "id": 3,
        "email": "charlie@example.com",
        "segment": "growth",
        "created_at": datetime(2024, 1, 3, tzinfo=timezone.utc).isoformat(),
    },
    {
        "id": 4,
        "email": "danielle@example.com",
        "segment": "enterprise",
        "created_at": datetime(2024, 2, 7, tzinfo=timezone.utc).isoformat(),
    },
    {
        "id": 5,
        "email": "eve@example.com",
        "segment": "growth",
        "created_at": datetime(2024, 3, 1, tzinfo=timezone.utc).isoformat(),
    },
]


EVENTS = [
    {
        "event_id": f"evt-{i}",
        "event_type": "page_view",
        "customer_id": (i % 5) + 1,
        "value": i * 0.1,
        "emitted_at": datetime(2024, 4, 1, tzinfo=timezone.utc).isoformat(),
    }
    for i in range(50)
]


@app.get("/customers")
def get_customers(limit: int = Query(1000, ge=1, le=1000)) -> dict[str, List[dict]]:
    records = CUSTOMERS[:limit]
    return {"data": records, "next": None}


@app.get("/events")
def get_events(limit: int = Query(1000, ge=1, le=1000)) -> dict[str, List[dict]]:
    return {"data": EVENTS[:limit], "next": None}


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
