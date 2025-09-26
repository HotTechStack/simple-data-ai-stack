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
