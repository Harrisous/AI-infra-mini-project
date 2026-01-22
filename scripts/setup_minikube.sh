#!/bin/bash
# Setup minikube for local Kubernetes development

set -e

echo "=== Minikube Setup ==="

# Check if minikube is installed
if ! command -v minikube &> /dev/null; then
    echo "Error: minikube is not installed"
    echo "Install from: https://minikube.sigs.k8s.io/docs/start/"
    exit 1
fi

# Start minikube if not running
if ! minikube status &> /dev/null; then
    echo "Starting minikube..."
    minikube start --driver=docker --memory=8192 --cpus=4
else
    echo "Minikube is already running"
fi

# Enable addons
echo "Enabling minikube addons..."
minikube addons enable storage-provisioner
minikube addons enable default-storageclass

# Load Docker images into minikube
echo "Loading Docker images into minikube..."
minikube image load inference-server:latest || echo "Note: inference-server image not found. Build it first with scripts/build_images.sh"
minikube image load trainer-server:latest || echo "Note: trainer-server image not found. Build it first with scripts/build_images.sh"

echo ""
echo "=== Minikube Setup Complete ==="
echo "To use minikube's Docker daemon: eval \$(minikube docker-env)"
echo "To access services: minikube service <service-name>"
