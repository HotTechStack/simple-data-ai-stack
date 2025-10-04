"""
End-to-End Polars Pipeline Example

This demonstrates a realistic data engineering workflow:
1. Load raw sales data (CSV)
2. Clean and filter data
3. Join with product catalog
4. Aggregate by region
5. Export final results

This is what developers actually do with data tools!
"""

import asyncio
import sys
from pathlib import Path
import polars as pl

sys.path.insert(0, 'src')

from data_agent_sdk.agents.base import DataAgent
from data_agent_sdk.tools.polars_tool import (
    run_polars,
    transform_csv,
    join_datasets,
    aggregate_data
)
from data_agent_sdk.tools.sql import run_sql
from data_agent_sdk.types import SessionContext


async def setup_sample_data():
    """Create realistic sample datasets."""
    print("=" * 70)
    print("SETUP: Creating sample datasets")
    print("=" * 70)

    # 1. Raw sales data (CSV) - Messy, real-world data
    sales_data = pl.DataFrame({
        "order_id": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "product_id": ["P001", "P002", "P001", "P003", "P002", "P001", "P003", "P002", "P001", "P003"],
        "quantity": [2, 1, 5, 3, 2, 1, 4, 3, 2, 1],
        "price": [1200, 25, 1200, 75, 25, 1200, 75, 25, 1200, 75],
        "region": ["North", "South", "East", "West", "North", "South", "East", "West", "North", "South"],
        "order_date": ["2024-01-15", "2024-01-16", "2024-01-17", "2024-01-18", "2024-01-19",
                      "2024-01-20", "2024-01-21", "2024-01-22", "2024-01-23", "2024-01-24"],
        "status": ["completed", "completed", "completed", "cancelled", "completed",
                  "completed", "completed", "completed", "pending", "completed"]
    })

    sales_csv = "/tmp/raw_sales.csv"
    sales_data.write_csv(sales_csv)
    print(f"✓ Created raw sales data: {sales_csv}")
    print(f"  - {len(sales_data)} orders")
    print(f"  - Columns: {list(sales_data.columns)}")

    # 2. Product catalog (Parquet) - Reference data
    products_data = pl.DataFrame({
        "product_id": ["P001", "P002", "P003"],
        "product_name": ["Laptop", "Mouse", "Keyboard"],
        "category": ["Electronics", "Accessories", "Accessories"],
        "supplier": ["TechCorp", "PeripheralInc", "PeripheralInc"]
    })

    products_parquet = "/tmp/products.parquet"
    products_data.write_parquet(products_parquet)
    print(f"✓ Created product catalog: {products_parquet}")
    print(f"  - {len(products_data)} products")
    print()

    return sales_csv, products_parquet


