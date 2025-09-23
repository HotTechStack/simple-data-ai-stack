# ================================================================
# FILE 1: notebooks/01_snapshot.py
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
    from src.snapshot import create_snapshot
    from src.converter import convert_to_documents
    return convert_to_documents, create_snapshot, mo, os, traceback


@app.cell
def _(mo):
    mo.md("""# 📸 Create Data Warehouse Snapshot""")
    return


@app.cell
def _(mo):
    mo.md("""## Step 1: Creating snapshot...""")
    return


@app.cell
def _(create_snapshot, mo, os, traceback):
    pg_conn = "postgresql://user:password@postgres:5432/warehouse"
    snap_path = "/app/data/snapshots/warehouse.duckdb"
    os.makedirs("/app/data/snapshots", exist_ok=True)

    try:
        result_path = create_snapshot(pg_conn, snap_path)
        snapshot_msg = mo.md(f"""
        ✅ **Snapshot Created!**

        Path: `{result_path}`
        """)
        snap_success = True
    except Exception as e:
        snapshot_msg = mo.md(f"""
        ❌ **Error:**
        ```
        {str(e)}

        {traceback.format_exc()}
        ```
        """)
        snap_success = False

    snapshot_msg
    return snap_path, snap_success


@app.cell
def _(mo):
    mo.md("---")
    mo.md("## Step 2: Converting to documents...")
    return


@app.cell
def _(convert_to_documents, mo, os, snap_path, snap_success, traceback):
    docs_dir = "/app/data/documents"
    os.makedirs(docs_dir, exist_ok=True)

    if not snap_success:
        convert_msg = mo.md("⚠️ **Snapshot failed, skipping conversion**")
    else:
        try:
            doc_list = convert_to_documents(snap_path, docs_dir)
            convert_msg = mo.md(f"""
            ✅ **Documents Created!**

            Total: {len(doc_list)} documents

            ➡️ Next: Open `02_validate_kg.py`
            """)
        except Exception as e:
            convert_msg = mo.md(f"""
            ❌ **Error:**
            ```
            {str(e)}

            {traceback.format_exc()}
            ```
            """)

    convert_msg
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
