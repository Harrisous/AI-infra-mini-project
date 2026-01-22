#!/bin/bash
# Helper script to discover inference server pod endpoints
# Usage: ./discover-pods.sh

set -e

NAMESPACE="${NAMESPACE:-default}"
SERVICE_NAME="${SERVICE_NAME:-inference-headless}"

echo "Discovering inference server pods in namespace: $NAMESPACE"
echo ""

# Get pod IPs
POD_IPS=$(kubectl get pods -n "$NAMESPACE" -l app=inference-server -o jsonpath='{.items[*].status.podIP}')

if [ -z "$POD_IPS" ]; then
    echo "No inference server pods found"
    exit 1
fi

# Convert to URLs
URLS=""
for IP in $POD_IPS; do
    if [ -n "$URLS" ]; then
        URLS="$URLS,http://$IP:8000"
    else
        URLS="http://$IP:8000"
    fi
done

echo "Found pod URLs: $URLS"
echo ""
echo "To update trainer config:"
echo "kubectl patch configmap trainer-config -n $NAMESPACE --type merge -p '{\"data\":{\"INFERENCE_URLS\":\"$URLS\"}}'"
echo ""
echo "Or export for use:"
echo "export INFERENCE_URLS=\"$URLS\""
