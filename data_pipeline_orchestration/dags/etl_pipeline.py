"""
Main ETL DAG - Simple and effective
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from airflow.utils.dates import days_ago
import logging

# DAG configuration
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'max_active_runs': 1,
}

# Create DAG
dag = DAG(
    'etl_pipeline',
    default_args=default_args,
    description='Main ETL pipeline',
    schedule_interval=timedelta(hours=2),
    catchup=False,
    max_active_tasks=4,
    tags=['etl', 'production']
)

def run_etl_pipeline(**context):
    """Execute the main ETL pipeline"""
    import subprocess
    import sys
    
    # Get chunk size from DAG run config if provided
    chunk_size = context['dag_run'].conf.get('chunk_size') if context['dag_run'].conf else None
    
    cmd = [sys.executable, '/opt/airflow/dags/../scripts/etl_pipeline.py']
    if chunk_size:
        cmd.extend(['--chunk-size', str(chunk_size)])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        logging.info("ETL Pipeline output:")
        logging.info(result.stdout)
        
        if result.stderr:
            logging.warning("ETL Pipeline warnings:")
            logging.warning(result.stderr)
        
        return "ETL pipeline completed successfully"
        
    except subprocess.CalledProcessError as e:
        logging.error(f"ETL Pipeline failed with return code {e.returncode}")
        logging.error(f"Error output: {e.stderr}")
        raise

def cleanup_temp_data(**context):
    """Clean up temporary data"""
    import os
    import glob
    
    temp_patterns = ['/tmp/*.csv', '/tmp/*.parquet', '/tmp/*.json']
    
    cleaned_files = 0
    for pattern in temp_patterns:
        files = glob.glob(pattern)
        for file in files:
            try:
                os.remove(file)
                cleaned_files += 1
                logging.info(f"Removed temp file: {file}")
            except Exception as e:
                logging.warning(f"Could not remove {file}: {e}")
    
    logging.info(f"Cleanup completed - removed {cleaned_files} temporary files")
    return cleaned_files

# Task definitions
run_etl = PythonOperator(
    task_id='run_etl_pipeline',
    python_callable=run_etl_pipeline,
    dag=dag
)

cleanup = PythonOperator(
    task_id='cleanup_temp_data',
    python_callable=cleanup_temp_data,
    dag=dag
)

# Health check
health_check = BashOperator(
    task_id='system_health_check',
    bash_command='''
        echo "=== ETL Pipeline Health Check ==="
        echo "Timestamp: $(date)"
        echo "Available Memory: $(free -h | grep "Mem:" | awk '{print $7}')"
        echo "Disk Usage: $(df -h / | tail -1 | awk '{print $5}')"
        echo "=== Health Check Complete ==="
    ''',
    dag=dag
)

# Task dependencies
run_etl >> cleanup >> health_check