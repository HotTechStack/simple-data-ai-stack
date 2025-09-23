# ================================================================
# FILE 2: notebooks/02_validate_kg.py
# ================================================================

import marimo

__generated_with = "0.16.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import sys
    import json
    import os
    import traceback
    sys.path.append('/app')
    from src.indexer import index_documents
    from src.validator import validate_knowledge_graph
    return index_documents, json, mo, os, traceback, validate_knowledge_graph


@app.cell
def _(mo):
    mo.md("""# 🔍 Validate Knowledge Graph""")
    return


@app.cell
def _(mo):
    mo.md("""## Step 1: Loading documents...""")
    return


@app.cell
def _(json, mo, os, traceback):
    docs_dir = "/app/data/documents"

    if not os.path.exists(docs_dir):
        load_msg = mo.md("❌ Run `01_snapshot.py` first!")
        loaded_docs = []
        docs_loaded = False
    else:
        try:
            loaded_docs = []
            json_files = [f for f in os.listdir(docs_dir) if f.endswith('.json')]

            for json_file in json_files:
                with open(os.path.join(docs_dir, json_file)) as f:
                    docs = json.load(f)
                    loaded_docs.extend(docs)

            load_msg = mo.md(f"✅ Loaded {len(loaded_docs)} documents")
            docs_loaded = True
        except Exception as e:
            load_msg = mo.md(f"❌ **Error:** ```{traceback.format_exc()}```")
            loaded_docs = []
            docs_loaded = False

    load_msg
    return docs_loaded, loaded_docs


@app.cell
def _(mo):
    mo.md("---")
    mo.md("## Step 2: Indexing into LightRAG...")
    return


@app.cell
def _(docs_loaded, index_documents, loaded_docs, mo, os, traceback):
    storage_dir = "/app/data/lightrag"
    os.makedirs(storage_dir, exist_ok=True)

    if not docs_loaded:
        index_msg = mo.md("⚠️ No documents to index")
        rag_instance = None
        indexing_done = False
    else:
        try:
            rag_instance = index_documents(loaded_docs, storage_dir)
            index_msg = mo.md(f"✅ Indexed {len(loaded_docs)} documents")
            indexing_done = True
        except Exception as e:
            index_msg = mo.md(f"❌ **Error:** ```{traceback.format_exc()}```")
            rag_instance = None
            indexing_done = False

    index_msg
    return indexing_done, rag_instance


@app.cell
def _(mo):
    mo.md("---")
    mo.md("## Step 3: Validating knowledge graph...")
    return


@app.cell
def _(indexing_done, mo, rag_instance, traceback, validate_knowledge_graph):
    if not indexing_done:
        validation_msg = mo.md("⚠️ Indexing failed")
    else:
        try:
            results = validate_knowledge_graph(rag_instance)
            validation_msg = mo.md(f"""
            ✅ **Validation Complete!**

            - Entities: {results['entity_count']}
            - Relations: {results['relation_count']}
            - Orphans: {len(results['orphan_nodes'])}
            - Accuracy: {results['extraction_accuracy']:.1%}

            ➡️ Next: Open `03_test_agent.py`
            """)
        except Exception as e:
            validation_msg = mo.md(f"❌ **Error:** ```{traceback.format_exc()}```")

    validation_msg
    return


if __name__ == "__main__":
    app.run()
