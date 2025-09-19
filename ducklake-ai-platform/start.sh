#!/bin/bash
echo "🦆 Starting DuckLake Sandbox..."
docker-compose up -d

echo ""
echo "⏰ Waiting for services to start..."
sleep 30

echo ""
echo "🎉 DuckLake Sandbox is ready!"
echo ""
echo "📊 Marimo Notebooks: http://localhost:2718"
echo "🗄️  MinIO Console:    http://localhost:9001"
echo "🐘 PostgreSQL:       localhost:5432"
echo ""
echo "🔑 Default credentials:"
echo "   MinIO: minioadmin / minioadmin"
echo "   PostgreSQL: postgres / ducklake123"
echo ""
echo "📖 Check README.md for usage examples"
echo ""
