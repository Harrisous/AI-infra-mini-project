# Kubernetes Deployment Guide

This directory contains Kubernetes manifests for deploying the AI Infra Mini Project.

## Architecture

The deployment consists of:
- **Inference Server**: 2 replicas serving model inference (GPU required)
- **Trainer Server**: 1 replica that orchestrates training simulations
- **UI Server**: 1 replica providing web interface
- **Shared Storage**: PersistentVolumeClaim for model cache (100Gi)

## Prerequisites

1. **Kubernetes cluster** with:
   - GPU nodes (for inference servers)
   - Storage class configured (adjust `storageClassName` in `storage.yaml` if needed)
   - kubectl configured

2. **Docker images** built and available:
   - `inference-server:latest`
   - `trainer-server:latest`
   - `ui-server:latest`

## Building Docker Images

```bash
# From project root
docker build -f docker/inference-server.Dockerfile -t inference-server:latest .
docker build -f docker/trainer-server.Dockerfile -t trainer-server:latest .
docker build -f docker/ui-server.Dockerfile -t ui-server:latest .

# If using a private registry, tag and push:
# docker tag inference-server:latest your-registry/inference-server:latest
# docker push your-registry/inference-server:latest
```

## Deployment Steps

### 1. Create Storage

```bash
kubectl apply -f k8s/storage.yaml
```

Wait for PVC to be bound:
```bash
kubectl get pvc model-storage
```

### 2. Create ConfigMaps

```bash
kubectl apply -f k8s/config.yaml
```

### 3. Deploy Inference Servers

```bash
kubectl apply -f k8s/inference-service.yaml
kubectl apply -f k8s/inference-headless-service.yaml
kubectl apply -f k8s/inference-deployment.yaml
```

Check deployment status:
```bash
kubectl get pods -l app=inference-server
kubectl logs -l app=inference-server --tail=50
```

**Note**: Initial model download may take several minutes. Pods will be ready when models are loaded.

### 4. Deploy Trainer Server

```bash
kubectl apply -f k8s/trainer-service.yaml
kubectl apply -f k8s/trainer-deployment.yaml
```

### 5. Deploy UI Server

```bash
kubectl apply -f k8s/ui-deployment.yaml
kubectl apply -f k8s/ui-service.yaml
```

### 6. Access the UI

The UI service is configured as `LoadBalancer`. Get the external IP:

```bash
kubectl get svc ui-service
```

If using `NodePort` or `ClusterIP`, use port-forwarding:

```bash
kubectl port-forward svc/ui-service 8080:80
```

Then access at `http://localhost:8080`

## Configuration

### Model Configuration

Edit `k8s/config.yaml` to change:
- Initial model: `INITIAL_MODEL_REPO_ID` in `inference-config`
- Substitute model: `SUBSTITUTE_MODEL` in `trainer-config`

### Resource Requirements

**Inference Servers** (per replica):
- Memory: 8-16 Gi
- CPU: 2-4 cores
- GPU: 1 NVIDIA GPU (required)

**Trainer Server**:
- Memory: 512 Mi - 1 Gi
- CPU: 0.5-1 core

**UI Server**:
- Memory: 256-512 Mi
- CPU: 0.25-0.5 core

Adjust in deployment YAMLs if needed.

### Storage

The default PVC requests 100Gi. Adjust in `k8s/storage.yaml`:

```yaml
resources:
  requests:
    storage: 100Gi  # Change as needed
```

For cloud providers, update `storageClassName`:
- AWS: `gp3` or `gp2`
- GCP: `standard` or `premium-rwo`
- Azure: `managed-premium`

## Synchronization

The deployment uses **file-based synchronization** for model updates:

1. Trainer or any pod writes to `/models/sync_state.json` on the shared PVC
2. All inference pods watch this file via `SyncCoordinator`
3. When the file changes, pods automatically update their models

This ensures all replicas stay in sync without requiring direct pod-to-pod communication.

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods
kubectl describe pod <pod-name>
```

### View Logs

```bash
# Inference servers
kubectl logs -l app=inference-server --tail=100

# Trainer
kubectl logs -l app=trainer-server --tail=100

# UI
kubectl logs -l app=ui-server --tail=100
```

### Check Services

```bash
kubectl get svc
kubectl describe svc inference-service
```

### Check Storage

```bash
kubectl get pvc
kubectl describe pvc model-storage
```

### Common Issues

1. **Pods stuck in Pending**: Check resource availability (especially GPU)
   ```bash
   kubectl describe pod <pod-name>
   ```

2. **PVC not binding**: Check storage class and available storage
   ```bash
   kubectl get storageclass
   ```

3. **Models not loading**: Check logs for download errors
   ```bash
   kubectl logs -l app=inference-server | grep -i error
   ```

4. **Service not accessible**: Verify service selectors match pod labels
   ```bash
   kubectl get endpoints inference-service
   ```

## Scaling

### Scale Inference Servers

```bash
kubectl scale deployment inference-server --replicas=3
```

**Note**: All replicas share the same PVC, so model updates will sync automatically.

### Scale UI Server

```bash
kubectl scale deployment ui-server --replicas=2
```

## Cleanup

To remove all resources:

```bash
kubectl delete -f k8s/
```

Or delete individually:
```bash
kubectl delete deployment inference-server trainer-server ui-server
kubectl delete svc inference-service inference-headless trainer-service ui-service
kubectl delete configmap inference-config trainer-config ui-config
kubectl delete pvc model-storage
```

## Advanced: Pod Discovery for Trainer

The trainer needs individual pod URLs. With a headless service, you can discover pods:

```bash
# Get pod IPs
kubectl get pods -l app=inference-server -o jsonpath='{.items[*].status.podIP}'

# Or use DNS (requires StatefulSet for predictable names)
# inference-server-0.inference-headless.default.svc.cluster.local
```

For production, consider:
1. Using a StatefulSet for predictable pod names
2. Using a service mesh (Istio, Linkerd) for service discovery
3. Using Kubernetes API from trainer to discover pods dynamically

## Network Policies (Optional)

For production, consider adding NetworkPolicies to restrict traffic:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: inference-policy
spec:
  podSelector:
    matchLabels:
      app: inference-server
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: trainer-server
    - podSelector:
        matchLabels:
          app: ui-server
    ports:
    - protocol: TCP
      port: 8000
```

## Monitoring (Optional)

Consider adding:
- Prometheus metrics endpoints
- Grafana dashboards
- Alerting rules for pod failures

See `inference-server/server.py` for existing health/ready endpoints.
