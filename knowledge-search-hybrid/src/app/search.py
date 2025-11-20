import pathlib
from typing import Dict, List, Tuple

import hnswlib
import orjson
import tantivy
from fastembed import TextEmbedding

from .config import AppConfig
from .schema import build_schema


class HybridSearcher:
    def __init__(self, config: AppConfig):
        self.config = config
        self.schema, self.field_types = build_schema(config)
        self.index_dir = pathlib.Path(config.storage.index_dir)
        if not self.index_dir.exists():
            raise FileNotFoundError(
                f"Lexical index not found at {self.index_dir}. Run ETL + indexing first."
            )

        self.index = tantivy.Index(self.schema, path=str(self.index_dir))
        self.index.reload()
        self.searcher = self.index.searcher()
        self.text_fields = [f.name for f in config.lexical.fields if f.type == "text"]

        self.vector = hnswlib.Index(space="cosine", dim=config.embedding.dimensions)
        self.vector.load_index(str(config.storage.vector_store))

        doc_store_path = pathlib.Path(config.storage.doc_store)
        if not doc_store_path.exists():
            raise FileNotFoundError(f"Doc store missing at {doc_store_path}")
        self.doc_store = self._load_doc_store(doc_store_path)

        self.embedder = TextEmbedding(
            model_name=config.embedding.model,
            batch_size=config.embedding.batch_size,
            normalize=config.embedding.normalize,
        )

    def _load_doc_store(self, path: pathlib.Path) -> Dict[int, dict]:
        with path.open("rb") as f:
            docs = orjson.loads(f.read())
        return {int(doc[self.config.data.id_field]): doc for doc in docs}

    def _lexical(self, query: str) -> List[Tuple[int, float]]:
        parsed = self.index.parse_query(query, self.text_fields)
        top_docs = self.searcher.search(parsed, self.config.hybrid.bm25_k)
        scored = []
        for score, address in top_docs.hits:
            doc = self.searcher.doc(address)
            doc_id_value = doc.get_first(self.config.data.id_field)
            if doc_id_value is None:
                continue
            doc_id = int(doc_id_value)
            scored.append((doc_id, float(score)))
        return scored

    def _semantic(self, query: str) -> List[Tuple[int, float]]:
        vector = next(self.embedder.embed([query]))
        k = min(self.config.hybrid.knn_k, self.vector.get_current_count())
        if k == 0:
            return []
        self.vector.set_ef(max(50, k * 2))
        labels, distances = self.vector.knn_query(vector, k=k)
        results: List[Tuple[int, float]] = []
        for label, distance in zip(labels[0], distances[0]):
            # HNSW returns cosine distance; convert to similarity where higher is better
            similarity = 1.0 - float(distance)
            results.append((int(label), similarity))
        return results

    def _fuse(self, lexical: List[Tuple[int, float]], semantic: List[Tuple[int, float]]) -> List[dict]:
        k = self.config.hybrid.fusion.k
        lex_weight = self.config.hybrid.fusion.lexical_weight
        sem_weight = self.config.hybrid.fusion.semantic_weight

        def score_block(block: List[Tuple[int, float]], weight: float) -> Dict[int, float]:
            scores: Dict[int, float] = {}
            for rank, (doc_id, _) in enumerate(block, start=1):
                scores[doc_id] = scores.get(doc_id, 0.0) + weight * (1.0 / (k + rank))
            return scores

        total = score_block(lexical, lex_weight)
        semantic_scores = score_block(semantic, sem_weight)
        for doc_id, score in semantic_scores.items():
            total[doc_id] = total.get(doc_id, 0.0) + score

        ranked = sorted(total.items(), key=lambda item: item[1], reverse=True)
        results = []
        for doc_id, score in ranked:
            doc = self.doc_store.get(doc_id)
            if not doc:
                continue
            results.append(
                {"doc_id": doc_id, "score": score, "document": doc},
            )
        return results

    def search(self, query: str) -> List[dict]:
        lexical_hits = self._lexical(query)
        semantic_hits = self._semantic(query)
        return self._fuse(lexical_hits, semantic_hits)

    def autocomplete(self, prefix: str, limit: int = 5) -> List[str]:
        if len(prefix) < self.config.autocomplete.min_chars:
            return []

        lower_prefix = prefix.lower()
        suggestions = []
        for doc in self.doc_store.values():
            for field in self.config.autocomplete.fields:
                value = doc.get(field)
                if isinstance(value, str) and value.lower().startswith(lower_prefix):
                    suggestions.append(value)
        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for s in suggestions:
            if s not in seen:
                deduped.append(s)
                seen.add(s)
        return deduped[:limit]
