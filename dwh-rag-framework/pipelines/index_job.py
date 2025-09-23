#!/usr/bin/env python3
import sys
sys.path.append('/app')

from src.converter import convert_to_documents
from src.indexer import index_documents
import glob

def main():
    # Find latest snapshot
    snapshots = glob.glob("/app/data/snapshots/warehouse*.duckdb")
    if not snapshots:
        print("No snapshots found")
        return
    
    latest_snapshot = max(snapshots)
    
    # Convert and index
    docs = convert_to_documents(latest_snapshot, "/app/data/documents")
    rag = index_documents(docs, "/app/data/lightrag")
    
    print(f"Indexed {len(docs)} documents from {latest_snapshot}")

if __name__ == "__main__":
    main()
