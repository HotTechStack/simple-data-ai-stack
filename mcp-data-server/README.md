# Universal MCP Server for Data & AI Engineering

Stop arguing about file formats. This MCP server ingests **any data file** and makes it queryable instantly.

Upload CSV, JSON, Excel, Parquet, Avro — the system auto-detects, routes to the right parser, and loads into a query engine.

**No configuration. No format wars. No custom loaders.**

---

## 🎯 What This Solves

Every data and AI team wastes time on:
- ❌ Debating which format to use (CSV vs Parquet vs JSON)
- ❌ Writing custom parsers for every data source
- ❌ "We don't support that format" tickets blocking progress
- ❌ Ad-hoc scripts breaking in production
- ❌ Friction between business users and engineers

**This MCP server eliminates all of that.**

---

## ✨ Features

✅ **Auto-format detection** - Upload any file, system figures out the format  
✅ **Smart routing** - Polars for speed, Pandas for compatibility  
✅ **Instant SQL queries** - DuckDB integration, query uploaded data immediately  
✅ **Zero configuration** - Works out of the box  
✅ **REST API** - Easy integration with any tool or LLM  
✅ **Production-ready** - Health checks, error handling, proper logging  

---

## 📦 Supported Formats

| Format | Extensions | Status |
|--------|-----------|--------|
| CSV | `.csv`, `.tsv`, `.txt` | ✅ Full support |
| JSON | `.json`, `.jsonl` | ✅ Full support |
| Excel | `.xlsx`, `.xls` | ✅ Full support |
| Parquet | `.parquet` | ✅ Full support |
| Avro | `.avro` | ✅ Full support |

---

## 🚀 Quick Start

### Prerequisites

- Docker installed ([Get Docker](https://docs.docker.com/get-docker/))
- Docker Compose installed (included with Docker Desktop)
- That's it. No Python setup needed.

### Start the Server (3 Commands)

```bash
# 1. Navigate to project directory
cd mcp-data-server

# 2. Start the server
docker-compose up --build

# 3. Wait for this message:
# "Application startup complete"
```

**Server is now running at: http://localhost:8000**

---

## 📘 Basic Usage

### 1️⃣ Upload a File

**Create a sample CSV:**
```bash
cat > sample.csv << EOF
id,name,department,salary
1,Alice,Engineering,95000
2,Bob,Marketing,75000
3,Charlie,Engineering,105000
4,Diana,Sales,85000
EOF
```

**Upload it:**
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@sample.csv"
```

**Response you'll get:**
```json
{
  "success": true,
  "filename": "sample.csv",
  "data": {
    "table_name": "sample",
    "rows": 4,
    "columns": 4,
    "column_names": ["id", "name", "department", "salary"],
    "format": "csv",
    "preview": [
      {"id": 1, "name": "Alice", "department": "Engineering", "salary": 95000},
      {"id": 2, "name": "Bob", "department": "Marketing", "salary": 75000}
    ]
  }
}
```

### 2️⃣ Query Your Data

**Simple filter:**
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM sample WHERE department = '\''Engineering'\''"}'
```

**Aggregation:**
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT department, AVG(salary) as avg_salary, COUNT(*) as count FROM sample GROUP BY department"}'
```

**Response:**
```json
{
  "success": true,
  "rows": 3,
  "data": [
    {"department": "Engineering", "avg_salary": 100000, "count": 2},
    {"department": "Marketing", "avg_salary": 75000, "count": 1},
    {"department": "Sales", "avg_salary": 85000, "count": 1}
  ]
}
```

### 3️⃣ List All Tables

```bash
curl http://localhost:8000/tables
```

Returns all uploaded datasets currently loaded.

### 4️⃣ Check Server Health

```bash
curl http://localhost:8000/health
```

---

## 🧪 Run Automated Tests

The project includes a test suite:

```bash
# Make test script executable
chmod +x test.sh

# Run all tests
./test.sh
```

**What it tests:**
- ✅ Server health check
- ✅ CSV upload and query
- ✅ JSON upload and query
- ✅ Filtering queries
- ✅ Aggregation queries
- ✅ Table listing

---

## 🎓 Real-World Examples

### Example 1: Excel Report Analysis

```bash
# Upload your Excel file
curl -X POST "http://localhost:8000/upload" \
  -F "file=@quarterly_report.xlsx"

# Query it immediately (no conversion needed!)
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT quarter, SUM(revenue) as total_revenue FROM quarterly_report GROUP BY quarter"}'
```

### Example 2: JSON API Data Processing

```bash
# Create JSON data (e.g., from an API response)
cat > products.json << EOF
[
  {"id": 1, "name": "Laptop", "price": 1200, "stock": 45},
  {"id": 2, "name": "Mouse", "price": 25, "stock": 150},
  {"id": 3, "name": "Keyboard", "price": 75, "stock": 89}
]
EOF

# Upload
curl -X POST "http://localhost:8000/upload" -F "file=@products.json"

# Find low-price items
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT name, price FROM products WHERE price < 100 ORDER BY price DESC"}'
```

### Example 3: Multi-File Join Analysis

```bash
# Upload customers data
curl -X POST "http://localhost:8000/upload" -F "file=@customers.csv"

# Upload orders data
curl -X POST "http://localhost:8000/upload" -F "file=@orders.csv"

# Join across datasets
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT c.name, COUNT(o.id) as order_count, SUM(o.amount) as total_spent FROM customers c LEFT JOIN orders o ON c.id = o.customer_id GROUP BY c.name ORDER BY total_spent DESC"}'
```

### Example 4: Parquet File Processing

```bash
# Upload Parquet file (common in data engineering)
curl -X POST "http://localhost:8000/upload" \
  -F "file=@large_dataset.parquet"

# Query instantly - no conversion needed
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT category, COUNT(*) FROM large_dataset GROUP BY category LIMIT 10"}'
```

---

## 🤖 LLM Integration Examples

### Python Integration

```python
import requests

def upload_file(filepath: str):
    with open(filepath, 'rb') as f:
        response = requests.post(
            'http://localhost:8000/upload',
            files={'file': f}
        )
    return response.json()

def query_data(sql: str):
    response = requests.post(
        'http://localhost:8000/query',
        json={'sql': sql}
    )
    return response.json()

# Use it
upload_file('sales_data.csv')
result = query_data("SELECT product, SUM(revenue) FROM sales_data GROUP BY product")
print(result)
```

### LangChain Integration

```python
from langchain.tools import Tool
import requests

def query_database(sql_query: str) -> dict:
    response = requests.post(
        "http://localhost:8000/query",
        json={"sql": sql_query}
    )
    return response.json()

# Create tool for your agent
data_query_tool = Tool(
    name="QueryData",
    func=query_database,
    description="Query uploaded datasets using SQL. Input should be a valid SQL query string."
)

# Add to your agent's tools
# Now your LLM can query any uploaded dataset!
```

### OpenAI Function Calling

```python
import openai
import requests

functions = [
    {
        "name": "query_database",
        "description": "Execute SQL query on uploaded data files",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "SQL query to execute on the data"
                }
            },
            "required": ["sql"]
        }
    }
]

