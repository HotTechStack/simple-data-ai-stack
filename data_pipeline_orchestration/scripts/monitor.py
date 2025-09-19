#!/usr/bin/env python3
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("ETL Worker ready - use 'docker-compose exec etl-worker python /app/scripts/etl_pipeline.py'")
    while True:
        logger.info("ETL Worker heartbeat")
        time.sleep(3600)  # Log every hour

if __name__ == "__main__":
    main()
