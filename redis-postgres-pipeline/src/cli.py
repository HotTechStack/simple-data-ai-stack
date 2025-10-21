"""Command-line interface for the pipeline."""

import click
import time
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

from .pipeline import PipelineOrchestrator, Worker
from .data_generator import OrderGenerator
from .config import pipeline_config

console = Console()


@click.group()
def cli():
    """Redis + Postgres Data Engineering Pipeline.

    Demonstrates high-performance patterns for data engineering:
    - Redis queues (replacing Kafka)
    - Deduplication with Redis hashes
    - Cached lookups to avoid joins
    - Polars for fast transformations
    - UNLOGGED tables for staging
    - Materialized views for aggregations
    - Connection pooling with PgBouncer
    """
    pass


@cli.command()
@click.option('--products', is_flag=True, help='Load product catalog')
@click.option('--currencies', is_flag=True, help='Load currency rates')
@click.option('--zipcodes', is_flag=True, help='Load zip code zones')
@click.option('--all', 'load_all', is_flag=True, help='Load all lookup tables')
def init_cache(products, currencies, zipcodes, load_all):
    """Initialize Redis cache with lookup tables from Postgres."""
    if not any([products, currencies, zipcodes, load_all]):
        console.print("[yellow]Specify what to cache (--all recommended)[/yellow]")
        return

    orchestrator = PipelineOrchestrator()

    try:
        with console.status("[bold green]Loading lookup tables into Redis..."):
            orchestrator.initialize_lookup_cache()

        console.print("[green]✓ Lookup cache initialized successfully[/green]")

    except Exception as e:
        console.print(f"[red]✗ Failed to initialize cache: {e}[/red]")
        raise
    finally:
        orchestrator.cleanup()


@cli.command()
@click.option('--count', '-n', default=1000, help='Number of orders to generate')
@click.option('--duplicates', '-d', default=0.05, help='Duplicate rate (0.0-1.0)')
@click.option('--burst', is_flag=True, help='Generate burst at same timestamp')
def generate(count, duplicates, burst):
    """Generate sample orders and push to ingestion queue."""
    console.print(f"[yellow]Generating {count:,} orders (duplicate rate: {duplicates:.1%})...[/yellow]")

    generator = OrderGenerator(duplicate_rate=duplicates)
    orchestrator = PipelineOrchestrator()

    try:
        # Generate orders
        if burst:
            orders = generator.generate_burst(count)
            console.print("[yellow]Generated burst orders[/yellow]")
        else:
            orders = generator.generate_batch(count, time_spread_seconds=3600)
            console.print("[yellow]Generated orders spread over 1 hour[/yellow]")

        # Ingest with deduplication
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ) as progress:
            task = progress.add_task("[cyan]Ingesting orders...", total=count)

            stats = orchestrator.ingest_orders(orders)

            progress.update(task, completed=count)

        # Display results
        console.print(f"\n[green]✓ Ingestion complete[/green]")
        console.print(f"  Total orders: {stats['total']:,}")
        console.print(f"  New orders: {stats['new']:,}")
        console.print(f"  Duplicates caught: {stats['duplicates']:,}")
        console.print(f"  Queued for processing: {stats['queued']:,}")

    except Exception as e:
        console.print(f"[red]✗ Failed to generate orders: {e}[/red]")
        raise
    finally:
        orchestrator.cleanup()


