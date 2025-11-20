import pathlib
from datetime import datetime
from typing import Iterable

import polars as pl

from .config import AppConfig, load_config


RAW_DIR = pathlib.Path(__file__).resolve().parents[2] / "data" / "raw"


def _read_csv(name: str) -> pl.DataFrame:
    path = RAW_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing expected raw file: {path}")
    return pl.read_csv(path)


def build_processed_dataset(config: AppConfig) -> pathlib.Path:
    confluence = _read_csv("confluence_articles.csv").with_columns(
        pl.lit("confluence").alias("source"),
        pl.lit("internal-docs").alias("service"),
        pl.lit(["confluence", "how-to"]).alias("tags"),
    )

    github = _read_csv("github_docs.csv").with_columns(
        pl.lit("github").alias("source"),
        pl.lit("repos").alias("service"),
        pl.lit(["github", "runbook"]).alias("tags"),
        pl.col("path").alias("title"),
    )

    slack = _read_csv("slack_messages.csv").with_columns(
        pl.lit("slack").alias("source"),
        pl.lit("chat").alias("service"),
        pl.lit(["slack", "announcement"]).alias("tags"),
        pl.col("channel").alias("title"),
        pl.col("message").alias("body"),
        pl.col("created_at").alias("updated_at"),
        pl.col("user").alias("author"),
    )

    merged = pl.concat(
        [
            confluence.select("title", "body", "source", "service", "tags", "updated_at", "author"),
            github.select("title", "body", "source", "service", "tags", "updated_at", "author"),
            slack.select("title", "body", "source", "service", "tags", "updated_at", "author"),
        ],
        how="vertical",
    ).with_columns(
        pl.arange(1, pl.len() + 1).cast(pl.Int64).alias(config.data.id_field),
        pl.when(pl.col("updated_at").str.contains("-"))
        .then(pl.col("updated_at"))
        .otherwise(pl.lit(datetime.utcnow().strftime("%Y-%m-%d")))
        .alias("updated_at"),
        pl.col("tags").cast(pl.List(pl.Utf8)),
    )

    out_path = pathlib.Path(config.data.processed_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged.write_ndjson(out_path)
    return out_path


def run_etl(config_path: str | pathlib.Path = None) -> pathlib.Path:
    cfg = load_config(config_path or pathlib.Path(__file__).resolve().parents[2] / "config" / "search_config.yaml")
    return build_processed_dataset(cfg)


if __name__ == "__main__":
    out = run_etl()
    print(f"Wrote processed dataset to {out}")
