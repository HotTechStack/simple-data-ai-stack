#!/usr/bin/env python3
"""
Hybrid search implementation combining Elasticsearch and pgvector.

Demonstrates: "Filter 1M docs to 1K with keywords, then vector search the rest"

This is the practical approach that most teams should use:
1. Use Elasticsearch to quickly filter based on exact criteria
2. Use vector search only on the filtered results for semantic ranking
"""

import os
import time
from typing import List, Dict, Optional
from elasticsearch import Elasticsearch
import psycopg2
from sentence_transformers import SentenceTransformer
from rich.console import Console
from rich.table import Table

console = Console()

ES_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "5432")
PG_USER = os.getenv("POSTGRES_USER", "searchuser")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "searchpass")
PG_DB = os.getenv("POSTGRES_DB", "searchdb")


class HybridSearch:
    """
    Hybrid search combining Elasticsearch filtering + pgvector semantic ranking.

    This demonstrates the best practice approach:
    "Filter 1M docs to 1K with keywords, then vector search the rest"
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.es = Elasticsearch([ES_URL])
        self.pg_conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASSWORD,
            dbname=PG_DB
        )
        self.model = SentenceTransformer(model_name)
        console.print(f"[green]✓ Hybrid search initialized[/green]")

    def hybrid_search(
        self,
        query: str,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        in_stock_only: bool = False,
        filter_limit: int = 100,
        final_limit: int = 10
    ) -> Dict:
        """
        Two-stage hybrid search:
        1. Elasticsearch filters documents based on criteria (fast)
        2. pgvector ranks filtered results semantically (accurate)
        """
        total_start = time.time()

        # ═══ STAGE 1: Elasticsearch Filtering ═══
        console.print(f"[yellow]Stage 1: Filtering with Elasticsearch...[/yellow]")
        filter_start = time.time()

        # Build Elasticsearch query for filtering
        filter_clauses = []

        if category:
            filter_clauses.append({"term": {"category": category}})

        if min_price or max_price:
            price_range = {}
            if min_price:
                price_range["gte"] = min_price
            if max_price:
                price_range["lte"] = max_price
            filter_clauses.append({"range": {"price": price_range}})

        if in_stock_only:
            filter_clauses.append({"range": {"stock_quantity": {"gt": 0}}})

        es_query = {
            "query": {
                "bool": {
                    "must": [{"match_all": {}}],
                    "filter": filter_clauses
                }
            },
            "size": filter_limit,
            "_source": ["id", "sku"]  # Only get IDs for next stage
        }

        es_result = self.es.search(index="products", body=es_query)
        filtered_ids = [int(hit["_source"]["id"]) for hit in es_result["hits"]["hits"]]

        filter_time = (time.time() - filter_start) * 1000
        console.print(f"  ✓ Filtered to {len(filtered_ids)} candidates in {filter_time:.2f}ms")

        if not filtered_ids:
            return {
                "results": [],
                "similarities": [],
                "total": 0,
                "filter_time_ms": filter_time,
                "embed_time_ms": 0,
                "vector_search_time_ms": 0,
                "total_time_ms": (time.time() - total_start) * 1000,
                "filtered_count": 0
            }

        # ═══ STAGE 2: Vector Search on Filtered Results ═══
        console.print(f"[yellow]Stage 2: Semantic ranking with pgvector...[/yellow]")

        # Generate query embedding
        embed_start = time.time()
        query_embedding = self.model.encode(query)
        embed_time = (time.time() - embed_start) * 1000
        console.print(f"  ✓ Generated query embedding in {embed_time:.2f}ms")

        # Vector search only on filtered IDs
        vector_start = time.time()

        cur = self.pg_conn.cursor()

        # Create parameter placeholders for the IN clause
        placeholders = ','.join(['%s'] * len(filtered_ids))

        query_sql = f"""
            SELECT
                id, sku, name, description, category, price, stock_quantity, error_code,
                1 - (embedding <=> %s::vector) as similarity
            FROM products
            WHERE id IN ({placeholders})
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """

        params = [query_embedding.tolist()] + filtered_ids + [query_embedding.tolist(), final_limit]
        cur.execute(query_sql, params)

        results = cur.fetchall()
        vector_time = (time.time() - vector_start) * 1000

        console.print(f"  ✓ Ranked {len(filtered_ids)} docs in {vector_time:.2f}ms")

        cur.close()

        # Format results
        formatted_results = []
        similarities = []

        for row in results:
            formatted_results.append({
                "id": row[0],
                "sku": row[1],
                "name": row[2],
                "description": row[3],
                "category": row[4],
                "price": float(row[5]) if row[5] else 0.0,
                "stock_quantity": row[6],
                "error_code": row[7]
            })
            similarities.append(float(row[8]))

        total_time = (time.time() - total_start) * 1000

        return {
            "results": formatted_results,
            "similarities": similarities,
            "total": len(formatted_results),
            "filter_time_ms": filter_time,
            "embed_time_ms": embed_time,
            "vector_search_time_ms": vector_time,
            "total_time_ms": total_time,
            "filtered_count": len(filtered_ids)
        }

    def compare_approaches(
        self,
        query: str,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> Dict:
        """
        Compare all three approaches side-by-side:
        1. Pure keyword search
        2. Pure vector search
        3. Hybrid search
        """
        console.print(f"\n[bold cyan]Comparing Search Approaches[/bold cyan]")
        console.print(f"Query: '{query}'")
        if category:
            console.print(f"Category: {category}")
        if min_price or max_price:
            console.print(f"Price range: ${min_price or 0} - ${max_price or '∞'}")

        # 1. Keyword search
        keyword_start = time.time()
        filter_clauses = []
        must_clauses = [{"match": {"description": query}}]

        if category:
            filter_clauses.append({"term": {"category": category}})
        if min_price or max_price:
            price_range = {}
            if min_price:
                price_range["gte"] = min_price
            if max_price:
                price_range["lte"] = max_price
            filter_clauses.append({"range": {"price": price_range}})

        es_query = {
            "query": {
                "bool": {
                    "must": must_clauses,
                    "filter": filter_clauses
                }
            },
            "size": 5
        }

        keyword_result = self.es.search(index="products", body=es_query)
        keyword_time = (time.time() - keyword_start) * 1000

        # 2. Pure vector search
        vector_start = time.time()
        query_embedding = self.model.encode(query)
        embed_time = (time.time() - vector_start) * 1000

        cur = self.pg_conn.cursor()

        where_clauses = []
        params = [query_embedding.tolist()]

        if category:
            where_clauses.append("category = %s")
            params.append(category)
        if min_price:
            where_clauses.append("price >= %s")
            params.append(min_price)
        if max_price:
            where_clauses.append("price <= %s")
            params.append(max_price)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        query_sql = f"""
            SELECT sku, name, category, price, 1 - (embedding <=> %s::vector) as similarity
            FROM products
            WHERE {where_sql}
            ORDER BY embedding <=> %s::vector
            LIMIT 5
        """

        params.append(query_embedding.tolist())
        cur.execute(query_sql, params)
        vector_results = cur.fetchall()
        vector_time = (time.time() - vector_start) * 1000

        # 3. Hybrid search
        hybrid_result = self.hybrid_search(
            query=query,
            category=category,
            min_price=min_price,
            max_price=max_price,
            final_limit=5
        )

        cur.close()

        return {
            "keyword": {
                "time_ms": keyword_time,
                "count": keyword_result["hits"]["total"]["value"],
                "results": [hit["_source"] for hit in keyword_result["hits"]["hits"]]
            },
            "vector": {
                "time_ms": vector_time,
                "embed_time_ms": embed_time,
                "count": len(vector_results),
                "results": vector_results
            },
            "hybrid": hybrid_result
        }

    def __del__(self):
        """Cleanup connections."""
        if hasattr(self, 'pg_conn'):
            self.pg_conn.close()


def print_hybrid_results(results: Dict, title: str):
    """Pretty print hybrid search results."""
    console.print(f"\n[bold cyan]{title}[/bold cyan]")
    console.print(f"[bold]Performance Breakdown:[/bold]")
    console.print(f"  1. Elasticsearch filtering:    {results['filter_time_ms']:.2f}ms → {results['filtered_count']} candidates")
    console.print(f"  2. Query embedding:            {results['embed_time_ms']:.2f}ms")
    console.print(f"  3. Vector ranking:             {results['vector_search_time_ms']:.2f}ms → {results['total']} results")
    console.print(f"  [green]Total time:                   {results['total_time_ms']:.2f}ms[/green]\n")

    if not results['results']:
        console.print("[yellow]No results found[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Rank", style="dim", width=4)
    table.add_column("SKU", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Price", justify="right")
    table.add_column("Similarity", justify="right", style="blue")

    for i, product in enumerate(results['results'][:5], 1):
        table.add_row(
            str(i),
            product['sku'],
            product['name'][:35] + "..." if len(product['name']) > 35 else product['name'],
            f"${product['price']:.2f}",
            f"{results['similarities'][i-1]:.3f}"
        )

    console.print(table)


def demo_hybrid_search():
    """Demonstrate hybrid search approach."""
    console.print("[bold green]═══ Hybrid Search Demo ═══[/bold green]")
    console.print('[yellow]"Filter 1M docs to 1K with keywords, then vector search the rest"[/yellow]\n')

    searcher = HybridSearch()

    # Example 1: Category + semantic query
    console.print("\n[bold]Example 1: Filtered Semantic Search[/bold]")
    console.print("Scenario: Find ergonomic work items in office supplies under $200")
    results = searcher.hybrid_search(
        query="ergonomic comfortable work setup",
        category="office_supplies",
        max_price=200,
        filter_limit=100,
        final_limit=5
    )
    print_hybrid_results(results, "Hybrid Search: Ergonomic office items")

    # Example 2: Price range + semantic
    console.print("\n[bold]Example 2: Price-Filtered Semantic Search[/bold]")
    console.print("Scenario: Budget-friendly fitness equipment")
    results = searcher.hybrid_search(
        query="home workout strength training",
        category="sports_fitness",
        max_price=100,
        filter_limit=100,
        final_limit=5
    )
    print_hybrid_results(results, "Hybrid Search: Affordable fitness gear")

    # Example 3: Comparison
    console.print("\n[bold]Example 3: Approach Comparison[/bold]")
    comparison = searcher.compare_approaches(
        query="portable wireless audio",
        category="electronics",
        max_price=150
    )

    console.print(f"\n[bold cyan]Performance Comparison:[/bold cyan]")
    console.print(f"  Keyword search:  {comparison['keyword']['time_ms']:.2f}ms ({comparison['keyword']['count']} results)")
    console.print(f"  Vector search:   {comparison['vector']['time_ms']:.2f}ms ({comparison['vector']['count']} results)")
    console.print(f"  Hybrid search:   {comparison['hybrid']['total_time_ms']:.2f}ms ({comparison['hybrid']['total']} results)")

    console.print("\n[bold green]Key Insights:[/bold green]")
    console.print("  ✓ Elasticsearch quickly filters large datasets")
    console.print("  ✓ Vector search provides semantic ranking on filtered set")
    console.print("  ✓ Hybrid approach combines speed + relevance")
    console.print("  ✓ Best of both worlds for most production use cases")
    console.print(f"\n[bold yellow]This is the 'boring' stack that actually works:[/yellow]")
    console.print("  → Elastic for filters, vectors only when meaning matters\n")


if __name__ == "__main__":
    demo_hybrid_search()
