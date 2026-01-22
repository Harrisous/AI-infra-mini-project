#!/bin/bash
# Deploy to Kubernetes (minikube or cluster)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "=== Deploying to Kubernetes ==="

# Apply manifests in order
echo "Creating storage..."
kubectl apply -f k8s/storage.yaml

echo "Creating config..."
kubectl apply -f k8s/config.yaml

echo "Creating inference deployment..."
kubectl apply -f k8s/inference-deployment.yaml

echo "Creating inference service..."
kubectl apply -f k8s/inference-service.yaml

echo "Creating trainer deployment..."
kubectl apply -f k8s/trainer-deployment.yaml

echo ""
echo "=== Deployment Complete ==="
echo "Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app=inference-server --timeout=300s || true
kubectl wait --for=condition=ready pod -l app=trainer-server --timeout=60s || true

echo ""
echo "Status:"
kubectl get pods
kubectl get services
