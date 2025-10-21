#!/bin/bash
# Health check script for monitoring

set -e

API_URL="${API_URL:-http://localhost:8000}"

echo "=== Insight Graph Health Check ==="
echo "API URL: $API_URL"
echo ""

# Check API health
echo "Checking API health..."
HEALTH=$(curl -s "$API_URL/health" || echo '{"status": "error"}')
STATUS=$(echo "$HEALTH" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

if [ "$STATUS" = "healthy" ]; then
    echo "✓ API is healthy"
else
    echo "✗ API is unhealthy"
    exit 1
fi

# Check stats
echo ""
echo "Checking stats..."
STATS=$(curl -s "$API_URL/stats" || echo '{}')
echo "$STATS" | python3 -m json.tool

echo ""
echo "=== Health Check Complete ==="
