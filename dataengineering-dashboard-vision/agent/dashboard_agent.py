#!/usr/bin/env python3
"""
CUA Dashboard Agent - Conversational Data Validation
Reads Grafana dashboards and answers questions about your metrics
"""

import asyncio
import os
from datetime import datetime
from computer import Computer
from agent import ComputerAgent


async def analyze_dashboard(question: str):
    """
    Point CUA at Grafana and ask questions about your metrics
    """

    grafana_url = os.getenv("GRAFANA_URL", "http://grafana:3000")
    grafana_user = os.getenv("GRAFANA_USER", "admin")
    grafana_password = os.getenv("GRAFANA_PASSWORD", "admin")

    print(f"\n{'=' * 60}")
    print(f"CUA Dashboard Agent - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}")
    print(f"\nQuestion: {question}")
    print(f"\nConnecting to Grafana at {grafana_url}...")

    # Initialize CUA computer (Docker container)
    async with Computer(
            os_type="linux",
            provider_type="docker",
            name="trycua/cua-ubuntu:latest"
    ) as computer:

        print("✓ Computer container started")

        # Initialize agent with Anthropic Claude
        agent = ComputerAgent(
            model="anthropic/claude-3-5-sonnet-20241022",
            tools=[computer],
            max_trajectory_budget=5.0
        )

        print("✓ Agent initialized")

        # Construct the prompt
        task = f"""
Navigate to {grafana_url} and log in with username '{grafana_user}' and password '{grafana_password}'.

Once logged in, analyze the available dashboards and answer this question:
{question}

Look for:
- Metric values and trends
- Anomalies or spikes
- Resource utilization patterns
- Any concerning patterns

Take screenshots of relevant panels and provide a detailed analysis.
"""

        messages = [{"role": "user", "content": task}]

        print("\nAnalyzing dashboard...")
        print("-" * 60)

        # Run the agent
        async for result in agent.run(messages):
            for item in result["output"]:
                if item["type"] == "message":
                    response = item["content"][0]["text"]
                    print(f"\n{response}")

                    # Save output
                    output_file = f"outputs/analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    with open(output_file, "w") as f:
                        f.write(f"Question: {question}\n\n")
                        f.write(f"Analysis:\n{response}\n")
                    print(f"\n✓ Analysis saved to {output_file}")

                elif item["type"] == "reasoning":
                    # Print agent's reasoning steps
                    for summary in item.get("summary", []):
                        if summary["type"] == "summary_text":
                            print(f"  → {summary['text']}")

        print("\n" + "=" * 60)
        print("Analysis complete")
        print("=" * 60 + "\n")


async def run_example_scenarios():
    """
    Run example analysis scenarios
    """

    scenarios = [
        "What metrics are currently being collected? List all available dashboards.",
        "Show me system CPU and memory usage. Are there any concerning trends?",
        "Analyze the last 6 hours of data. Report any spikes or anomalies.",
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n\n{'#' * 60}")
        print(f"Scenario {i}/{len(scenarios)}")
        print(f"{'#' * 60}")

        await analyze_dashboard(scenario)

        if i < len(scenarios):
            print("\nWaiting 10 seconds before next scenario...")
            await asyncio.sleep(10)


async def interactive_mode():
    """
    Interactive mode - ask questions in real-time
    """

    print("\n" + "=" * 60)
    print("CUA Dashboard Agent - Interactive Mode")
    print("=" * 60)
    print("\nAsk questions about your Grafana dashboards.")
    print("Type 'quit' or 'exit' to stop.\n")

    while True:
        try:
            question = input("Your question: ").strip()

            if question.lower() in ['quit', 'exit', 'q']:
                print("\nExiting...")
                break

            if not question:
                continue

            await analyze_dashboard(question)

        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Continuing...\n")


async def main():
    """
    Main entry point
    """

    mode = os.getenv("MODE", "interactive")

    if mode == "examples":
        await run_example_scenarios()
    else:
        await interactive_mode()


if __name__ == "__main__":
    # Check for required API keys
    if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable")
        print("Example: export ANTHROPIC_API_KEY='your-key-here'")
        exit(1)

    asyncio.run(main())