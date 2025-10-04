"""
Simple Data Agent Example - Working Demo

This demonstrates a minimal working data agent that:
1. Creates a sample database
2. Executes SQL queries
3. Applies governance hooks (access control)
4. Logs lineage automatically
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

from data_agent_sdk.agents.base import DataAgent
from data_agent_sdk.tools.sql import run_sql, read_metadata
from data_agent_sdk.types import SessionContext


async def setup_database():
    """Create a sample sales database."""
    import duckdb

    db_path = "/tmp/sales.db"
    conn = duckdb.connect(db_path)

    # Drop table if exists and create fresh
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
    # Setup
    db_path = await setup_database()

    # Create agent with session context
    agent = DataAgent(
        allowed_tools=["run_sql", "read_metadata"],
        session_context=SessionContext(
            warehouse=f"duckdb://{db_path}",
            user="analyst",
            role="analyst"
        )
    )

    # Register tools
    agent.register_tool(run_sql)
    agent.register_tool(read_metadata)

    print("=" * 60)
    print("DATA AGENT SDK - Simple Example")
    print("=" * 60)

    # Example 1: Run SQL Query
    print("\n[Example 1] Query all sales:")
    print("-" * 60)
    async for msg in agent.query("SELECT * FROM sales"):
        if msg["type"] == "result":
            result = msg["result"]
            print(f"✓ Query executed successfully")
            print(f"  - Output: {result['uri']}")
            print(f"  - Rows: {result['row_count']}")
            print(f"  - Schema: {result['schema']}")
        elif msg["type"] == "error":
            print(f"✗ Error: {msg.get('error', msg.get('message'))}")

    # Example 2: Read Metadata
    print("\n[Example 2] Read table metadata:")
    print("-" * 60)
    async for msg in agent.query("describe sales"):
        if msg["type"] == "result":
            result = msg["result"]
            print(f"✓ Metadata retrieved")
            print(f"  - Table: {result['table']}")
            print(f"  - Rows: {result['row_count']}")
            print(f"  - Schema: {result['schema']}")
        elif msg["type"] == "error":
            print(f"✗ Error: {msg.get('error', msg.get('message'))}")

    # Example 3: Aggregation Query
    print("\n[Example 3] Aggregate revenue by region:")
    print("-" * 60)
    async for msg in agent.query("SELECT region, SUM(revenue) as total FROM sales GROUP BY region"):
        if msg["type"] == "result":
            result = msg["result"]
            print(f"✓ Aggregation completed")
            print(f"  - Output: {result['uri']}")
            print(f"  - Rows: {result['row_count']}")
        elif msg["type"] == "error":
            print(f"✗ Error: {msg.get('error', msg.get('message'))}")

    # Check lineage log
    print("\n[Lineage] Check lineage log:")
    print("-" * 60)
    lineage_path = Path("/tmp/lineage.jsonl")
    if lineage_path.exists():
        with open(lineage_path) as f:
            lines = f.readlines()
            print(f"✓ {len(lines)} lineage entries logged")
            if lines:
                import json
                last_entry = json.loads(lines[-1])
                print(f"  Last entry: {last_entry}")
    else:
        print("  No lineage file found")

    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
