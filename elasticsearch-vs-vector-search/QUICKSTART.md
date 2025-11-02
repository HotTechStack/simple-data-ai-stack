# Elasticsearch vs Vector Search - Quick Start

Get up and running in 3 minutes!

## Prerequisites
- Docker & Docker Compose
- 4GB RAM available
- ~2GB disk space

## 🚀 Quick Start

```bash
# 1. Navigate to directory
cd elasticsearch-vs-vector-search

# 2. Start services
./run.sh start

# 3. Set up data (generates 1,000 products and loads into both systems)
./run.sh setup

# 4. Run the comprehensive demo
./run.sh demo
```

That's it! The demo will walk you through all the key scenarios from the blog post.

## 📋 Available Commands

```bash
./run.sh start      # Start Elasticsearch + PostgreSQL + pgvector
./run.sh setup      # Generate and load sample data
./run.sh demo       # Run comprehensive demo (all scenarios)
./run.sh keyword    # Run keyword search demo only
./run.sh vector     # Run vector search demo only
./run.sh hybrid     # Run hybrid search demo only
./run.sh shell      # Interactive Python shell with search modules
./run.sh status     # Check service status and data counts
./run.sh logs       # View service logs
./run.sh stop       # Stop all services
./run.sh clean      # Remove all containers and data
```

## 🎯 What You'll See

### Part 1: When Keyword Search Wins
- Exact SKU lookup (< 5ms)
- Error code search (structured data)
- Boolean logic (AND, OR, NOT)
- Typo handling without embeddings

### Part 2: When Vector Search Wins
- Vague conceptual queries
- Semantic similarity
- Cross-category discovery

### Part 3: Cost Comparison
- Data loading time differences
- Infrastructure requirements
- Query latency comparison

### Part 4: Hybrid Approach (Best Practice)
- Filter 1M → 1K with Elasticsearch
- Rank with vector similarity
- Best of both worlds

### Part 5: Decision Framework
- Clear guidelines for choosing the right approach
- Production considerations

## 🔍 Try Your Own Queries

```bash
# Start interactive shell
./run.sh shell

# In the Python shell:
keyword_searcher = KeywordSearch()
vector_searcher = VectorSearch()
hybrid_searcher = HybridSearch()

# Example: Exact match
keyword_searcher.search_by_sku("ELEC-000001")

# Example: Semantic search
vector_searcher.semantic_search("comfortable work from home setup")

# Example: Hybrid
hybrid_searcher.hybrid_search(
    query="portable audio",
    category="electronics",
    max_price=100
)
```

## 📊 Service Endpoints

- **Elasticsearch**: http://localhost:9200
- **PostgreSQL**: localhost:5432
  - Database: `searchdb`
  - User: `searchuser`
  - Password: `searchpass`

## 🐛 Troubleshooting

### Services won't start
```bash
# Check if ports are already in use
lsof -i :9200  # Elasticsearch
lsof -i :5432  # PostgreSQL

# Clean up and restart
./run.sh clean
./run.sh start
```

### Data won't load
```bash
# Check service health
./run.sh status

# View logs
./run.sh logs

# Retry setup
./run.sh setup
```

### Out of memory
```bash
# Stop other Docker containers
docker ps
docker stop <container-id>

# Or increase Docker memory limit in Docker Desktop settings
```

## 📚 Learn More

- Full documentation: [README.md](README.md)
- Blog post insights: All key points validated in demo
- Code examples: Check `scripts/` directory

## 💡 Key Takeaways

1. **Start with keyword search** — handles 80% of use cases
2. **Add vectors when meaning matters** — semantic understanding
3. **Use hybrid for production** — filter + rank approach
4. **pgvector wins for most teams** — simpler than separate DBs
5. **Fix data quality first** — garbage embeddings lose to good keyword search
6. **The best stack is boring** — Elastic for filters, vectors for meaning

Happy searching! 🔍