def execute_query(sql: str):
    return requests.post(
        "http://localhost:8000/query",
        json={"sql": sql}
    ).json()

# Your AI can now generate and execute queries on any uploaded data
```

---

## 📊 Interactive API Documentation

Once the server is running, explore the API interactively:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Test endpoints directly in your browser!

---

## 🔧 Configuration & Customization

### Change the Port

Edit `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Change 8001 to your desired port
```

Then restart:
```bash
docker-compose down
docker-compose up --build
```

### Enable Persistent Storage

By default, data is stored in memory. To persist data across restarts:

**Edit `server.py`**, change line:
```python
conn = duckdb.connect(':memory:')
```

To:
```python
conn = duckdb.connect('/app/data/database.db')
```

Restart the server. Your data will now persist!

### Add File Size Limits

**Edit `server.py`**, add to the `upload_file` function:
```python
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    
    # ... rest of existing code
```

### Add Authentication

For production use, add API key authentication:

```python
from fastapi import Header, HTTPException

API_KEY = "your-secret-key"

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

# Add to endpoints
@app.post("/upload", dependencies=[Depends(verify_api_key)])
async def upload_file(file: UploadFile = File(...)):
    # ... existing code
```

---

## 🏗️ How It Works

```
┌─────────────────┐
│  Upload File    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Auto-Detect Format     │ ← CSV, JSON, Excel, Parquet, Avro
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│   Route to Parser       │
├─────────────────────────┤
│ Try: Polars (fast)      │ ← 5-10x faster than Pandas
│ Fallback: Pandas        │ ← Handles edge cases
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Load into DuckDB       │ ← In-memory SQL engine
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Query via REST API     │ ← SQL queries, instant results
└─────────────────────────┘
```

**Key Design Decisions:**

1. **Polars First**: 5-10x faster for most operations
2. **Pandas Fallback**: Broader compatibility for edge cases
3. **DuckDB**: Fast analytical queries without database setup
4. **In-Memory**: Zero configuration, instant queries
5. **REST API**: Easy integration with any language or tool

---

## 🐛 Troubleshooting

### Port Already in Use

**Error**: `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Solution**:
```bash
# Check what's using port 8000
lsof -i :8000

# Kill the process or change port in docker-compose.yml
```

