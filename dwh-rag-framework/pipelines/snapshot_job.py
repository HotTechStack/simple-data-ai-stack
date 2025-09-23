#!/usr/bin/env python3
import sys
sys.path.append('/app')

from src.snapshot import create_snapshot
from datetime import datetime

def main():
    pg_conn_str = "postgresql://user:password@postgres:5432/warehouse"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_path = f"/app/data/snapshots/warehouse_{timestamp}.duckdb"
    
    create_snapshot(pg_conn_str, snapshot_path)
    print(f"Snapshot created: {snapshot_path}")

if __name__ == "__main__":
    main()
