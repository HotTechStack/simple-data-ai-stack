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
