#!/bin/bash

set -e

echo "🚦 Setting up Orchestrator Battle Demo..."

# Check for required tools
command -v docker >/dev/null 2>&1 || { echo "❌ Docker required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose required but not installed. Aborting." >&2; exit 1; }

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
OPENAI_API_KEY=sk-dummy-key-for-demo
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/dummy/webhook/url
POSTGRES_HOST=postgres
POSTGRES_DB=tickets
POSTGRES_USER=demo
POSTGRES_PASSWORD=demo
EOF
    echo "⚠️  Please update .env with your actual OpenAI API key and Slack webhook URL"
fi

# Generate all code files
echo "📁 Generating core pipeline files..."

# Core pipeline logic
mkdir -p core
cat > core/pipeline.py << 'EOF'
import psycopg2
import requests
import json
from datetime import datetime, timedelta
import os
from typing import List, Dict

class TicketPipeline:
    def __init__(self):
        self.postgres_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'database': os.getenv('POSTGRES_DB', 'tickets'),
            'user': os.getenv('POSTGRES_USER', 'demo'),
            'password': os.getenv('POSTGRES_PASSWORD', 'demo')
        }
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
    
    def extract_tickets(self) -> List[Dict]:
        """Extract yesterday's tickets from Postgres"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        conn = psycopg2.connect(**self.postgres_config)
        cur = conn.cursor()
        
        query = """
        SELECT id, title, description, priority, created_at 
        FROM tickets 
        WHERE DATE(created_at) = %s
        ORDER BY priority DESC, created_at DESC
        """
        
        cur.execute(query, (yesterday,))
        tickets = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return [
            {
                'id': t[0],
                'title': t[1],
                'description': t[2],
                'priority': t[3],
                'created_at': t[4].isoformat()
            }
            for t in tickets
        ]
    
    def summarize_with_llm(self, tickets: List[Dict]) -> str:
        """Generate summary using OpenAI"""
        if not tickets:
            return "No tickets found for yesterday."
        
        tickets_text = "\n".join([
            f"- [{t['priority']}] {t['title']}: {t['description'][:100]}..."
            for t in tickets
        ])
        
        # Mock LLM call for demo (replace with actual OpenAI API call)
        summary = f"""
📊 Daily Ticket Summary ({len(tickets)} tickets)

High Priority: {len([t for t in tickets if t['priority'] == 'high'])}
Medium Priority: {len([t for t in tickets if t['priority'] == 'medium'])}  
Low Priority: {len([t for t in tickets if t['priority'] == 'low'])}

Top Issues:
{tickets_text[:500]}...

Recommendation: Focus on high priority items first.
        """.strip()
        
        return summary
    
    def send_to_slack(self, summary: str):
        """Send summary to Slack webhook"""
        if not self.slack_webhook or 'dummy' in self.slack_webhook:
            print("📤 Would send to Slack:")
            print(summary)
            return
            
        payload = {
            'text': summary,
            'username': 'Ticket Bot',
            'icon_emoji': ':ticket:'
        }
        
        response = requests.post(self.slack_webhook, json=payload)
        if response.status_code != 200:
            raise Exception(f"Slack webhook failed: {response.status_code}")
    
    def run(self):
        """Execute the complete pipeline"""
        print("🎫 Extracting tickets...")
        tickets = self.extract_tickets()
        
        print("🤖 Generating summary...")
        summary = self.summarize_with_llm(tickets)
        
        print("📤 Sending to Slack...")
        self.send_to_slack(summary)
        
        print("✅ Pipeline completed successfully!")
        return summary

if __name__ == "__main__":
    pipeline = TicketPipeline()
    pipeline.run()
EOF

cat > core/requirements.txt << 'EOF'
psycopg2-binary==2.9.7
requests==2.31.0
openai==1.3.0
EOF

# Database setup
mkdir -p data
cat > data/init.sql << 'EOF'
CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data for yesterday and today
INSERT INTO tickets (title, description, priority, created_at) VALUES
('Login page not loading', 'Users cannot access the login page, getting 500 error', 'high', CURRENT_DATE - INTERVAL '1 day'),
('Slow dashboard performance', 'Dashboard takes 30+ seconds to load with large datasets', 'medium', CURRENT_DATE - INTERVAL '1 day'),
('Email notifications delayed', 'User notifications are arriving 2-3 hours late', 'medium', CURRENT_DATE - INTERVAL '1 day'),
('Mobile app crashes on iOS', 'App crashes when user tries to upload files on iOS 17', 'high', CURRENT_DATE - INTERVAL '1 day'),
('Export feature missing data', 'CSV export only showing first 100 rows instead of all data', 'low', CURRENT_DATE - INTERVAL '1 day'),
('Search functionality broken', 'Search returns no results even for existing records', 'high', CURRENT_DATE),
('Password reset emails not sent', 'Users not receiving password reset emails', 'medium', CURRENT_DATE);
EOF

# Cron implementation
mkdir -p cron
cat > cron/cron_pipeline.py << 'EOF'
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
EOF

cat > cron/crontab << 'EOF'
# Run ticket summary every day at 9:00 AM
0 9 * * * /usr/bin/python3 /app/cron/cron_pipeline.py
EOF

# Airflow DAG
mkdir -p airflow/dags
cat > airflow/dags/ticket_summary_dag.py << 'EOF'
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
EOF

# Prefect flow
mkdir -p prefect
cat > prefect/ticket_flow.py << 'EOF'
from prefect import flow, task
from typing import List, Dict
import sys
import os

sys.path.append('/app/core')
from pipeline import TicketPipeline

@task(retries=2, retry_delay_seconds=60)
def extract_tickets() -> List[Dict]:
    """Extract yesterday's tickets from Postgres"""
    pipeline = TicketPipeline()
    return pipeline.extract_tickets()

