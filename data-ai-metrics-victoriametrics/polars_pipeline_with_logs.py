"""
Polars Pipeline with VictoriaLogs Integration

This extends polars_pipeline.py to send structured logs to VictoriaLogs
"""

import logging
import requests
import json
from datetime import datetime
from polars_pipeline import ETLPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VictoriaLogsHandler(logging.Handler):
    """Custom logging handler to send logs to VictoriaLogs"""

    def __init__(self, victoria_logs_url='http://localhost:9428'):
        super().__init__()
        self.url = f"{victoria_logs_url}/insert/jsonline"

    def emit(self, record):
        """Send log record to VictoriaLogs"""
        try:
            log_entry = {
                "_msg": self.format(record),
                "_time": datetime.utcnow().isoformat() + "Z",
                "level": record.levelname,
                "logger": record.name,
                "service_name": "polars_pipeline",
                "environment": "dev",
                "pipeline_name": "etl_pipeline",
            }

            # Add extra fields if available
            if hasattr(record, 'stage'):
                log_entry['stage'] = record.stage
            if hasattr(record, 'rows'):
                log_entry['rows'] = record.rows
            if hasattr(record, 'duration'):
                log_entry['duration'] = record.duration

            # Send to VictoriaLogs
            requests.post(
                self.url,
                data=json.dumps(log_entry),
                headers={'Content-Type': 'application/json'},
                timeout=2
            )
        except Exception as e:
            # Don't let logging errors crash the app
            print(f"Failed to send log to VictoriaLogs: {e}")


def setup_logging():
    """Setup logging to both console and VictoriaLogs"""
    root_logger = logging.getLogger()

    # Add VictoriaLogs handler
    vl_handler = VictoriaLogsHandler()
    vl_handler.setLevel(logging.INFO)
    root_logger.addHandler(vl_handler)

    return root_logger


def main():
    """Run pipeline with VictoriaLogs integration"""
    # Setup logging
    logger = setup_logging()

    logger.info("Starting ETL pipeline with VictoriaLogs integration")

    # Start metrics server
    from prometheus_client import start_http_server, CollectorRegistry
    from polars_pipeline import registry

    logger.info("Starting Prometheus metrics server on port 8000...")
    start_http_server(8000, registry=registry)
    logger.info("Metrics available at http://localhost:8000/metrics")

    # Run pipeline
    iteration = 0
    import time

    while True:
        iteration += 1
        logger.info(f"Pipeline Iteration #{iteration}", extra={
            'stage': 'initialization',
            'iteration': iteration
        })

        try:
            pipeline = ETLPipeline(
                pipeline_name="etl_pipeline",
                environment="dev"
            )

            num_rows = 5000 + (iteration % 3) * 5000

            # Log pipeline start
            start_time = time.time()

            pipeline.run(num_rows=num_rows)

            duration = time.time() - start_time

            # Log pipeline completion
            logger.info(
                f"Pipeline iteration #{iteration} completed successfully",
                extra={
                    'stage': 'completed',
                    'duration': duration,
                    'rows': num_rows,
                    'iteration': iteration
                }
            )

        except Exception as e:
            logger.error(
                f"Pipeline iteration failed: {e}",
                extra={
                    'stage': 'error',
                    'iteration': iteration
                }
            )

        sleep_time = 45
        logger.info(f"Waiting {sleep_time}s before next iteration...")
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()
