"""
Subprocess Transport for MCP Servers

This transport communicates with MCP servers running as subprocesses
via stdin/stdout (JSON-RPC protocol).
"""

import json
import asyncio
from typing import Any, Dict, List


class SubprocessTransport:
    """Transport for communicating with MCP server via subprocess."""

    def __init__(self, command: List[str]):
        """
        Initialize subprocess transport.

        Args:
            command: Command to start MCP server (e.g., ["python", "mcp_server.py", "--db", "/tmp/sales.db"])
        """
        self.command = command
        self.process = None
        self.request_id = 0

    async def start(self):
        """Start the MCP server subprocess."""
        self.process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # Give server time to start
        await asyncio.sleep(0.1)

    async def stop(self):
        """Stop the MCP server subprocess."""
        if self.process:
            self.process.terminate()
            await self.process.wait()

    async def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send JSON-RPC request to MCP server."""
        if not self.process:
            raise RuntimeError("Transport not started")

        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }

        # Write request
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()

        # Read response
        response_line = await self.process.stdout.readline()
        response = json.loads(response_line.decode())

        if "error" in response:
            raise RuntimeError(f"MCP Error: {response['error']}")

        return response.get("result", {})

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from MCP server."""
        result = await self.send_request("tools/list")
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server."""
        result = await self.send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })

        # Extract content from MCP response
        content = result.get("content", [])
        if content and content[0].get("type") == "text":
            return json.loads(content[0]["text"])

        return result

    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.stop()
