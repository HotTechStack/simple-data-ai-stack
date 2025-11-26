#!/bin/bash
# Script to setup Grafana datasources and import dashboard

set -e

GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
GRAFANA_USER="${GRAFANA_USER:-admin}"
GRAFANA_PASS="${GRAFANA_PASS:-admin}"

echo "=========================================="
echo "Grafana Dashboard Setup"
echo "=========================================="
echo ""

# Wait for Grafana to be ready
echo "Waiting for Grafana to be ready..."
for i in {1..30}; do
    if curl -s "${GRAFANA_URL}/api/health" > /dev/null 2>&1; then
        echo "✓ Grafana is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "✗ Grafana failed to start"
        exit 1
    fi
    sleep 1
done

echo ""
echo "Importing dashboard..."

# Import dashboard (datasource will be resolved by name "VictoriaMetrics")
DASHBOARD_JSON=$(cat grafana/dashboards/pipeline-observability.json)

IMPORT_PAYLOAD=$(cat <<EOF
{
  "dashboard": ${DASHBOARD_JSON},
  "overwrite": true,
  "inputs": []
}
EOF
)

RESPONSE=$(curl -s -X POST "${GRAFANA_URL}/api/dashboards/db" \
  -H "Content-Type: application/json" \
  -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
  -d "${IMPORT_PAYLOAD}")

if echo "$RESPONSE" | grep -q '"status":"success"'; then
    DASHBOARD_URL=$(echo "$RESPONSE" | grep -o '"url":"[^"]*"' | cut -d'"' -f4)
    echo "✓ Dashboard imported successfully!"
    echo ""
    echo "Dashboard URL: ${GRAFANA_URL}${DASHBOARD_URL}"
else
    echo "✗ Dashboard import failed"
    echo "Response: $RESPONSE"
    echo ""
    echo "This is normal if datasource doesn't exist yet."
    echo "Please create VictoriaMetrics datasource first in Grafana UI."
    exit 1
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Start the pipeline: uv run python polars_pipeline.py"
echo "2. View dashboard: ${GRAFANA_URL}/d/pipeline-observability"
echo ""
