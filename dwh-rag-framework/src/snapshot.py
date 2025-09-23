import duckdb
import psycopg2
from datetime import datetime

def create_snapshot(pg_conn_str: str, snapshot_path: str):
    """Snapshot Postgres warehouse into DuckDB"""
    
    pg_conn = psycopg2.connect(pg_conn_str)
    
    # Delete existing snapshot if it exists
    import os
    if os.path.exists(snapshot_path):
        os.remove(snapshot_path)
    
    # Create fresh DuckDB connection
    duck_conn = duckdb.connect(snapshot_path)
    
    with pg_conn.cursor() as cur:
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [row[0] for row in cur.fetchall()]
    
    for table in tables:
        with pg_conn.cursor() as cur:
            cur.execute(f"SELECT * FROM {table}")
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            
            if rows:
                placeholders = ', '.join(['?' for _ in cols])
                values_clause = ', '.join([f"({placeholders})" for _ in rows])
                flat_values = [item for row in rows for item in row]
                
                duck_conn.execute(
                    f"CREATE TABLE {table} AS SELECT * FROM (VALUES {values_clause}) AS t({', '.join(cols)})",
                    flat_values
                )
    
    pg_conn.close()
    duck_conn.close()
    
    return snapshot_path