### Permission Denied

**Error**: `Permission denied` when accessing uploads directory

**Solution**:
```bash
chmod -R 777 uploads/
```

### Container Won't Start

**Solution**:
```bash
# Check logs for detailed error
docker-compose logs

# Rebuild from scratch
docker-compose down
docker-compose up --build --force-recreate
```

### Out of Memory

**Error**: Container crashes with large files

**Solutions**:
1. Increase Docker memory: Docker Desktop → Settings → Resources → Memory
2. Use persistent storage instead of in-memory (see Configuration section)
3. Process large files in chunks

### Tests Fail with "Connection Refused"

**Solution**: Server takes time to start. Wait longer:
```bash
sleep 10 && ./test.sh
```

### Upload Fails with Specific Format

**Solution**: Check format is supported. For unsupported formats:
1. Convert to CSV/JSON first
2. Open an issue on GitHub for format support request

---

## 📁 Project Structure

```
mcp-data-server/
├── Dockerfile              # Container definition
├── docker-compose.yml      # Service orchestration
├── requirements.txt        # Python dependencies
├── server.py              # Main application
├── test.sh                # Automated tests
├── .gitignore             # Git exclusions
├── README.md              # This file
├── uploads/               # (created on first run)
└── data/                  # (created on first run)
```

### Key Files Explained

**`Dockerfile`**  
Defines the Python 3.11 environment with all system dependencies.

**`docker-compose.yml`**  
Single-service setup with health checks and volume mounts for data persistence.

**`requirements.txt`**  
All Python dependencies with pinned versions:
- FastAPI: REST API framework
- Polars: Fast data processing
- Pandas: Data compatibility layer
- DuckDB: In-memory SQL engine
- Format libraries: openpyxl, pyarrow, xlrd

**`server.py`**  
Main application with:
- Format auto-detection logic
- Smart routing (Polars → Pandas)
- DuckDB integration
- REST endpoints

**`test.sh`**  
Automated test suite covering all features.

---

## 🚀 Production Deployment Checklist

Before deploying to production:

- [ ] **Authentication**: Add API key or OAuth
- [ ] **Rate Limiting**: Prevent abuse
- [ ] **Persistent Storage**: Use DuckDB file storage
- [ ] **File Validation**: Check file types and sizes
- [ ] **Monitoring**: Add logging and metrics
- [ ] **CORS**: Configure for web clients
- [ ] **SSL/TLS**: Use HTTPS
- [ ] **Backups**: Regular data backups
- [ ] **Load Balancing**: For high traffic
- [ ] **Environment Variables**: For secrets management

---

## 💡 Common Use Cases

### 1. Self-Service Analytics for Business Users
- Analysts upload their own data files
- Query without waiting for engineering
- No format conversion needed

### 2. LLM Data Pipeline
- Upload datasets once
- LLM generates SQL queries
- Conversational data exploration

### 3. Data Integration Testing
- Upload test data in any format
- Validate transformations
- Quick iteration

### 4. Rapid Prototyping
- Experiment with different data sources
- No database setup required
- Instant feedback

### 5. Data Quality Checks
- Upload production exports
- Run validation queries
- Identify issues quickly

---

## 🤝 Contributing

Found a bug? Want a feature?

1. Check existing issues on GitHub
2. Fork the repository
3. Create a feature branch
4. Make your changes
5. Add tests if applicable
6. Submit a pull request

---

## 📄 License

MIT License - Use it, modify it, ship it to production.

See LICENSE file for full details.

---

## 🆘 Support

- **Issues**: [GitHub Issues](your-repo/issues)
- **API Docs**: http://localhost:8000/docs (when running)
- **Examples**: See test.sh for working code samples

---

## 🎯 What's Next?

This MCP server is a foundation. Extend it:

- [ ] Add streaming data support
- [ ] Connect to cloud storage (S3, GCS, Azure Blob)
- [ ] Build a web UI for non-technical users
- [ ] Add more data sources (APIs, databases)
- [ ] Integrate with data warehouses
- [ ] Add data transformation capabilities
- [ ] Support for more file formats
- [ ] Implement caching for repeated queries

