from typing import Dict

import tantivy

from .config import AppConfig, FieldConfig


def _add_field(builder: tantivy.SchemaBuilder, field: FieldConfig) -> None:
    if field.type == "text":
        builder.add_text_field(field.name, stored=field.stored)
    elif field.type == "u64":
        builder.add_u64_field(field.name, stored=field.stored)
    elif field.type == "i64":
        builder.add_i64_field(field.name, stored=field.stored)
    elif field.type == "f64":
        builder.add_f64_field(field.name, stored=field.stored)
    elif field.type == "bool":
        builder.add_bool_field(field.name, stored=field.stored)
    elif field.type == "json":
        builder.add_json_field(field.name, stored=field.stored)
    else:
        raise ValueError(f"Unsupported field type: {field.type}")


def build_schema(config: AppConfig) -> tuple[tantivy.Schema, Dict[str, str]]:
    builder = tantivy.SchemaBuilder()
    mapping: Dict[str, str] = {}

    for field in config.lexical.fields:
        _add_field(builder, field)
        mapping[field.name] = field.type

    return builder.build(), mapping
