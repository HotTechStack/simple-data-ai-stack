import asyncio
import click
from .agents.base import DataAgent
from .tools import sql
from .types import SessionContext

@click.group()
def main():
    pass

@main.command()
@click.argument("prompt")
def run(prompt: str):
    asyncio.run(_run_agent(prompt))

async def _run_agent(prompt: str):
    agent = DataAgent(allowed_tools=["run_sql", "read_metadata"],
        session_context=SessionContext(warehouse="duckdb:///:memory:", user="cli", role="analyst"))
    agent.register_tool(sql.run_sql)
    agent.register_tool(sql.read_metadata)
    async for msg in agent.query(prompt):
        print(msg)

if __name__ == "__main__":
    main()