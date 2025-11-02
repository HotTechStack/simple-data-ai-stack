#!/usr/bin/env python3
"""
Load sample data into Elasticsearch and PostgreSQL with pgvector.

This script demonstrates:
1. Loading data into Elasticsearch for keyword search
2. Generating embeddings and loading into pgvector for semantic search
3. The cost/complexity difference between the two approaches
"""

import json
import time
import os
from typing import List, Dict
import psycopg2
from psycopg2.extras import execute_values
from elasticsearch import Elasticsearch, helpers
from sentence_transformers import SentenceTransformer
import numpy as np
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

console = Console()

# Configuration from environment
ES_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "5432")
PG_USER = os.getenv("POSTGRES_USER", "searchuser")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "searchpass")
PG_DB = os.getenv("POSTGRES_DB", "searchdb")


def load_products_from_json(filename: str = "/app/data/products.json") -> List[Dict]:
    """Load products from JSON file."""
    with open(filename, 'r') as f:
        return json.load(f)


def setup_elasticsearch_index(es: Elasticsearch, index_name: str = "products"):
    """Create Elasticsearch index with proper mappings."""
    console.print(f"[yellow]Setting up Elasticsearch index: {index_name}[/yellow]")

    # Delete index if it exists
    if es.indices.exists(index=index_name):
        es.indices.delete(index=index_name)
        console.print(f"  ✓ Deleted existing index")

    # Create index with mappings
    index_config = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "default": {
                        "type": "standard"
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "id": {"type": "integer"},
                "sku": {"type": "keyword"},  # Exact match
                "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "description": {"type": "text"},
                "category": {"type": "keyword"},
                "price": {"type": "float"},
                "stock_quantity": {"type": "integer"},
                "error_code": {"type": "keyword"}
            }
        }
    }

    es.indices.create(index=index_name, body=index_config)
    console.print(f"  ✓ Created index with mappings")


def load_to_elasticsearch(products: List[Dict], index_name: str = "products"):
    """Load products into Elasticsearch."""
    console.print(f"\n[cyan]Loading {len(products)} products into Elasticsearch...[/cyan]")

    es = Elasticsearch([ES_URL])

    # Setup index
    setup_elasticsearch_index(es, index_name)

    # Bulk insert
    start_time = time.time()

    actions = [
        {
            "_index": index_name,
            "_id": product["id"],
            "_source": product
        }
        for product in products
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Indexing documents...", total=len(actions))

        success, failed = helpers.bulk(es, actions, raise_on_error=False)

        progress.update(task, completed=len(actions))

    elapsed_time = time.time() - start_time

    console.print(f"  ✓ Indexed {success} documents in {elapsed_time:.2f} seconds")
    console.print(f"  ✓ Speed: {success / elapsed_time:.0f} docs/sec")

    if failed:
        console.print(f"  ✗ Failed to index {len(failed)} documents", style="red")

    return elapsed_time


def generate_embeddings(products: List[Dict], model_name: str = "all-MiniLM-L6-v2"):
    """
    Generate embeddings for products.

    Note: This demonstrates the 'expensive theater' mentioned in the blog.
    Every data change requires re-embedding!
    """
    console.print(f"\n[cyan]Generating embeddings using {model_name}...[/cyan]")
    console.print(f"  [yellow]⚠ This is the 'expensive pipeline' the blog warns about![/yellow]")

    start_time = time.time()

    # Load model
    console.print(f"  Loading embedding model...")
    model = SentenceTransformer(model_name)

    # Generate text to embed (name + description)
    texts = [f"{p['name']}. {p['description']}" for p in products]

    # Generate embeddings in batches
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Generating embeddings...", total=len(texts))

        embeddings = model.encode(
            texts,
            show_progress_bar=False,
            batch_size=32
        )

        progress.update(task, completed=len(texts))

    elapsed_time = time.time() - start_time

    console.print(f"  ✓ Generated {len(embeddings)} embeddings in {elapsed_time:.2f} seconds")
    console.print(f"  ✓ Speed: {len(embeddings) / elapsed_time:.0f} embeddings/sec")
    console.print(f"  ℹ Embedding dimensions: {embeddings[0].shape[0]}")

    return embeddings, elapsed_time


def load_to_postgres(products: List[Dict], embeddings: np.ndarray):
    """Load products and embeddings into PostgreSQL with pgvector."""
    console.print(f"\n[cyan]Loading {len(products)} products into PostgreSQL with pgvector...[/cyan]")

    start_time = time.time()

    # Connect to PostgreSQL
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASSWORD,
        dbname=PG_DB
    )
    cur = conn.cursor()

    # Clear existing data
    cur.execute("TRUNCATE TABLE products RESTART IDENTITY CASCADE")
    console.print(f"  ✓ Cleared existing data")

    # Prepare data for insertion
    insert_data = []
    for product, embedding in zip(products, embeddings):
        insert_data.append((
            product["sku"],
            product["name"],
            product["description"],
            product["category"],
            product["price"],
            product["stock_quantity"],
            product["error_code"],
            embedding.tolist()  # Convert numpy array to list for PostgreSQL
        ))

    # Bulk insert using execute_values (much faster than individual inserts)
    insert_query = """
        INSERT INTO products (sku, name, description, category, price, stock_quantity, error_code, embedding)
        VALUES %s
    """

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Inserting records...", total=None)

        execute_values(cur, insert_query, insert_data, page_size=100)
        conn.commit()

        progress.update(task, completed=True)

    # Get actual count
    cur.execute("SELECT COUNT(*) FROM products")
    count = cur.fetchone()[0]

    elapsed_time = time.time() - start_time

    console.print(f"  ✓ Inserted {count} products in {elapsed_time:.2f} seconds")
    console.print(f"  ✓ Speed: {count / elapsed_time:.0f} records/sec")

    cur.close()
    conn.close()

    return elapsed_time


def main():
    """Main loading process."""
    console.print("[bold green]═══ Elasticsearch vs Vector Search - Data Loading ═══[/bold green]\n")

    # Load products
    products = load_products_from_json()
    console.print(f"✓ Loaded {len(products)} products from JSON\n")

    # Load to Elasticsearch
    console.print("[bold]Step 1: Elasticsearch (Keyword Search)[/bold]")
    es_time = load_to_elasticsearch(products)

    # Generate embeddings and load to PostgreSQL
    console.print(f"\n[bold]Step 2: PostgreSQL + pgvector (Semantic Search)[/bold]")
    embeddings, embedding_time = generate_embeddings(products)
    pg_time = load_to_postgres(products, embeddings)

    # Summary
    console.print("\n" + "═" * 60)
    console.print("[bold green]Loading Summary[/bold green]")
    console.print("═" * 60)
    console.print(f"Elasticsearch indexing time:  {es_time:.2f}s")
    console.print(f"Vector embedding generation:   {embedding_time:.2f}s")
    console.print(f"PostgreSQL insertion time:     {pg_time:.2f}s")
    console.print(f"Total vector pipeline time:    {embedding_time + pg_time:.2f}s")
    console.print("─" * 60)
    console.print(f"[yellow]Vector search took {(embedding_time + pg_time) / es_time:.1f}x longer than keyword search[/yellow]")
    console.print("[yellow]This demonstrates the 'expensive pipeline' mentioned in the blog![/yellow]")
    console.print("═" * 60 + "\n")

    console.print("[bold green]✓ Data loading complete![/bold green]")


if __name__ == "__main__":
    main()
