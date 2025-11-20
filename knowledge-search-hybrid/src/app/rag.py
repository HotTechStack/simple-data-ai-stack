import os
import re
from typing import List

import httpx


class RagResponder:
    def __init__(self):
        self.ollama_model = os.getenv("OLLAMA_MODEL")
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.openai_key = os.getenv("OPENAI_API_KEY")

    async def _ollama_available(self) -> bool:
        if not self.ollama_model:
            return False
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{self.ollama_host}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    async def _ollama_generate(self, query: str, context: str) -> str:
        payload = {
            "model": self.ollama_model,
            "prompt": f"Answer the query using only the provided context.\n\nQuery: {query}\nContext:\n{context}",
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(f"{self.ollama_host}/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "").strip()

    def _extractive_summary(self, query: str, snippets: List[str], limit: int = 3) -> str:
        # Fallback deterministic summarizer that keeps the most query-relevant sentences.
        text = " ".join(snippets)
        sentences = re.split(r"(?<=[.!?]) +", text)
        keywords = [kw.lower() for kw in query.split() if len(kw) > 2]
        scored = []
        for sent in sentences:
            score = sum(sent.lower().count(kw) for kw in keywords)
            scored.append((score, sent.strip()))
        top = [sent for score, sent in sorted(scored, key=lambda x: x[0], reverse=True) if sent][:limit]
        return "\n".join(f"- {sent}" for sent in top if sent)

    async def answer(self, query: str, docs: List[dict]) -> str:
        context = "\n".join(
            f"{d['document'].get('title')}: {d['document'].get('body')}" for d in docs
        )
        if await self._ollama_available():
            try:
                return await self._ollama_generate(query, context)
            except Exception:
                pass
        return self._extractive_summary(query, [d["document"].get("body", "") for d in docs])
