from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass
class IngestionJob:
    source_name: str
    source_type: str
    options: Dict[str, Any]
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    attempt: int = 1
    enqueued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_json(self) -> str:
        data = {
            "source_name": self.source_name,
            "source_type": self.source_type,
            "options": self.options,
            "run_id": self.run_id,
            "attempt": self.attempt,
            "enqueued_at": self.enqueued_at.isoformat(),
        }
        return json.dumps(data)

    @classmethod
    def from_json(cls, data: str) -> "IngestionJob":
        payload = json.loads(data)
        payload["enqueued_at"] = datetime.fromisoformat(payload["enqueued_at"])
        return cls(**payload)

    def next_attempt(self) -> "IngestionJob":
        return IngestionJob(
            source_name=self.source_name,
            source_type=self.source_type,
            options=self.options,
            run_id=self.run_id,
            attempt=self.attempt + 1,
            enqueued_at=datetime.now(timezone.utc),
        )
