# Data Agent SDK - How It Actually Works

## Simple Agent Loop (The Core Pattern)

```
┌────────────────────────────────────────────────────────────┐
│                     USER QUERY                             │
│  agent.query("SELECT * FROM sales WHERE revenue > 100")    │
└──────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  1. Parse       │
                  │  Prompt         │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  2. Pre-Hooks   │
                  │  (Governance)   │
                  └────────┬────────┘
                           │
                    Allow? │ Deny?
              ┌────────────┼────────────┐
              │ allow      │ deny       │
              ▼            ▼            │
     ┌─────────────┐  ┌────────┐       │
     │ 3. Execute  │  │ Return │       │
     │    Tool     │  │ Error  │◄──────┘
     └──────┬──────┘  └────────┘
            │
            ▼
     ┌─────────────┐
     │ 4. Post-    │
     │    Hooks    │
     │  (Lineage)  │
     └──────┬──────┘
            │
            ▼
     ┌─────────────┐
     │ 5. Return   │
     │   Result    │
     └─────────────┘
```

## The Complete Flow (What Really Happens)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER CALLS AGENT                                │
│  async for msg in agent.query("SELECT * FROM sales WHERE revenue > 100")│
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 1: PARSE PROMPT                                                    │
│                                                                          │
│  tool_use = _parse_prompt(prompt)                                       │
│                                                                          │
│  Returns: ToolUseMessage(                                               │
│    tool_name = "run_sql"                                                │
│    tool_input = {"sql": "SELECT * FROM sales WHERE revenue > 100"}      │
│    tool_use_id = "uuid-123"                                             │
│  )                                                                       │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 2: PRE-TOOL HOOKS (Governance)                                     │
│                                                                          │
│  for hook in PRE_TOOL_USE_HOOKS:                                        │
│    result = await check_access(tool_use, session_context)               │
│                                                                          │
│    if result["permission"] == "deny":                                   │
│      yield {"type": "error", "message": "Unauthorized"}                 │
│      return  ← STOPS HERE IF DENIED                                     │
│                                                                          │
│  Example check:                                                          │
│    - Is user allowed to query this table?                               │
│    - Is dataset tagged as "pii" and user lacks permissions?             │
│    - Has user exceeded quota?                                           │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 3: EXECUTE TOOL                                                    │
│                                                                          │
│  tool_func = self.tools.get("run_sql")                                  │
│  tool_input = {                                                          │
│    "sql": "SELECT * FROM sales WHERE revenue > 100",                    │
│    "session_context": session_context                                   │
│  }                                                                       │
│                                                                          │
│  result = await run_sql(**tool_input)                                   │
│                                                                          │
│  Returns: Artifact(                                                      │
│    uri = "/tmp/query_abc123.parquet"                                    │
│    format = "parquet"                                                    │
│    schema = {"id": "Int32", "product": "String", "revenue": "Decimal"}  │
│    row_count = 3                                                         │
│    lineage = {"query": "SELECT...", "tool": "run_sql"}                  │
│  )                                                                       │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 4: POST-TOOL HOOKS (Lineage)                                       │
│                                                                          │
│  tool_result = ToolResultMessage(                                        │
│    tool_use_id = "uuid-123"                                             │
│    result = artifact                                                     │
│    artifact = artifact                                                   │
│  )                                                                       │
│                                                                          │
│  for hook in POST_TOOL_USE_HOOKS:                                       │
│    await log_lineage(tool_result, session_context)                      │
│                                                                          │
│  What it logs:                                                           │
│    {                                                                     │
│      "timestamp": "2025-10-04T16:30:00",                                │
│      "user": "alice@company.com",                                       │
│      "output": "/tmp/query_abc123.parquet",                             │
│      "rows": 3                                                           │
│    }                                                                     │
│                                                                          │
│  Written to: /tmp/lineage.jsonl                                         │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 5: RETURN RESULT                                                   │
│                                                                          │
│  yield {                                                                 │
│    "type": "result",                                                     │
│    "result": {                                                           │
│      "uri": "/tmp/query_abc123.parquet",                                │
│      "format": "parquet",                                                │
│      "schema": {"id": "Int32", ...},                                    │
│      "row_count": 3                                                      │
│    }                                                                     │
│  }                                                                       │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
                            USER RECEIVES
                            RESULT MESSAGE
