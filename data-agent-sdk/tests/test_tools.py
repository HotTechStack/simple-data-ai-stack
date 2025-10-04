import pytest
import sys
sys.path.insert(0, 'src')
from data_agent_sdk.tools.sql import run_sql
from data_agent_sdk.types import Artifact

@pytest.mark.asyncio
async def test_run_sql():
    result = await run_sql("SELECT 1 as num")
    assert isinstance(result, Artifact)
    assert "num" in result.schema