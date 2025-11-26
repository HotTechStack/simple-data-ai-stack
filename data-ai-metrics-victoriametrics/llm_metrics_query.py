"""
LLM-Powered VictoriaMetrics Query Interface

Demonstrates:
- Natural language to PromQL conversion using OpenAI function calling
- Direct querying of VictoriaMetrics from LLM
- Unified observability for AI-enhanced pipelines (LLM tokens + data processing metrics)
"""

import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


class LLMMetricsQuerying:
    """Natural language interface to VictoriaMetrics"""

    def __init__(self, vm_url: str = "http://localhost:8428"):
        self.vm_url = vm_url

    def query_victoriametrics(self, promql: str, query_type: str = "instant") -> dict:
        """Execute PromQL query against VictoriaMetrics"""
        try:
            if query_type == "instant":
                response = requests.get(
                    f"{self.vm_url}/api/v1/query",
                    params={'query': promql}
                )
            else:  # range query
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=1)
                response = requests.get(
                    f"{self.vm_url}/api/v1/query_range",
                    params={
                        'query': promql,
                        'start': int(start_time.timestamp()),
                        'end': int(end_time.timestamp()),
                        'step': '1m'
                    }
                )

            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def format_vm_result(self, result: dict) -> str:
        """Format VictoriaMetrics result for human readability"""
        if "error" in result:
            return f"Error: {result['error']}"

        if result.get('status') != 'success':
            return f"Query failed: {result}"

        data = result.get('data', {})
        result_type = data.get('resultType')
        results = data.get('result', [])

        if not results:
            return "No data found for this query."

        formatted_lines = []

        if result_type == 'vector':
            for item in results:
                metric = item.get('metric', {})
                value = item.get('value', [None, None])[1]
                labels = ', '.join([f"{k}={v}" for k, v in metric.items()])
                formatted_lines.append(f"  • {labels}: {value}")

        elif result_type == 'matrix':
            for item in results:
                metric = item.get('metric', {})
                values = item.get('values', [])
                labels = ', '.join([f"{k}={v}" for k, v in metric.items()])
                formatted_lines.append(f"  • {labels}: {len(values)} data points")

        return "\n".join(formatted_lines) if formatted_lines else "No results"

    # Define function schema for OpenAI function calling
    FUNCTIONS = [
        {
            "name": "query_pipeline_metrics",
            "description": "Query data pipeline metrics from VictoriaMetrics using PromQL. Use this to answer questions about pipeline performance, errors, data quality, throughput, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "promql": {
                        "type": "string",
                        "description": "The PromQL query to execute. Examples: 'sum(pipeline_rows_processed_total)', 'rate(pipeline_rows_processed_total[5m])', 'pipeline_data_quality_score{check_type=\"overall\"}'",
                    },
                    "query_type": {
                        "type": "string",
                        "enum": ["instant", "range"],
                        "description": "Type of query: 'instant' for current value, 'range' for time series data",
                    }
                },
                "required": ["promql", "query_type"],
            },
        },
        {
            "name": "get_pipeline_status",
            "description": "Get overall status and health of data pipelines",
            "parameters": {
                "type": "object",
                "properties": {
                    "pipeline_name": {
                        "type": "string",
                        "description": "Name of the pipeline (optional, leave empty for all pipelines)",
                    }
                },
            },
        },
    ]

    def handle_function_call(self, function_name: str, arguments: dict) -> str:
        """Handle function calls from OpenAI"""

        if function_name == "query_pipeline_metrics":
            promql = arguments.get("promql")
            query_type = arguments.get("query_type", "instant")

            result = self.query_victoriametrics(promql, query_type)
            formatted = self.format_vm_result(result)

            return f"Query Result:\n{formatted}"

        elif function_name == "get_pipeline_status":
            pipeline_name = arguments.get("pipeline_name", "")

            # Get multiple metrics for comprehensive status
            queries = [
                ("Total Rows", f"sum(pipeline_rows_processed_total)"),
                ("Data Quality", f"pipeline_data_quality_score{{check_type='overall'}}"),
                ("Errors", f"sum(pipeline_errors_total)"),
                ("Throughput", f"sum(rate(pipeline_rows_processed_total[5m]))"),
            ]

            status_lines = ["Pipeline Status:"]
            for label, query in queries:
                result = self.query_victoriametrics(query, "instant")
                formatted = self.format_vm_result(result)
                status_lines.append(f"\n{label}:\n{formatted}")

            return "\n".join(status_lines)

        return f"Unknown function: {function_name}"

    def chat(self, user_question: str) -> str:
        """
        Process natural language question about metrics
        Uses OpenAI function calling to convert to PromQL
        """
        print(f"\n💬 User: {user_question}")

        messages = [
            {
                "role": "system",
                "content": """You are a data pipeline observability expert. You help users understand their pipeline metrics stored in VictoriaMetrics.

Available metrics:
- pipeline_rows_processed_total: Total rows processed by stage
- pipeline_stage_duration_seconds: Time spent in each stage
- pipeline_data_quality_score: Quality scores (0-100) by check type
- pipeline_errors_total: Error counts by stage and type
- pipeline_data_freshness_seconds: Age of most recent data

Common PromQL patterns:
- Current totals: sum(metric_name)
- Rates: rate(metric_name[5m])
- By label: sum by (label_name) (metric_name)
- Aggregations: avg, max, min, count

Always use function calling to query metrics. Explain results in simple terms."""
            },
            {
                "role": "user",
                "content": user_question
            }
        ]

        # Initial call with function definitions
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=[{"type": "function", "function": f} for f in self.FUNCTIONS],
            tool_choice="auto",
        )

        assistant_message = response.choices[0].message
        messages.append(assistant_message)

        # Handle function calls
        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                print(f"\n🔧 Function Call: {function_name}")
                print(f"   Arguments: {json.dumps(arguments, indent=2)}")

                # Execute function
                function_result = self.handle_function_call(function_name, arguments)

                # Add function result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": function_result
                })

            # Get final response with function results
            final_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )

            answer = final_response.choices[0].message.content
        else:
            answer = assistant_message.content

        print(f"\n🤖 Assistant: {answer}\n")
        return answer


