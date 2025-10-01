from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import polars as pl
import duckdb
import os
from pathlib import Path
from typing import Optional
import uvicorn

app = FastAPI(title="Universal Data MCP Server", version="1.0.0")

UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

conn = duckdb.connect(':memory:')

class DataLoader:
    @staticmethod
    def detect_format(filename: str) -> str:
        ext = filename.lower().split('.')[-1]
        format_map = {
            'csv': 'csv',
            'json': 'json',
            'xlsx': 'excel',
            'xls': 'excel',
            'parquet': 'parquet',
            'avro': 'avro',
            'txt': 'csv'
        }
        return format_map.get(ext, 'unknown')
    
    @staticmethod
    def load_with_polars(filepath: str, format_type: str) -> Optional[pl.DataFrame]:
        try:
            if format_type == 'csv':
                return pl.read_csv(filepath, ignore_errors=True)
            elif format_type == 'json':
                return pl.read_json(filepath)
            elif format_type == 'parquet':
                return pl.read_parquet(filepath)
            elif format_type == 'avro':
                return pl.read_avro(filepath)
        except Exception as e:
            print(f"Polars failed: {e}, falling back to pandas")
            return None
    
    @staticmethod
    def load_with_pandas(filepath: str, format_type: str) -> Optional[pd.DataFrame]:
        try:
            if format_type == 'csv':
                return pd.read_csv(filepath)
            elif format_type == 'json':
                return pd.read_json(filepath)
            elif format_type == 'excel':
                return pd.read_excel(filepath)
            elif format_type == 'parquet':
                return pd.read_parquet(filepath)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to load file: {str(e)}")
    
    @staticmethod
    def load_file(filepath: str) -> dict:
        filename = os.path.basename(filepath)
        format_type = DataLoader.detect_format(filename)
        
        if format_type == 'unknown':
            raise HTTPException(status_code=400, detail=f"Unsupported format: {filename}")
        
        df = DataLoader.load_with_polars(filepath, format_type)
        
        if df is None:
            df_pandas = DataLoader.load_with_pandas(filepath, format_type)
            df = pl.from_pandas(df_pandas)
        
        table_name = filename.split('.')[0].replace('-', '_').replace(' ', '_')
        conn.register(table_name, df.to_pandas())
        
        return {
            "table_name": table_name,
            "rows": df.shape[0],
            "columns": df.shape[1],
            "column_names": df.columns,
            "format": format_type,
            "preview": df.head(5).to_dicts()
        }

@app.get("/")
async def root():
    return {
        "message": "Universal Data MCP Server",
        "status": "running",
        "endpoints": {
            "upload": "/upload",
            "query": "/query",
            "tables": "/tables",
            "health": "/health"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_path = UPLOAD_DIR / file.filename
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        result = DataLoader.load_file(str(file_path))
        
        return JSONResponse(content={
            "success": True,
            "filename": file.filename,
            "data": result
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_data(query: dict):
    try:
        sql = query.get("sql")
        if not sql:
            raise HTTPException(status_code=400, detail="SQL query required")
        
        result = conn.execute(sql).fetchdf()
        
        return JSONResponse(content={
            "success": True,
            "rows": len(result),
            "data": result.to_dict(orient='records')
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/tables")
async def list_tables():
    try:
        tables = conn.execute("SHOW TABLES").fetchdf()
        return JSONResponse(content={
            "success": True,
            "tables": tables.to_dict(orient='records')
        })
    except Exception:
        return JSONResponse(content={"success": True, "tables": []})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
