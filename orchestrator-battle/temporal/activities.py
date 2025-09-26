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
