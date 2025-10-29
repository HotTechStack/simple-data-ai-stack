import os
import time
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count as spark_count, sum as spark_sum, udf
from pyspark.sql.types import StringType


def spending_tier(total_amount: float) -> str:
    """Example business rule implemented as a Python UDF."""
    if total_amount is None:
        return "unknown"
    if total_amount >= 1000:
        return "enterprise"
    if total_amount >= 500:
        return "growth"
    if total_amount >= 200:
        return "scale"
    return "starter"


SPENDING_TIER_UDF = udf(spending_tier, StringType())


def main() -> None:
    data_path = Path(os.environ.get("ORDERS_PATH", "/opt/project/data/orders.csv"))
    output_dir = Path(os.environ.get("SPARK_OUTPUT_PATH", "/opt/project/output/spark"))
    output_dir.mkdir(parents=True, exist_ok=True)

    spark = (
        SparkSession.builder.appName("spark_udf_customer_tiers")
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )

    start = time.perf_counter()
    orders_df = (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .csv(str(data_path))
        .cache()
    )

    aggregated = (
        orders_df.groupBy("customer_id", "region")
        .agg(
            spark_count("*").alias("order_count"),
            spark_sum(col("amount")).alias("total_amount"),
        )
        .withColumn("spending_tier", SPENDING_TIER_UDF(col("total_amount")))
        .orderBy(col("total_amount").desc())
    )

    aggregated.write.mode("overwrite").parquet(str(output_dir / "customer_spend"))

    elapsed = time.perf_counter() - start
    aggregated.show(truncate=False)
    print(f"\nSpark pipeline finished in {elapsed:.2f} seconds.")
    print(f"Results saved to {output_dir / 'customer_spend'}")

    spark.stop()


if __name__ == "__main__":
    main()
