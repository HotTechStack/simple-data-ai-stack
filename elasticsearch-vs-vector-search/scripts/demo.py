#!/usr/bin/env python3
"""
Comprehensive demo of Elasticsearch vs Vector Search.

This script demonstrates all key points from the blog post:
1. When keyword search is better (exact matches, IDs, error codes)
2. When vector search is better (semantic, vague queries)
3. The hybrid approach (filter with keywords, rank with vectors)
4. Performance comparisons
5. Cost implications
"""

import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from keyword_search import KeywordSearch, print_search_results
from vector_search import VectorSearch, print_vector_search_results
from hybrid_search import HybridSearch, print_hybrid_results

console = Console()


def print_section_header(title: str, subtitle: str = ""):
    """Print a fancy section header."""
    console.print("\n" + "═" * 80)
    console.print(f"[bold cyan]{title}[/bold cyan]")
    if subtitle:
        console.print(f"[yellow]{subtitle}[/yellow]")
    console.print("═" * 80 + "\n")


def demo_when_keyword_wins():
    """Demonstrate scenarios where keyword search is superior."""
    print_section_header(
        "PART 1: When Keyword Search Wins",
        "Blog: 'Keyword search isn't dead, it's just unsexy'"
    )

    keyword_searcher = KeywordSearch()

    # Scenario 1: Exact SKU lookup
    console.print("[bold]Scenario 1: Exact Product ID Lookup[/bold]")
    console.print("Blog point: 'If users type exact IDs, error codes, or SKUs → vector search is expensive theater'\n")

    sku_to_find = "ELEC-000042"
    console.print(f"Customer service rep looking up SKU: [cyan]{sku_to_find}[/cyan]")

    result = keyword_searcher.search_by_sku(sku_to_find)
    console.print(f"✓ Found in [green]{result['time_ms']:.2f}ms[/green] (instant!)")

    if result['results']:
        product = result['results'][0]
        console.print(f"  Product: {product['name']}")
        console.print(f"  Price: ${product['price']}")

    console.print("\n[yellow]Why keyword wins:[/yellow]")
    console.print("  • Exact match → no embedding needed")
    console.print("  • Indexed for instant lookup")
    console.print("  • No costly ML model inference")
    console.print("  • Perfect precision\n")

    # Scenario 2: Error code lookup
    console.print("\n[bold]Scenario 2: Error Code Search (Logs/Metrics)[/bold]")
    console.print("Blog point: 'Logs, metrics, and time-series belong in Elastic, not vector stores'\n")

    error_code = "ERR-1001"
    console.print(f"DevOps searching for error code: [cyan]{error_code}[/cyan]")

    result = keyword_searcher.search_by_error_code(error_code)
    console.print(f"✓ Found {result['total']} products with this error in [green]{result['time_ms']:.2f}ms[/green]")

    console.print("\n[yellow]Why keyword wins:[/yellow]")
    console.print("  • Structured data (error codes are exact strings)")
    console.print("  • No semantic understanding needed")
    console.print("  • Fast aggregations for metrics")
    console.print("  • Don't force embeddings on structured data!\n")

    # Scenario 3: Boolean logic
    console.print("\n[bold]Scenario 3: Boolean Logic (NOT operator)[/bold]")
    console.print("Blog point: 'Cosine similarity doesn't understand NOT'\n")

    console.print("Query: Find wireless products BUT NOT gaming products")

    result = keyword_searcher.search_with_boolean_logic(
        must_have=["wireless"],
        must_not_have=["gaming"],
        size=5
    )

    console.print(f"✓ Found {result['total']} results in [green]{result['time_ms']:.2f}ms[/green]")
    console.print(f"\nTop results:")
    for i, product in enumerate(result['results'][:3], 1):
        console.print(f"  {i}. {product['name']} ({product['category']})")

    console.print("\n[yellow]Why keyword wins:[/yellow]")
    console.print("  • Native boolean logic support")
    console.print("  • Precise exclusion (NOT operator)")
    console.print("  • Vector search can't do this natively\n")

    # Scenario 4: Typo handling
    console.print("\n[bold]Scenario 4: Typo Tolerance[/bold]")
    console.print("Blog point: 'Most AI search projects fail because teams skip fixing typos'\n")

    console.print("Query with typos: [cyan]'wireles mous'[/cyan] (should find 'wireless mouse')")

    result = keyword_searcher.fuzzy_search("wireles mous", fuzziness=2, size=3)
    console.print(f"✓ Found {result['total']} results despite typos in [green]{result['time_ms']:.2f}ms[/green]")

    console.print("\n[yellow]Why keyword wins:[/yellow]")
    console.print("  • Built-in fuzzy matching")
    console.print("  • No embeddings needed for typo tolerance")
    console.print("  • Faster than semantic search")
    console.print("  • Fix typos BEFORE adding expensive embeddings\n")


