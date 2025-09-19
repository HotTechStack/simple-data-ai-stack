# 🦆 DuckLake AI Platform - Lakehouse in a Box

Build a complete data platform in 30 minutes with DuckDB + DuckLake + Marimo.

**What you get:** Enterprise lakehouse capabilities that normally cost $50K+/year, running on your laptop for $0.

## 🚀 Quick Start (30 seconds)

```bash
# Start the lakehouse
docker-compose up -d

# Wait 30 seconds for services to start, then visit:
# 📊 Marimo Notebooks: http://localhost:2718
# 🗄️  MinIO Console: http://localhost:9001 (minioadmin/minioadmin)
```

## 📦 What's Inside

- **DuckDB with DuckLake** - SQLite for analytics, now with snapshots
- **PostgreSQL** - The metadata brain  
- **MinIO** - S3-compatible storage that runs locally
- **Marimo** - Python notebooks that actually work
- **Full ACID transactions** - Multiple users, no conflicts
- **Time travel queries** - Rollback experiments instantly
- **Vector search ready** - VSS + FTS extensions loaded

## 🎯 Perfect For

- **Prototyping AI features** without burning warehouse credits
- **Data team sandboxes** with proper isolation  
- **Local development** that scales to production
- **Learning modern data stack** without complexity
- **Cost optimization** - offload expensive ad-hoc queries

## 🛠️ Setup Details

### File Structure
```
ducklake-sandbox/
├── docker-compose.yml          # Main orchestration
├── Dockerfile.marimo          # Marimo environment  
├── requirements.txt           # Python dependencies
├── init-scripts/             
│   └── 01-init-ducklake.sql   # Postgres setup
├── notebooks/
│   └── ducklake_demo.py       # Demo notebook
└── .env.example               # Configuration template
```

### Services

| Service | Port | Purpose |
|---------|------|---------|
| Marimo | 2718 | Interactive notebooks |
| PostgreSQL | 5432 | Metadata catalog |
| MinIO | 9000/9001 | Object storage + UI |

### Default Credentials
- **MinIO**: `minioadmin` / `minioadmin`  
- **PostgreSQL**: `postgres` / `ducklake123`

## 📈 Usage Examples

### 1. Load Your Data
```python
# In Marimo notebook
import duckdb
conn = duckdb.connect()

# Connect to your lakehouse
conn.execute("USE lakehouse;")

# Load from anywhere
conn.execute("CREATE TABLE my_data AS SELECT * FROM 'path/to/data.csv';")
```

### 2. Create Snapshots
```python
# Save current state
conn.execute("SELECT ducklake_snapshot('lakehouse');")

# Query historical data
conn.execute("SELECT * FROM my_table FOR SNAPSHOT 1;")
```

### 3. AI Integration
```python
# Vector search ready
conn.execute("CREATE INDEX my_vectors ON my_table USING HNSW (embedding);")

# Full-text search  
conn.execute("CREATE INDEX my_text_idx ON my_table USING FTS (text_column);")
```

## 🔥 Advanced Features

### Multiple Environments
```bash
# Production-like setup
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up

# Add more compute nodes
docker-compose scale marimo=3
```

### External Storage
```yaml
# Use real S3 in production
environment:
  - AWS_ACCESS_KEY_ID=your_real_key
  - AWS_SECRET_ACCESS_KEY=your_real_secret  
  - AWS_ENDPOINT_URL=https://s3.amazonaws.com
```

### Team Sharing
```python
# Each user gets isolated sandbox
ATTACH 'ducklake:postgres:...' AS user_sandbox_alice (DATA_PATH 's3://team-bucket/alice/');
ATTACH 'ducklake:postgres:...' AS user_sandbox_bob (DATA_PATH 's3://team-bucket/bob/');
```

## 🚀 Production Deployment

This same setup runs on any cloud provider:

1. **AWS**: RDS Postgres + S3 + ECS/EKS
2. **GCP**: Cloud SQL + GCS + GKE  
3. **Azure**: PostgreSQL + Blob Storage + AKS
4. **Any VPS**: Same docker-compose on $5/month server

No vendor lock-in, no surprise bills.

## 🤝 Contributing

Found a bug? Want to add features? PRs welcome!

Common additions:
- dbt integration
- Streamlit dashboard
- Airflow scheduling  
- Prometheus monitoring

## 📚 Learn More

- [DuckLake Docs](https://ducklake.select/)
- [DuckDB Extensions](https://duckdb.org/docs/extensions/)
- [Marimo Guide](https://docs.marimo.io/)

## ⭐ Star This Repo

If this saved you from expensive warehouse bills, consider giving it a star! 

**Questions?** Open an issue or discussion.

---

*Built with ❤️ by the data community. From laptop to lakehouse in minutes.*
