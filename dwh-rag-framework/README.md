# Data-Warehouse-First RAG + Agent Testing Environment

A complete Docker-based environment for testing RAG pipelines and LLM agents against data warehouse snapshots. Built with DuckDB, LightRAG, Marimo, and modern Python tooling.

## Overview

This project provides:
- Isolated testing of RAG systems using DuckDB snapshots (no impact on production)
- Incremental indexing with LightRAG (vector + knowledge graph hybrid search)
- Interactive validation via Marimo notebooks
- Automated pipelines with Cronicle scheduling
- Text-to-SQL agents with graceful fallback to live databases

## Quick Start

```bash
# 1. Clone/download the project
cd rag-testing-env

# 2. Set up environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Start all services
docker-compose up -d

# 4. Access Marimo notebooks
open http://localhost:8080
```

## Architecture

```
Production Postgres → DuckDB Snapshot → Documents (CSV/JSON)
                                           ↓
                                      LightRAG Index
                                    (Vector + Graph)
                                           ↓
                                      LLM Agents
                                (Text-to-SQL, Q&A)
```

## Prerequisites

- Docker & Docker Compose
- OpenAI API key (or configure for local models)
- 4GB+ RAM recommended
- 10GB+ disk space

## Project Structure

```
rag-testing-env/
├── docker-compose.yml          # All services orchestration
├── Dockerfile                  # Python app container
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
├── data/
│   ├── warehouse/             # Postgres init SQL (sample data)
│   ├── snapshots/             # DuckDB snapshot files
│   ├── documents/             # Converted documents (CSV, JSON)
│   └── lightrag/              # LightRAG vector/graph storage
├── notebooks/                 # Marimo interactive notebooks
│   ├── 01_snapshot.py         # Create snapshot & convert
│   ├── 02_validate_kg.py      # Index & validate KG
│   └── 03_test_agent.py       # Test Text-to-SQL agent
├── pipelines/                 # Cronicle automation jobs
│   ├── snapshot_job.py        # Scheduled snapshot creation
│   ├── index_job.py           # Scheduled indexing
│   └── validation_job.py      # Scheduled validation
└── src/                       # Core Python modules
    ├── snapshot.py            # Postgres → DuckDB snapshotting
    ├── converter.py           # DuckDB → documents conversion
    ├── indexer.py             # LightRAG indexing (async)
    ├── validator.py           # Knowledge graph validation
    └── agent.py               # Text-to-SQL LLM agent
```

## Services

The docker-compose stack includes:

| Service | Port | Purpose |
|---------|------|---------|
| **Postgres** | 5432 (internal) / 5438 (host) | Sample data warehouse |
| **Redis** | 6379 | Caching layer |
| **Cronicle** | 3012 | Job scheduler & orchestrator |
| **App (Marimo)** | 8080 | Interactive Python notebooks |

## Setup Instructions

### 1. Environment Configuration

Create `.env` file:
```bash
cp .env.example .env
```

Edit `.env` and add:
```env
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### 2. Start Services

```bash
# Start everything
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f app
```

### 3. Verify Setup

```bash
# Test Postgres connection
docker-compose exec postgres psql -U user -d warehouse -c "SELECT COUNT(*) FROM customers;"

# Test Python environment
docker-compose exec app python3 -c "import lightrag; print('LightRAG OK')"

# Test OpenAI connection (if configured)
docker-compose exec app python3 -c "import openai; print('OpenAI OK')"
```

## Usage Workflow

### Step 1: Create Snapshot (Notebook 01)

Open http://localhost:8080 and select `01_snapshot.py`

The notebook automatically:
1. Connects to Postgres warehouse
2. Creates DuckDB snapshot at `/app/data/snapshots/warehouse.duckdb`
3. Converts tables to CSV and JSON documents
4. Saves to `/app/data/documents/`

**Expected Output:**
```
✅ Snapshot Created!
Path: /app/data/snapshots/warehouse.duckdb

✅ Documents Created!
Total: 9 documents
```

**What's happening:**
- Tables: `customers`, `orders`, `products` → DuckDB
- Each row becomes a JSON document for RAG
- CSV exports for human inspection

### Step 2: Index & Validate (Notebook 02)

Open `02_validate_kg.py`

The notebook automatically:
1. Loads JSON documents from Step 1
2. Indexes into LightRAG (async initialization)
3. Creates vector embeddings + knowledge graph
4. Validates entity extraction and relationships

**Expected Output:**
```
✅ Loaded 9 documents

✅ Indexed 9 documents

✅ Validation Complete!
- Entities: 45
- Relations: 38
- Orphans: 2
- Accuracy: 95.6%
```

**What's happening:**
- LightRAG extracts entities (customers, products, etc.)
- Builds relationship graph (customer → orders → products)
- Validates graph structure for completeness

### Step 3: Test Agent (Notebook 03)

Open `03_test_agent.py`

The notebook:
1. Initializes Text-to-SQL agent
2. Provides text input for natural language queries
3. Converts to SQL using LLM + RAG context
4. Executes against DuckDB snapshot
5. Falls back to live warehouse if snapshot fails

**Example Usage:**
```
Query: "How many customers do we have?"

