"""
MCP Server Example - Complete Demo

This demonstrates the ACTUAL MCP architecture:
1. MCP Server runs as a subprocess (exposes tools via stdio)
2. SubprocessTransport communicates with it (JSON-RPC)
3. Agent uses transport instead of calling tools directly

This is the "800 lines" pattern mentioned in the blog post.
"""

import asyncio
import sys
import duckdb
from pathlib import Path

sys.path.insert(0, 'src')

from data_agent_sdk.transport.subprocess import SubprocessTransport


async def setup_database():
    """Create a sample sales database."""
    db_path = "/tmp/sales.db"
    conn = duckdb.connect(db_path)

    conn.execute("DROP TABLE IF EXISTS sales")
    conn.execute("""
        CREATE TABLE sales (
            id INTEGER,
            product VARCHAR,
            revenue DECIMAL,
            region VARCHAR
        )
    """)

    conn.execute("""
        INSERT INTO sales VALUES
        (1, 'Laptop', 1200, 'North'),
        (2, 'Mouse', 25, 'South'),
        (3, 'Keyboard', 75, 'East'),
        (4, 'Monitor', 300, 'West')
    """)

    conn.close()
    print(f"✓ Database created at {db_path}\n")
    return db_path


async def main():
    # Setup database
    db_path = await setup_database()

    print("=" * 60)
    print("MCP SERVER EXAMPLE - SubprocessTransport")
    print("=" * 60)

    # Start MCP server as subprocess
    mcp_command = [
        "uv", "run", "--no-project", "python",
        "mcp_server_standalone.py",
        "--db", db_path
    ]

    print(f"\n[1] Starting MCP Server...")
    print(f"    Command: {' '.join(mcp_command)}")

    async with SubprocessTransport(mcp_command) as transport:
        print("    ✓ MCP Server started\n")

        # List available tools
        print("[2] Listing available tools from MCP server:")
        print("-" * 60)
        tools = await transport.list_tools()
        for tool in tools:
            print(f"  • {tool['name']}: {tool['description']}")
        print()

        # Call run_sql tool
        print("[3] Calling tool: run_sql")
        print("-" * 60)
        result = await transport.call_tool(
            "run_sql",
            {"sql": "SELECT * FROM sales"}
        )
        print(f"  ✓ Query executed")
        print(f"    - Output: {result['uri']}")
        print(f"    - Rows: {result['row_count']}")
        print(f"    - Schema: {result['schema']}")
        print()

        # Call read_metadata tool
        print("[4] Calling tool: read_metadata")
        print("-" * 60)
        result = await transport.call_tool(
            "read_metadata",
            {"table": "sales"}
        )
        print(f"  ✓ Metadata retrieved")
        print(f"    - Table: {result['table']}")
        print(f"    - Rows: {result['row_count']}")
        print(f"    - Schema: {result['schema']}")
        print()

        # Aggregation
        print("[5] Calling tool: run_sql (aggregation)")
        print("-" * 60)
        result = await transport.call_tool(
            "run_sql",
            {"sql": "SELECT region, SUM(revenue) as total FROM sales GROUP BY region"}
        )
        print(f"  ✓ Aggregation completed")
        print(f"    - Output: {result['uri']}")
        print(f"    - Rows: {result['row_count']}")
        print()

    print("=" * 60)
    print("MCP Server stopped")
    print("=" * 60)
    print("\n✅ This is the REAL MCP architecture:")
    print("   - Server runs as subprocess (stdio communication)")
    print("   - Transport wraps subprocess communication")
    print("   - Agent calls transport instead of tools directly")
    print("\nCompare this to simple_example.py which calls tools directly!")


if __name__ == "__main__":
    asyncio.run(main())
