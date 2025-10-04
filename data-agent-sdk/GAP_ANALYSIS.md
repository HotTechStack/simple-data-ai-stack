# Gap Analysis: Pitch vs Implementation

## Summary

| Gap | Effort | Lines | Priority | Status |
|-----|--------|-------|----------|--------|
| 1. Missing types (Dataset, QueryPlan, JobRun) | **2 hours** | ~150 | Medium | Not implemented |
| 2. Missing tools (polars, dbt, write_table) | **4 hours** | ~300 | High | Not implemented |
| 3. Permission enforcement (allowed_tools check) | **30 min** | ~20 | High | Partially done |
| 4. Tool tagging & richer governance | **2 hours** | ~100 | Medium | Not implemented |
| 5. Plan mode, streaming, retries, observability | **6 hours** | ~250 | Low | Skeleton only |
| 6. Test coverage (hooks, transport, MCP) | **3 hours** | ~200 | High | Minimal |
| **TOTAL** | **~18 hours** | **~1,020 lines** | | |

**Verdict:** Can be completed in **2-3 days** of focused work.

---

## Gap 1: Missing Core Types
**Status:** ❌ Not implemented
**Effort:** 2 hours
**Lines:** ~150
**Priority:** Medium

### What's Missing
- `Dataset` - Represents a logical dataset (table, view, file)
- `QueryPlan` - Execution plan before running
- `JobRun` - Runtime metadata (start time, duration, cost)

### Current State
```python
# types.py has:
Artifact        ✅
SessionContext  ✅
ToolUseMessage  ✅
AgentConfig     ✅

# Missing:
Dataset         ❌
QueryPlan       ❌
JobRun          ❌
```

### What to Add

```python
@dataclass
class Dataset:
    """Logical dataset reference."""
    uri: str                    # "duckdb://db/table" or "s3://bucket/file.parquet"
    format: str                 # "table", "parquet", "csv"
    schema: Dict[str, str]      # Column name → type
    catalog_ref: Optional[str]  # External catalog ID
    tags: List[str] = field(default_factory=list)  # ["pii", "finance"]

@dataclass
class QueryPlan:
    """Execution plan (dry-run)."""
    tool_name: str
    tool_input: Dict[str, Any]
    estimated_cost: Optional[float] = None  # $0.05
    estimated_rows: Optional[int] = None
    datasets_read: List[Dataset] = field(default_factory=list)
    datasets_written: List[Dataset] = field(default_factory=list)

@dataclass
class JobRun:
    """Runtime execution metadata."""
    job_id: str = field(default_factory=lambda: str(uuid4()))
    tool_name: str
    status: Literal["pending", "running", "success", "failed"]
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    error: Optional[str] = None

    def duration_ms(self) -> Optional[int]:
        if self.end_time:
            return int((self.end_time - self.start_time).total_seconds() * 1000)
        return None
```

### Effort Breakdown
- Define types: **30 min**
- Update tools to return JobRun: **1 hour**
- Update agent to track JobRun: **30 min**

---

## Gap 2: Missing Tools
**Status:** ❌ Not implemented
**Effort:** 4 hours
**Lines:** ~300
**Priority:** High

### What's Missing
Currently have: `run_sql`, `read_metadata` (2 tools)
Promised: "five core tools"

### Tools to Add

#### 1. `run_polars` (1.5 hours, ~100 lines)
```python
async def run_polars(
    input_uri: str,
    transform_expr: str,
    output_uri: str,
    session_context: SessionContext
) -> Artifact:
    """
    Run Polars transformation.

    Example:
        run_polars(
            input_uri="s3://bucket/data.parquet",
            transform_expr="filter(pl.col('revenue') > 100)",
            output_uri="/tmp/filtered.parquet"
        )
    """
    import polars as pl

    # Read input
    df = pl.read_parquet(input_uri)

    # Apply transform (eval transform_expr in context with pl and df)
    # WARNING: eval is dangerous, use AST or predefined transforms in prod
    result = eval(f"df.{transform_expr}")

    # Write output
    result.write_parquet(output_uri)

    return Artifact(
        uri=output_uri,
        format="parquet",
        schema={col: str(dtype) for col, dtype in result.schema.items()},
        row_count=len(result),
        lineage={
            "tool": "run_polars",
            "input": input_uri,
            "transform": transform_expr
        }
    )
```