async def main():
    # Setup sample data
    sales_csv, products_parquet = await setup_sample_data()

    # Create agent
    agent = DataAgent(
        allowed_tools=["transform_csv", "join_datasets", "aggregate_data", "run_polars", "run_sql"],
        session_context=SessionContext(
            warehouse="duckdb:///tmp/analytics.db",
            user="data_engineer",
            role="engineer"
        )
    )

    # Register Polars tools
    agent.register_tool(transform_csv)
    agent.register_tool(join_datasets)
    agent.register_tool(aggregate_data)
    agent.register_tool(run_polars)
    agent.register_tool(run_sql)

    print("=" * 70)
    print("POLARS DATA PIPELINE - End-to-End Example")
    print("=" * 70)
    print()

    # ====================================================================
    # STEP 1: Clean and filter raw sales data
    # ====================================================================
    print("[Step 1] Clean raw sales data")
    print("-" * 70)
    print("Task: Remove cancelled/pending orders, select relevant columns")
    print()

    cleaned_sales = await transform_csv(
        input_csv=sales_csv,
        filter_expr="pl.col('status') == 'completed'",
        select_cols=["order_id", "product_id", "quantity", "price", "region"],
        session_context=agent.session_context
    )

    print(f"✓ Cleaned sales data")
    print(f"  - Input: {sales_csv}")
    print(f"  - Output: {cleaned_sales.uri}")
    print(f"  - Rows: 10 → {cleaned_sales.row_count} (filtered out {10 - cleaned_sales.row_count} orders)")
    print(f"  - Schema: {cleaned_sales.schema}")
    print()

    # ====================================================================
    # STEP 2: Calculate revenue (quantity * price)
    # ====================================================================
    print("[Step 2] Calculate revenue for each order")
    print("-" * 70)
    print("Task: Add 'revenue' column (quantity * price)")
    print()

    enriched_sales = await run_polars(
        input_uri=cleaned_sales.uri,
        operations="with_columns((pl.col('quantity') * pl.col('price')).alias('revenue'))",
        session_context=agent.session_context
    )

    print(f"✓ Added revenue column")
    print(f"  - Output: {enriched_sales.uri}")
    print(f"  - New schema: {enriched_sales.schema}")
    print()

    # ====================================================================
    # STEP 3: Join with product catalog
    # ====================================================================
    print("[Step 3] Enrich sales with product information")
    print("-" * 70)
    print("Task: Join sales with product catalog on product_id")
    print()

    enriched_with_products = await join_datasets(
        left_uri=enriched_sales.uri,
        right_uri=products_parquet,
        on="product_id",
        how="left",
        session_context=agent.session_context
    )

    print(f"✓ Joined with product catalog")
    print(f"  - Left: {enriched_sales.uri}")
    print(f"  - Right: {products_parquet}")
    print(f"  - Output: {enriched_with_products.uri}")
    print(f"  - Rows: {enriched_with_products.row_count}")
    print(f"  - Schema: {enriched_with_products.schema}")
    print()

    # ====================================================================
    # STEP 4: Aggregate by region and category
    # ====================================================================
    print("[Step 4] Aggregate sales by region and category")
    print("-" * 70)
    print("Task: Calculate total revenue and order count by region/category")
    print()

    regional_summary = await aggregate_data(
        input_uri=enriched_with_products.uri,
        group_by=["region", "category"],
        aggregations={
            "revenue": "sum",
            "order_id": "count",
            "quantity": "sum"
        },
        session_context=agent.session_context
    )

    print(f"✓ Aggregated by region and category")
    print(f"  - Output: {regional_summary.uri}")
    print(f"  - Rows: {regional_summary.row_count} summary rows")
    print(f"  - Schema: {regional_summary.schema}")
    print()

    # ====================================================================
    # STEP 5: Show final results
    # ====================================================================
    print("[Step 5] Preview final results")
    print("-" * 70)

    # Read final parquet
    final_df = pl.read_parquet(regional_summary.uri)
    print(final_df)
    print()

    # ====================================================================
    # BONUS: Advanced Polars operations
    # ====================================================================
    print("[Bonus] Advanced Polars: Top products by revenue")
    print("-" * 70)
    print("Task: Find top 3 products by total revenue")
    print()

    top_products = await run_polars(
        input_uri=enriched_with_products.uri,
        operations="group_by('product_name').agg(pl.col('revenue').sum().alias('total_revenue')).sort('total_revenue', descending=True).head(3)",
        session_context=agent.session_context
    )

    print(f"✓ Top products calculated")
    print(f"  - Output: {top_products.uri}")
    print()

    top_products_df = pl.read_parquet(top_products.uri)
    print(top_products_df)
    print()

    # ====================================================================
    # Pipeline Summary
    # ====================================================================
    print("=" * 70)
    print("PIPELINE SUMMARY")
    print("=" * 70)
    print()
    print("Data Flow:")
    print(f"  1. Raw CSV ({sales_csv})")
    print(f"     ↓ filter + select")
    print(f"  2. Cleaned ({cleaned_sales.uri})")
    print(f"     ↓ calculate revenue")
    print(f"  3. Enriched ({enriched_sales.uri})")
    print(f"     ↓ join with products")
    print(f"  4. Complete ({enriched_with_products.uri})")
    print(f"     ↓ aggregate")
    print(f"  5. Final Summary ({regional_summary.uri})")
    print()
    print("Artifacts created: 5")
    print("Tools used: transform_csv, run_polars, join_datasets, aggregate_data")
    print()

    # Check lineage
    lineage_file = Path("/tmp/lineage.jsonl")
    if lineage_file.exists():
        with open(lineage_file) as f:
            lines = f.readlines()
            print(f"Lineage entries logged: {len(lines)}")
            print()

    print("=" * 70)
    print("✅ Pipeline completed successfully!")
    print("=" * 70)
    print()
    print("What you just saw:")
    print("  ✓ Real-world data pipeline (CSV → clean → join → aggregate)")
    print("  ✓ Polars transformations (filter, select, join, group_by)")
    print("  ✓ Artifact tracking (every step logged)")
    print("  ✓ Lineage tracking (full data provenance)")
    print("  ✓ Type safety (schema preserved throughout)")
    print()
    print("This is what developers actually do with data tools! 🚀")


if __name__ == "__main__":
    asyncio.run(main())
