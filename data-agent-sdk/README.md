# Data Agent SDK

> **A minimal, production-ready SDK for building data engineering agents in a weekend.**

Stop wrestling with complex agent frameworks. This SDK shows you exactly how agents work under the hood—no magic, just clean patterns you can understand and extend.

---

## 🎯 What Is This?

A **Data Engineering Agent SDK** that demonstrates:

- ✅ How to build agents that execute SQL queries, read metadata, and transform data
- ✅ How to add **governance** (access control, throttling)
- ✅ How to track **lineage** (who ran what, when)
- ✅ How to use **MCP servers** for process isolation
- ✅ How to build **real data pipelines** with Polars
- ✅ How to do all this in ~2,000 lines of code

**Not included:** LLM integration (use Claude/OpenAI API), complex orchestration, or batteries-included everything. This is a **learning SDK** that shows you the patterns.

---

## 🚀 Quick Start (30 seconds)

```bash
# Install dependencies (uses UV for fast installs)
uv pip install -e .

# Run the Polars pipeline (⭐ BEST DEMO - Real data engineering!)
uv run python polars_pipeline_example.py

# Run the simple SQL example
uv run python simple_example.py

# Run the MCP server example (advanced)
uv run python mcp_example.py
```

**Or use Makefile:**
```bash
make install
make run-polars    # Polars pipeline
make run-simple    # SQL example
make run-mcp       # MCP server
```

---

## 📊 Three Examples, Three Patterns

### Example 1: Simple SQL Agent (`simple_example.py`)

**What it shows:** Basic agent executing SQL queries with hooks.

```python
from data_agent_sdk.agents.base import DataAgent
from data_agent_sdk.tools.sql import run_sql

agent = DataAgent(
    allowed_tools=["run_sql"],
    session_context=SessionContext(
        warehouse="duckdb:///tmp/sales.db",
        user="analyst",
        role="analyst"
    )
)
agent.register_tool(run_sql)

async for msg in agent.query("SELECT * FROM sales"):
    print(msg)
```

**Output:**
```
✓ Query executed successfully
  - Output: /tmp/query_abc123.parquet
  - Rows: 4
```

---

### Example 2: Polars Data Pipeline (`polars_pipeline_example.py`) ⭐

**What it shows:** Real-world data engineering workflow.

**5-Step Pipeline:**
```
Raw CSV (10 orders)
  ↓ Step 1: Filter cancelled orders
Cleaned Parquet (8 orders)
  ↓ Step 2: Calculate revenue (quantity × price)
Enriched Parquet (8 orders + revenue)
  ↓ Step 3: Join with product catalog
Complete Parquet (8 orders + product names)
  ↓ Step 4: Aggregate by region + category
Summary Parquet (7 summary rows)
```

**Code:**
```python
from data_agent_sdk.tools.polars_tool import (
    transform_csv, join_datasets, aggregate_data, run_polars
)

# Step 1: Clean CSV data
cleaned = await transform_csv(
    input_csv="/tmp/raw_sales.csv",
    filter_expr="pl.col('status') == 'completed'",
    select_cols=["product_id", "quantity", "price", "region"]
)

# Step 2: Calculate revenue
enriched = await run_polars(
    input_uri=cleaned.uri,
    operations="with_columns((pl.col('quantity') * pl.col('price')).alias('revenue'))"
)

# Step 3: Join with product catalog
joined = await join_datasets(
    left_uri=enriched.uri,
    right_uri="/tmp/products.parquet",
    on="product_id"
)

# Step 4: Aggregate by region
summary = await aggregate_data(
    input_uri=joined.uri,
    group_by=["region", "category"],
    aggregations={"revenue": "sum", "quantity": "sum"}
)
```

**Output:**
```
======================================================================
POLARS DATA PIPELINE - End-to-End Example
======================================================================

[Step 1] Clean raw sales data
  ✓ Cleaned sales data: 10 → 8 rows

[Step 2] Calculate revenue
  ✓ Added revenue column

[Step 3] Join with products
  ✓ Joined with product catalog

[Step 4] Aggregate by region
  ✓ Aggregated: 7 summary rows

[Step 5] Results
shape: (7, 5)
┌────────┬─────────────┬─────────────┬────────────────┐
│ region ┆ category    ┆ revenue_sum ┆ quantity_sum   │
│ East   ┆ Electronics ┆ 6000        ┆ 5              │
│ North  ┆ Electronics ┆ 2400        ┆ 2              │
└────────┴─────────────┴─────────────┴────────────────┘

Artifacts created: 5
Lineage entries: 6
✅ Pipeline completed!
```

