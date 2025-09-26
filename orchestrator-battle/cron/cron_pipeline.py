#!/usr/bin/env python3

import sys
import os
sys.path.append('/app/core')

from pipeline import TicketPipeline
import logging

# Configure logging for cron
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/cron.log'),
        logging.StreamHandler()
    ]
)

def main():
    try:
        pipeline = TicketPipeline()
        result = pipeline.run()
        logging.info("Cron pipeline completed successfully")
    except Exception as e:
        logging.error(f"Cron pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