#### 2. `trigger_dbt` (1.5 hours, ~100 lines)
```python
async def trigger_dbt(
    model_name: str,
    project_dir: str = ".",
    session_context: SessionContext = None
) -> Dict[str, Any]:
    """
    Trigger dbt run via subprocess.

    Example:
        trigger_dbt(model_name="stg_orders", project_dir="/dbt/myproject")
    """
    import subprocess
    import json

    # Run dbt command
    cmd = ["dbt", "run", "--select", model_name, "--project-dir", project_dir]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"dbt failed: {result.stderr}")

    # Parse dbt output for metadata
    # (simplified - real dbt outputs JSON with run_results.json)
    return {
        "model": model_name,
        "status": "success",
        "command": " ".join(cmd),
        "output": result.stdout
    }
```

#### 3. `write_table` (1 hour, ~100 lines)
```python
async def write_table(
    input_uri: str,
    table_name: str,
    mode: Literal["create", "append", "replace"] = "create",
    session_context: SessionContext = None
) -> Artifact:
    """
    Write Parquet file to database table.

    Example:
        write_table(
            input_uri="/tmp/results.parquet",
            table_name="analytics.daily_sales",
            mode="replace"
        )
    """
    import polars as pl
    import duckdb

    # Extract database path
    database = session_context.warehouse.replace("duckdb://", "")

    # Read parquet
    df = pl.read_parquet(input_uri)

    # Write to database
    conn = duckdb.connect(database)
    try:
        if mode == "replace":
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")

        # Convert polars to arrow and insert
        conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM df")

        return Artifact(
            uri=f"{session_context.warehouse}/{table_name}",
            format="table",
            schema={col: str(dtype) for col, dtype in df.schema.items()},
            row_count=len(df),
            lineage={"tool": "write_table", "source": input_uri}
        )
    finally:
        conn.close()
```

### Effort Breakdown
- `run_polars`: **1.5 hours**
- `trigger_dbt`: **1.5 hours**
- `write_table`: **1 hour**

---

## Gap 3: Permission Enforcement
**Status:** ⚠️ Partially implemented
**Effort:** 30 minutes
**Lines:** ~20
**Priority:** High

### What's Missing
`allowed_tools` is stored in `AgentConfig` but never checked before execution.

### Current Code
```python
# base.py:18-20
self.config = AgentConfig(
    allowed_tools=allowed_tools or [],  # Stored but not used!
)

# base.py:51-53
tool_func = self.tools.get(tool_use.tool_name)
if not tool_func:
    raise ValueError(f"Tool {tool_use.tool_name} not found")
# ⚠️ Missing: Check if tool_name in allowed_tools
```

### Fix (30 min)
```python
# base.py:51-57
async def query(self, prompt: str) -> AsyncIterator[Dict[str, Any]]:
    tool_use = self._parse_prompt(prompt)

    # ✅ Check allowed_tools
    if self.config.allowed_tools and tool_use.tool_name not in self.config.allowed_tools:
        yield {
            "type": "error",
            "message": f"Tool '{tool_use.tool_name}' not in allowed_tools: {self.config.allowed_tools}"
        }
        return

    # Check permissions (existing hooks)
    for hook in PRE_TOOL_USE_HOOKS:
        ...
```

### Test to Add
```python
async def test_allowed_tools_enforcement():
    agent = DataAgent(allowed_tools=["read_metadata"])  # Only allow read_metadata
    agent.register_tool(run_sql)
    agent.register_tool(read_metadata)

    # Should fail: run_sql not in allowed_tools
    async for msg in agent.query("SELECT * FROM sales"):
        assert msg["type"] == "error"
        assert "not in allowed_tools" in msg["message"]

    # Should succeed: read_metadata is allowed
    async for msg in agent.query("describe sales"):
        assert msg["type"] == "result"
```

