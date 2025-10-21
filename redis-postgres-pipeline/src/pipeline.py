"""Main pipeline orchestration demonstrating all blog concepts.

This module ties together all the patterns:
- Redis queues for job distribution
- Deduplication before Postgres
- Cached lookups to avoid joins
- Polars for 6x faster transformations
- Bulk loading with COPY
- Pub/sub for coordination
- Backpressure monitoring
"""

import time
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import polars as pl
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .redis_utils import (
    RedisQueue,
    RedisDeduplicator,
    RedisCache,
    RedisPubSub,
    RedisBackpressure,
    get_redis_client
)
from .postgres_utils import (
    PostgresConnection,
    StagingTable,
    MaterializedViewManager,
    BulkLoader,
    LookupTableCache,
    get_postgres_connection
)
from .data_generator import OrderGenerator
from .config import pipeline_config

console = Console()


class PipelineOrchestrator:
    """Main pipeline orchestrator."""

    def __init__(self):
        """Initialize pipeline components."""
        self.redis = get_redis_client()

        # Redis components
        self.ingestion_queue = RedisQueue(self.redis, "orders:ingestion")
        self.processing_queue = RedisQueue(self.redis, "orders:processing")
        self.deduplicator = RedisDeduplicator(
            self.redis,
            "orders:dedup",
            ttl_seconds=pipeline_config.dedup_window_seconds
        )
        self.lookup_cache = RedisCache(self.redis, "lookups")
        self.pubsub = RedisPubSub(self.redis)
        self.backpressure = RedisBackpressure(self.redis)

        # Postgres components
        self.pg_conn: Optional[PostgresConnection] = None

    def initialize_lookup_cache(self) -> None:
        """Load lookup tables from Postgres into Redis."""
        console.print("[yellow]Loading lookup tables into Redis cache...[/yellow]")

        with get_postgres_connection(use_pgbouncer=False) as conn:
            cache_loader = LookupTableCache(conn)

            # Load products
            products_df = cache_loader.load_products()
            for row in products_df.iter_rows(named=True):
                key = f"product:{row['product_id']}"
                value = json.dumps({
                    'product_name': row['product_name'],
                    'category': row['category'],
                    'base_price': float(row['base_price'])
                })
                self.lookup_cache.set(key, value)

            # Load currency rates
            currency_df = cache_loader.load_currency_rates()
            for row in currency_df.iter_rows(named=True):
                key = f"currency:{row['currency_code']}"
                value = str(row['rate_to_usd'])
                self.lookup_cache.set(key, value)

            # Load zip codes
            zip_df = cache_loader.load_zip_codes()
            for row in zip_df.iter_rows(named=True):
                key = f"zipcode:{row['zip_code']}"
                value = json.dumps({
                    'city': row['city'],
                    'state': row['state'],
                    'country': row['country'],
                    'timezone': row['timezone'],
                    'shipping_zone': row['shipping_zone']
                })
                self.lookup_cache.set(key, value)

        console.print(
            f"[green]✓[/green] Cached {len(products_df)} products, "
            f"{len(currency_df)} currencies, {len(zip_df)} zip codes"
        )

    def ingest_orders(self, orders: List[Dict[str, Any]]) -> Dict[str, int]:
        """Ingest orders with deduplication.

        This demonstrates:
        - Redis hash-based deduplication
        - Redis list-based queue (replacing Kafka)
        - Backpressure monitoring

        Args:
            orders: List of order dictionaries

        Returns:
            Statistics dict with counts
        """
        stats = {
            'total': len(orders),
            'new': 0,
            'duplicates': 0,
            'queued': 0
        }

        # Check backpressure
        if self.backpressure.should_throttle(
            'ingestion',
            pipeline_config.max_queue_depth
        ):
            console.print("[red]⚠ Backpressure detected! Queue is full.[/red]")
            return stats

        new_orders = []
        for order in orders:
            order_id = order['order_id']

            # Deduplicate using Redis hash
            if self.deduplicator.mark_seen(order_id):
                stats['new'] += 1
                new_orders.append(order)
            else:
                stats['duplicates'] += 1

        # Queue new orders in batch
        if new_orders:
            self.ingestion_queue.push_batch(new_orders)
            stats['queued'] = len(new_orders)

            # Update backpressure counter
            self.backpressure.increment('ingestion', len(new_orders))

        return stats

    def process_batch(self, batch_size: int = 5000) -> Dict[str, Any]:
        """Process a batch from the ingestion queue.

        This demonstrates:
        - BRPOP for blocking queue consumption
        - Polars for fast transformations (6x faster than Pandas)
        - Cached lookups to avoid Postgres joins
        - UNLOGGED table for staging
        - Pub/sub to signal completion

        Args:
            batch_size: Maximum batch size to process

        Returns:
            Processing statistics
        """
        stats = {
            'processed': 0,
            'enriched': 0,
            'staged': 0,
            'errors': 0
        }

        orders_batch = []

        # Pull batch from queue
        for _ in range(batch_size):
            order = self.ingestion_queue.pop(timeout=1)
            if order is None:
                break
            orders_batch.append(order)
            stats['processed'] += 1

        if not orders_batch:
            return stats

        # Update backpressure
        self.backpressure.decrement('ingestion', len(orders_batch))

        # Convert to Polars DataFrame for fast processing
        df = pl.DataFrame(orders_batch)

        # Enrich with cached lookups (avoiding Postgres joins)
        enriched_rows = []
        for row in df.iter_rows(named=True):
            try:
                # Lookup product info
                product_key = f"product:{row['product_id']}"
                product_data = self.lookup_cache.get_json(product_key)

                # Lookup currency rate
                currency_key = f"currency:{row['currency']}"
                currency_rate = float(self.lookup_cache.get(currency_key))

                # Lookup zip code info
                zip_key = f"zipcode:{row['zip_code']}"
                zip_data = self.lookup_cache.get_json(zip_key)

                if not all([product_data, currency_rate, zip_data]):
                    stats['errors'] += 1
                    continue

                # Enrich the row
                enriched_row = {
                    'order_id': row['order_id'],
                    'customer_id': row['customer_id'],
                    'product_id': row['product_id'],
                    'quantity': row['quantity'],
                    'unit_price': row['unit_price'],
                    'currency': row['currency'],
                    'zip_code': row['zip_code'],
                    'order_timestamp': row['order_timestamp'],
                    'raw_data': json.dumps(row.get('raw_data', {}))
                }

                enriched_rows.append(enriched_row)
                stats['enriched'] += 1

            except Exception as e:
                console.print(f"[red]Error enriching order {row.get('order_id')}: {e}[/red]")
                stats['errors'] += 1

        if not enriched_rows:
            return stats

        # Convert to Polars for bulk insert
        enriched_df = pl.DataFrame(enriched_rows)

        # Write to UNLOGGED staging table (3x faster than regular table)
        with get_postgres_connection(use_pgbouncer=False) as conn:
            staging = StagingTable(conn)

            # Use COPY for maximum speed
            try:
                count = staging.bulk_insert(enriched_df)
                stats['staged'] = count

                # Signal completion via pub/sub
                self.pubsub.publish('pipeline:events', {
                    'event': 'batch_staged',
                    'count': count,
                    'timestamp': datetime.now().isoformat()
                })

            except Exception as e:
                console.print(f"[red]Error staging batch: {e}[/red]")
                stats['errors'] += len(enriched_rows)

        return stats

    def promote_to_production(self) -> int:
        """Promote validated staging data to production tables.

        This demonstrates:
        - Using stored procedures for complex operations
        - Materialized view refresh

        Returns:
            Number of records promoted
        """
        with get_postgres_connection(use_pgbouncer=False) as conn:
            staging = StagingTable(conn)

            # Promote using stored procedure
            promoted_count = staging.promote_to_production()

            if promoted_count > 0:
                # Refresh materialized views for dashboards
                console.print("[yellow]Refreshing materialized views...[/yellow]")
                mv_manager = MaterializedViewManager(conn)
                mv_manager.refresh_all()

                # Signal completion
                self.pubsub.publish('pipeline:events', {
                    'event': 'batch_promoted',
                    'count': promoted_count,
                    'timestamp': datetime.now().isoformat()
                })

            return promoted_count

    def get_stats(self) -> Dict[str, Any]:
        """Get current pipeline statistics."""
        with get_postgres_connection(use_pgbouncer=False) as conn:
            staging = StagingTable(conn)

            # Get counts while connection is open
            staging_count = staging.count()

            # Get production table count
            result = conn.fetchone("SELECT COUNT(*) as count FROM orders")
            production_count = result['count'] if result else 0

            # Get materialized view stats
            mv_manager = MaterializedViewManager(conn)
            mv_views = mv_manager.list_views()

        return {
            'ingestion_queue_depth': self.ingestion_queue.size(),
            'processing_queue_depth': self.processing_queue.size(),
            'dedup_window_size': self.deduplicator.count_seen(),
            'lookup_cache_size': self.lookup_cache.size(),
            'staging_count': staging_count,
            'production_count': production_count,
            'materialized_views': mv_views,
            'total_processed': self.ingestion_queue.counter(),
        }

    def display_stats(self) -> None:
        """Display pipeline statistics in a nice table."""
        stats = self.get_stats()

        table = Table(title="Pipeline Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Ingestion Queue Depth", str(stats['ingestion_queue_depth']))
        table.add_row("Dedup Window Size", f"{stats['dedup_window_size']:,}")
        table.add_row("Lookup Cache Size", str(stats['lookup_cache_size']))
        table.add_row("Staging Table Rows", f"{stats['staging_count']:,}")
        table.add_row("Production Table Rows", f"{stats['production_count']:,}")
        table.add_row("Total Jobs Processed", f"{stats['total_processed']:,}")

        console.print(table)

        # Materialized views
        if stats['materialized_views']:
            mv_table = Table(title="Materialized Views")
            mv_table.add_column("View Name", style="cyan")
            mv_table.add_column("Populated", style="yellow")
            mv_table.add_column("Size", style="green")

            for mv in stats['materialized_views']:
                mv_table.add_row(
                    mv['matviewname'],
                    "Yes" if mv['ispopulated'] else "No",
                    mv['size']
                )

            console.print(mv_table)

    def cleanup(self) -> None:
        """Cleanup pipeline resources."""
        if self.redis:
            self.redis.close()
        if self.pg_conn:
            self.pg_conn.close()