def demo_queries():
    """Demonstrate various natural language queries"""

    llm_query = LLMMetricsQuerying()

    # Example questions that get translated to PromQL
    questions = [
        "How many total rows have been processed across all pipelines?",
        "What's the current data quality score?",
        "Which ETL jobs failed today?",
        "Show me the throughput rate for each pipeline stage",
        "Are there any errors in the pipeline?",
        "What's the average processing time per stage?",
    ]

    print("="*70)
    print("LLM-Powered VictoriaMetrics Query Interface")
    print("="*70)
    print("\nThis demonstrates natural language to PromQL conversion")
    print("using OpenAI function calling.\n")

    for i, question in enumerate(questions, 1):
        print(f"\n{'='*70}")
        print(f"Example {i}/{len(questions)}")
        print('='*70)

        try:
            llm_query.chat(question)
        except requests.exceptions.ConnectionError:
            print("\n❌ Cannot connect to VictoriaMetrics!")
            print("   Make sure Docker Compose is running: docker compose up -d")
            print("   And that polars_pipeline.py has run to generate some metrics\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")

        # Pause between queries
        import time
        time.sleep(2)


def interactive_mode():
    """Interactive chat mode for querying metrics"""
    llm_query = LLMMetricsQuerying()

    print("\n" + "="*70)
    print("Interactive LLM Metrics Query Mode")
    print("="*70)
    print("\nAsk questions about your pipeline metrics in natural language.")
    print("Examples:")
    print("  - How many rows were processed?")
    print("  - What's the data quality score?")
    print("  - Show me error rates by stage")
    print("\nType 'quit' or 'exit' to stop.\n")

    while True:
        try:
            question = input("💬 You: ").strip()

            if not question:
                continue

            if question.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye! 👋\n")
                break

            llm_query.chat(question)

        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


def main():
    """Main entry point"""
    import sys

    if not os.environ.get("OPENAI_API_KEY"):
        print("\n❌ Error: OPENAI_API_KEY not found in environment")
        print("   Create a .env file with: OPENAI_API_KEY=your_key_here\n")
        sys.exit(1)

    # Check if VictoriaMetrics is accessible
    try:
        response = requests.get("http://localhost:8428/api/v1/query?query=up", timeout=2)
        response.raise_for_status()
    except Exception:
        print("\n❌ Cannot connect to VictoriaMetrics at http://localhost:8428")
        print("   Make sure Docker Compose is running: docker compose up -d\n")
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_mode()
    else:
        demo_queries()


if __name__ == "__main__":
    main()