```

---

## The Actual Code (Simplified)

```python
async def query(self, prompt: str) -> AsyncIterator[Dict[str, Any]]:
    """Execute query - this is the complete agent loop."""

    # STEP 1: Parse prompt
    tool_use = self._parse_prompt(prompt)
    # Returns: ToolUseMessage(tool_name="run_sql", tool_input={...})

    # STEP 2: Pre-tool hooks (governance)
    for hook in PRE_TOOL_USE_HOOKS:
        result = await hook(tool_use, self.session_context)
        if result.get("permission") == "deny":
            yield {"type": "error", "message": result.get("reason")}
            return  # ← STOPS HERE IF DENIED

    # STEP 3: Execute tool
    try:
        tool_func = self.tools.get(tool_use.tool_name)
        tool_input = {**tool_use.tool_input, "session_context": self.session_context}
        result = await tool_func(**tool_input)  # ← Actual work happens here

        # STEP 4: Post-tool hooks (lineage)
        tool_result = ToolResultMessage(
            tool_use_id=tool_use.tool_use_id,
            result=result,
            artifact=result if isinstance(result, Artifact) else None
        )

        for hook in POST_TOOL_USE_HOOKS:
            await hook(tool_result, self.session_context)

        # STEP 5: Return result
        yield {
            "type": "result",
            "result": result if not isinstance(result, Artifact) else result.to_manifest()
        }
    except Exception as e:
        yield {"type": "error", "error": str(e)}