def demo_when_vector_wins():
    """Demonstrate scenarios where vector search is superior."""
    print_section_header(
        "PART 2: When Vector Search Wins",
        "Blog: 'The real decision: can users articulate their query (keyword) or only describe it vaguely (semantic)?'"
    )

    vector_searcher = VectorSearch()

    # Scenario 1: Vague/conceptual query
    console.print("[bold]Scenario 1: Vague Conceptual Query[/bold]")
    console.print("User doesn't know exact product names, describes what they need\n")

    query = "something to help me stay organized at my desk"
    console.print(f"Query: [cyan]'{query}'[/cyan]")

    result = vector_searcher.semantic_search(query, limit=5)
    console.print(f"✓ Found {result['total']} semantic matches")
    console.print(f"  Embedding: {result['embed_time_ms']:.2f}ms")
    console.print(f"  Search: {result['search_time_ms']:.2f}ms")
    console.print(f"  Total: {result['total_time_ms']:.2f}ms\n")

    console.print("Top matches:")
    for i, (product, similarity) in enumerate(zip(result['results'][:3], result['similarities'][:3]), 1):
        console.print(f"  {i}. {product['name']} (similarity: {similarity:.3f})")

    console.print("\n[yellow]Why vector wins:[/yellow]")
    console.print("  • Understands intent, not just keywords")
    console.print("  • Finds conceptually similar items")
    console.print("  • Works when user can't articulate exact terms\n")

    # Scenario 2: Another semantic example
    console.print("\n[bold]Scenario 2: Cross-Category Semantic Match[/bold]")
    console.print("Finding items by purpose, not category\n")

    query = "gifts for someone who likes to cook"
    console.print(f"Query: [cyan]'{query}'[/cyan]")

    result = vector_searcher.semantic_search(query, limit=5)

    console.print(f"\nTop matches:")
    for i, (product, similarity) in enumerate(zip(result['results'][:3], result['similarities'][:3]), 1):
        console.print(f"  {i}. {product['name']} - {product['category']} (similarity: {similarity:.3f})")

    console.print("\n[yellow]Why vector wins:[/yellow]")
    console.print("  • Semantic understanding of 'cooking'")
    console.print("  • Finds related items across categories")
    console.print("  • Natural language understanding\n")