---

## Gap 4: Tool Tagging & Richer Governance
**Status:** ❌ Not implemented
**Effort:** 2 hours
**Lines:** ~100
**Priority:** Medium

### What's Missing
Tools need metadata (read-only, writes data, expensive) for governance.

### Current Governance
```python
# hooks/governance.py:7-12
async def check_access(tool_use: ToolUseMessage, context: SessionContext):
    dataset = tool_use.tool_input.get("table")
    if dataset and dataset.startswith("finance."):  # Too simple!
        if context.role != "finance":
            return {"permission": "deny", "reason": "Unauthorized"}
    return {"permission": "allow"}
```

### What to Add

#### 1. Tool Metadata (30 min, ~30 lines)
```python
# types.py
@dataclass
class ToolMetadata:
    name: str
    description: str
    tags: List[str] = field(default_factory=list)  # ["read_only", "expensive", "writes_data"]
    estimated_cost: Optional[float] = None  # $0.01 per call

# Register tools with metadata
TOOL_REGISTRY = {
    "run_sql": ToolMetadata(
        name="run_sql",
        description="Execute SQL query",
        tags=["read_only", "expensive"],
        estimated_cost=0.05
    ),
    "write_table": ToolMetadata(
        name="write_table",
        description="Write to table",
        tags=["writes_data", "expensive"],
        estimated_cost=0.10
    ),
}
```

#### 2. Enhanced Governance Hooks (1.5 hours, ~70 lines)
```python
# hooks/governance.py
async def check_write_permissions(tool_use: ToolUseMessage, context: SessionContext):
    """Prevent writes in read-only mode."""
    tool_meta = TOOL_REGISTRY.get(tool_use.tool_name)

    if tool_meta and "writes_data" in tool_meta.tags:
        if context.role == "analyst":  # Analysts can't write
            return {"permission": "deny", "reason": "Analysts cannot write data"}

    return {"permission": "allow"}

async def check_cost_limits(tool_use: ToolUseMessage, context: SessionContext):
    """Enforce cost budgets."""
    tool_meta = TOOL_REGISTRY.get(tool_use.tool_name)

    if tool_meta and tool_meta.estimated_cost:
        # Check if user has budget (pseudo-code)
        if user_budget[context.user] < tool_meta.estimated_cost:
            return {"permission": "deny", "reason": "Insufficient budget"}

    return {"permission": "allow"}

async def check_dataset_tags(tool_use: ToolUseMessage, context: SessionContext):
    """Block access to PII datasets."""
    dataset_uri = tool_use.tool_input.get("table") or tool_use.tool_input.get("input_uri")

    if dataset_uri:
        # Look up dataset in catalog (pseudo-code)
        dataset = catalog.get_dataset(dataset_uri)
        if "pii" in dataset.tags and context.role != "privacy_officer":
            return {"permission": "deny", "reason": "PII data requires privacy_officer role"}

    return {"permission": "allow"}

PRE_TOOL_USE_HOOKS = [
    check_access,
    check_write_permissions,
    check_cost_limits,
    check_dataset_tags,
]
```

---

## Gap 5: Plan Mode, Streaming, Retries
**Status:** ⚠️ Skeleton only
**Effort:** 6 hours
**Lines:** ~250
**Priority:** Low

### What's Missing

#### 1. Plan Mode (2 hours, ~80 lines)
```python
# Current: plan() just returns tool_name + inputs
# Needed: Actually run pre-flight checks without executing

async def plan(self, prompt: str) -> QueryPlan:
    """Generate execution plan with cost/row estimates."""
    tool_use = self._parse_prompt(prompt)

    # Run dry-run hooks
    for hook in PRE_TOOL_USE_HOOKS:
        result = await hook(tool_use, self.session_context)
        if result.get("permission") == "deny":
            raise PermissionError(result.get("reason"))

    # Estimate cost/rows (tool-specific)
    if tool_use.tool_name == "run_sql":
        estimated_rows = await _estimate_sql_rows(tool_use.tool_input["sql"])
    else:
        estimated_rows = None

    return QueryPlan(
        tool_name=tool_use.tool_name,
        tool_input=tool_use.tool_input,
        estimated_cost=TOOL_REGISTRY[tool_use.tool_name].estimated_cost,
        estimated_rows=estimated_rows,
    )
```

