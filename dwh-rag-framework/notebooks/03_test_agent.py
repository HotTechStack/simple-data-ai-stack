# ================================================================
# FILE 3: notebooks/03_test_agent.py
# ================================================================

import marimo

__generated_with = "0.16.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import sys
    import os
    import traceback
    sys.path.append('/app')
    from src.agent import TextToSQLAgent
    return TextToSQLAgent, mo, os, traceback


@app.cell
def _(mo):
    mo.md("""# 🤖 Test LLM Agent""")
    return


@app.cell
def _(mo):
    mo.md("""## Initializing agent...""")
    return


@app.cell
def _(TextToSQLAgent, mo, os, traceback):
    agent_snap_path = "/app/data/snapshots/warehouse.duckdb"

    if not os.path.exists(agent_snap_path):
        init_msg = mo.md("❌ Run `01_snapshot.py` first!")
        sql_agent = None
        agent_ready = False
    else:
        try:
            sql_agent = TextToSQLAgent(
                snapshot_path=agent_snap_path,
                fallback_conn_str="postgresql://user:password@postgres:5432/warehouse"
            )
            init_msg = mo.md("✅ Agent initialized!")
            agent_ready = True
        except Exception as e:
            init_msg = mo.md(f"❌ **Error:** ```{traceback.format_exc()}```")
            sql_agent = None
            agent_ready = False

    init_msg
    return agent_ready, sql_agent


@app.cell
def _(mo):
    mo.md("---")
    mo.md("## Ask a Question")
    return


@app.cell
def _(mo):
    query_input = mo.ui.text_area(
        label="Natural Language Query",
        value="How many customers do we have?"
    )
    query_input
    return (query_input,)


@app.cell
def _(agent_ready, mo, query_input, sql_agent, traceback):
    if not agent_ready:
        query_output = mo.md("⚠️ Agent not ready")
    elif not query_input.value:
        query_output = mo.md("⚠️ Enter a query above")
    else:
        try:
            result = sql_agent.query(query_input.value)

            if "error" in result:
                query_output = mo.md(f"⚠️ {result['error']}")
            else:
                query_output = mo.vstack([
                    mo.md(f"""
                    ✅ **Success!**

                    **SQL:**
                    ```sql
                    {result['sql']}
                    ```
                    """),
                    mo.ui.table(result['result'])
                ])
        except Exception as e:
            query_output = mo.md(f"❌ **Error:** ```{traceback.format_exc()}```")

    query_output
    return


if __name__ == "__main__":
    app.run()