✅ Success!

SQL:
SELECT COUNT(*) as customer_count FROM customers

Results:
| customer_count |
|---------------|
| 3             |
```

**Try these queries:**
- "What is the total revenue from completed orders?"
- "List all products in the Electronics category"
- "Which customer has the highest order amount?"
- "Show me pending orders with customer names"

## Automation with Cronicle

Once validated manually, schedule automated jobs:

1. Visit http://localhost:3012
2. Login: `admin` / `admin`
3. Create jobs:

**Daily Snapshot:**
- Schedule: `0 2 * * *` (2 AM daily)
- Command: `/opt/cronicle/plugins/pipelines/snapshot_job.py`
- Creates fresh snapshot every night

**Hourly Indexing:**
- Schedule: `0 * * * *` (every hour)
- Command: `/opt/cronicle/plugins/pipelines/index_job.py`
- Updates RAG index with new data

**Post-Index Validation:**
- Trigger: After indexing job completes
- Command: `/opt/cronicle/plugins/pipelines/validation_job.py`
- Validates knowledge graph quality

## Monitoring & Validation

### Check Snapshot Health

```bash
# Verify snapshot exists
docker-compose exec app ls -lh /app/data/snapshots/

# Inspect snapshot
docker-compose exec app python3 << EOF
import duckdb
conn = duckdb.connect('/app/data/snapshots/warehouse.duckdb', read_only=True)
print("Tables:", conn.execute("SHOW TABLES").fetchall())
print("Rows:", conn.execute("SELECT COUNT(*) FROM customers").fetchone())
conn.close()
EOF
```

### Check Document Conversion

```bash
# List converted files
docker-compose exec app ls -lh /app/data/documents/

# Inspect JSON structure
docker-compose exec app head -20 /app/data/documents/customers.json
```

### Check LightRAG Index

```bash
# Check index files
docker-compose exec app ls -lh /app/data/lightrag/

# View graph structure (if available)
docker-compose exec app python3 -c "
from lightrag import LightRAG
rag = LightRAG(working_dir='/app/data/lightrag')
print('Index loaded successfully')
"
```

## Key Components Explained

### Snapshot Module (`src/snapshot.py`)

Creates isolated DuckDB copies of Postgres tables:
- Connects to Postgres warehouse
- Iterates through all tables
- Copies data to DuckDB file
- Deletes old snapshot if exists

**Why?** Test RAG without impacting production database.

### Converter Module (`src/converter.py`)

Transforms DuckDB tables into documents:
- Exports tables to CSV (human-readable)
- Creates JSON documents per row (for RAG)
- Includes metadata (table name, row ID)

**Why?** RAG systems need document format, not SQL tables.

### Indexer Module (`src/indexer.py`)

Async LightRAG indexing:
- Uses OpenAI embeddings via `openai_embed`
- Uses GPT-4o-mini for completions via `gpt_4o_mini_complete`
- Initializes storage + pipeline status
- Supports incremental updates

**Important:** Uses async/await pattern with `nest_asyncio` for Marimo compatibility.

### Validator Module (`src/validator.py`)

Knowledge graph quality checks:
- Entity count
- Relation count
- Orphan node detection (entities without connections)
- Extraction accuracy metric

**Why?** Ensures RAG is extracting meaningful information.

### Agent Module (`src/agent.py`)

Text-to-SQL conversion:
- Takes natural language query
- Uses LLM to generate SQL
- Executes against DuckDB snapshot
- Falls back to live warehouse on failure

**Why?** Make data accessible via natural language.

## Troubleshooting

### Issue: Marimo button does nothing

**Solution:** Hard refresh browser
```bash
# Windows/Linux: Ctrl + Shift + R
# Mac: Cmd + Shift + R
```

### Issue: "Table already exists" error

**Solution:** Delete old snapshot
```bash
docker-compose exec app rm -f /app/data/snapshots/warehouse.duckdb
```

### Issue: "Pipeline not initialized" error

**Solution:** Ensure `initialize_pipeline_status()` is called in `src/indexer.py`
```python
await rag.initialize_storages()
await initialize_pipeline_status()  # Must be after initialize_storages()
```

### Issue: "RuntimeError: Event loop already running"

**Solution:** Already fixed with `nest_asyncio` in indexer. If still occurring:
```bash
# Rebuild container
docker-compose down
docker-compose build --no-cache app
docker-compose up -d
```

### Issue: OpenAI API errors

**Solution:** Check API key
```bash
docker-compose exec app env | grep OPENAI_API_KEY
# Should show: OPENAI_API_KEY=sk-...

# If missing, add to .env and restart
docker-compose restart app
```

### Issue: Postgres connection refused

**Solution:** Check Postgres is running
```bash
docker-compose ps postgres
docker-compose logs postgres