#### 2. Streaming Progress (2 hours, ~80 lines)
```python
async def query(self, prompt: str) -> AsyncIterator[Dict[str, Any]]:
    """Stream progress updates."""
    tool_use = self._parse_prompt(prompt)

    # Yield start event
    yield {"type": "progress", "status": "starting", "tool": tool_use.tool_name}

    # Run tool
    try:
        result = await tool_func(**tool_input)

        # Yield progress during execution (if tool supports it)
        # async for progress in tool_func.stream_progress():
        #     yield {"type": "progress", "pct": progress.pct, "rows": progress.rows}

        yield {"type": "result", "result": result.to_manifest()}
    except Exception as e:
        yield {"type": "error", "error": str(e)}
```

#### 3. Retries (1 hour, ~40 lines)
```python
async def query(self, prompt: str, max_retries: int = 3) -> AsyncIterator[Dict[str, Any]]:
    """Retry transient failures."""
    for attempt in range(max_retries):
        try:
            async for msg in self._execute_tool(prompt):
                yield msg
            return  # Success
        except TransientError as e:
            if attempt == max_retries - 1:
                yield {"type": "error", "error": f"Failed after {max_retries} retries: {e}"}
            else:
                yield {"type": "progress", "status": "retrying", "attempt": attempt + 1}
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

#### 4. OpenTelemetry Hooks (1 hour, ~50 lines)
```python
# hooks/observability.py
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def trace_tool_execution(tool_result: ToolResultMessage, context: SessionContext):
    """Send telemetry to OpenTelemetry."""
    with tracer.start_as_current_span("tool_execution") as span:
        span.set_attribute("tool_name", tool_result.tool_use_id)
        span.set_attribute("user", context.user)
        span.set_attribute("rows", tool_result.artifact.row_count if tool_result.artifact else 0)

        if tool_result.is_error:
            span.set_status(trace.Status(trace.StatusCode.ERROR))

POST_TOOL_USE_HOOKS.append(trace_tool_execution)
```

---

## Gap 6: Test Coverage
**Status:** ❌ Minimal
**Effort:** 3 hours
**Lines:** ~200
**Priority:** High

### Current State
```python
# tests/test_tools.py (11 lines)
async def test_run_sql():
    result = await run_sql("SELECT 1")
    assert isinstance(result, Artifact)
```

### Tests to Add

#### 1. Hook Tests (1 hour, ~70 lines)
```python
async def test_governance_hook_denies_finance():
    from data_agent_sdk.hooks.governance import check_access

    tool_use = ToolUseMessage(
        tool_name="read_metadata",
        tool_input={"table": "finance.salaries"}
    )
    context = SessionContext(warehouse="duckdb:///:memory:", user="alice", role="analyst")

    result = await check_access(tool_use, context)
    assert result["permission"] == "deny"
    assert "Unauthorized" in result["reason"]

async def test_lineage_hook_logs():
    from data_agent_sdk.hooks.lineage import log_lineage

    artifact = Artifact(uri="/tmp/test.parquet", format="parquet", schema={}, row_count=10)
    tool_result = ToolResultMessage(tool_use_id="123", result=artifact, artifact=artifact)
    context = SessionContext(warehouse="duckdb:///:memory:", user="bob", role="analyst")

    await log_lineage(tool_result, context)

    # Check lineage file
    with open("/tmp/lineage.jsonl") as f:
        last_line = f.readlines()[-1]
        entry = json.loads(last_line)
        assert entry["user"] == "bob"
        assert entry["rows"] == 10
