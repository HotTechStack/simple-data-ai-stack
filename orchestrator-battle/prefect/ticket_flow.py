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
