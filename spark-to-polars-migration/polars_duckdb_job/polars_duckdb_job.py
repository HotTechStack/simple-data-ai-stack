import os
import time
from pathlib import Path

import duckdb
import polars as pl


def run_polars_pipeline(data_path: Path, output_dir: Path) -> float:
    start = time.perf_counter()

    result = (
        pl.scan_csv(data_path)
        .with_columns(pl.col("amount").cast(pl.Float64))
        .group_by("customer_id", "region")
        .agg(
            pl.len().alias("order_count"),
            pl.col("amount").sum().alias("total_amount"),
        )
        .with_columns(
            pl.when(pl.col("total_amount") >= 1000)
            .then(pl.lit("enterprise"))
            .when(pl.col("total_amount") >= 500)
            .then(pl.lit("growth"))
            .when(pl.col("total_amount") >= 200)
            .then(pl.lit("scale"))
            .otherwise(pl.lit("starter"))
            .alias("spending_tier")
        )
        .sort("total_amount", descending=True)
        .collect()
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    result.write_parquet(output_dir / "customer_spend.parquet")
    print("\nPolars result:")
    print(result)

    return time.perf_counter() - start


def run_duckdb_pipeline(data_path: Path, output_dir: Path) -> float:
    start = time.perf_counter()
    con = duckdb.connect(database=":memory:")

    sql = f"""
        WITH aggregated AS (
            SELECT
                customer_id,
                region,
                COUNT(*) AS order_count,
                SUM(amount) AS total_amount
            FROM read_csv_auto('{data_path}')
            GROUP BY customer_id, region
        )
        SELECT
            customer_id,
            region,
            order_count,
            total_amount,
            CASE
                WHEN total_amount >= 1000 THEN 'enterprise'
                WHEN total_amount >= 500 THEN 'growth'
                WHEN total_amount >= 200 THEN 'scale'
                ELSE 'starter'
            END AS spending_tier
        FROM aggregated
        ORDER BY total_amount DESC
    """

    result = con.execute(sql).pl()
    output_dir.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY ({sql}) TO '{output_dir / 'customer_spend.parquet'}' (FORMAT PARQUET)")
    print("\nDuckDB result:")
    print(result)
    con.close()
    return time.perf_counter() - start


def main() -> None:
    data_path = Path(os.environ.get("ORDERS_PATH", "/opt/project/data/orders.csv"))
    polars_output = Path(
        os.environ.get("POLARS_OUTPUT_PATH", "/opt/project/output/polars")
    )
    duckdb_output = Path(
        os.environ.get("DUCKDB_OUTPUT_PATH", "/opt/project/output/duckdb")
    )

    polars_elapsed = run_polars_pipeline(data_path, polars_output)
    duckdb_elapsed = run_duckdb_pipeline(data_path, duckdb_output)

    print(f"\nPolars pipeline finished in {polars_elapsed:.2f} seconds.")
    print(f"DuckDB pipeline finished in {duckdb_elapsed:.2f} seconds.")
    print(f"Results saved to {polars_output} and {duckdb_output}")


if __name__ == "__main__":
    main()
