import duckdb
from pathlib import Path
import json

def convert_to_documents(snapshot_path: str, output_dir: str):
    """Convert DuckDB tables to various document formats"""
    
    conn = duckdb.connect(snapshot_path, read_only=True)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    tables = conn.execute("SHOW TABLES").fetchall()
    
    all_documents = []
    
    for table_tuple in tables:
        table_name = table_tuple[0]
        
        # Export as CSV
        csv_path = output_path / f"{table_name}.csv"
        conn.execute(f"COPY {table_name} TO '{csv_path}' (HEADER, DELIMITER ',')")
        
        # Create documents for this table
        table_docs = []
        df = conn.execute(f"SELECT * FROM {table_name}").fetchdf()
        
        for idx, row in df.iterrows():
            doc = {
                "id": f"{table_name}_{idx}",
                "source": table_name,
                "content": json.dumps(row.to_dict(), default=str),
                "metadata": {"table": table_name, "row_id": int(idx)}
            }
            table_docs.append(doc)
            all_documents.append(doc)
        
        # Save this table's docs as JSON
        json_path = output_path / f"{table_name}.json"
        with open(json_path, 'w') as f:
            json.dump(table_docs, f, indent=2)
    
    conn.close()
    return all_documents