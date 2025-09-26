from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os

# Add core to path
sys.path.append('/opt/airflow/core')
from pipeline import TicketPipeline

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}

dag = DAG(
    'ticket_summary_dag',
    default_args=default_args,
    description='Daily ticket summary pipeline',
    schedule_interval='0 9 * * *',  # 9 AM daily
    catchup=False,
    tags=['tickets', 'daily', 'summary']
)

def extract_tickets_task():
    pipeline = TicketPipeline()
    tickets = pipeline.extract_tickets()
    return tickets

def summarize_tickets_task(**context):
    tickets = context['task_instance'].xcom_pull(task_ids='extract_tickets')
    pipeline = TicketPipeline()
    summary = pipeline.summarize_with_llm(tickets)
    return summary

def send_to_slack_task(**context):
    summary = context['task_instance'].xcom_pull(task_ids='summarize_tickets')
    pipeline = TicketPipeline()
    pipeline.send_to_slack(summary)

extract_tickets = PythonOperator(
    task_id='extract_tickets',
    python_callable=extract_tickets_task,
    dag=dag
)

summarize_tickets = PythonOperator(
    task_id='summarize_tickets', 
    python_callable=summarize_tickets_task,
    dag=dag
)

send_to_slack = PythonOperator(
    task_id='send_to_slack',
    python_callable=send_to_slack_task,
    dag=dag
)

extract_tickets >> summarize_tickets >> send_to_slack