@task(retries=2, retry_delay_seconds=30)
def summarize_tickets(tickets: List[Dict]) -> str:
    """Generate summary using LLM"""
    pipeline = TicketPipeline()
    return pipeline.summarize_with_llm(tickets)

@task(retries=3, retry_delay_seconds=10)  
def send_to_slack(summary: str):
    """Send summary to Slack"""
    pipeline = TicketPipeline()
    pipeline.send_to_slack(summary)

@flow(name="ticket-summary-flow")
def ticket_summary_flow():
    """Daily ticket summary workflow"""
    tickets = extract_tickets()
    summary = summarize_tickets(tickets)
    send_to_slack(summary)
    return summary

if __name__ == "__main__":
    ticket_summary_flow()
EOF

# Dagster assets
mkdir -p dagster
cat > dagster/ticket_assets.py << 'EOF'
from dagster import asset, AssetExecutionContext, Definitions, ScheduleDefinition
from typing import List, Dict
import sys
import os

sys.path.append('/app/core')
from pipeline import TicketPipeline

@asset(group_name="tickets")
def raw_tickets(context: AssetExecutionContext) -> List[Dict]:
    """Yesterday's support tickets from Postgres"""
    pipeline = TicketPipeline()
    tickets = pipeline.extract_tickets()
    context.log.info(f"Extracted {len(tickets)} tickets")
    return tickets

@asset(deps=[raw_tickets], group_name="tickets")
def ticket_summary(context: AssetExecutionContext, raw_tickets: List[Dict]) -> str:
    """LLM-generated summary of tickets"""
    pipeline = TicketPipeline()
    summary = pipeline.summarize_with_llm(raw_tickets)
    context.log.info("Generated ticket summary")
    return summary

@asset(deps=[ticket_summary], group_name="tickets")
def slack_notification(context: AssetExecutionContext, ticket_summary: str):
    """Send summary to Slack channel"""
    pipeline = TicketPipeline()
    pipeline.send_to_slack(ticket_summary)
    context.log.info("Sent notification to Slack")

# Schedule to run daily at 9 AM
daily_schedule = ScheduleDefinition(
    name="daily_ticket_summary",
    cron_schedule="0 9 * * *",
    target=[raw_tickets, ticket_summary, slack_notification]
)

defs = Definitions(
    assets=[raw_tickets, ticket_summary, slack_notification],
    schedules=[daily_schedule]
)
EOF

# Temporal workflow
mkdir -p temporal
cat > temporal/activities.py << 'EOF'
from temporalio import activity
from typing import List, Dict
import sys
import os

sys.path.append('/app/core')
from pipeline import TicketPipeline

@activity.defn
async def extract_tickets_activity() -> List[Dict]:
    """Extract tickets from database"""
    pipeline = TicketPipeline()
    return pipeline.extract_tickets()

@activity.defn  
async def summarize_tickets_activity(tickets: List[Dict]) -> str:
    """Generate LLM summary"""
    pipeline = TicketPipeline()
    return pipeline.summarize_with_llm(tickets)

@activity.defn
async def send_slack_activity(summary: str):
    """Send to Slack webhook"""
    pipeline = TicketPipeline()
    pipeline.send_to_slack(summary)
EOF

cat > temporal/workflow.py << 'EOF'
from datetime import timedelta
from temporalio import workflow
from typing import List, Dict

