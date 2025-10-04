"""Governance hooks."""

from typing import Any, Dict
from ..types import SessionContext, ToolUseMessage


async def check_access(tool_use: ToolUseMessage, context: SessionContext) -> Dict[str, Any]:
    """Check dataset access."""
    dataset = tool_use.tool_input.get("table")
    if dataset and dataset.startswith("finance.") and context.role != "finance":
        return {"permission": "deny", "reason": "Unauthorized"}
    return {"permission": "allow"}


PRE_TOOL_USE_HOOKS = [check_access]
