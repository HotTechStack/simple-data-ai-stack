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
