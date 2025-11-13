"""Executable MDM pipeline that follows the Polars & DuckDB blog checklist."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import duckdb
import pandas as pd
import polars as pl
from rapidfuzz import fuzz, process

from .config import (
    ARTIFACTS_DIR,
    COLUMN_ALIASES,
    DATA_DIR,
    FUZZY_MATCH_THRESHOLD,
    HIGH_TRUST_SOURCES,
    ISO_COUNTRY_MAP,
    SOURCE_FILES,
    SOURCE_PRIORITIES,
    utcnow,
)
from .data_generation import generate_sample_sources
from .validators import CUSTOMER_SCHEMA


def _normalize_schema(df: pl.DataFrame, source_system: str) -> pl.DataFrame:
    rename_map: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in df.columns and canonical not in df.columns:
                rename_map[alias] = canonical
                break
    df = df.rename(rename_map)
    for required in COLUMN_ALIASES:
        if required not in df.columns:
            df = df.with_columns(pl.lit(None).alias(required))

    df = df.with_columns(
        [
            pl.lit(source_system).alias("source_system"),
            pl.concat_str(
                [pl.lit(source_system), pl.col("customer_id").cast(pl.Utf8)],
                separator="::",
            ).alias("source_record_id"),
        ]
    )

    selected_cols = [
        "customer_id",
        "customer_name",
        "email",
        "phone",
        "address",
        "country",
        "updated_at",
        "source_system",
        "source_record_id",
    ]
    extras = [c for c in df.columns if c not in selected_cols]
    return df.select(selected_cols + extras)


def _load_duckdb_table(path: Path, table: str) -> pl.DataFrame:
    with duckdb.connect(str(path)) as con:
        data = con.execute(f"SELECT * FROM {table}").arrow()
    return pl.from_arrow(data)


def load_sources() -> pl.DataFrame:
    """Read all seven upstream sources using the right reader for each."""
    frames: list[pl.DataFrame] = []

    billing = (
        pl.scan_csv(str(SOURCE_FILES["billing_system"]), infer_schema_length=0)
        .collect()
    )
    frames.append(_normalize_schema(billing, "billing_system"))

    crm = (
        pl.scan_csv(str(SOURCE_FILES["crm_system"]), infer_schema_length=0)
        .collect()
    )
    frames.append(_normalize_schema(crm, "crm_system"))

    erp = pl.scan_ndjson(str(SOURCE_FILES["erp_exports"])).collect()
    frames.append(_normalize_schema(erp, "erp_exports"))

    finance = pl.read_excel(str(SOURCE_FILES["finance_excel"]))
    frames.append(_normalize_schema(finance, "finance_excel"))

    marketing = (
        pl.scan_csv(str(SOURCE_FILES["marketing_automation"]), infer_schema_length=0)
        .collect()
    )
    frames.append(_normalize_schema(marketing, "marketing_automation"))

    support = (
        pl.scan_csv(str(SOURCE_FILES["support_desk"]), infer_schema_length=0).collect()
    )
    frames.append(_normalize_schema(support, "support_desk"))

    legacy = _load_duckdb_table(SOURCE_FILES["legacy_duckdb"], "legacy_customers")
    frames.append(_normalize_schema(legacy, "legacy_duckdb"))

    combined = pl.concat(frames, how="diagonal_relaxed")
    return combined.with_row_index("row_id")


def run_schema_validation(df: pl.DataFrame) -> None:
    """Validate the first 1000 records with Pandera before heavy lifting."""
    sample = df.head(1000).to_pandas()
    if "updated_at" in sample.columns:
        sample["updated_at"] = (
            pd.to_datetime(sample["updated_at"], errors="coerce", utc=True)
            .dt.tz_localize(None)
        )
    CUSTOMER_SCHEMA.validate(sample)


def standardize_values(df: pl.DataFrame) -> pl.DataFrame:
    """Clean values: strip whitespace, normalize casing, align countries."""
    normalized_country = (
        pl.col("country")
        .cast(pl.Utf8, strict=False)
        .str.strip_chars()
        .replace(ISO_COUNTRY_MAP)
        .str.to_uppercase()
    )

    cleaned_email = (
        pl.col("email").cast(pl.Utf8, strict=False).str.strip_chars().str.to_lowercase()
    )

    digits_only = (
        pl.col("phone").cast(pl.Utf8, strict=False).str.replace_all(r"[^0-9]", "")
    )
    normalized_phone = (
        pl.when(digits_only.str.len_bytes() > 0)
        .then(pl.lit("+") + digits_only)
        .otherwise(None)
    )

    parsed_updated = (
        pl.col("updated_at")
        .cast(pl.Utf8, strict=False)
        .str.replace(" ", "T")
        .str.to_datetime(strict=False, time_zone="UTC")
    )

    return (
        df.with_columns(
            [
                pl.col("customer_name")
                .cast(pl.Utf8, strict=False)
                .str.strip_chars()
                .str.to_titlecase(),
                cleaned_email.alias("email"),
                normalized_phone.alias("phone"),
                pl.col("address").cast(pl.Utf8, strict=False).str.strip_chars(),
                normalized_country.alias("country"),
                parsed_updated.alias("updated_at"),
                pl.col("source_system").cast(pl.Utf8),
                pl.col("source_record_id").cast(pl.Utf8),
                pl.lit("schema_normalization").alias("conflict_rules_applied"),
                pl.col("source_system")
                .replace(SOURCE_PRIORITIES, default=0)
                .alias("source_priority"),
            ]
        )
        .with_columns(
            pl.when(
                pl.col("email").is_not_null() & pl.col("phone").is_not_null()
            )
            .then(pl.col("email") + "|" + pl.col("phone"))
            .otherwise(None)
            .alias("composite_key")
        )
    )


def compute_data_quality(df: pl.DataFrame) -> pl.DataFrame:
    """Compute completeness + recency score per record."""
    now = utcnow()
    mandatory = ["customer_id", "customer_name", "email", "phone", "address", "country"]
    completeness = (
        pl.sum_horizontal(
            [pl.col(col).is_not_null().cast(pl.Float64) for col in mandatory]
        )
        / len(mandatory)
    )
    recency_days = (
        (pl.lit(now).alias("now") - pl.col("updated_at"))
        .dt.total_days()
        .abs()
    )
    recency_score = (
        pl.when(pl.col("updated_at").is_not_null())
        .then((1 - (recency_days / 365.0)).clip(0.0, 1.0))
        .otherwise(0.2)
    )

    return df.with_columns(
        [
            completeness.alias("completeness_fraction"),
            recency_days.alias("recency_days"),
            (
                (completeness * 0.7) + (recency_score * 0.3)
            )
            .round(3)
            .alias("data_quality_score"),
        ]
    )


def _fuzzy_updates(df: pl.DataFrame) -> pl.DataFrame:
    canonical = df.filter(pl.col("composite_key").is_not_null())
    unresolved = df.filter(pl.col("composite_key").is_null())
    if canonical.is_empty() or unresolved.is_empty():
        return df

    choices = [
        (
            f"{row.get('customer_name','')}|{row.get('address','')}",
            row["composite_key"],
        )
        for row in canonical.select(["customer_name", "address", "composite_key"]).to_dicts()
    ]

    updates: list[dict[str, str]] = []
    for row in unresolved.select(["row_id", "customer_name", "address"]).to_dicts():
        query = f"{row.get('customer_name','')}|{row.get('address','')}"
        match = process.extractOne(
            query,
            choices,
            scorer=fuzz.WRatio,
            score_cutoff=FUZZY_MATCH_THRESHOLD,
        )
        if match:
            updates.append(
                {
                    "row_id": row["row_id"],
                    "fuzzy_composite_key": match[1],
                    "fuzzy_rule": "fuzzy_name_address_match",
                }
            )

    if not updates:
        return df

    update_df = pl.DataFrame(updates)
    merged = df.join(update_df, on="row_id", how="left")
    return merged.with_columns(
        [
            pl.when(
                (pl.col("composite_key").is_null())
                & (pl.col("fuzzy_composite_key").is_not_null())
            )
            .then(pl.col("fuzzy_composite_key"))
            .otherwise(pl.col("composite_key"))
            .alias("composite_key"),
            pl.when(pl.col("fuzzy_rule").is_not_null())
            .then(pl.col("conflict_rules_applied") + "|fuzzy_name_address_match")
            .otherwise(pl.col("conflict_rules_applied"))
            .alias("conflict_rules_applied"),
        ]
    ).drop(["fuzzy_composite_key", "fuzzy_rule"])


def finalize_composite_keys(df: pl.DataFrame) -> pl.DataFrame:
    """Fill any still-missing composite_key with the fallback customer id."""
    df = _fuzzy_updates(df)
    return df.with_columns(
        pl.col("composite_key")
        .fill_null(pl.col("customer_id").cast(pl.Utf8))
        .alias("composite_key")
    )


def resolve_conflicts(df: pl.DataFrame) -> pl.DataFrame:
    """Deduplicate via window functions + explicit source priorities."""
    df = df.sort(
        ["composite_key", "data_quality_score", "source_priority"],
        descending=[False, True, True],
    ).with_columns(
        pl.col("data_quality_score")
        .rank(method="dense", descending=True)
        .over("composite_key")
        .alias("quality_rank")
    )

    def prefer_trusted(column: str) -> pl.Expr:
        return (
            pl.col(column)
            .sort_by(
                by=[pl.col("source_priority"), pl.col("data_quality_score")],
                descending=[True, True],
            )
            .first()
        )

    def prefer_best(column: str) -> pl.Expr:
        return (
            pl.col(column)
            .sort_by(
                by=[pl.col("data_quality_score"), pl.col("source_priority")],
                descending=[True, True],
            )
            .first()
        )

    aggregated = (
        df.group_by("composite_key", maintain_order=False)
        .agg(
            [
                prefer_best("customer_id").alias("customer_id"),
                prefer_best("customer_name").alias("customer_name"),
                prefer_trusted("email").alias("email"),
                prefer_trusted("phone").alias("phone"),
                prefer_trusted("address").alias("address"),
                prefer_trusted("country").alias("country"),
                prefer_trusted("updated_at").alias("updated_at"),
                pl.col("data_quality_score").max().alias("data_quality_score"),
                pl.col("source_priority").max().alias("winning_source_priority"),
                prefer_trusted("source_system").alias("winning_source_system"),
                pl.col("source_system")
                    .unique()
                    .alias("source_systems"),
                pl.col("conflict_rules_applied")
                    .unique()
                    .alias("conflict_rules_applied"),
                pl.col("source_record_id")
                    .sort_by(
                        by=[pl.col("source_priority"), pl.col("data_quality_score")],
                        descending=[True, True],
                    )
                    .first()
                    .alias("winning_source_record_id"),
                pl.col("quality_rank").max().alias("max_quality_rank"),
                pl.col("completeness_fraction")
                    .max()
                    .alias("max_completeness_fraction"),
            ]
        )
        .with_columns(
            [
                pl.lit(utcnow()).alias("created_at"),
                pl.col("updated_at").alias("last_updated_at"),
            ]
        )
        .select(
            [
                pl.col("composite_key"),
                pl.col("customer_id"),
                pl.col("customer_name"),
                pl.col("email"),
                pl.col("phone"),
                pl.col("address"),
                pl.col("country"),
                pl.col("data_quality_score"),
                pl.col("max_completeness_fraction").alias("completeness_fraction"),
                pl.col("winning_source_system").alias("primary_source"),
                pl.col("winning_source_record_id").alias("primary_source_record"),
                pl.col("source_systems"),
                pl.col("conflict_rules_applied"),
                pl.col("created_at"),
                pl.col("last_updated_at"),
            ]
        )
    )
    return aggregated


def write_duckdb_table(df: pl.DataFrame) -> Path:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    db_path = ARTIFACTS_DIR / "golden_customers.duckdb"
    with duckdb.connect(str(db_path)) as con:
        con.execute("DROP TABLE IF EXISTS golden_customers")
        con.execute("CREATE TABLE golden_customers AS SELECT * FROM df")
    csv_path = ARTIFACTS_DIR / "golden_customers.csv"
    flattened = df.with_columns(
        [
            pl.col("source_systems")
            .list.join("|")
            .alias("source_systems"),
            pl.col("conflict_rules_applied")
            .list.join("|")
            .alias("conflict_rules_applied"),
        ]
    )
    flattened.write_csv(csv_path)
    return db_path


def summarize(df: pl.DataFrame) -> dict[str, int | float]:
    return {
        "records_in_golden_table": df.height,
        "unique_sources": df.select(pl.col("primary_source").unique().len()).item(),
        "avg_quality_score": round(df["data_quality_score"].mean(), 3),
    }


def main() -> None:
    print("🔧 Generating seven messy source extracts...")
    generate_sample_sources()

    print("📥 Loading sources with Polars scan/read APIs...")
    stacked = load_sources()
    print(f"   Loaded {stacked.height} raw records across {len(SOURCE_FILES)} systems.")

    print("🧪 Running Pandera validation on the first 1000 rows...")
    run_schema_validation(stacked)

    print("🧼 Standardizing values + schema...")
    normalized = standardize_values(stacked)

    print("📊 Computing data quality scores...")
    scored = compute_data_quality(normalized)

    print("🧮 Fuzzy matching missing keys with RapidFuzz...")
    keyed = finalize_composite_keys(scored)

    print("⚖️  Resolving conflicts with window functions + priorities...")
    golden = resolve_conflicts(keyed)

    print("🦆 Writing golden table to DuckDB + CSV...")
    db_path = write_duckdb_table(golden)

    metrics = summarize(golden)
    print("✅ Golden table ready:")
    print(json.dumps(metrics, indent=2))
    print(f"📂 DuckDB file: {db_path}")
    print(f"📄 CSV sample: {ARTIFACTS_DIR / 'golden_customers.csv'}")


if __name__ == "__main__":
    main()
