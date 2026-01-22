#!/bin/bash
# Build Docker images for inference and trainer servers

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "=== Building Docker Images ==="

# Build inference server
echo "Building inference-server image..."
docker build -f docker/inference-server.Dockerfile -t inference-server:latest .

# Build trainer server
echo "Building trainer-server image..."
docker build -f docker/trainer-server.Dockerfile -t trainer-server:latest .

echo "✓ Images built successfully"
echo "  - inference-server:latest"
echo "  - trainer-server:latest"
