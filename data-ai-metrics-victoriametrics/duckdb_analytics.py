"""
DuckDB Integration with VictoriaMetrics

This demonstrates:
- Querying VictoriaMetrics HTTP API from DuckDB
- Joining pipeline metrics with business data
- Exporting metrics to Parquet for long-term analysis
- Analytics queries on time-series data
"""

import duckdb
import requests
import json
from datetime import datetime, timedelta
import polars as pl
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class VictoriaMetricsAnalytics:
    """Analytics engine combining VictoriaMetrics and DuckDB"""

    def __init__(self, vm_url: str = "http://localhost:8428"):
        self.vm_url = vm_url
        self.conn = duckdb.connect()
        logger.info(f"Connected to VictoriaMetrics at {vm_url}")

    def query_vm_instant(self, promql: str) -> dict:
        """Execute instant PromQL query against VictoriaMetrics"""
        try:
            response = requests.get(
                f"{self.vm_url}/api/v1/query",
                params={'query': promql}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to query VictoriaMetrics: {e}")
            raise

    def query_vm_range(self, promql: str, start: str, end: str, step: str = "30s") -> dict:
        """Execute range PromQL query against VictoriaMetrics"""
        try:
            response = requests.get(
                f"{self.vm_url}/api/v1/query_range",
                params={
                    'query': promql,
                    'start': start,
                    'end': end,
                    'step': step
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to query VictoriaMetrics range: {e}")
            raise

    def vm_to_dataframe(self, vm_result: dict) -> pl.DataFrame:
        """Convert VictoriaMetrics result to Polars DataFrame"""
        if vm_result['status'] != 'success':
            raise ValueError(f"Query failed: {vm_result}")

        result_type = vm_result['data']['resultType']

        if result_type == 'vector':
            # Instant query result
            data = []
            for item in vm_result['data']['result']:
                metric_labels = item['metric']
                value = float(item['value'][1])
                timestamp = item['value'][0]

                row = {**metric_labels, 'value': value, 'timestamp': timestamp}
                data.append(row)

            return pl.DataFrame(data) if data else pl.DataFrame()

        elif result_type == 'matrix':
            # Range query result
            data = []
            for item in vm_result['data']['result']:
                metric_labels = item['metric']
                for timestamp, value in item['values']:
                    row = {**metric_labels, 'value': float(value), 'timestamp': timestamp}
                    data.append(row)

            return pl.DataFrame(data) if data else pl.DataFrame()

        else:
            raise ValueError(f"Unsupported result type: {result_type}")

    def get_pipeline_summary(self) -> pl.DataFrame:
        """Get summary of all pipeline runs"""
        logger.info("Fetching pipeline summary...")

        query = 'sum by (pipeline_name, environment) (pipeline_rows_processed_total)'
        result = self.query_vm_instant(query)
        df = self.vm_to_dataframe(result)

        if not df.is_empty():
            logger.info(f"Found {len(df)} pipeline configurations")
            print("\n=== Pipeline Summary ===")
            print(df)

        return df

    def get_stage_performance(self) -> pl.DataFrame:
        """Analyze stage performance metrics"""
        logger.info("Analyzing stage performance...")

        # Get average duration per stage
        query = '''
        avg by (pipeline_name, stage) (
            pipeline_stage_duration_seconds_sum / pipeline_stage_duration_seconds_count
        )
        '''
        result = self.query_vm_instant(query)
        df = self.vm_to_dataframe(result)

        if not df.is_empty():
            df = df.with_columns([
                pl.col('value').alias('avg_duration_seconds')
            ]).sort('avg_duration_seconds', descending=True)

            print("\n=== Stage Performance (Avg Duration) ===")
            print(df)

        return df

    def get_data_quality_trends(self, hours: int = 1) -> pl.DataFrame:
        """Get data quality score trends over time"""
        logger.info(f"Fetching data quality trends for last {hours} hours...")

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        query = 'pipeline_data_quality_score{check_type="overall"}'
        result = self.query_vm_range(
            query,
            start=int(start_time.timestamp()),
            end=int(end_time.timestamp()),
            step="1m"
        )

        df = self.vm_to_dataframe(result)

        if not df.is_empty():
            df = df.with_columns([
                pl.from_epoch(pl.col('timestamp'), time_unit='s').alias('datetime'),
                pl.col('value').alias('quality_score')
            ]).sort('datetime')

            print("\n=== Data Quality Trends ===")
            print(df.tail(10))

        return df

    def get_error_analysis(self) -> pl.DataFrame:
        """Analyze pipeline errors"""
        logger.info("Analyzing pipeline errors...")

        query = 'sum by (pipeline_name, stage, error_type) (pipeline_errors_total)'
        result = self.query_vm_instant(query)
        df = self.vm_to_dataframe(result)

        if not df.is_empty():
            print("\n=== Error Analysis ===")
            print(df)
        else:
            print("\n=== Error Analysis ===")
            print("No errors detected - pipeline is healthy!")

        return df

    def pipeline_metrics_to_duckdb(self) -> None:
        """Load pipeline metrics into DuckDB for advanced analytics"""
        logger.info("Loading metrics into DuckDB...")

        # Get pipeline rows processed over time
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)

        query = 'sum by (pipeline_name, stage) (rate(pipeline_rows_processed_total[5m]))'
        result = self.query_vm_range(
            query,
            start=int(start_time.timestamp()),
            end=int(end_time.timestamp()),
            step="1m"
        )

        df = self.vm_to_dataframe(result)

        if df.is_empty():
            logger.warning("No metrics data available yet")
            return

        # Convert to pandas for DuckDB (or use Polars directly)
        df_pd = df.to_pandas()

        # Register DataFrame in DuckDB
        self.conn.register('pipeline_metrics', df_pd)

        logger.info("Running DuckDB analytics on metrics...")

        # Example analytics queries
        queries = [
            {
                'name': 'Average throughput by pipeline',
                'sql': '''
                    SELECT
                        pipeline_name,
                        stage,
                        AVG(value) as avg_rows_per_second,
                        MAX(value) as peak_rows_per_second,
                        COUNT(*) as sample_count
                    FROM pipeline_metrics
                    GROUP BY pipeline_name, stage
                    ORDER BY avg_rows_per_second DESC
                '''
            },
            {
                'name': 'Peak processing times',
                'sql': '''
                    SELECT
                        pipeline_name,
                        stage,
                        timestamp,
                        value as rows_per_second
                    FROM pipeline_metrics
                    WHERE value = (SELECT MAX(value) FROM pipeline_metrics)
                '''
            }
        ]

        for query_info in queries:
            print(f"\n=== {query_info['name']} ===")
            result = self.conn.execute(query_info['sql']).fetchdf()
            print(result)

    def export_metrics_to_parquet(self, output_path: str = "output/metrics_export.parquet"):
        """Export VictoriaMetrics data to Parquet for long-term analysis"""
        logger.info(f"Exporting metrics to {output_path}...")

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)

        # Get comprehensive metrics
        query = 'pipeline_rows_processed_total'
        result = self.query_vm_range(
            query,
            start=int(start_time.timestamp()),
            end=int(end_time.timestamp()),
            step="30s"
        )

        df = self.vm_to_dataframe(result)

        if df.is_empty():
            logger.warning("No data to export")
            return

        # Add datetime column
        df = df.with_columns([
            pl.from_epoch(pl.col('timestamp'), time_unit='s').alias('datetime')
        ])

        # Write to Parquet
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.write_parquet(output_path)

        logger.info(f"Exported {len(df)} records to {output_path}")

        # Demonstrate reading back with DuckDB
        print("\n=== Parquet Export Verification ===")
        query = f"SELECT * FROM read_parquet('{output_path}') LIMIT 5"
        result = self.conn.execute(query).fetchdf()
        print(result)

    def join_with_business_data(self):
        """
        Demonstrate joining pipeline metrics with business data
        Simulates correlating processing metrics with revenue
        """
        logger.info("Joining pipeline metrics with business data...")

        # Simulate business data
        business_data = pl.DataFrame({
            'date': [datetime.now().date() - timedelta(days=i) for i in range(7)],
            'revenue': [15000 + i * 1000 for i in range(7)],
            'orders': [150 + i * 10 for i in range(7)],
        })

        print("\n=== Business Data ===")
        print(business_data)

        # Get pipeline metrics for same period
        query = 'sum(pipeline_rows_processed_total)'
        result = self.query_vm_instant(query)
        metrics_df = self.vm_to_dataframe(result)

        if not metrics_df.is_empty():
            print("\n=== Current Pipeline Metrics ===")
            print(metrics_df)

            # In a real scenario, you'd join on date/timestamp
            # This demonstrates the concept
            print("\n✓ Correlation analysis ready - join metrics with revenue data")
            print("  Use case: Spot processing delays that impact revenue")

    def detect_anomalies(self):
        """Detect anomalies in pipeline metrics"""
        logger.info("Detecting anomalies in pipeline performance...")

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)

        # Get stage duration over time
        query = '''
        pipeline_stage_duration_seconds_sum / pipeline_stage_duration_seconds_count
        '''
        result = self.query_vm_range(
            query,
            start=int(start_time.timestamp()),
            end=int(end_time.timestamp()),
            step="1m"
        )

        df = self.vm_to_dataframe(result)

        if df.is_empty():
            logger.warning("Not enough data for anomaly detection")
            return

        # Simple anomaly detection: values > 2x median
        if 'stage' in df.columns:
            for stage in df['stage'].unique():
                stage_df = df.filter(pl.col('stage') == stage)
                median_duration = stage_df['value'].median()
                threshold = median_duration * 2

                anomalies = stage_df.filter(pl.col('value') > threshold)

                if len(anomalies) > 0:
                    print(f"\n⚠️  Anomaly detected in stage '{stage}':")
                    print(f"   Median duration: {median_duration:.2f}s")
                    print(f"   Threshold (2x): {threshold:.2f}s")
                    print(f"   Anomalous readings: {len(anomalies)}")
                else:
                    print(f"\n✓ Stage '{stage}' performing normally")


