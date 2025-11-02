#!/usr/bin/env python3
"""
pgvector semantic search implementation.

Demonstrates when vector search excels:
- Semantic understanding ("vague" queries)
- Conceptual similarity
- When users can't articulate exact query

Also demonstrates the costs and limitations mentioned in the blog.
"""

import os
import time
from typing import List, Dict, Optional
import psycopg2
import numpy as np
from sentence_transformers import SentenceTransformer
from rich.console import Console
from rich.table import Table

console = Console()

PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "5432")
PG_USER = os.getenv("POSTGRES_USER", "searchuser")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "searchpass")
PG_DB = os.getenv("POSTGRES_DB", "searchdb")


class VectorSearch:
    """pgvector semantic search implementation."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASSWORD,
            dbname=PG_DB
        )
        console.print(f"[green]✓ Loaded embedding model: {model_name} ({self.model.get_sentence_embedding_dimension()}d)[/green]")

    def semantic_search(self, query: str, limit: int = 10, similarity_threshold: float = 0.0) -> Dict:
        """
        Semantic search using cosine similarity.
        This is where vector search shines - conceptual matches.
        """
        # Step 1: Generate query embedding (cost for every search!)
        embed_start = time.time()
        query_embedding = self.model.encode(query)
        embed_time = (time.time() - embed_start) * 1000

        # Step 2: Search using vector similarity
        search_start = time.time()

        cur = self.conn.cursor()

        # Using cosine distance (1 - cosine similarity)
        # Lower distance = higher similarity
        query_sql = """
            SELECT
                id, sku, name, description, category, price, stock_quantity, error_code,
                1 - (embedding <=> %s::vector) as similarity
            FROM products
            WHERE 1 - (embedding <=> %s::vector) >= %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """

        cur.execute(
            query_sql,
            (query_embedding.tolist(), query_embedding.tolist(), similarity_threshold, query_embedding.tolist(), limit)
        )

        results = cur.fetchall()
        search_time = (time.time() - search_start) * 1000

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

        return {
            "results": formatted_results,
            "similarities": similarities,
            "total": len(formatted_results),
            "embed_time_ms": embed_time,
            "search_time_ms": search_time,
            "total_time_ms": embed_time + search_time
        }

    def search_with_metadata_filter(
        self,
        query: str,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 10
    ) -> Dict:
        """
        Hybrid approach: SQL filters THEN vector search.
        Blog: "filter 1M docs to 1K with keywords, then vector search the rest"
        """
        embed_start = time.time()
        query_embedding = self.model.encode(query)
        embed_time = (time.time() - embed_start) * 1000

        search_start = time.time()

        cur = self.conn.cursor()

        # Build WHERE clause
        where_clauses = []
        params = [query_embedding.tolist()]

        if category:
            where_clauses.append(f"category = %s")
            params.append(category)

        if min_price is not None:
            where_clauses.append(f"price >= %s")
            params.append(min_price)

        if max_price is not None:
            where_clauses.append(f"price <= %s")
            params.append(max_price)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        query_sql = f"""
            SELECT
                id, sku, name, description, category, price, stock_quantity, error_code,
                1 - (embedding <=> %s::vector) as similarity
            FROM products
            WHERE {where_sql}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """

        params.append(query_embedding.tolist())
        params.append(limit)

        cur.execute(query_sql, params)
        results = cur.fetchall()
        search_time = (time.time() - search_start) * 1000

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

        return {
            "results": formatted_results,
            "similarities": similarities,
            "total": len(formatted_results),
            "embed_time_ms": embed_time,
            "search_time_ms": search_time,
            "total_time_ms": embed_time + search_time
        }

    def demonstrate_boolean_limitation(self, positive_term: str, negative_term: str, limit: int = 10) -> Dict:
        """
        Demonstrate: "Cosine similarity doesn't understand NOT"

        Vector search will still return results containing the negative term
        because it's matching on overall semantic similarity, not boolean logic.
        """
        query = f"{positive_term}"  # We only embed the positive term

        result = self.semantic_search(query, limit=limit * 3)  # Get more results to show the problem

        # Try to manually filter results (this is a workaround, not native capability)
        filtered_results = []
        filtered_similarities = []

        negative_lower = negative_term.lower()

        for i, res in enumerate(result['results']):
            # Check if negative term appears in name or description
            text = f"{res['name']} {res['description']}".lower()
            if negative_lower not in text:
                filtered_results.append(res)
                filtered_similarities.append(result['similarities'][i])

                if len(filtered_results) >= limit:
                    break

        return {
            "results": filtered_results,
            "similarities": filtered_similarities,
            "total": len(filtered_results),
            "embed_time_ms": result['embed_time_ms'],
            "search_time_ms": result['search_time_ms'],
            "total_time_ms": result['total_time_ms'],
            "note": "Had to manually filter results - vector search doesn't support NOT natively"
        }

    def __del__(self):
        """Close database connection."""
        if hasattr(self, 'conn'):
            self.conn.close()


def print_vector_search_results(results: Dict, title: str):
    """Pretty print vector search results."""
    console.print(f"\n[bold cyan]{title}[/bold cyan]")
    console.print(f"Found {results['total']} results")
    console.print(f"Embedding time: {results['embed_time_ms']:.2f}ms")
    console.print(f"Search time: {results['search_time_ms']:.2f}ms")
    console.print(f"Total time: {results['total_time_ms']:.2f}ms\n")

    if 'note' in results:
        console.print(f"[yellow]Note: {results['note']}[/yellow]\n")

    if not results['results']:
        console.print("[yellow]No results found[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("SKU", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Category", style="yellow")
    table.add_column("Price", justify="right")
    table.add_column("Similarity", justify="right", style="blue")

    for i, product in enumerate(results['results'][:5]):  # Show top 5
        table.add_row(
            product['sku'],
            product['name'][:40] + "..." if len(product['name']) > 40 else product['name'],
            product['category'],
            f"${product['price']:.2f}",
            f"{results['similarities'][i]:.3f}"
        )

    console.print(table)


def demo_vector_search():
    """Demonstrate vector search capabilities and limitations."""
    console.print("[bold green]═══ Vector Search Demo (pgvector) ═══[/bold green]\n")

    searcher = VectorSearch()

    # 1. Semantic search - where it shines
    console.print("\n[bold]Scenario 1: Vague/Conceptual Query[/bold]")
    console.print("Use case: User can't articulate exact query, describes concept instead")
    console.print("Query: 'something to help me work from home comfortably'")
    results = searcher.semantic_search("something to help me work from home comfortably", limit=5)
    print_vector_search_results(results, "Semantic Search: Work from home comfort")

    # 2. Another semantic example
    console.print("\n[bold]Scenario 2: Conceptual Match[/bold]")
    console.print("Use case: Finding similar items without exact keywords")
    console.print("Query: 'equipment for getting fit at home'")
    results = searcher.semantic_search("equipment for getting fit at home", limit=5)
    print_vector_search_results(results, "Semantic Search: Home fitness")

    # 3. Hybrid search with filters
    console.print("\n[bold]Scenario 3: Hybrid Search (Filter → Vector)[/bold]")
    console.print("Use case: 'Filter 1M docs to 1K with keywords, then vector search the rest'")
    console.print("Query: 'portable audio' in electronics under $150")
    results = searcher.search_with_metadata_filter(
        query="portable audio",
        category="electronics",
        max_price=150,
        limit=5
    )
    print_vector_search_results(results, "Hybrid: Semantic + SQL Filters")

    # 4. Boolean limitation
    console.print("\n[bold]Scenario 4: Boolean Logic Limitation[/bold]")
    console.print("Use case: 'Cosine similarity doesn't understand NOT'")
    console.print("Trying to find: wireless products BUT NOT gaming")
    results = searcher.demonstrate_boolean_limitation("wireless", "gaming", limit=5)
    print_vector_search_results(results, "Attempting: wireless NOT gaming")

    # 5. Exact match (where it fails)
    console.print("\n[bold]Scenario 5: Exact SKU Search (Vector Search Weakness)[/bold]")
    console.print("Use case: User has exact SKU - vector search is 'expensive theater'")
    console.print("Query: 'ELEC-000001'")
    results = searcher.semantic_search("ELEC-000001", limit=5)
    print_vector_search_results(results, "Vector Search for Exact SKU (Anti-pattern!)")
    console.print("[yellow]⚠ This is wasteful - use keyword search for exact matches![/yellow]")

    console.print("\n[bold green]Key Takeaways:[/bold green]")
    console.print("  ✓ Great for conceptual/vague queries")
    console.print("  ✓ Finds semantic similarity")
    console.print("  ✗ Slower due to embedding generation")
    console.print("  ✗ Can't do boolean NOT natively")
    console.print("  ✗ Wasteful for exact matches")
    console.print("  ✗ Requires re-embedding on data changes\n")


if __name__ == "__main__":
    demo_vector_search()
