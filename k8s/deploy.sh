#!/bin/bash
# Deployment script for Kubernetes
# Usage: ./deploy.sh [namespace]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAMESPACE="${1:-default}"

echo "=== Deploying AI Infra Mini Project to Kubernetes ==="
echo "Namespace: $NAMESPACE"
echo ""

# Create namespace if it doesn't exist (if not using default)
if [ "$NAMESPACE" != "default" ]; then
    echo "Creating namespace: $NAMESPACE"
    kubectl create namespace "$NAMESPACE" || true
fi

# Apply manifests in order
echo "1. Creating storage..."
kubectl apply -f "$SCRIPT_DIR/storage.yaml" -n "$NAMESPACE"

echo "Waiting for PVC to be bound..."
kubectl wait --for=condition=Bound pvc/model-storage -n "$NAMESPACE" --timeout=60s || echo "Warning: PVC not bound yet"

echo "2. Creating config maps..."
kubectl apply -f "$SCRIPT_DIR/config.yaml" -n "$NAMESPACE"

echo "3. Deploying inference servers..."
kubectl apply -f "$SCRIPT_DIR/inference-service.yaml" -n "$NAMESPACE"
kubectl apply -f "$SCRIPT_DIR/inference-headless-service.yaml" -n "$NAMESPACE"
kubectl apply -f "$SCRIPT_DIR/inference-deployment.yaml" -n "$NAMESPACE"

echo "4. Deploying trainer server..."
kubectl apply -f "$SCRIPT_DIR/trainer-service.yaml" -n "$NAMESPACE"
kubectl apply -f "$SCRIPT_DIR/trainer-deployment.yaml" -n "$NAMESPACE"

echo "5. Deploying UI server..."
kubectl apply -f "$SCRIPT_DIR/ui-deployment.yaml" -n "$NAMESPACE"
kubectl apply -f "$SCRIPT_DIR/ui-service.yaml" -n "$NAMESPACE"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Checking pod status..."
kubectl get pods -n "$NAMESPACE" -l 'app in (inference-server,trainer-server,ui-server)'

echo ""
echo "To view logs:"
echo "  kubectl logs -l app=inference-server -n $NAMESPACE"
echo "  kubectl logs -l app=trainer-server -n $NAMESPACE"
echo "  kubectl logs -l app=ui-server -n $NAMESPACE"
echo ""
echo "To access UI:"
echo "  kubectl port-forward svc/ui-service 8080:80 -n $NAMESPACE"
echo "  Then open http://localhost:8080"
echo ""
echo "To discover inference pod URLs for trainer:"
echo "  ./discover-pods.sh"