def main():
    """Run comprehensive analytics demo"""
    print("\n" + "="*60)
    print("VictoriaMetrics + DuckDB Analytics Demo")
    print("="*60)

    analytics = VictoriaMetricsAnalytics()

    try:
        # 1. Pipeline summary
        analytics.get_pipeline_summary()

        # 2. Stage performance
        analytics.get_stage_performance()

        # 3. Data quality trends
        analytics.get_data_quality_trends(hours=1)

        # 4. Error analysis
        analytics.get_error_analysis()

        # 5. DuckDB integration
        analytics.pipeline_metrics_to_duckdb()

        # 6. Export to Parquet
        analytics.export_metrics_to_parquet()

        # 7. Business data correlation
        analytics.join_with_business_data()

        # 8. Anomaly detection
        analytics.detect_anomalies()

        print("\n" + "="*60)
        print("✓ Analytics complete!")
        print("="*60 + "\n")

    except requests.exceptions.ConnectionError:
        logger.error("\n❌ Cannot connect to VictoriaMetrics!")
        logger.error("   Make sure Docker Compose is running: docker compose up -d")
        logger.error("   VictoriaMetrics should be available at http://localhost:8428\n")
    except Exception as e:
        logger.error(f"Analytics failed: {e}")
        raise


if __name__ == "__main__":
    main()