class Worker:
    """Pipeline worker process.

    Each worker:
    - Pulls jobs from Redis queue (BRPOP)
    - Transforms with Polars
    - Writes to Postgres via PgBouncer
    """

    def __init__(self, worker_id: int):
        """Initialize worker.

        Args:
            worker_id: Unique worker identifier
        """
        self.worker_id = worker_id
        self.orchestrator = PipelineOrchestrator()
        self.running = False

    def run(self, max_iterations: Optional[int] = None) -> None:
        """Run worker loop.

        Args:
            max_iterations: Max iterations (None = infinite)
        """
        self.running = True
        iterations = 0

        console.print(f"[green]Worker {self.worker_id} started[/green]")

        while self.running:
            if max_iterations and iterations >= max_iterations:
                break

            # Process batch
            stats = self.orchestrator.process_batch(
                batch_size=pipeline_config.batch_size
            )

            if stats['processed'] > 0:
                console.print(
                    f"[blue]Worker {self.worker_id}:[/blue] "
                    f"Processed {stats['processed']}, "
                    f"Enriched {stats['enriched']}, "
                    f"Staged {stats['staged']}, "
                    f"Errors {stats['errors']}"
                )

            iterations += 1

            # Small sleep if queue empty
            if stats['processed'] == 0:
                time.sleep(1)

        console.print(f"[yellow]Worker {self.worker_id} stopped[/yellow]")

    def stop(self) -> None:
        """Stop the worker."""
        self.running = False
        self.orchestrator.cleanup()
