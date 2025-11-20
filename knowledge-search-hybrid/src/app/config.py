import pathlib
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


FieldType = Literal["text", "u64", "i64", "f64", "bool", "json"]


class FieldConfig(BaseModel):
    name: str
    type: FieldType
    stored: bool = True


class FusionConfig(BaseModel):
    k: int = 60
    lexical_weight: float = 0.5
    semantic_weight: float = 0.5


class HybridConfig(BaseModel):
    bm25_k: int = 10
    knn_k: int = 10
    fusion: FusionConfig = FusionConfig()


class LexicalConfig(BaseModel):
    analyzer: str = "default"
    fields: List[FieldConfig]


class EmbeddingConfig(BaseModel):
    model: str
    dimensions: int
    batch_size: int = 32
    normalize: bool = True


class StorageConfig(BaseModel):
    index_dir: str
    doc_store: str
    vector_store: str


class DataConfig(BaseModel):
    processed_jsonl: str
    id_field: str = "doc_id"


class AutocompleteConfig(BaseModel):
    fields: List[str]
    min_chars: int = 2


class AppConfig(BaseSettings):
    meta: Dict[str, Any]
    storage: StorageConfig
    data: DataConfig
    embedding: EmbeddingConfig
    lexical: LexicalConfig
    hybrid: HybridConfig
    autocomplete: AutocompleteConfig

    class Config:
        env_prefix = "SEARCH_"
        extra = "ignore"


def load_config(path: str | pathlib.Path) -> AppConfig:
    config_path = pathlib.Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return AppConfig(**raw)
