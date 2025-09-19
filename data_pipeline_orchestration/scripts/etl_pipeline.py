#!/usr/bin/env python3
"""
Simplified ETL Pipeline - Resource monitoring handled by Beszel
"""

import os
import time
import logging
from datetime import datetime
from typing import Optional

import polars as pl
import duckdb
from minio import Minio
from minio.error import S3Error

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MinIOHandler:
    """Handle MinIO operations with error handling"""
    
    def __init__(self):
        self.client = Minio(
            endpoint=os.getenv('MINIO_ENDPOINT', 'minio:9000').replace('http://', ''),
            access_key=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
            secret_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin123'),
            secure=False
        )
    
    def download_file(self, bucket: str, object_name: str, local_path: str) -> bool:
        """Download file from MinIO"""
        try:
            self.client.fget_object(bucket, object_name, local_path)
            logger.info(f"Downloaded {object_name} from {bucket}")
            return True
        except S3Error as e:
            logger.error(f"Failed to download {object_name}: {e}")
            return False
    
    def upload_file(self, bucket: str, object_name: str, local_path: str) -> bool:
        """Upload file to MinIO"""
        try:
            self.client.fput_object(bucket, object_name, local_path)
            logger.info(f"Uploaded {object_name} to {bucket}")
            return True
        except S3Error as e:
            logger.error(f"Failed to upload {object_name}: {e}")
            return False
    
    def list_objects(self, bucket: str, prefix: str = "") -> list:
        """List objects in bucket"""
        try:
            objects = list(self.client.list_objects(bucket, prefix=prefix))
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"Failed to list objects in {bucket}: {e}")
            return []

class ETLPipeline:
    """Simplified ETL Pipeline - monitoring handled externally by Beszel"""
    
    def __init__(self, chunk_size: int = None):
        self.minio = MinIOHandler()
        self.duckdb_conn = duckdb.connect(':memory:')
        self.chunk_size = chunk_size or int(os.getenv('ETL_CHUNK_SIZE', '50000'))
        
        # Setup DuckDB with reasonable settings
        self.duckdb_conn.execute("SET memory_limit='4GB'")
        self.duckdb_conn.execute("SET threads=4")
    
    def extract_data(self, source_bucket: str = "raw-data") -> Optional[pl.DataFrame]:
        """Extract data from MinIO"""
        logger.info("Starting data extraction...")
        
        # List available files
        files = self.minio.list_objects(source_bucket)
        csv_files = [f for f in files if f.endswith('.csv')]
        
        if not csv_files:
            logger.warning("No CSV files found in raw-data bucket")
            return None
        
        # Process first file (extend for multiple files)
        file_name = csv_files[0]
        local_path = f"/tmp/{file_name}"
        
        if not self.minio.download_file(source_bucket, file_name, local_path):
            return None
        
        try:
            # Check file size and use chunking if needed
            file_size_mb = os.path.getsize(local_path) / (1024 * 1024)
            logger.info(f"Processing file: {file_name} ({file_size_mb:.2f} MB)")
            
            if file_size_mb > 100:  # > 100MB files use chunking
                logger.info(f"Large file detected, processing in chunks of {self.chunk_size} rows")
                df = pl.scan_csv(local_path).head(self.chunk_size).collect()
            else:
                df = pl.read_csv(local_path)
            
            logger.info(f"Extracted {df.height} rows, {df.width} columns")
            return df
            
        except Exception as e:
            logger.error(f"Failed to read CSV file: {e}")
            return None
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)
    
    def transform_data(self, df: pl.DataFrame) -> pl.DataFrame:
        """Transform data using Polars and DuckDB"""
        logger.info("Starting data transformation...")
        
        try:
            # Basic transformations using Polars
            transformed_df = (
                df
                .with_columns([
                    pl.col("*").fill_null(""),
                    pl.lit(datetime.now()).alias("processed_at")
                ])
                .filter(pl.all_horizontal(pl.col("*") != ""))
            )
            
            # Use DuckDB for complex analytical transformations
            self.duckdb_conn.register('temp_df', transformed_df.to_pandas())
            
            result = self.duckdb_conn.execute("""
                SELECT *, 
                       ROW_NUMBER() OVER() as row_id,
                       CURRENT_TIMESTAMP as etl_timestamp
                FROM temp_df
            """).fetchdf()
            
            transformed_df = pl.from_pandas(result)
            
            logger.info(f"Transformed data: {transformed_df.height} rows, {transformed_df.width} columns")
            return transformed_df
            
        except Exception as e:
            logger.error(f"Transformation failed: {e}")
            return df
    
    def load_data(self, df: pl.DataFrame, target_bucket: str = "processed-data") -> bool:
        """Load transformed data to MinIO"""
        logger.info("Starting data loading...")
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"processed_data_{timestamp}.parquet"
            local_path = f"/tmp/{output_file}"
            
            # Save as Parquet for better performance
            df.write_parquet(local_path, compression="snappy")
            
            # Upload to MinIO
            success = self.minio.upload_file(target_bucket, output_file, local_path)
            
            if success:
                logger.info(f"Successfully loaded data to {target_bucket}/{output_file}")
                
                # Save summary statistics
                summary_file = f"summary_{timestamp}.json"
                summary_path = f"/tmp/{summary_file}"
                
                summary = {
                    "row_count": df.height,
                    "column_count": df.width,
                    "file_size_mb": os.path.getsize(local_path) / (1024 * 1024),
                    "processed_at": datetime.now().isoformat()
                }
                
                with open(summary_path, 'w') as f:
                    import json
                    json.dump(summary, f, indent=2)
                
                self.minio.upload_file(target_bucket, summary_file, summary_path)
                
                # Cleanup
                os.remove(local_path)
                os.remove(summary_path)
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Loading failed: {e}")
            return False
    
    def run_pipeline(self) -> bool:
        """Run the complete ETL pipeline"""
        logger.info("Starting ETL Pipeline")
        start_time = time.time()
        
        try:
            # Extract
            df = self.extract_data()
            if df is None:
                logger.error("Extraction failed")
                return False
            
            # Transform
            transformed_df = self.transform_data(df)
            
            # Load
            success = self.load_data(transformed_df)
            
            if success:
                end_time = time.time()
                duration = end_time - start_time
                logger.info(f"ETL Pipeline completed successfully in {duration:.2f} seconds")
                return True
            else:
                logger.error("ETL Pipeline failed at loading stage")
                return False
                
        except Exception as e:
            logger.error(f"ETL Pipeline failed: {e}")
            return False
        finally:
            self.duckdb_conn.close()

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ETL Pipeline")
    parser.add_argument("--chunk-size", type=int, help="Chunk size for large file processing")
    args = parser.parse_args()
    
    pipeline = ETLPipeline(chunk_size=args.chunk_size)
    success = pipeline.run_pipeline()
    
    if success:
        logger.info("ETL Pipeline completed successfully")
        exit(0)
    else:
        logger.error("ETL Pipeline failed")
        exit(1)

if __name__ == "__main__":
    main()