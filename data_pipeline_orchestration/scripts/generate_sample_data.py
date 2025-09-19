#!/usr/bin/env python3
"""
Simple Sample Data Generator
"""

import os
import logging
import random
from datetime import datetime, timedelta
import polars as pl
from minio import Minio
from minio.error import S3Error

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_minio_client():
    """Create MinIO client"""
    return Minio(
        endpoint='minio:9000',
        access_key='minioadmin',
        secret_key='minioadmin123',
        secure=False
    )

def generate_sales_data(num_records=10000):
    """Generate sample sales data"""
    logger.info(f"Generating {num_records} sales records")
    
    products = ['Widget A', 'Widget B', 'Gadget X', 'Tool Pro']
    regions = ['North', 'South', 'East', 'West']
    
    data = []
    start_date = datetime.now() - timedelta(days=365)
    
    for i in range(num_records):
        record = {
            'transaction_id': f'TXN_{i+1:08d}',
            'product_name': random.choice(products),
            'region': random.choice(regions),
            'quantity': random.randint(1, 100),
            'unit_price': round(random.uniform(10, 1000), 2),
            'transaction_date': (start_date + timedelta(days=random.randint(0, 365))).strftime('%Y-%m-%d'),
            'customer_segment': random.choice(['Enterprise', 'SMB', 'Consumer'])
        }
        
        # Calculate total
        record['total_amount'] = round(record['quantity'] * record['unit_price'], 2)
        data.append(record)
    
    return pl.DataFrame(data)

def upload_to_minio(df, filename, bucket='raw-data'):
    """Upload DataFrame to MinIO"""
    try:
        client = create_minio_client()
        
        # Save locally first
        local_path = f'/tmp/{filename}'
        df.write_csv(local_path)
        
        # Upload to MinIO
        client.fput_object(bucket, filename, local_path)
        
        # Cleanup
        os.remove(local_path)
        
        logger.info(f"Uploaded {filename} to {bucket} bucket")
        return True
        
    except Exception as e:
        logger.error(f"Failed to upload {filename}: {e}")
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, default=5000, help="Number of records to generate")
    parser.add_argument("--large", type=int, help="Generate large dataset with specified size in MB")
    args = parser.parse_args()
    
    if args.large:
        # Rough estimate: 1MB ≈ 1000 records
        estimated_records = args.large * 1000
        logger.info(f"Generating ~{args.large}MB dataset ({estimated_records} records)")
        df = generate_sales_data(estimated_records)
        filename = f'large_dataset_{args.large}mb.csv'
    else:
        df = generate_sales_data(args.records)
        filename = f'sales_data_{args.records}.csv'
    
    if upload_to_minio(df, filename):
        logger.info("Sample data generation completed successfully")
    else:
        logger.error("Sample data generation failed")
        exit(1)

if __name__ == "__main__":
    main()