**Why this matters:**
- ✅ Real-world data engineering workflow
- ✅ CSV → clean → join → aggregate (what engineers actually do!)
- ✅ Shows Polars power (fast, typed, expressive)
- ✅ Artifact tracking at each step
- ✅ Full lineage provenance

---

### Example 3: MCP Server (`mcp_example.py`)

**What it shows:** Process isolation via MCP protocol.

```python
from data_agent_sdk.transport.subprocess import SubprocessTransport

async with SubprocessTransport([
    "uv", "run", "--no-project", "python",
    "mcp_server_standalone.py", "--db", "/tmp/sales.db"
]) as transport:
    # List tools
    tools = await transport.list_tools()

    # Call tool via JSON-RPC
    result = await transport.call_tool("run_sql", {"sql": "SELECT * FROM sales"})
```

**Why MCP?**
- ✅ Process isolation (tools can't crash your agent)
- ✅ Language-agnostic (wrap any CLI: dbt, spark-submit)
- ✅ Scalable (tools can run on different machines)

---

## 🏗️ Architecture

### Simple SDK Architecture

```
┌─────────────────────────────────────────┐
│           DataAgent                     │
│  ┌────────────────────────────────┐    │
│  │  query("SELECT * FROM sales")  │    │
│  └────────────┬───────────────────┘    │
│               │                         │
│  ┌────────────▼───────────────────┐    │
│  │  Pre-Tool Hooks (Governance)   │    │
│  │  • Check access                 │    │
│  │  • Throttle                     │    │
│  └────────────┬───────────────────┘    │
│               │                         │
│  ┌────────────▼───────────────────┐    │
│  │  run_sql(sql="SELECT...")      │    │
│  │  → Returns Artifact            │    │
│  └────────────┬───────────────────┘    │
│               │                         │
│  ┌────────────▼───────────────────┐    │
│  │  Post-Tool Hooks (Lineage)     │    │
│  │  • Log execution                │    │
│  │  • Track artifacts              │    │
│  └────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

### MCP Server Architecture

```
┌──────────────┐   JSON-RPC    ┌──────────────────┐
│   Agent      │──(stdin/out)──│   MCP Server     │
│              │               │  (subprocess)    │
│ SubProcess   │               │                  │
│ Transport    │               │  ┌────────────┐  │
│              │               │  │ run_sql    │  │
│              │               │  │ read_meta  │  │
└──────────────┘               │  └────────────┘  │
                               └──────────────────┘
```

---

## 🛠️ Core Concepts

### 1. Tools = Functions that do work

```python
async def run_sql(sql: str, session_context: SessionContext) -> Artifact:
    """Execute SQL and return results as Parquet."""
    conn = duckdb.connect(session_context.warehouse)
    result = conn.execute(sql).pl()
    path = f"/tmp/query_{uuid4()}.parquet"
    result.write_parquet(path)

    return Artifact(
        uri=path,
        format="parquet",
        schema={col: str(dtype) for col, dtype in result.schema.items()},
        row_count=len(result),
        lineage={"query": sql, "tool": "run_sql"}
    )
```

**Tools included:**
- `run_sql()` - Execute SQL query → Parquet
- `read_metadata()` - Get table schema + row count
- `run_polars()` - Execute Polars operations
- `transform_csv()` - Clean CSV → Parquet
- `join_datasets()` - Join two datasets
- `aggregate_data()` - Group by + aggregate

---

### 2. Hooks = Policies that run before/after tools

**Pre-tool hooks (governance):**
```python
async def check_access(tool_use: ToolUseMessage, context: SessionContext):
    if tool_use.tool_input.get("table") == "finance.salaries":
        if context.role != "finance":
            return {"permission": "deny", "reason": "Unauthorized"}
    return {"permission": "allow"}
```

**Post-tool hooks (lineage):**
```python
async def log_lineage(tool_result: ToolResultMessage, context: SessionContext):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "user": context.user,
        "output": tool_result.artifact.uri,
        "rows": tool_result.artifact.row_count
    }
    with open("/tmp/lineage.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")
```

---

### 3. Session Context = User identity + environment

```python
@dataclass
class SessionContext:
    warehouse: str      # "duckdb:///tmp/sales.db"
    user: str           # "alice@company.com"
    role: str           # "analyst" or "admin"
    catalog_uri: str    # Optional: external catalog API
```

Passed to every tool and hook. **No global state.**

---

### 4. Artifacts = Structured outputs with lineage

```python
@dataclass
class Artifact:
    uri: str                    # Where output is stored
    format: str                 # "parquet", "csv", "json"
    schema: Dict[str, str]      # Column name → type
    row_count: int              # Number of rows
    lineage: Dict[str, Any]     # How this was created
