#!/usr/bin/env python3
"""
Elasticsearch keyword search implementation.

Demonstrates when keyword search excels:
- Exact matches (SKUs, error codes, IDs)
- Boolean logic (AND, OR, NOT)
- Fast indexing and searching
- Filters and facets
"""

import os
import time
from typing import List, Dict, Optional
from elasticsearch import Elasticsearch
from rich.console import Console
from rich.table import Table

console = Console()

ES_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")


class KeywordSearch:
    """Elasticsearch keyword search implementation."""

    def __init__(self, es_url: str = ES_URL, index_name: str = "products"):
        self.es = Elasticsearch([es_url])
        self.index_name = index_name

    def search_by_sku(self, sku: str) -> Dict:
        """
        Search by exact SKU.
        This is where keyword search shines - exact matches.
        """
        start_time = time.time()

        query = {
            "query": {
                "term": {
                    "sku": sku
                }
            }
        }

        result = self.es.search(index=self.index_name, body=query)
        elapsed = time.time() - start_time

        return {
            "results": [hit["_source"] for hit in result["hits"]["hits"]],
            "total": result["hits"]["total"]["value"],
            "time_ms": elapsed * 1000
        }

    def search_by_error_code(self, error_code: str) -> Dict:
        """
        Search by exact error code.
        Perfect for logs, metrics, error tracking - exact match scenarios.
        """
        start_time = time.time()

        query = {
            "query": {
                "term": {
                    "error_code": error_code
                }
            }
        }

        result = self.es.search(index=self.index_name, body=query)
        elapsed = time.time() - start_time

        return {
            "results": [hit["_source"] for hit in result["hits"]["hits"]],
            "total": result["hits"]["total"]["value"],
            "time_ms": elapsed * 1000
        }

    def search_with_filters(
        self,
        query_text: str,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        in_stock_only: bool = False,
        size: int = 10
    ) -> Dict:
        """
        Search with filters - demonstrates Elasticsearch's strength in filtering.
        This is the first step in hybrid search: filter 1M docs to 1K with keywords.
        """
        start_time = time.time()

        # Build query
        must_clauses = []
        filter_clauses = []

        # Text search
        if query_text:
            must_clauses.append({
                "multi_match": {
                    "query": query_text,
                    "fields": ["name^2", "description"],
                    "type": "best_fields"
                }
            })

        # Category filter
        if category:
            filter_clauses.append({"term": {"category": category}})

        # Price range filter
        if min_price or max_price:
            price_range = {}
            if min_price:
                price_range["gte"] = min_price
            if max_price:
                price_range["lte"] = max_price
            filter_clauses.append({"range": {"price": price_range}})

        # Stock filter
        if in_stock_only:
            filter_clauses.append({"range": {"stock_quantity": {"gt": 0}}})

        query = {
            "query": {
                "bool": {
                    "must": must_clauses if must_clauses else [{"match_all": {}}],
                    "filter": filter_clauses
                }
            },
            "size": size
        }

        result = self.es.search(index=self.index_name, body=query)
        elapsed = time.time() - start_time

        return {
            "results": [hit["_source"] for hit in result["hits"]["hits"]],
            "scores": [hit["_score"] for hit in result["hits"]["hits"]],
            "total": result["hits"]["total"]["value"],
            "time_ms": elapsed * 1000
        }

    def search_with_boolean_logic(self, must_have: List[str], must_not_have: List[str], size: int = 10) -> Dict:
        """
        Boolean search - something vector search cannot do well.
        Demonstrates: "Cosine similarity doesn't understand NOT"
        """
        start_time = time.time()

        must_clauses = [{"match": {"description": term}} for term in must_have]
        must_not_clauses = [{"match": {"description": term}} for term in must_not_have]

        query = {
            "query": {
                "bool": {
                    "must": must_clauses,
                    "must_not": must_not_clauses
                }
            },
            "size": size
        }

        result = self.es.search(index=self.index_name, body=query)
        elapsed = time.time() - start_time

        return {
            "results": [hit["_source"] for hit in result["hits"]["hits"]],
            "total": result["hits"]["total"]["value"],
            "time_ms": elapsed * 1000
        }

    def fuzzy_search(self, query_text: str, fuzziness: int = 2, size: int = 10) -> Dict:
        """
        Fuzzy search - handles typos without semantic understanding.
        Blog point: "Most AI search projects fail because teams skip fixing typos and synonyms"
        """
        start_time = time.time()

        query = {
            "query": {
                "multi_match": {
                    "query": query_text,
                    "fields": ["name", "description"],
                    "fuzziness": fuzziness
                }
            },
            "size": size
        }

        result = self.es.search(index=self.index_name, body=query)
        elapsed = time.time() - start_time

        return {
            "results": [hit["_source"] for hit in result["hits"]["hits"]],
            "scores": [hit["_score"] for hit in result["hits"]["hits"]],
            "total": result["hits"]["total"]["value"],
            "time_ms": elapsed * 1000
        }

    def get_aggregations(self, field: str = "category") -> Dict:
        """
        Aggregations - get faceted counts.
        Useful for filtering UI, analytics - not something vector search does.
        """
        start_time = time.time()

        query = {
            "size": 0,
            "aggs": {
                f"{field}_counts": {
                    "terms": {
                        "field": field,
                        "size": 100
                    }
                }
            }
        }

        result = self.es.search(index=self.index_name, body=query)
        elapsed = time.time() - start_time

        buckets = result["aggregations"][f"{field}_counts"]["buckets"]

        return {
            "aggregations": {bucket["key"]: bucket["doc_count"] for bucket in buckets},
            "time_ms": elapsed * 1000
        }


