import asyncio
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
from lightrag.kg.shared_storage import initialize_pipeline_status

async def async_index_documents(documents: list, storage_dir: str):
    """Async version - Index documents into LightRAG"""
    
    rag = LightRAG(
        working_dir=storage_dir,
        embedding_func=openai_embed,
        llm_model_func=gpt_4o_mini_complete,
    )
    
    # Initialize in correct order (from the demo)
    await rag.initialize_storages()
    await initialize_pipeline_status()
    
    # Combine all documents into one text
    combined_text = "\n\n".join([doc["content"] for doc in documents])
    
    # Use ainsert (async insert)
    await rag.ainsert(combined_text)
    
    return rag

def index_documents(documents: list, storage_dir: str):
    """Synchronous wrapper for notebook usage"""
    
    try:
        loop = asyncio.get_running_loop()
        import nest_asyncio
        nest_asyncio.apply()
        return asyncio.run(async_index_documents(documents, storage_dir))
    except RuntimeError:
        return asyncio.run(async_index_documents(documents, storage_dir))

async def async_query_rag(rag: LightRAG, query: str, mode: str = "hybrid"):
    """Async query"""
    return await rag.aquery(query, param=QueryParam(mode=mode))

def query_rag(rag: LightRAG, query: str, mode: str = "hybrid"):
    """Synchronous wrapper"""
    try:
        loop = asyncio.get_running_loop()
        import nest_asyncio
        nest_asyncio.apply()
        return asyncio.run(async_query_rag(rag, query, mode))
    except RuntimeError:
        return asyncio.run(async_query_rag(rag, query, mode))