```

#### 2. Transport Tests (1 hour, ~70 lines)
```python
async def test_subprocess_transport():
    from data_agent_sdk.transport.subprocess import SubprocessTransport

    async with SubprocessTransport([
        "uv", "run", "--no-project", "python",
        "mcp_server_standalone.py", "--db", ":memory:"
    ]) as transport:
        # List tools
        tools = await transport.list_tools()
        assert len(tools) == 2
        assert tools[0]["name"] == "run_sql"

        # Call tool
        result = await transport.call_tool("run_sql", {"sql": "SELECT 1 as test"})
        assert result["row_count"] == 1
```

#### 3. MCP Flow Tests (1 hour, ~60 lines)
```python
async def test_mcp_server_error_handling():
    """Test MCP server handles invalid requests."""
    from mcp_server_standalone import MCPServer

    server = MCPServer(db_path=":memory:")

    # Invalid method
    response = await server.handle_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "invalid_method",
        "params": {}
    })
    assert "error" in response
    assert response["error"]["code"] == -32603

    # Invalid tool
    response = await server.handle_request({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "nonexistent_tool", "arguments": {}}
    })
    assert "error" in response
```

---

## Implementation Roadmap

### Phase 1: High-Priority Fixes (4.5 hours)
**Goal:** Close critical gaps that undermine the pitch

1. ✅ **Permission enforcement** (30 min)
   - Add `allowed_tools` check in `query()`
   - Add test

2. ✅ **Missing tools** (4 hours)
   - Add `run_polars` (1.5h)
   - Add `trigger_dbt` (1.5h)
   - Add `write_table` (1h)

### Phase 2: Medium-Priority Enhancements (4 hours)
**Goal:** Deliver on core abstractions

3. ✅ **Core types** (2 hours)
   - Add `Dataset`, `QueryPlan`, `JobRun`
   - Update tools to use them

4. ✅ **Tool tagging + governance** (2 hours)
   - Add `ToolMetadata`
   - Add richer governance hooks

### Phase 3: Nice-to-Haves (9 hours)
**Goal:** Complete the vision (if time allows)

5. ⚠️ **Plan mode, streaming, retries** (6 hours)
   - Implement real plan mode (2h)
   - Add streaming progress (2h)
   - Add retries (1h)
   - Add OpenTelemetry (1h)

6. ⚠️ **Test coverage** (3 hours)
   - Hook tests (1h)
   - Transport tests (1h)
   - MCP tests (1h)

---

## Recommendation

### Minimum Viable (Phase 1 + 2): **8.5 hours** (1 day)
Closes the most glaring gaps:
- ✅ Permission enforcement works
- ✅ Five tools demonstrated
- ✅ Core types present
- ✅ Richer governance

**Impact:** SDK now delivers on pitch, feels production-ready.

### Complete (All Phases): **17.5 hours** (2-3 days)
Full implementation:
- ✅ All gaps closed
- ✅ Streaming, retries, observability
- ✅ Comprehensive tests

**Impact:** Production-grade, nothing feels like a toy.

---

## Effort Summary

| Phase | Hours | Lines | Deliverable |
|-------|-------|-------|-------------|
| Phase 1 (Critical) | 4.5 | 320 | Enforced permissions + 5 tools |
| Phase 2 (Core) | 4 | 250 | Core types + tool tagging |
| **Subtotal (MVP)** | **8.5** | **570** | **Pitch-complete SDK** |
| Phase 3 (Polish) | 9 | 450 | Streaming, retries, tests |
| **Total (Complete)** | **17.5** | **1,020** | **Production SDK** |

---

## Conclusion

**Can we close all gaps?** Yes, in **2-3 days** of work.

**Should we?** Depends on goal:
- **Learning SDK:** Keep it minimal (current state is fine)
- **Production blueprint:** Do Phase 1+2 (8.5 hours)
- **Reference implementation:** Do all phases (17.5 hours)

**Recommendation:** Implement **Phase 1 + 2** (8.5 hours). This closes the critical gaps without adding too much complexity, and keeps the SDK learnable while feeling production-ready.
