#!/bin/bash

echo "=== Testing MCP Server ==="
sleep 5

echo "Creating test CSV..."
cat > test_data.csv << CSVEOF
id,name,department,salary
1,Alice,Engineering,95000
2,Bob,Marketing,75000
3,Charlie,Engineering,105000
CSVEOF

echo "1. Health check..."
curl -s http://localhost:8000/health | jq '.'

echo -e "\n2. Uploading CSV..."
curl -s -X POST "http://localhost:8000/upload" -F "file=@test_data.csv" | jq '.'

echo -e "\n3. Querying data..."
curl -s -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM test_data WHERE department = '\''Engineering'\''"}' | jq '.'

echo -e "\n=== Tests complete ==="