```

Every tool returns an Artifact. Hooks can inspect/log them.

---

## 📁 Project Structure

```
data-agent-sdk/
├── README.md                       # This file
├── Makefile                        # Build commandsƒ
├── pyproject.toml                  # Package config
│
├── simple_example.py               # SQL example
├── polars_pipeline_example.py      # Polars pipeline (⭐ BEST DEMO)
├── mcp_example.py                  # MCP server example
├── mcp_server_standalone.py        # Standalone MCP server
│
├── src/data_agent_sdk/
│   ├── types.py                    # Core types
│   ├── agents/base.py              # DataAgent
│   ├── tools/
│   │   ├── sql.py                  # SQL tools
│   │   └── polars_tool.py          # Polars tools
│   ├── hooks/
│   │   ├── governance.py           # Pre-tool: access control
│   │   └── lineage.py              # Post-tool: logging
│   ├── transport/
│   │   └── subprocess.py           # MCP subprocess transport
│   └── cli.py                      # CLI interface
│
└── tests/
    └── test_tools.py
```

**Total:** ~2,000 lines of code. You can read it all in an afternoon.

---

## 🎓 Why This SDK?

### Comparison with LangChain/AutoGen/CrewAI

| Feature | This SDK | LangChain | AutoGen |
|---------|----------|-----------|---------|
| **Lines of code** | 2,000 | 100,000+ | 50,000+ |
| **Focus** | Data engineering | General AI chains | Multi-agent chat |
| **Governance** | Built-in hooks | Plugin | External |
| **Lineage** | First-class | Not included | Not included |
| **MCP support** | Native | No | No |
| **Polars tools** | Yes | No | No |
| **Learning curve** | Read in 1 afternoon | Weeks | Weeks |

**This SDK is:**
- ✅ **Educational** - Shows you how agents actually work
- ✅ **Minimal** - No 10-layer abstractions
- ✅ **Data-focused** - Built for data eng, not chatbots
- ✅ **Production patterns** - Hooks, context, artifacts from day 1

**This SDK is NOT:**
- ❌ A batteries-included framework
- ❌ Trying to do everything
- ❌ Hiding implementation details

---

## 🚦 When to Use This

### ✅ Use this SDK if you want to:
- Build data transformation agents
- Learn how agent frameworks work
- Add governance/lineage to data tools
- Wrap CLI tools (dbt, spark-submit) as agents
- Build real data pipelines with Polars
- Prototype quickly without framework bloat

### ❌ Don't use this if you need:
- Pre-built LLM integration (add it yourself via Claude API)
- Complex multi-agent orchestration
- Production-ready everything (this is a learning SDK)
- Vector databases, RAG, embeddings (out of scope)

---

## 🔧 How to Extend

### Add a New Tool

```python
# src/data_agent_sdk/tools/csv_tool.py
async def transform_csv(input_path: str, output_path: str,
                       session_context: SessionContext) -> Artifact:
    import polars as pl
    df = pl.read_csv(input_path).filter(pl.col("revenue") > 100)
    df.write_parquet(output_path)

    return Artifact(uri=output_path, format="parquet", ...)

# Register it
agent.register_tool(transform_csv)
```

### Add a New Hook

```python
# src/data_agent_sdk/hooks/governance.py
async def throttle(tool_use: ToolUseMessage, context: SessionContext):
    if call_count[context.user] > 100:
        return {"permission": "deny", "reason": "Quota exceeded"}
    return {"permission": "allow"}

PRE_TOOL_USE_HOOKS = [check_access, throttle]
```

---

## 🔍 MCP Server Protocol

The MCP server speaks JSON-RPC 2.0 over stdio.

### Test Manually

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | \
  uv run --no-project python mcp_server_standalone.py --db /tmp/sales.db
```

**Response:**
```json
{
  "jsonrpc":"2.0",
  "id":1,
  "result":{
    "tools":[
      {"name":"run_sql","description":"Execute SQL query"},
      {"name":"read_metadata","description":"Read table metadata"}
    ]
  }
}
```

### Architecture Comparison

| Feature | Simple SDK | MCP Server |
|---------|-----------|------------|
| **Tool execution** | Direct Python call | Subprocess + JSON-RPC |
| **Process** | Single process | Multi-process |
| **Isolation** | None | Full process isolation |
| **Latency** | ~10ms | ~50ms (IPC overhead) |
| **Use case** | Fast prototyping | Production isolation |

---

## 📚 How It Works (Under the Hood)

### Agent Query Flow

```python
# User calls:
async for msg in agent.query("SELECT * FROM sales"):
    print(msg)

# What happens:
1. Parse prompt → ToolUseMessage(tool_name="run_sql", ...)
2. Run PRE hooks → check_access() → allow/deny
3. Execute tool → run_sql() → Artifact
4. Run POST hooks → log_lineage()
5. Yield result
```

