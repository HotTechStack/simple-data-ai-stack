import json
import pathlib
import shutil
from typing import Iterable, List

import hnswlib
import orjson
import polars as pl
import tantivy
from fastembed import TextEmbedding

from .config import AppConfig, load_config
from .schema import build_schema


class Indexer:
    def __init__(self, config: AppConfig):
        self.config = config
        self.schema, self.field_types = build_schema(config)
        self.index_dir = pathlib.Path(config.storage.index_dir)
        self.doc_store_path = pathlib.Path(config.storage.doc_store)
        self.vector_path = pathlib.Path(config.storage.vector_store)

    def _load_docs(self) -> List[dict]:
        path = pathlib.Path(self.config.data.processed_jsonl)
        if not path.exists():
            raise FileNotFoundError(f"Processed JSONL missing, run ETL first: {path}")
        df = pl.read_ndjson(path)
        return df.to_dicts()

    def _build_lexical(self, docs: Iterable[dict]) -> tantivy.Index:
        if self.index_dir.exists():
            shutil.rmtree(self.index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        index = tantivy.Index(self.schema, path=str(self.index_dir))
        writer = index.writer()

        for doc in docs:
            tdoc = tantivy.Document()
            for field in self.config.lexical.fields:
                value = doc.get(field.name)
                if value is None:
                    continue
                if field.type == "text":
                    if isinstance(value, list):
                        for v in value:
                            tdoc.add_text(field.name, str(v))
                    else:
                        tdoc.add_text(field.name, str(value))
                elif field.type == "u64":
                    tdoc.add_u64(field.name, int(value))
                elif field.type == "i64":
                    tdoc.add_i64(field.name, int(value))
                elif field.type == "f64":
                    tdoc.add_f64(field.name, float(value))
                elif field.type == "bool":
                    tdoc.add_bool(field.name, bool(value))
                elif field.type == "json":
                    payload = {"values": value} if isinstance(value, list) else value
                    tdoc.add_json(field.name, json.dumps(payload))
                else:
                    raise ValueError(f"Unsupported field type: {field.type}")
            writer.add_document(tdoc)
        writer.commit()
        index.reload()
        return index

    def _build_vector(self, docs: List[dict]) -> hnswlib.Index:
        embedder = TextEmbedding(
            model_name=self.config.embedding.model,
            batch_size=self.config.embedding.batch_size,
            normalize=self.config.embedding.normalize,
        )
        text_to_encode = [
            f"{doc.get('title', '')}. {doc.get('body', '')} {' '.join(doc.get('tags', []) or [])}"
            for doc in docs
        ]
        vectors = list(embedder.embed(text_to_encode))

        index = hnswlib.Index(space="cosine", dim=self.config.embedding.dimensions)
        index.init_index(
            max_elements=len(vectors),
            ef_construction=200,
            M=16,
        )
        labels = [int(doc[self.config.data.id_field]) for doc in docs]
        index.add_items(vectors, labels)
        self.vector_path.parent.mkdir(parents=True, exist_ok=True)
        index.save_index(str(self.vector_path))
        return index

    def _persist_doc_store(self, docs: List[dict]) -> None:
        self.doc_store_path.parent.mkdir(parents=True, exist_ok=True)
        with self.doc_store_path.open("wb") as f:
            f.write(orjson.dumps(docs))

    def rebuild(self) -> None:
        docs = self._load_docs()
        lexical_index = self._build_lexical(docs)
        self._build_vector(docs)
        self._persist_doc_store(docs)
        print(f"Indexed {len(docs)} docs into {self.index_dir}")
        print(f"Lexical schema fields: {list(self.field_types.keys())}")


def rebuild(config_path: str | pathlib.Path = None) -> None:
    cfg = load_config(config_path or pathlib.Path(__file__).resolve().parents[2] / "config" / "search_config.yaml")
    Indexer(cfg).rebuild()


if __name__ == "__main__":
    rebuild()
