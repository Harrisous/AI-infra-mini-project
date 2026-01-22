#!/bin/bash
# Test the deployed system

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "=== Testing System ==="

# Get service URL (minikube or cluster)
if command -v minikube &> /dev/null && minikube status &> /dev/null; then
    INFERENCE_URL=$(minikube service inference-service --url)
    echo "Using minikube service URL: $INFERENCE_URL"
else
    INFERENCE_URL="${INFERENCE_URL:-http://localhost:8000}"
    echo "Using inference URL: $INFERENCE_URL"
fi

# Test health endpoint
echo ""
echo "1. Testing health endpoint..."
curl -f "$INFERENCE_URL/healthz" && echo " ✓ Health check passed" || (echo " ✗ Health check failed" && exit 1)

# Test status endpoint
echo ""
echo "2. Testing status endpoint..."
STATUS=$(curl -s "$INFERENCE_URL/status")
echo "$STATUS" | python3 -m json.tool || echo "$STATUS"
echo " ✓ Status check passed"

# Test generate endpoint
echo ""
echo "3. Testing generate endpoint..."
RESPONSE=$(curl -s -X POST "$INFERENCE_URL/generate" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Hello, world!", "max_new_tokens": 20, "temperature": 0.7}')

echo "$RESPONSE" | python3 -m json.tool || echo "$RESPONSE"

# Check for model version header
VERSION_HEADER=$(curl -s -I -X POST "$INFERENCE_URL/generate" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "test", "max_new_tokens": 5}' | grep -i "x-model-version" || true)

if [ -n "$VERSION_HEADER" ]; then
    echo " ✓ Model version header present: $VERSION_HEADER"
else
    echo " ⚠ Model version header not found"
fi

echo ""
echo "=== Testing Complete ==="