# Restart if needed
docker-compose restart postgres
```

## Customization

### Using Your Own Database

Edit connection string in notebooks:
```python
# notebooks/01_snapshot.py
pg_conn = "postgresql://your_user:your_pass@your_host:5432/your_db"
```

### Using Local Models (Ollama)

Modify `src/indexer.py` to use local embeddings:
```python
from lightrag.llm import ollama_model_complete, ollama_embedding

rag = LightRAG(
    working_dir=storage_dir,
    embedding_func=ollama_embedding,
    llm_model_func=ollama_model_complete,
)
```

### Custom Document Formats

Extend `src/converter.py` to support more formats:
```python
# Add PDF support
from pypdf import PdfReader

def convert_to_pdf(df, output_path):
    # Your PDF conversion logic
    pass
```

### Custom Validation Rules

Add business logic to `src/validator.py`:
```python
def validate_business_rules(rag, rules):
    # Check for required entities
    # Validate relationship constraints
    # Return compliance report
    pass
```

## Performance Optimization

### For Large Databases

1. **Sample data** instead of full snapshot:
```python
# In src/snapshot.py
cur.execute(f"SELECT * FROM {table} LIMIT 10000")
```

2. **Batch document processing**:
```python
# In src/indexer.py
for batch in chunk_documents(documents, batch_size=100):
    await rag.ainsert(batch)
```

3. **Parallel table conversion**:
```python
# In src/converter.py
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor() as executor:
    executor.map(convert_table, tables)
```

### For Faster Indexing

1. Use smaller embedding models
2. Reduce chunk size in LightRAG config
3. Skip validation step in production runs

## Security Considerations

### Production Deployment

1. **Change default passwords:**
```yaml
# docker-compose.yml
POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}  # Use env var
```

2. **Add authentication to Marimo:**
```dockerfile
# Dockerfile
CMD ["marimo", "edit", "--host", "0.0.0.0", "--port", "8080", "--auth"]
```

3. **Restrict network access:**
```yaml
# docker-compose.yml
services:
  app:
    networks:
      - internal
networks:
  internal:
    internal: true  # No external access
```

4. **Encrypt snapshots at rest:**
```bash
# Use encrypted volumes
docker volume create --driver local \
  --opt type=none \
  --opt device=/encrypted/path \
  --opt o=bind \
  encrypted_snapshots
```

## Advanced Features

### Version Control

Track snapshot schemas:
```bash
# In pipelines/snapshot_job.py
import hashlib
schema = get_database_schema()
schema_hash = hashlib.sha256(schema.encode()).hexdigest()
save_schema_version(schema_hash)
```

### A/B Testing

Compare RAG configurations:
```python
# Create two indexes with different settings
rag_v1 = LightRAG(working_dir="./v1", chunk_size=512)
rag_v2 = LightRAG(working_dir="./v2", chunk_size=1024)

# Compare results
results_v1 = rag_v1.query("test query")
results_v2 = rag_v2.query("test query")
```

### Multi-tenant Support

Separate storage per tenant:
```python
# In src/indexer.py
def index_documents(documents, storage_dir, tenant_id):
    tenant_dir = f"{storage_dir}/{tenant_id}"
    rag = LightRAG(working_dir=tenant_dir)
    # ... rest of indexing
```

## Contributing

This is a reference implementation. Key areas for enhancement:

1. **Additional connectors:** MySQL, BigQuery, Snowflake support
2. **More document formats:** Excel, PowerPoint, Confluence
3. **Advanced validation:** Schema drift detection, data quality checks
4. **UI improvements:** Web dashboard, real-time metrics
5. **Cost optimization:** Token usage tracking, caching strategies

## FAQ

**Q: Can I use this with production databases?**  
A: Yes, but use read replicas and schedule snapshots during low-traffic periods.

**Q: How often should I refresh snapshots?**  
A: Depends on data velocity. Daily for slowly-changing data, hourly for dynamic datasets.

**Q: What if my database is too large?**  
A: Implement sampling, partition by date ranges, or focus on specific tables.

**Q: Can I use other LLM providers?**  
A: Yes, modify `src/indexer.py` and `src/agent.py` to use Anthropic, Cohere, or local models.

**Q: How do I scale this horizontally?**  
A: Deploy multiple app containers with shared storage (NFS/S3) and load balancing.

**Q: What about cost control?**  
A: Use local models for embeddings, cache LLM responses, implement rate limiting.

## License

MIT

## Support

For issues and questions:
1. Check Troubleshooting section above
2. Review docker-compose logs: `docker-compose logs`
3. Inspect notebook errors in browser
4. Test components individually as shown in Monitoring section

## Acknowledgments

- **LightRAG:** https://github.com/HKUDS/LightRAG
- **Marimo:** https://marimo.io
- **DuckDB:** https://duckdb.org
- **Cronicle:** https://github.com/jhuckaby/Cronicle