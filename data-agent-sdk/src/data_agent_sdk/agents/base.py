"""Base agent."""

from typing import Any, AsyncIterator, Dict, List
from ..types import AgentConfig, SessionContext, ToolUseMessage, ToolResultMessage, Artifact, PermissionMode
from ..hooks.governance import PRE_TOOL_USE_HOOKS
from ..hooks.lineage import POST_TOOL_USE_HOOKS


class DataAgent:
    """Base data agent."""

    def __init__(
        self,
        allowed_tools: List[str] | None = None,
        permission_mode: PermissionMode = PermissionMode.DEFAULT,
        session_context: SessionContext | Dict[str, Any] | None = None,
    ):
        self.config = AgentConfig(
            allowed_tools=allowed_tools or [],
            permission_mode=permission_mode,
        )

        if isinstance(session_context, dict):
            self.session_context = SessionContext(**session_context)
        else:
            self.session_context = session_context or SessionContext(
                warehouse="duckdb:///:memory:",
                user="default",
                role="analyst",
            )

        self.tools: Dict[str, Any] = {}

    def register_tool(self, tool_func: Any) -> None:
        """Register a tool."""
        self.tools[tool_func.__name__] = tool_func

    async def query(self, prompt: str) -> AsyncIterator[Dict[str, Any]]:
        """Execute query."""
        tool_use = self._parse_prompt(prompt)

        # Check permissions
        for hook in PRE_TOOL_USE_HOOKS:
            result = await hook(tool_use, self.session_context)
            if result.get("permission") == "deny":
                yield {"type": "error", "message": result.get("reason")}
                return

        # Execute tool
        try:
            tool_func = self.tools.get(tool_use.tool_name)
            if not tool_func:
                raise ValueError(f"Tool {tool_use.tool_name} not found")

            # Pass session context to tool
            tool_input = {**tool_use.tool_input, "session_context": self.session_context}
            result = await tool_func(**tool_input)

            tool_result = ToolResultMessage(
                tool_use_id=tool_use.tool_use_id,
                result=result,
                artifact=result if isinstance(result, Artifact) else None,
            )

            # Run hooks
            for hook in POST_TOOL_USE_HOOKS:
                await hook(tool_result, self.session_context)

            yield {
                "type": "result",
                "result": result if not isinstance(result, Artifact) else result.to_manifest(),
            }
        except Exception as e:
            yield {"type": "error", "error": str(e)}

    async def plan(self, prompt: str) -> Dict[str, Any]:
        """Generate execution plan."""
        tool_use = self._parse_prompt(prompt)
        return {
            "tool": tool_use.tool_name,
            "inputs": tool_use.tool_input,
        }

    def _parse_prompt(self, prompt: str) -> ToolUseMessage:
        """Parse prompt to tool use."""
        prompt_lower = prompt.lower()

        # Polars operations
        if "transform" in prompt_lower and "csv" in prompt_lower:
            return ToolUseMessage(
                tool_name="transform_csv",
                tool_input={"input_csv": "/tmp/input.csv"},
            )
        elif "join" in prompt_lower:
            return ToolUseMessage(
                tool_name="join_datasets",
                tool_input={"left_uri": "/tmp/left.parquet", "right_uri": "/tmp/right.parquet", "on": "id"},
            )
        elif "aggregate" in prompt_lower or "group by" in prompt_lower:
            return ToolUseMessage(
                tool_name="aggregate_data",
                tool_input={"input_uri": "/tmp/data.parquet", "group_by": ["region"], "aggregations": {"value": "sum"}},
            )
        elif "polars" in prompt_lower or "filter" in prompt_lower:
            return ToolUseMessage(
                tool_name="run_polars",
                tool_input={"input_uri": "/tmp/data.parquet", "operations": "head(10)"},
            )
        # SQL operations
        elif "select" in prompt_lower or "sql" in prompt_lower:
            return ToolUseMessage(
                tool_name="run_sql",
                tool_input={"sql": prompt if "select" in prompt_lower else "SELECT 1"},
            )
        elif "describe" in prompt_lower or "metadata" in prompt_lower:
            table = prompt.split()[-1]
            return ToolUseMessage(
                tool_name="read_metadata",
                tool_input={"table": table},
            )
        else:
            return ToolUseMessage(
                tool_name="run_sql",
                tool_input={"sql": "SELECT 1"},
            )