**Key insight:** It's just a **message loop** with hooks. No magic.

### MCP Transport Flow

```python
# User calls:
result = await transport.call_tool("run_sql", {"sql": "SELECT..."})

# What happens:
1. Write JSON-RPC to subprocess stdin
2. MCP server reads, executes tool
3. MCP server writes result to stdout
4. Transport reads, parses, returns
```

**Key insight:** It's just **JSON-RPC over stdin/stdout**. Simple IPC.

---

## 🎯 Real-World Use Cases

### 1. SQL Analytics Agent
- User asks: "Show me top products by revenue"
- Agent parses → runs SQL → governance checks → returns Parquet
- **Value:** Governed, auditable analytics

### 2. Polars Data Pipeline
- Clean CSV → filter → join → aggregate → export
- Each step tracked with lineage
- **Value:** Reproducible data transformations

### 3. DBT Pipeline Agent
- Wrap dbt as MCP server
- Agent calls: `trigger_dbt("dbt run --select model_name")`
- **Value:** Orchestrate dbt from natural language

### 4. Data Quality Agent
- Agent runs validation queries
- Governance prevents writes to prod
- **Value:** Automated validation with guardrails

---

## 🛡️ Governance & Security

### Access Control

```python
async def check_access(tool_use: ToolUseMessage, context: SessionContext):
    dataset = tool_use.tool_input.get("table")
    if dataset and dataset.startswith("finance."):
        if context.role != "finance":
            return {"permission": "deny", "reason": "Unauthorized"}
    return {"permission": "allow"}
```

### Audit Logging

```python
async def log_lineage(tool_result: ToolResultMessage, context: SessionContext):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "user": context.user,
        "output": tool_result.artifact.uri,
    }
    with open("/var/log/agent-audit.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")
```

**Value:** Every query is logged with full context.

---

## 📈 Performance

| Architecture | Latency | Throughput | Isolation |
|--------------|---------|------------|-----------|
| Simple SDK   | ~10ms   | 1000+ q/s  | None      |
| MCP Server   | ~50ms   | 100+ q/s   | Full      |

**When to use MCP:** Production, untrusted tools, CLI wrappers.

---

## 🚀 What's Next?

### Add LLM Integration

Replace `_parse_prompt()` with Claude API:

```python
import anthropic

def _parse_prompt(self, prompt: str) -> ToolUseMessage:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        messages=[{"role": "user", "content": prompt}],
        tools=[...],  # Tool schemas
    )
    # Extract tool_use from response
    return ToolUseMessage(...)
```

### Add More Tools

Extend the SDK with:
- `trigger_dbt()` - Run dbt models
- `write_table()` - Write Parquet → database
- `validate_data()` - Data quality checks
- `call_api()` - External API integration

---

## 🎓 5-Minute Tutorial

```python
import asyncio
from data_agent_sdk.agents.base import DataAgent
from data_agent_sdk.tools.sql import run_sql
from data_agent_sdk.types import SessionContext

async def main():
    agent = DataAgent(
        allowed_tools=["run_sql"],
        session_context=SessionContext(
            warehouse="duckdb:///tmp/mydata.db",
            user="you@company.com",
            role="analyst"
        )
    )
    agent.register_tool(run_sql)

    async for msg in agent.query("SELECT 1 as test"):
        print(msg)

asyncio.run(main())
```

**Congrats! You just:**
- ✅ Created an agent
- ✅ Executed a query
- ✅ Got lineage tracking (check `/tmp/lineage.jsonl`)

---

## 💡 Summary

**You just learned how agent frameworks actually work:**

1. **Tools** = Functions that return structured outputs (Artifacts)
2. **Hooks** = Policies that run before/after tools (governance + lineage)
3. **Session Context** = User identity passed everywhere (no globals)
4. **MCP Servers** = Tools in subprocesses (JSON-RPC over stdio)
5. **Agents** = Orchestrators that wire it all together

**Total code:** ~2,000 lines. Read it all. Understand it. Extend it.

**Now go build something.** 🚀

---

## 📖 Additional Resources

- **MCP Protocol:** https://modelcontextprotocol.io
- **Polars Docs:** https://pola.rs

---

## 📄 License

MIT - Do whatever you want with this.

---

## 🙏 Acknowledgments

Inspired by:
- [Claude Agent SDK](https://github.com/anthropics/anthropic-sdk-python) - Architecture patterns
- [Model Context Protocol](https://modelcontextprotocol.io) - MCP specification
- [Polars](https://pola.rs) - Fast DataFrame library

---
