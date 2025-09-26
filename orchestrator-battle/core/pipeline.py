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
