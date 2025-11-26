"""
Comprehensive Polars Data Pipeline with VictoriaMetrics Observability

This demonstrates:
- Prometheus metrics instrumentation (rows_processed, stage_duration, data_freshness)
- Automatic metrics exposure via HTTP server
- Direct push to vmagent
- Multi-stage ETL pipeline tracking
- Data quality metrics
"""

import time
import requests
import polars as pl
from datetime import datetime, timedelta
from prometheus_client import Counter, Gauge, Histogram, start_http_server, CollectorRegistry
from faker import Faker
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create custom registry for metrics
registry = CollectorRegistry()

# Define Prometheus metrics with pipeline context
rows_processed = Counter(
    'pipeline_rows_processed_total',
    'Total number of rows processed through pipeline stages',
    ['pipeline_name', 'stage', 'environment', 'data_source'],
    registry=registry
)

stage_duration = Histogram(
    'pipeline_stage_duration_seconds',
    'Time spent in each pipeline stage',
    ['pipeline_name', 'stage', 'environment'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
    registry=registry
)

data_freshness = Gauge(
    'pipeline_data_freshness_seconds',
    'Age of the most recent data processed',
    ['pipeline_name', 'data_source', 'environment'],
    registry=registry
)

error_count = Counter(
    'pipeline_errors_total',
    'Total number of errors in pipeline',
    ['pipeline_name', 'stage', 'error_type', 'environment'],
    registry=registry
)

data_quality_score = Gauge(
    'pipeline_data_quality_score',
    'Data quality score (0-100)',
    ['pipeline_name', 'check_type', 'environment'],
    registry=registry
)

memory_usage = Gauge(
    'pipeline_memory_usage_bytes',
    'Memory usage of pipeline process',
    ['pipeline_name', 'environment'],
    registry=registry
)


def generate_sample_data(num_rows: int = 10000) -> pl.DataFrame:
    """Generate realistic sample data using Faker"""
    logger.info(f"Generating {num_rows} sample records...")

    fake = Faker()
    Faker.seed(42)

    data = {
        'user_id': [fake.uuid4() for _ in range(num_rows)],
        'email': [fake.email() for _ in range(num_rows)],
        'signup_date': [fake.date_time_between(start_date='-2y', end_date='now') for _ in range(num_rows)],
        'country': [fake.country_code() for _ in range(num_rows)],
        'revenue': [round(fake.random.uniform(10.0, 5000.0), 2) for _ in range(num_rows)],
        'product_category': [fake.random_element(['Electronics', 'Books', 'Clothing', 'Home', 'Sports']) for _ in range(num_rows)],
        'session_duration_minutes': [fake.random.randint(1, 180) for _ in range(num_rows)],
        'is_active': [fake.boolean(chance_of_getting_true=75) for _ in range(num_rows)],
    }

    return pl.DataFrame(data)


def push_metrics_to_vmagent(metric_name: str, value: float, labels: dict, timestamp: int = None):
    """
    Push metrics directly to VictoriaMetrics using Prometheus format
    """
    try:
        if timestamp is None:
            timestamp = int(time.time() * 1000)  # milliseconds

        # Build Prometheus format: metric_name{label1="value1"} value timestamp
        label_str = ','.join([f'{k}="{v}"' for k, v in labels.items()])
        line = f"{metric_name}{{{label_str}}} {value} {timestamp}"

        # Push to VictoriaMetrics import endpoint
        response = requests.post(
            'http://localhost:8428/api/v1/import/prometheus',
            data=line,
            headers={'Content-Type': 'text/plain'}
        )
        response.raise_for_status()
        logger.debug(f"Pushed metric: {line}")
    except Exception as e:
        logger.error(f"Failed to push metrics to VictoriaMetrics: {e}")


class ETLPipeline:
    """ETL Pipeline with comprehensive metrics tracking"""

    def __init__(self, pipeline_name: str = "etl_pipeline", environment: str = "dev"):
        self.pipeline_name = pipeline_name
        self.environment = environment
        self.start_time = time.time()

    def extract(self, num_rows: int = 10000) -> pl.DataFrame:
        """Extract stage - simulate data source extraction"""
        stage_name = "extract"
        logger.info(f"[{stage_name.upper()}] Starting extraction...")

        with stage_duration.labels(
            pipeline_name=self.pipeline_name,
            stage=stage_name,
            environment=self.environment
        ).time():
            # Generate sample data
            df = generate_sample_data(num_rows)

            # Track rows processed
            row_count = df.shape[0]
            rows_processed.labels(
                pipeline_name=self.pipeline_name,
                stage=stage_name,
                environment=self.environment,
                data_source="faker"
            ).inc(row_count)

            # Calculate data freshness (most recent signup_date)
            if 'signup_date' in df.columns:
                max_date = df['signup_date'].max()
                freshness_seconds = (datetime.now() - max_date).total_seconds()
                data_freshness.labels(
                    pipeline_name=self.pipeline_name,
                    data_source="faker",
                    environment=self.environment
                ).set(freshness_seconds)

            logger.info(f"[{stage_name.upper()}] Extracted {row_count} rows")

            # Push custom metric via InfluxDB protocol
            push_metrics_to_vmagent(
                'pipeline_extraction_rows',
                row_count,
                {
                    'pipeline_name': self.pipeline_name,
                    'environment': self.environment,
                    'data_source': 'faker'
                }
            )

        return df

    def transform(self, df: pl.DataFrame) -> pl.DataFrame:
        """Transform stage - clean and enrich data"""
        stage_name = "transform"
        logger.info(f"[{stage_name.upper()}] Starting transformation...")

        with stage_duration.labels(
            pipeline_name=self.pipeline_name,
            stage=stage_name,
            environment=self.environment
        ).time():
            try:
                # Data transformations
                df_transformed = df.with_columns([
                    # Normalize email to lowercase
                    pl.col('email').str.to_lowercase().alias('email_normalized'),

                    # Calculate customer lifetime value
                    (pl.col('revenue') * pl.col('session_duration_minutes') / 60.0).alias('estimated_ltv'),

                    # Extract signup year
                    pl.col('signup_date').dt.year().alias('signup_year'),

                    # Categorize revenue
                    pl.when(pl.col('revenue') < 100).then(pl.lit('low'))
                      .when(pl.col('revenue') < 1000).then(pl.lit('medium'))
                      .otherwise(pl.lit('high')).alias('revenue_category'),
                ])

                # Filter active users only
                df_transformed = df_transformed.filter(pl.col('is_active') == True)

                row_count = df_transformed.shape[0]
                rows_processed.labels(
                    pipeline_name=self.pipeline_name,
                    stage=stage_name,
                    environment=self.environment,
                    data_source="memory"
                ).inc(row_count)

                logger.info(f"[{stage_name.upper()}] Transformed {row_count} rows")

            except Exception as e:
                logger.error(f"Transform error: {e}")
                error_count.labels(
                    pipeline_name=self.pipeline_name,
                    stage=stage_name,
                    error_type=type(e).__name__,
                    environment=self.environment
                ).inc()
                raise

        return df_transformed

    def data_quality_checks(self, df: pl.DataFrame) -> dict:
        """Perform data quality checks and track metrics"""
        stage_name = "quality_check"
        logger.info(f"[{stage_name.upper()}] Running data quality checks...")

        quality_results = {}

        with stage_duration.labels(
            pipeline_name=self.pipeline_name,
            stage=stage_name,
            environment=self.environment
        ).time():
            # Check 1: Null values
            total_rows = df.shape[0]
            null_counts = df.null_count()
            null_percentage = (null_counts.sum_horizontal()[0] / (total_rows * len(df.columns))) * 100
            null_score = max(0, 100 - null_percentage)

            data_quality_score.labels(
                pipeline_name=self.pipeline_name,
                check_type="null_check",
                environment=self.environment
            ).set(null_score)
            quality_results['null_score'] = null_score

            # Check 2: Email validity (simple check)
            valid_emails = df.filter(pl.col('email').str.contains('@')).shape[0]
            email_validity_score = (valid_emails / total_rows) * 100

            data_quality_score.labels(
                pipeline_name=self.pipeline_name,
                check_type="email_validity",
                environment=self.environment
            ).set(email_validity_score)
            quality_results['email_validity_score'] = email_validity_score

            # Check 3: Revenue range check
            revenue_in_range = df.filter(
                (pl.col('revenue') >= 0) & (pl.col('revenue') <= 10000)
            ).shape[0]
            revenue_score = (revenue_in_range / total_rows) * 100

            data_quality_score.labels(
                pipeline_name=self.pipeline_name,
                check_type="revenue_range",
                environment=self.environment
            ).set(revenue_score)
            quality_results['revenue_score'] = revenue_score

            # Overall quality score
            overall_score = (null_score + email_validity_score + revenue_score) / 3
            data_quality_score.labels(
                pipeline_name=self.pipeline_name,
                check_type="overall",
                environment=self.environment
            ).set(overall_score)
            quality_results['overall_score'] = overall_score

            logger.info(f"[{stage_name.upper()}] Quality Score: {overall_score:.2f}/100")

            # Push to vmagent
            push_metrics_to_vmagent(
                'pipeline_quality_overall',
                overall_score,
                {
                    'pipeline_name': self.pipeline_name,
                    'environment': self.environment
                }
            )

        return quality_results

    def load(self, df: pl.DataFrame, output_path: str = "output/data.parquet"):
        """Load stage - write to Parquet"""
        stage_name = "load"
        logger.info(f"[{stage_name.upper()}] Starting load...")

        with stage_duration.labels(
            pipeline_name=self.pipeline_name,
            stage=stage_name,
            environment=self.environment
        ).time():
            try:
                # Create output directory
                import os
                os.makedirs(os.path.dirname(output_path), exist_ok=True)

                # Write to Parquet
                df.write_parquet(output_path)

                row_count = df.shape[0]
                rows_processed.labels(
                    pipeline_name=self.pipeline_name,
                    stage=stage_name,
                    environment=self.environment,
                    data_source="parquet"
                ).inc(row_count)

                # Get file size
                file_size = os.path.getsize(output_path)
                push_metrics_to_vmagent(
                    'pipeline_output_size_bytes',
                    file_size,
                    {
                        'pipeline_name': self.pipeline_name,
                        'environment': self.environment,
                        'format': 'parquet'
                    }
                )

                logger.info(f"[{stage_name.upper()}] Loaded {row_count} rows to {output_path} ({file_size:,} bytes)")

            except Exception as e:
                logger.error(f"Load error: {e}")
                error_count.labels(
                    pipeline_name=self.pipeline_name,
                    stage=stage_name,
                    error_type=type(e).__name__,
                    environment=self.environment
                ).inc()
                raise

    def run(self, num_rows: int = 10000):
        """Run the complete ETL pipeline"""
        pipeline_start = time.time()
        logger.info(f"Starting ETL pipeline: {self.pipeline_name}")

        try:
            # Extract
            df = self.extract(num_rows)

            # Transform
            df_transformed = self.transform(df)

            # Quality checks
            quality_results = self.data_quality_checks(df_transformed)

            # Load
            self.load(df_transformed)

            # Track total pipeline duration
            total_duration = time.time() - pipeline_start
            push_metrics_to_vmagent(
                'pipeline_total_duration_seconds',
                total_duration,
                {
                    'pipeline_name': self.pipeline_name,
                    'environment': self.environment,
                    'status': 'success'
                }
            )

            logger.info(f"Pipeline completed successfully in {total_duration:.2f}s")
            logger.info(f"Quality Results: {quality_results}")

        except Exception as e:
            total_duration = time.time() - pipeline_start
            push_metrics_to_vmagent(
                'pipeline_total_duration_seconds',
                total_duration,
                {
                    'pipeline_name': self.pipeline_name,
                    'environment': self.environment,
                    'status': 'failed'
                }
            )
            logger.error(f"Pipeline failed: {e}")
            raise


def main():
    """Main entry point - starts metrics server and runs pipeline continuously"""
    # Start Prometheus metrics HTTP server on port 8000
    logger.info("Starting Prometheus metrics server on port 8000...")
    start_http_server(8000, registry=registry)
    logger.info("Metrics available at http://localhost:8000/metrics")

    # Run pipeline continuously
    iteration = 0
    while True:
        iteration += 1
        logger.info(f"\n{'='*60}")
        logger.info(f"Pipeline Iteration #{iteration}")
        logger.info(f"{'='*60}\n")

        try:
            pipeline = ETLPipeline(
                pipeline_name="etl_pipeline",
                environment="dev"
            )

            # Run with varying data sizes to show metrics changes
            num_rows = 5000 + (iteration % 3) * 5000  # 5k, 10k, 15k rotation
            pipeline.run(num_rows=num_rows)

        except Exception as e:
            logger.error(f"Pipeline iteration failed: {e}")

        # Wait before next iteration
        sleep_time = 45
        logger.info(f"\nWaiting {sleep_time}s before next iteration...\n")
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()
