import asyncio
import pathlib
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from .config import load_config
from .etl import run_etl
from .indexer import Indexer
from .rag import RagResponder
from .search import HybridSearcher


CONFIG_PATH = pathlib.Path(__file__).resolve().parents[2] / "config" / "search_config.yaml"

app = FastAPI(title="Hybrid Knowledge Search", version="0.1.0")


def _bootstrap_searcher() -> HybridSearcher:
    cfg = load_config(CONFIG_PATH)
    return HybridSearcher(cfg)


@app.on_event("startup")
async def startup_event() -> None:
    app.state.config = load_config(CONFIG_PATH)
    try:
        app.state.searcher = HybridSearcher(app.state.config)
    except FileNotFoundError:
        # Index missing; user should trigger ETL + index build
        app.state.searcher = None
    app.state.rag = RagResponder()


@app.get("/health")
async def health() -> dict:
    ready = app.state.searcher is not None
    return {"status": "ok", "search_ready": ready}


@app.post("/etl-and-index")
async def etl_and_index() -> dict:
    cfg = app.state.config
    path = run_etl(CONFIG_PATH)
    Indexer(cfg).rebuild()
    app.state.searcher = HybridSearcher(cfg)
    return {"status": "indexed", "processed_path": str(path)}


@app.get("/search")
async def search(q: str = Query(..., description="Query string")) -> dict:
    searcher: Optional[HybridSearcher] = app.state.searcher
    if searcher is None:
        raise HTTPException(status_code=400, detail="Search index not ready. Run /etl-and-index first.")
    results = searcher.search(q)
    return {"query": q, "results": results}


@app.get("/autocomplete")
async def autocomplete(prefix: str = Query(..., description="Prefix to complete"), limit: int = 5) -> dict:
    searcher: Optional[HybridSearcher] = app.state.searcher
    if searcher is None:
        raise HTTPException(status_code=400, detail="Search index not ready. Run /etl-and-index first.")
    suggestions = searcher.autocomplete(prefix, limit=limit)
    return {"prefix": prefix, "suggestions": suggestions}


@app.get("/rag")
async def rag(q: str) -> JSONResponse:
    searcher: Optional[HybridSearcher] = app.state.searcher
    if searcher is None:
        raise HTTPException(status_code=400, detail="Search index not ready. Run /etl-and-index first.")
    results = searcher.search(q)
    top_docs = results[:3]
    responder: RagResponder = app.state.rag
    answer = await responder.answer(q, top_docs)
    return JSONResponse({"query": q, "answer": answer, "sources": top_docs})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
