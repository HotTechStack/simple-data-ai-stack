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