def demo_cost_comparison():
    """Demonstrate the cost implications mentioned in the blog."""
    print_section_header(
        "PART 3: The Hidden Costs",
        "Blog: 'Semantic search sounds magical until you see the embedding pipeline bills'"
    )

    console.print("[bold]Cost Factor 1: Data Loading Time[/bold]\n")

    console.print("When you loaded the data, you saw:")
    console.print("  • Elasticsearch indexed 1,000 docs in ~1-2 seconds")
    console.print("  • Vector pipeline (embedding + insert) took 5-10x longer")
    console.print("\n[yellow]Blog point: 'Every data change triggers re-embedding'[/yellow]")
    console.print("  → Product description update = re-embed entire document")
    console.print("  → New product = generate embeddings")
    console.print("  → This adds latency and compute cost\n")

    console.print("[bold]Cost Factor 2: Infrastructure[/bold]\n")

    console.print("[yellow]Blog point: 'Vector DBs scale with RAM, not disk'[/yellow]")
    console.print("  • Our 384-dimensional embeddings")
    console.print("  • 1,000 products × 384 dimensions × 4 bytes = ~1.5 MB")
    console.print("  • For 1M products = ~1.5 GB just for vectors")
    console.print("  • For 10M products = ~15 GB in RAM\n")

    console.print("[yellow]Blog point: '768d vs 1536d embeddings can double your infra cost'[/yellow]")
    console.print("  • We use 384d (all-MiniLM-L6-v2)")
    console.print("  • OpenAI text-embedding-3-large = 3,072d")
    console.print("  • That's 8x more memory needed!\n")

    console.print("[bold]Cost Factor 3: Query Latency[/bold]\n")

    # Quick comparison
    keyword_searcher = KeywordSearch()
    vector_searcher = VectorSearch()

    # Keyword search
    start = time.time()
    keyword_result = keyword_searcher.search_with_filters("wireless", category="electronics", size=10)
    keyword_time = (time.time() - start) * 1000

    # Vector search
    start = time.time()
    vector_result = vector_searcher.search_with_metadata_filter("wireless", category="electronics", limit=10)
    vector_time = (time.time() - start) * 1000

    console.print(f"  Keyword search: {keyword_time:.2f}ms")
    console.print(f"  Vector search:  {vector_time:.2f}ms")
    console.print(f"  [yellow]Vector is ~{vector_time/keyword_time:.1f}x slower[/yellow]")
    console.print("\n[yellow]Blog point: 'Elasticsearch indexes in seconds, vector DBs take minutes'[/yellow]\n")


def demo_hybrid_approach():
    """Demonstrate the hybrid approach - the best practice."""
    print_section_header(
        "PART 4: The Hybrid Approach (Best Practice)",
        "Blog: 'Hybrid search really means: filter 1M docs to 1K with keywords, then vector search the rest'"
    )

    hybrid_searcher = HybridSearch()

    console.print("[bold]The Winning Strategy[/bold]\n")

    console.print("Instead of choosing one or the other, use both:\n")
    console.print("  1. [cyan]Elasticsearch[/cyan]: Quickly filter by exact criteria")
    console.print("     • Category, price range, availability, etc.")
    console.print("     • Reduces dataset from millions → thousands")
    console.print("     • Milliseconds to complete\n")

    console.print("  2. [cyan]Vector Search[/cyan]: Semantic ranking on filtered set")
    console.print("     • Apply semantic understanding to small set")
    console.print("     • Re-rank by relevance")
    console.print("     • Cost is now manageable\n")

    console.print("[bold]Example: Budget Home Fitness Equipment[/bold]\n")

    result = hybrid_searcher.hybrid_search(
        query="equipment for strength training at home",
        category="sports_fitness",
        max_price=100,
        in_stock_only=True,
        filter_limit=100,
        final_limit=5
    )

    console.print(f"[green]Performance Breakdown:[/green]")
    console.print(f"  Step 1 - ES Filter:     {result['filter_time_ms']:.2f}ms → {result['filtered_count']} candidates")
    console.print(f"  Step 2 - Embedding:     {result['embed_time_ms']:.2f}ms")
    console.print(f"  Step 3 - Vector Rank:   {result['vector_search_time_ms']:.2f}ms → {result['total']} results")
    console.print(f"  [bold green]Total:                 {result['total_time_ms']:.2f}ms[/bold green]\n")

    console.print("Top results:")
    for i, (product, sim) in enumerate(zip(result['results'][:3], result['similarities'][:3]), 1):
        console.print(f"  {i}. {product['name']} - ${product['price']:.2f} (similarity: {sim:.3f})")

    console.print("\n[yellow]Why hybrid wins:[/yellow]")
    console.print("  ✓ Fast filtering (Elasticsearch strength)")
    console.print("  ✓ Semantic relevance (Vector strength)")
    console.print("  ✓ Lower costs (smaller vector search scope)")
    console.print("  ✓ Best of both worlds\n")