```

**That's it. 40 lines. No magic.**

---

## Direct SDK Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        DataAgent                               │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  query("SELECT * FROM sales")                        │    │
│  └─────────────────────┬────────────────────────────────┘    │
│                        │                                      │
│                        ▼                                      │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Pre-Tool Hooks (Governance)                         │    │
│  │  • check_access(tool_use, context)                   │    │
│  │  • check_quota(tool_use, context)                    │    │
│  └─────────────────────┬────────────────────────────────┘    │
│                        │                                      │
│                        ▼                                      │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Execute Tool                                        │    │
│  │  run_sql(sql="SELECT...", session_context=...)       │    │
│  │                                                       │    │
│  │  Returns: Artifact(uri, schema, row_count, lineage)  │    │
│  └─────────────────────┬────────────────────────────────┘    │
│                        │                                      │
│                        ▼                                      │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Post-Tool Hooks (Lineage)                           │    │
│  │  • log_lineage(tool_result, context)                 │    │
│  │  • send_metrics(tool_result, context)                │    │
│  └─────────────────────┬────────────────────────────────┘    │
│                        │                                      │
│                        ▼                                      │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  yield {"type": "result", "result": artifact}        │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## MCP Server Architecture

```
┌──────────────────┐   JSON-RPC    ┌─────────────────────────┐
│  Agent Process   │──(stdin/out)──│   MCP Server Process    │
│                  │               │      (subprocess)       │
│  ┌────────────┐  │               │                         │
│  │ Subprocess │  │   Request     │  ┌──────────────────┐   │
│  │ Transport  │──┼──────────────►│  │ handle_request() │   │
│  └────────────┘  │   {"method":  │  └────────┬─────────┘   │
│                  │    "tools/    │           │             │
│                  │    call"}     │           ▼             │
│                  │               │  ┌──────────────────┐   │
│                  │   Response    │  │  run_sql()       │   │
│                  │◄──────────────┼──│  read_metadata() │   │
│                  │   {"result":  │  └──────────────────┘   │
│                  │    {...}}     │                         │
└──────────────────┘               └─────────────────────────┘
```

## Session Context (No Globals!)

```
┌─────────────────────────────────────────────────────────┐
│  SessionContext(                                        │
│    warehouse = "duckdb:///tmp/sales.db"                 │
│    user = "alice@company.com"                           │
│    role = "analyst"                                     │
│  )                                                       │
└──────────────────┬──────────────────────────────────────┘
                   │
                   │ Passed to EVERY call
                   │
       ┌───────────┼───────────┬────────────┐
       │           │           │            │
       ▼           ▼           ▼            ▼
  ┌─────────┐ ┌────────┐ ┌─────────┐ ┌──────────┐
  │ Pre-    │ │ Tool   │ │ Post-   │ │ Parse    │
  │ Hook    │ │        │ │ Hook    │ │ Prompt   │
  │         │ │        │ │         │ │          │
  │ Uses:   │ │ Uses:  │ │ Uses:   │ │ Uses:    │
  │ • role  │ │ • wh   │ │ • user  │ │ • config │
  └─────────┘ └────────┘ └─────────┘ └──────────┘
```

## Polars Pipeline (5-Step Data Flow)

```
┌──────────────────────────────────────────────────────────────┐
│ INPUT: raw_sales.csv (10 orders)                             │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
              ┌──────────────────────────┐
              │ STEP 1: transform_csv    │
              │ • Filter: status='ok'    │
              │ • Select: [id, price]    │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────────────────┐
              │ Artifact(                            │
              │   uri = "/tmp/cleaned.parquet"       │
              │   row_count = 8                      │
              │ )                                     │
              └────────────┬─────────────────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │ STEP 2: run_polars       │
              │ • Add: revenue column    │
              │ • Calc: qty * price      │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────────────────┐
              │ Artifact(                            │
              │   uri = "/tmp/enriched.parquet"      │
              │   schema = {..., revenue: Int64}     │
              │ )                                     │
              └────────────┬─────────────────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │ STEP 3: join_datasets    │
              │ • Join: products on id   │
              │ • Add: product_name      │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────────────────┐
              │ Artifact(                            │
              │   uri = "/tmp/joined.parquet"        │
              │   schema = {..., product_name: Str}  │
              │ )                                     │
              └────────────┬─────────────────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │ STEP 4: aggregate_data   │
              │ • Group: region, category│
              │ • Sum: revenue, quantity │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────────────────┐
              │ Artifact(                            │
              │   uri = "/tmp/summary.parquet"       │
              │   row_count = 7                      │
              │ )                                     │
              └────────────┬─────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ OUTPUT: Regional sales summary (7 rows)                      │
│                                                              │
│ shape: (7, 5)                                                │
│ ┌────────┬─────────────┬─────────────┬──────────────┐       │
│ │ region ┆ category    ┆ revenue_sum ┆ quantity_sum │       │
│ │ East   ┆ Electronics ┆ 6000        ┆ 5            │       │
│ │ North  ┆ Electronics ┆ 2400        ┆ 2            │       │
│ └────────┴─────────────┴─────────────┴──────────────┘       │
└──────────────────────────────────────────────────────────────┘
```

## Artifact Chaining (Pipeline Pattern)

```
┌─────────────────┐         ┌─────────────────┐
│  Step 1: Clean  │         │  Step 2: Enrich │
│                 │         │                 │
│  Returns:       │  uri    │  Input:         │
│  Artifact ──────┼────────►│  previous.uri   │
│  (uri="/tmp/    │         │                 │
│   step1.parq")  │         │  Returns:       │
└─────────────────┘         │  Artifact ──────┼───►
                            │  (uri="/tmp/    │
                            │   step2.parq")  │
                            └─────────────────┘
                                     │
                                     │ uri
                                     ▼
                            ┌─────────────────┐
                            │  Step 3: Join   │
                            │                 │
                            │  Input:         │
                            │  previous.uri   │
                            │                 │
                            │  Returns:       │
                            │  Artifact       │
                            └─────────────────┘
```

## Hooks in Action

```
┌─────────────────────────────────────────────────────────────┐
│ PRE-TOOL HOOK (Governance)                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Input: ToolUseMessage(                                     │
│    tool_name = "run_sql"                                    │
│    tool_input = {"table": "finance.salaries"}               │
│  )                                                           │
│                                                             │
│  ┌────────────────────────────────────────┐                │
│  │  if table.startswith("finance."):      │                │
│  │    if context.role != "finance":       │                │
│  │      return {"permission": "deny"}     │                │
│  └────────────────────────────────────────┘                │
│                                                             │
│  Output: {"permission": "deny", "reason": "Unauthorized"}   │
│                                                             │
│  Result: ✗ TOOL EXECUTION BLOCKED                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ POST-TOOL HOOK (Lineage)                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Input: ToolResultMessage(                                  │
│    artifact = Artifact(                                     │
│      uri = "/tmp/query_abc.parquet"                         │
│      row_count = 3                                          │
│    )                                                         │
│  )                                                           │
│                                                             │
│  ┌────────────────────────────────────────┐                │
│  │  entry = {                             │                │
│  │    "timestamp": "2025-10-04...",       │                │
│  │    "user": context.user,               │                │
│  │    "output": artifact.uri,             │                │
│  │    "rows": artifact.row_count          │                │
│  │  }                                      │                │
│  │  write_to_lineage_log(entry)           │                │
│  └────────────────────────────────────────┘                │
│                                                             │
│  Result: ✓ LINEAGE LOGGED                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## MCP JSON-RPC Protocol

```
AGENT                          MCP SERVER
  │                                │
  │  1. Send Request               │
  ├───────────────────────────────►│
  │  {                             │
  │    "jsonrpc": "2.0",           │
  │    "id": 1,                    │
  │    "method": "tools/call",     │
  │    "params": {                 │
  │      "name": "run_sql",        │
  │      "arguments": {            │
  │        "sql": "SELECT..."      │
  │      }                          │
  │    }                            │
  │  }                             │
  │                                │
  │                                │ 2. Execute Tool
  │                                │    run_sql(...)
  │                                │
  │  3. Send Response              │
  │◄───────────────────────────────┤
  │  {                             │
  │    "jsonrpc": "2.0",           │
  │    "id": 1,                    │
  │    "result": {                 │
  │      "content": [{             │
  │        "type": "text",         │
  │        "text": "{...}"         │
  │      }]                         │
  │    }                            │
  │  }                             │
  │                                │
  ▼                                ▼
```

## USER: Run polars pipeline

┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: transform_csv (Clean CSV)                               │
│                                                                  │
│  Input:  /tmp/raw_sales.csv (10 rows)                           │
│  Filter: pl.col('status') == 'completed'                        │
│  Select: ['product_id', 'quantity', 'price', 'region']          │
│                                                                  │
│  Output: Artifact(                                               │
│    uri = "/tmp/transformed_abc.parquet"                         │
│    row_count = 8                                                 │
│  )                                                               │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: run_polars (Calculate revenue)                          │
│                                                                  │
│  Input:  /tmp/transformed_abc.parquet (8 rows)                  │
│  Ops:    with_columns((quantity * price).alias('revenue'))      │
│                                                                  │
│  Output: Artifact(                                               │
│    uri = "/tmp/polars_def.parquet"                              │
│    schema = {..., 'revenue': 'Int64'}  ← NEW COLUMN             │
│    row_count = 8                                                 │
│  )                                                               │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 3: join_datasets (Enrich with products)                    │
│                                                                  │
│  Left:   /tmp/polars_def.parquet (8 rows)                       │
│  Right:  /tmp/products.parquet (3 products)                     │
│  On:     'product_id'                                            │
│                                                                  │
│  Output: Artifact(                                               │
│    uri = "/tmp/joined_ghi.parquet"                              │
│    schema = {..., 'product_name': 'String', ...}  ← ENRICHED    │
│    row_count = 8                                                 │
│  )                                                               │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 4: aggregate_data (Group by region)                        │
│                                                                  │
│  Input:      /tmp/joined_ghi.parquet (8 rows)                   │
│  Group by:   ['region', 'category']                             │
│  Aggregate:  {'revenue': 'sum', 'quantity': 'sum'}              │
│                                                                  │
│  Output: Artifact(                                               │
│    uri = "/tmp/aggregated_jkl.parquet"                          │
│    row_count = 7  ← SUMMARY ROWS                                │
│  )                                                               │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ FINAL RESULT                                                     │
│                                                                  │
│  shape: (7, 5)                                                   │
│  ┌────────┬─────────────┬─────────────┬──────────────┐          │
│  │ region ┆ category    ┆ revenue_sum ┆ quantity_sum │          │
│  │ East   ┆ Electronics ┆ 6000        ┆ 5            │          │
│  │ North  ┆ Electronics ┆ 2400        ┆ 2            │          │
│  └────────┴─────────────┴─────────────┴──────────────┘          │
│                                                                  │
│  Lineage: 5 artifacts + 5 lineage entries logged                │
└──────────────────────────────────────────────────────────────────┘
```

**Each step:**
- Takes previous Artifact's URI as input
- Returns new Artifact with updated schema
- Logs lineage automatically via POST hooks
- Governance checks via PRE hooks (if configured)

---

## MCP Server Flow (Process Isolation)

```
┌──────────────────────────────────────────────────────────────────┐
│ AGENT PROCESS                                                    │
│                                                                  │
│  async with SubprocessTransport([                                │
│    "uv", "run", "python", "mcp_server_standalone.py"            │
│  ]) as transport:                                                │
│                                                                  │
│    result = await transport.call_tool(                           │
│      "run_sql",                                                  │
│      {"sql": "SELECT * FROM sales"}                              │
│    )                                                             │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ 1. Write JSON-RPC to stdin
                             │    {"method": "tools/call", ...}
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ MCP SERVER PROCESS (subprocess)                                  │
│                                                                  │
│  while True:                                                     │
│    request = json.loads(stdin.readline())                       │
│                                                                  │
│    if request["method"] == "tools/call":                         │
│      tool_name = request["params"]["name"]                       │
│      tool_args = request["params"]["arguments"]                 │
│                                                                  │
│      result = await self.tools[tool_name](**tool_args)          │
│                                                                  │
│      response = {                                                │
│        "jsonrpc": "2.0",                                         │
│        "id": request["id"],                                      │
│        "result": {"content": [{"type": "text", "text": ...}]}   │
│      }                                                           │
│                                                                  │
│      stdout.write(json.dumps(response))                         │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ 2. Write JSON-RPC to stdout
                             │    {"result": {...}}
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ AGENT PROCESS                                                    │
│                                                                  │
│  response = json.loads(stdout.readline())                       │
│  result = response["result"]["content"][0]["text"]              │
│  return json.loads(result)                                       │
│                                                                  │
│  Returns: {                                                      │
│    "uri": "/tmp/query.parquet",                                 │
│    "row_count": 4,                                               │
│    ...                                                           │
│  }                                                               │
└──────────────────────────────────────────────────────────────────┘
```

**Why MCP?**
- Tool crashes don't kill agent
- Can run tools on different machines
- Can wrap any CLI (dbt, spark-submit, etc.)

---

## Session Context Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ USER CREATES AGENT                                              │
│                                                                 │
│  agent = DataAgent(                                             │
│    session_context = SessionContext(                            │
│      warehouse = "duckdb:///tmp/sales.db"  ← DB path           │
│      user = "alice@company.com"             ← Who's running    │
│      role = "analyst"                       ← Permission level │
│    )                                                            │
│  )                                                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ Passed to EVERY call
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
  ┌──────────┐       ┌──────────┐       ┌──────────┐
  │ PRE-HOOK │       │   TOOL   │       │POST-HOOK │
  │          │       │          │       │          │
  │ Uses:    │       │ Uses:    │       │ Uses:    │
  │ • role   │       │ • warehouse      │ • user   │
  │          │       │           │       │          │
  └──────────┘       └──────────┘       └──────────┘
```

**No globals. Context passed explicitly everywhere.**

---

## Artifact Chaining (How Pipelines Work)

```
┌────────────────────────────────────────────────────────────────┐
│ STEP 1: transform_csv                                          │
│                                                                │
│  Returns: Artifact(uri="/tmp/step1.parquet")                  │
└────────────────────────────┬───────────────────────────────────┘
                             │
                             │ artifact.uri becomes next input
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│ STEP 2: run_polars                                             │
│                                                                │
│  Input: input_uri = step1_artifact.uri  ← USES PREVIOUS OUTPUT│
│  Returns: Artifact(uri="/tmp/step2.parquet")                  │
└────────────────────────────┬───────────────────────────────────┘
                             │
                             │ artifact.uri becomes next input
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│ STEP 3: join_datasets                                          │
│                                                                │
│  Input: left_uri = step2_artifact.uri  ← USES PREVIOUS OUTPUT │
│  Returns: Artifact(uri="/tmp/step3.parquet")                  │
└────────────────────────────────────────────────────────────────┘
```

**Pipeline = Chain of Artifacts**
- Each step takes previous URI
- Returns new Artifact
- Schema evolves at each step
- Lineage tracks full chain

---

## Summary: The Complete Pattern

```python
# 1. Define tools
async def run_sql(sql: str, session_context: SessionContext) -> Artifact:
    # Execute and return Artifact
    pass

# 2. Define hooks
async def check_access(tool_use, context):
    # Return allow/deny
    pass

async def log_lineage(tool_result, context):
    # Write to lineage store
    pass

# 3. Create agent
agent = DataAgent(
    allowed_tools=["run_sql"],
    session_context=SessionContext(...)
)
agent.register_tool(run_sql)

# 4. Execute
async for msg in agent.query("SELECT * FROM sales"):
    print(msg)

# What happens:
# Parse → Pre-hooks → Execute → Post-hooks → Return
```

**That's the entire pattern. 5 steps. No magic.**