@cli.command()
@click.option('--workers', '-w', default=1, help='Number of worker processes')
@click.option('--iterations', '-i', default=None, type=int, help='Max iterations per worker')
@click.option('--batch-size', '-b', default=None, type=int, help='Batch size override')
def process(workers, iterations, batch_size):
    """Process orders from the queue.

    Runs worker processes that:
    - Pull jobs from Redis queue (BRPOP)
    - Transform with Polars
    - Enrich with cached lookups
    - Write to UNLOGGED staging table
    """
    if batch_size:
        pipeline_config.batch_size = batch_size

    console.print(f"[green]Starting {workers} worker(s)...[/green]")
    console.print(f"Batch size: {pipeline_config.batch_size:,}")

    try:
        if workers == 1:
            # Single worker mode (simpler)
            worker = Worker(worker_id=1)
            worker.run(max_iterations=iterations)
        else:
            # Multi-worker would require multiprocessing
            console.print("[yellow]Multi-worker mode requires multiprocessing (not implemented in demo)[/yellow]")
            console.print("[yellow]Running single worker instead...[/yellow]")
            worker = Worker(worker_id=1)
            worker.run(max_iterations=iterations)

    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping workers...[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Worker error: {e}[/red]")
        raise


@cli.command()
def promote():
    """Promote staging data to production tables.

    This:
    - Validates and enriches staging data
    - Moves to durable production tables
    - Refreshes materialized views
    """
    orchestrator = PipelineOrchestrator()

    try:
        with console.status("[bold green]Promoting staging to production..."):
            count = orchestrator.promote_to_production()

        if count > 0:
            console.print(f"[green]✓ Promoted {count:,} orders to production[/green]")
        else:
            console.print("[yellow]No orders in staging to promote[/yellow]")

    except Exception as e:
        console.print(f"[red]✗ Failed to promote: {e}[/red]")
        raise
    finally:
        orchestrator.cleanup()


@cli.command()
@click.option('--watch', '-w', is_flag=True, help='Watch mode (refresh every 5s)')
def stats(watch):
    """Display pipeline statistics."""
    orchestrator = PipelineOrchestrator()

    try:
        if watch:
            console.print("[yellow]Watch mode - Press Ctrl+C to exit[/yellow]\n")
            while True:
                console.clear()
                orchestrator.display_stats()
                time.sleep(5)
        else:
            orchestrator.display_stats()

    except KeyboardInterrupt:
        console.print("\n[yellow]Exiting...[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Failed to get stats: {e}[/red]")
        raise
    finally:
        orchestrator.cleanup()


@cli.command()
@click.option('--total', '-t', default=100000, help='Total orders to generate')
@click.option('--batch-size', '-b', default=5000, help='Processing batch size')
@click.option('--skip-cache', is_flag=True, help='Skip cache initialization')
def benchmark(total, batch_size, skip_cache):
    """Run end-to-end pipeline benchmark.

    This simulates the blog's claim:
    - Handles 100k+ jobs/day
    - Processes in batches with Polars
    - Uses all optimization patterns
    """
    console.print(f"\n[bold cyan]Pipeline Benchmark[/bold cyan]")
    console.print(f"Total orders: {total:,}")
    console.print(f"Batch size: {batch_size:,}\n")

    orchestrator = PipelineOrchestrator()
    generator = OrderGenerator(duplicate_rate=0.05)

    try:
        # Step 1: Initialize cache
        if not skip_cache:
            with console.status("[bold green]Initializing lookup cache..."):
                orchestrator.initialize_lookup_cache()
            console.print("[green]✓ Cache initialized[/green]\n")

        # Step 2: Generate and ingest orders
        start_time = time.time()

        console.print("[yellow]Phase 1: Generating and ingesting orders...[/yellow]")
        orders = generator.generate_batch(total, time_spread_seconds=86400)

        ingest_start = time.time()
        stats = orchestrator.ingest_orders(orders)
        ingest_time = time.time() - ingest_start

        console.print(f"[green]✓ Ingested {stats['queued']:,} orders in {ingest_time:.2f}s[/green]")
        console.print(f"  Throughput: {stats['queued']/ingest_time:,.0f} orders/sec")
        console.print(f"  Duplicates caught: {stats['duplicates']:,}\n")

        # Step 3: Process orders
        console.print("[yellow]Phase 2: Processing orders...[/yellow]")

        worker = Worker(worker_id=1)
        process_start = time.time()

        # Process until queue empty
        processed_total = 0
        while orchestrator.ingestion_queue.size() > 0:
            batch_stats = orchestrator.process_batch(batch_size=batch_size)
            processed_total += batch_stats['processed']

            if batch_stats['processed'] > 0:
                console.print(
                    f"  Processed: {processed_total:,}/{stats['queued']:,} "
                    f"({100*processed_total/stats['queued']:.1f}%)"
                )

        process_time = time.time() - process_start

        console.print(f"[green]✓ Processed {processed_total:,} orders in {process_time:.2f}s[/green]")
        console.print(f"  Throughput: {processed_total/process_time:,.0f} orders/sec\n")

        # Step 4: Promote to production
        console.print("[yellow]Phase 3: Promoting to production...[/yellow]")

        promote_start = time.time()
        promoted = orchestrator.promote_to_production()
        promote_time = time.time() - promote_start

        console.print(f"[green]✓ Promoted {promoted:,} orders in {promote_time:.2f}s[/green]")
        console.print(f"  Throughput: {promoted/promote_time:,.0f} orders/sec\n")

        # Total time
        total_time = time.time() - start_time

        # Summary
        console.print(f"\n[bold green]Benchmark Complete[/bold green]")
        console.print(f"Total time: {total_time:.2f}s")
        console.print(f"End-to-end throughput: {promoted/total_time:,.0f} orders/sec")

        # Display final stats
        console.print()
        orchestrator.display_stats()

    except Exception as e:
        console.print(f"[red]✗ Benchmark failed: {e}[/red]")
        raise
    finally:
        orchestrator.cleanup()


@cli.command()
@click.option('--all', 'clear_all', is_flag=True, help='Clear all Redis data')
@click.option('--queues', is_flag=True, help='Clear queues only')
@click.option('--cache', is_flag=True, help='Clear cache only')
@click.option('--dedup', is_flag=True, help='Clear dedup window only')
def clear(clear_all, queues, cache, dedup):
    """Clear Redis data."""
    orchestrator = PipelineOrchestrator()

    try:
        if clear_all or queues:
            orchestrator.ingestion_queue.clear()
            orchestrator.processing_queue.clear()
            console.print("[green]✓ Cleared queues[/green]")

        if clear_all or cache:
            orchestrator.lookup_cache.clear()
            console.print("[green]✓ Cleared lookup cache[/green]")

        if clear_all or dedup:
            orchestrator.deduplicator.clear()
            console.print("[green]✓ Cleared dedup window[/green]")

        if not any([clear_all, queues, cache, dedup]):
            console.print("[yellow]Specify what to clear (--all, --queues, --cache, --dedup)[/yellow]")

    except Exception as e:
        console.print(f"[red]✗ Failed to clear: {e}[/red]")
        raise
    finally:
        orchestrator.cleanup()


if __name__ == '__main__':
    cli()
