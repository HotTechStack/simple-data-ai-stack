"""Lineage hooks."""

import json
from pathlib import Path
from datetime import datetime
from ..types import SessionContext, ToolResultMessage


async def log_lineage(tool_result: ToolResultMessage, context: SessionContext) -> None:
    """Log lineage."""
    if not tool_result.artifact:
        return

    entry = {
        "timestamp": datetime.now().isoformat(),
        "user": context.user,
        "output": tool_result.artifact.uri,
        "rows": tool_result.artifact.row_count,
    }

    with open("/tmp/lineage.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


POST_TOOL_USE_HOOKS = [log_lineage]