def print_search_results(results: Dict, title: str, show_scores: bool = False):
    """Pretty print search results."""
    console.print(f"\n[bold cyan]{title}[/bold cyan]")
    console.print(f"Found {results['total']} results in {results['time_ms']:.2f}ms\n")

    if not results['results']:
        console.print("[yellow]No results found[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("SKU", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Category", style="yellow")
    table.add_column("Price", justify="right")

    if show_scores and 'scores' in results:
        table.add_column("Score", justify="right", style="blue")

    for i, product in enumerate(results['results'][:5]):  # Show top 5
        row = [
            product['sku'],
            product['name'][:40] + "..." if len(product['name']) > 40 else product['name'],
            product['category'],
            f"${product['price']:.2f}"
        ]

        if show_scores and 'scores' in results:
            row.append(f"{results['scores'][i]:.2f}")

        table.add_row(*row)

    console.print(table)


def demo_keyword_search():
    """Demonstrate various keyword search capabilities."""
    console.print("[bold green]═══ Keyword Search Demo (Elasticsearch) ═══[/bold green]\n")

    searcher = KeywordSearch()

    # 1. Exact SKU search
    console.print("[bold]Scenario 1: Exact SKU Lookup[/bold]")
    console.print("Use case: Customer has exact product code, error code, or ID")
    results = searcher.search_by_sku("ELEC-000001")
    print_search_results(results, "Search for SKU: ELEC-000001")

    # 2. Error code search
    console.print("\n[bold]Scenario 2: Error Code Lookup[/bold]")
    console.print("Use case: Finding products with specific error/recall codes")
    results = searcher.search_by_error_code("ERR-1001")
    print_search_results(results, "Search for error code: ERR-1001")

    # 3. Filtered search
    console.print("\n[bold]Scenario 3: Filtered Search[/bold]")
    console.print("Use case: Filter 1M docs to 1K before semantic search (hybrid approach)")
    results = searcher.search_with_filters(
        query_text="wireless",
        category="electronics",
        min_price=20,
        max_price=100,
        in_stock_only=True
    )
    print_search_results(
        results,
        "Search: 'wireless' in electronics, $20-$100, in stock",
        show_scores=True
    )

    # 4. Boolean logic
    console.print("\n[bold]Scenario 4: Boolean Logic (NOT)[/bold]")
    console.print("Use case: Something vector search cannot do - 'Cosine similarity doesn't understand NOT'")
    results = searcher.search_with_boolean_logic(
        must_have=["wireless"],
        must_not_have=["gaming"]
    )
    print_search_results(results, "Search: wireless BUT NOT gaming")

    # 5. Fuzzy search for typos
    console.print("\n[bold]Scenario 5: Typo Handling[/bold]")
    console.print("Use case: 'Fix typos and synonyms before adding embeddings'")
    results = searcher.fuzzy_search("wireles mous")  # Typos!
    print_search_results(results, "Search with typos: 'wireles mous'", show_scores=True)

    # 6. Aggregations
    console.print("\n[bold]Scenario 6: Faceted Counts[/bold]")
    console.print("Use case: Category counts for filtering UI")
    results = searcher.get_aggregations("category")
    console.print(f"Category aggregations (in {results['time_ms']:.2f}ms):")
    for category, count in results['aggregations'].items():
        console.print(f"  {category}: {count}")

    console.print("\n[bold green]Key Takeaways:[/bold green]")
    console.print("  ✓ Exact matches (SKU, error codes) are instant")
    console.print("  ✓ Boolean logic works perfectly")
    console.print("  ✓ Filtering is extremely fast")
    console.print("  ✓ Handles typos without embeddings")
    console.print("  ✓ All searches completed in milliseconds\n")


if __name__ == "__main__":
    demo_keyword_search()
