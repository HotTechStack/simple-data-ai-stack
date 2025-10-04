#!/usr/bin/env python3
"""
Standalone MCP Server for Data Tools

This runs as a separate process and communicates via JSON-RPC over stdin/stdout.
No imports from data_agent_sdk to avoid circular import issues.
"""

import sys
import json
import asyncio
from pathlib import Path
from uuid import uuid4
import tempfile
import duckdb


class MCPServer:
    """MCP Server for data tools."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path

    def run_sql(self, sql: str) -> dict:
        """Execute SQL query."""
        conn = duckdb.connect(self.db_path)
        try:
            result = conn.execute(sql).pl()
            path = Path(tempfile.gettempdir()) / f"query_{uuid4()}.parquet"
            result.write_parquet(path)

            return {
                "uri": str(path),
                "format": "parquet",
                "schema": {col: str(dtype) for col, dtype in result.schema.items()},
                "row_count": len(result),
            }
        finally:
            conn.close()

    def read_metadata(self, table: str) -> dict:
        """Read table metadata."""
        conn = duckdb.connect(self.db_path)
        try:
            schema = conn.execute(f"DESCRIBE {table}").fetchall()
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            return {
                "table": table,
                "schema": {row[0]: row[1] for row in schema},
                "row_count": count,
            }
        finally:
            conn.close()

    def handle_request(self, request: dict) -> dict:
        """Handle MCP request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "tools/list":
                # List available tools
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": [
                            {
                                "name": "run_sql",
                                "description": "Execute SQL query",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "sql": {"type": "string"}
                                    },
                                    "required": ["sql"]
                                }
                            },
                            {
                                "name": "read_metadata",
                                "description": "Read table metadata",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "table": {"type": "string"}
                                    },
                                    "required": ["table"]
                                }
                            }
                        ]
                    }
                }

            elif method == "tools/call":
                # Execute tool
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})

                if tool_name == "run_sql":
                    result = self.run_sql(**tool_args)
                elif tool_name == "read_metadata":
                    result = self.read_metadata(**tool_args)
                else:
                    raise ValueError(f"Unknown tool: {tool_name}")

                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result)
                            }
                        ]
                    }
                }

            else:
                raise ValueError(f"Unknown method: {method}")

        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }

    def run(self):
        """Run MCP server (stdio mode)."""
        # Log to stderr (stdout is for MCP protocol)
        sys.stderr.write(f"MCP Server started (db={self.db_path})\n")
        sys.stderr.flush()

        # Read requests from stdin, write responses to stdout
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                request = json.loads(line)
                response = self.handle_request(request)

                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except json.JSONDecodeError as e:
                sys.stderr.write(f"Invalid JSON: {e}\n")
                sys.stderr.flush()
            except Exception as e:
                sys.stderr.write(f"Error: {e}\n")
                sys.stderr.flush()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MCP Server for data tools")
    parser.add_argument("--db", default=":memory:", help="Database path")
    args = parser.parse_args()

    server = MCPServer(db_path=args.db)
    server.run()