with workflow.unsafe.imports_passed_through():
    from activities import (
        extract_tickets_activity,
        summarize_tickets_activity,
        send_slack_activity
    )

@workflow.defn
class TicketSummaryWorkflow:
    @workflow.run
    async def run(self) -> str:
        # Extract tickets with retry policy
        tickets = await workflow.execute_activity(
            extract_tickets_activity,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=workflow.RetryPolicy(maximum_attempts=3)
        )
        
        # Generate summary
        summary = await workflow.execute_activity(
            summarize_tickets_activity,
            tickets,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=workflow.RetryPolicy(maximum_attempts=2)
        )
        
        # Send to Slack
        await workflow.execute_activity(
            send_slack_activity,
            summary,
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=workflow.RetryPolicy(maximum_attempts=3)
        )
        
        return summary

async def main():
    """Run workflow for demo"""
    from temporalio.client import Client
    
    client = await Client.connect("localhost:7233")
    
    result = await client.execute_workflow(
        TicketSummaryWorkflow.run,
        id="ticket-summary-workflow",
        task_queue="ticket-summary-queue"
    )
    
    print(f"Workflow result: {result}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
EOF

cat > temporal/worker.py << 'EOF'
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from workflow import TicketSummaryWorkflow
from activities import (
    extract_tickets_activity,
    summarize_tickets_activity, 
    send_slack_activity
)

async def main():
    client = await Client.connect("localhost:7233")
    
    worker = Worker(
        client,
        task_queue="ticket-summary-queue",
        workflows=[TicketSummaryWorkflow],
        activities=[
            extract_tickets_activity,
            summarize_tickets_activity,
            send_slack_activity
        ]
    )
    
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
EOF

# Flyte workflow  
mkdir -p flyte
cat > flyte/ticket_workflow.py << 'EOF'
from flytekit import task, workflow, LaunchPlan, CronSchedule
from typing import List, Dict
import sys
import os

sys.path.append('/app/core')
from pipeline import TicketPipeline

@task(retries=2, cache=True, cache_version="1.0")
def extract_tickets() -> List[Dict]:
    """Extract yesterday's tickets"""
    pipeline = TicketPipeline()
    return pipeline.extract_tickets()

@task(retries=2, cache=True, cache_version="1.0")
def summarize_tickets(tickets: List[Dict]) -> str:
    """Generate LLM summary with caching"""
    pipeline = TicketPipeline()
    return pipeline.summarize_with_llm(tickets)

@task(retries=3)
def send_to_slack(summary: str):
    """Send notification to Slack"""
    pipeline = TicketPipeline()
    pipeline.send_to_slack(summary)

@workflow
def ticket_summary_workflow() -> str:
    """Daily ticket summary pipeline with ML-style caching"""
    tickets = extract_tickets()
    summary = summarize_tickets(tickets=tickets)
    send_to_slack(summary=summary)
    return summary

# Schedule for daily execution
daily_launch_plan = LaunchPlan.create(
    "daily_ticket_summary",
    ticket_summary_workflow,
    schedule=CronSchedule("0 9 * * *")  # 9 AM daily
)
EOF

# Docker Compose file
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  # Postgres Database
  postgres:
    image: postgres:15
    container_name: postgres-tickets
    environment:
      POSTGRES_DB: tickets
      POSTGRES_USER: demo
      POSTGRES_PASSWORD: demo
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./data/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U demo -d tickets"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Cron Container
  cron-demo:
    build:
      context: .
      dockerfile: Dockerfile.cron
    container_name: cron-container
    depends_on:
      postgres:
        condition: service_healthy
    env_file: .env
    volumes:
      - ./core:/app/core
      - ./cron:/app/cron
      - cron_logs:/var/log

  # Airflow
  airflow-webserver:
    image: apache/airflow:2.7.0-python3.11
    container_name: airflow-webserver
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - AIRFLOW__CORE__EXECUTOR=LocalExecutor
      - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://demo:demo@postgres/tickets
      - AIRFLOW__CORE__FERNET_KEY=YlCImzjge_TeZc4RHSRHPVXphRPQGsluEUhz-WRUmBM=
      - AIRFLOW__WEBSERVER__DEFAULT_USER_USERNAME=admin
      - AIRFLOW__WEBSERVER__DEFAULT_USER_PASSWORD=admin
      - AIRFLOW__WEBSERVER__DEFAULT_USER_EMAIL=admin@example.com
      - AIRFLOW__WEBSERVER__DEFAULT_USER_FIRSTNAME=Admin
      - AIRFLOW__WEBSERVER__DEFAULT_USER_LASTNAME=User
    env_file: .env
    ports:
      - "8080:8080"
    volumes:
      - ./airflow/dags:/opt/airflow/dags
      - ./core:/opt/airflow/core
      - airflow_logs:/opt/airflow/logs
    command: >
      bash -c "
        airflow db init &&
        airflow users create --username admin --password admin --firstname Admin --lastname User --role Admin --email admin@example.com &&
        airflow webserver
      "

  # Prefect
  prefect-server:
    image: prefecthq/prefect:2.14-python3.11
    container_name: prefect-server
    ports:
      - "4200:4200"
    environment:
      - PREFECT_UI_URL=http://localhost:4200/api
      - PREFECT_API_URL=http://localhost:4200/api
      - PREFECT_SERVER_API_HOST=0.0.0.0
    command: prefect server start --host 0.0.0.0

  prefect-agent:
    image: prefecthq/prefect:2.14-python3.11
    container_name: prefect-agent
    depends_on:
      - prefect-server
      - postgres
    env_file: .env
    environment:
      - PREFECT_API_URL=http://prefect-server:4200/api
    volumes:
      - ./prefect:/app/prefect
      - ./core:/app/core
    working_dir: /app/prefect
    command: >
      bash -c "
        pip install psycopg2-binary requests openai &&
        python ticket_flow.py
      "

  # Dagster
  dagster:
    image: dagster/dagster-celery-docker:1.5.0
    container_name: dagster-webserver
    depends_on:
      postgres:
        condition: service_healthy
    env_file: .env
    ports:
      - "3000:3000"
    volumes:
      - ./dagster:/opt/dagster/app/dagster
      - ./core:/opt/dagster/app/core
    environment:
      - DAGSTER_CURRENT_IMAGE=dagster/dagster-celery-docker:1.5.0
    command: >
      bash -c "
        pip install psycopg2-binary requests openai &&
        dagster-webserver -h 0.0.0.0 -p 3000 -w /opt/dagster/app/dagster/ticket_assets.py
      "

  # Temporal
  temporal:
    image: temporalio/auto-setup:1.22.0
    container_name: temporal-server
    ports:
      - "7233:7233"
      - "8088:8088"
    environment:
      - DB=postgresql
      - DB_PORT=5432
      - POSTGRES_USER=demo
      - POSTGRES_PWD=demo
      - POSTGRES_SEEDS=postgres
      - DYNAMIC_CONFIG_FILE_PATH=config/dynamicconfig/development-sql.yaml
    depends_on:
      postgres:
        condition: service_healthy

  temporal-worker:
    build:
      context: .
      dockerfile: Dockerfile.temporal
    container_name: temporal-worker
    depends_on:
      - temporal
      - postgres
    env_file: .env
    volumes:
      - ./temporal:/app/temporal
      - ./core:/app/core

  # Flyte
  flyte-sandbox:
    image: cr.flyte.org/flyteorg/flyte-sandbox:latest
    container_name: flyte-sandbox
    ports:
      - "8089:8089"
      - "8088:8088"
    volumes:
      - ./flyte:/app/flyte
      - ./core:/app/core
    env_file: .env

volumes:
  postgres_data:
  airflow_logs:
  cron_logs:
EOF

# Create Dockerfiles
cat > Dockerfile.cron << 'EOF'
FROM python:3.11-slim

# Install cron
RUN apt-get update && apt-get install -y cron && apt-get clean

# Install Python dependencies
COPY core/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# Setup cron
COPY cron/crontab /etc/cron.d/ticket-summary
RUN chmod 0644 /etc/cron.d/ticket-summary
RUN crontab /etc/cron.d/ticket-summary

# Create log file
RUN touch /var/log/cron.log

WORKDIR /app

# Start cron and follow logs
CMD cron && tail -f /var/log/cron.log
EOF

cat > Dockerfile.temporal << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install temporal SDK
RUN pip install temporalio psycopg2-binary requests openai

# Copy application files
COPY temporal/ ./temporal/
COPY core/ ./core/

CMD ["python", "temporal/worker.py"]
EOF

echo "✅ All files generated successfully!"

# Build and start services
echo "🐳 Starting Docker services..."
docker-compose up -d --build

echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service health
echo "🔍 Checking service status..."
docker-compose ps

echo ""
echo "🎉 Setup complete! Access points:"
echo "   Postgres:  localhost:5432 (user: demo, password: demo, db: tickets)"
echo "   Airflow:   http://localhost:8080 (admin/admin)"
echo "   Prefect:   http://localhost:4200"
echo "   Dagster:   http://localhost:3000"
echo "   Temporal:  http://localhost:8088"
echo "   Flyte:     http://localhost:8089"
echo ""
echo "⚡ To test individual orchestrators:"
echo "   docker exec -it airflow-webserver airflow dags trigger ticket_summary_dag"
echo "   docker exec -it prefect-agent python ticket_flow.py"
echo ""
echo "🔥 To simulate failures:"
echo "   docker stop postgres-tickets  # Kill database mid-pipeline"
echo "   docker start postgres-tickets # Restart to see recovery"
echo ""
echo "📝 Don't forget to update .env with your real API keys!"
EOF

chmod +x setup.sh

echo "✅ Setup script created successfully!"

# Create .gitignore
cat > .gitignore << 'EOF'
# Environment variables
.env

# Docker volumes
postgres_data/
airflow_logs/
cron_logs/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/
EOF

# Create LICENSE
cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2024 Orchestrator Battle

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF

# Create test script
cat > test_pipeline.sh << 'EOF'
#!/bin/bash

echo "🧪 Testing orchestrator implementations..."

echo "1️⃣ Testing core pipeline directly..."
docker exec -it postgres-tickets python /app/core/pipeline.py

echo ""
echo "2️⃣ Testing Airflow DAG..."
docker exec -it airflow-webserver airflow dags trigger ticket_summary_dag

echo ""
echo "3️⃣ Testing Prefect flow..."
docker exec -it prefect-agent python ticket_flow.py

echo ""
echo "4️⃣ Checking Dagster assets (trigger via UI at localhost:3000)..."

echo ""
echo "5️⃣ Testing Temporal workflow..."
docker exec -it temporal-worker python temporal/workflow.py

echo ""
echo "🔥 Chaos testing - killing Postgres for 10 seconds..."
docker stop postgres-tickets
sleep 10
docker start postgres-tickets
echo "Postgres restarted - check how each orchestrator handled the failure!"

echo ""
echo "✅ Tests complete! Check the UIs to see results and error handling."
EOF

chmod +x test_pipeline.sh

# Create quick demo script
cat > demo.sh << 'EOF'
#!/bin/bash

echo "🎬 Running orchestrator demo..."

if [ ! -f .env ]; then
    echo "❌ Please run ./setup.sh first!"
    exit 1
fi

echo "📊 Current ticket data:"
docker exec -it postgres-tickets psql -U demo -d tickets -c "SELECT COUNT(*) as total_tickets, DATE(created_at) as date FROM tickets GROUP BY DATE(created_at) ORDER BY date;"

echo ""
echo "🚦 Running pipeline through different orchestrators..."

echo ""
echo "1️⃣ Cron (check logs):"
docker exec -it cron-container tail -n 20 /var/log/cron.log

echo ""
echo "2️⃣ Direct Python execution:"
docker exec -it postgres-tickets python -c "
import sys
sys.path.append('/app/core')
from pipeline import TicketPipeline
pipeline = TicketPipeline()
result = pipeline.run()
print('✅ Direct execution completed')
"

echo ""
echo "🎯 Demo complete! Visit the web UIs to explore further:"
echo "   • Airflow: http://localhost:8080"
echo "   • Prefect: http://localhost:4200" 
echo "   • Dagster: http://localhost:3000"
echo "   • Temporal: http://localhost:8088"
echo "   • Flyte: http://localhost:8089"
EOF

chmod +x demo.sh

# Create cleanup script
cat > cleanup.sh << 'EOF'
#!/bin/bash

echo "🧹 Cleaning up orchestrator demo..."

echo "Stopping all containers..."
docker-compose down -v

echo "Removing built images..."
docker rmi $(docker images | grep orchestrator-battle | awk '{print $3}') 2>/dev/null || true

echo "Removing dangling images..."
docker image prune -f

echo "✅ Cleanup complete!"
echo ""
echo "To restart the demo, run: ./setup.sh"
EOF

chmod +x cleanup.sh

echo "✅ All scripts and configuration files created!"
echo ""
echo "🚀 Repository ready! To get started:"
echo ""
echo "   git init"
echo "   git add ."
echo "   git commit -m 'Initial commit: Orchestrator Battle Demo'"
echo "   ./setup.sh"
echo ""
echo "📋 Available scripts:"
echo "   ./setup.sh      - Complete setup and start all services"
echo "   ./demo.sh       - Quick demo of core functionality"
echo "   ./test_pipeline.sh - Test all orchestrator implementations"
echo "   ./cleanup.sh    - Clean up all containers and images"
echo ""
echo "🎯 The demo proves the point: same pipeline, 6 orchestrators,"
echo "   each with different complexity tradeoffs."
echo ""
echo "💡 Perfect for your viral post - people can clone and run"
echo "   to experience the exact journey you described!"