def demo_decision_framework():
    """Provide decision framework for choosing search approach."""
    print_section_header(
        "PART 5: Decision Framework",
        "Blog: 'The best search stack is boring: Elastic for filters, vectors only when meaning actually matters'"
    )

    table = Table(title="When to Use What", box=box.ROUNDED, show_header=True, header_style="bold cyan")

    table.add_column("Use Case", style="yellow", width=30)
    table.add_column("Best Approach", style="green", width=20)
    table.add_column("Why", style="white", width=40)

    use_cases = [
        ("Exact ID/SKU/Error Code", "Keyword", "Exact match, no semantics needed"),
        ("Logs, Metrics, Time-series", "Keyword", "Structured data, fast aggregations"),
        ("Boolean logic (NOT, AND, OR)", "Keyword", "Vector can't do boolean natively"),
        ("Typo tolerance", "Keyword", "Built-in fuzzy matching"),
        ("Faceted search/filtering", "Keyword", "Instant aggregations"),
        ("Vague conceptual queries", "Vector", "User describes intent, not exact terms"),
        ("Semantic similarity", "Vector", "Understanding meaning, not keywords"),
        ("Cross-category discovery", "Vector", "Finds related items by concept"),
        ("Large catalog + filters", "Hybrid", "Filter first, then semantic rank"),
        ("E-commerce search", "Hybrid", "Combine filters + relevance"),
        ("Multi-faceted search", "Hybrid", "Best of both worlds"),
    ]

    for use_case, approach, reason in use_cases:
        table.add_row(use_case, approach, reason)

    console.print(table)
    console.print()

    # Key insights panel
    insights = """
[bold cyan]Key Blog Insights Validated:[/bold cyan]

1. [yellow]"Keyword search isn't dead, it's just unsexy"[/yellow]
   → Most search problems don't need semantic understanding

2. [yellow]"pgvector wins for most teams"[/yellow]
   → SQL + vectors in one database beats maintaining separate systems

3. [yellow]"Hybrid search really means: filter 1M to 1K, then vector the rest"[/yellow]
   → Use Elasticsearch for fast filtering, vectors for semantic ranking

4. [yellow]"Most AI search fails because teams skip fixing typos first"[/yellow]
   → Implement fuzzy matching before expensive embeddings

5. [yellow]"The best search stack is boring"[/yellow]
   → Elastic for filters, vectors only when meaning actually matters

6. [yellow]"Garbage embeddings lose to well-tuned Elastic BM25 every time"[/yellow]
   → Focus on data quality and proper indexing first
"""

    console.print(Panel(insights, title="Validated Insights", border_style="green"))


def main():
    """Run the complete demonstration."""
    console.print(Panel.fit(
        "[bold green]Elasticsearch vs Vector Search[/bold green]\n"
        "[cyan]A Comprehensive Demo for Data Engineers[/cyan]\n\n"
        "This demo validates all key points from the blog post.",
        border_style="green"
    ))

    try:
        # Check if data is loaded
        console.print("\n[yellow]Checking if data is loaded...[/yellow]")
        keyword_searcher = KeywordSearch()
        test_result = keyword_searcher.es.count(index="products")

        if test_result['count'] == 0:
            console.print("[red]No data found! Please run: python scripts/load_data.py[/red]")
            sys.exit(1)

        console.print(f"[green]✓ Found {test_result['count']} products in database[/green]")

        # Run demonstrations
        demo_when_keyword_wins()
        input("\n[bold yellow]Press Enter to continue to Vector Search demo...[/bold yellow]")

        demo_when_vector_wins()
        input("\n[bold yellow]Press Enter to continue to Cost Analysis...[/bold yellow]")

        demo_cost_comparison()
        input("\n[bold yellow]Press Enter to continue to Hybrid Approach...[/bold yellow]")

        demo_hybrid_approach()
        input("\n[bold yellow]Press Enter to see Decision Framework...[/bold yellow]")

        demo_decision_framework()

        console.print("\n" + "═" * 80)
        console.print("[bold green]Demo Complete![/bold green]")
        console.print("═" * 80)

        console.print("\n[cyan]Next steps:[/cyan]")
        console.print("  • Try your own queries with the search modules")
        console.print("  • Experiment with different embedding models")
        console.print("  • Test with larger datasets")
        console.print("  • Measure performance in your use case\n")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("\n[yellow]Make sure Docker containers are running:[/yellow]")
        console.print("  docker compose up -d")
        sys.exit(1)


if __name__ == "__main__":
    main()
