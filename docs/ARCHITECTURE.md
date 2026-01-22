# Architecture Documentation

## Overview

This project implements a Kubernetes-based model serving system with hot model reload capability. The system consists of:

1. **Inference Server Cluster**: 2+ replicas serving LLM inference with zero-downtime model updates
2. **Fake Trainer Server**: Simulates training workflow by sending prompts and requesting model updates
3. **Kubernetes Infrastructure**: Deployments, Services, ConfigMaps, and shared storage

## System Architecture

```
┌─────────────────┐
│ Trainer Server  │
│  (1 replica)   │
└────────┬────────┘
         │
         ├─── Sends Prompts ───┐
         │                     │
         └─── Model Updates ───┼───┐
                               │   │
                    ┌──────────▼───▼──────────┐
                    │  Inference Service      │
                    │  (Load Balancer)        │
                    └──────────┬─────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
         ┌──────────▼──────┐    ┌───────────▼──────┐
         │ Inference Pod 1 │    │ Inference Pod 2 │
         │   (Replica 1)   │    │   (Replica 2)   │
         └────────┬────────┘    └────────┬────────┘
                  │                      │
                  └──────────┬───────────┘
                             │
                    ┌────────▼────────┐
                    │  Shared PVC     │
                    │  (Model Cache)  │
                    └─────────────────┘
```

## Components

### Inference Server

**Location**: `inference-server/`

**Key Files**:
- `server.py`: FastAPI application with REST endpoints
- `model_manager.py`: Handles model loading, hot swap, and version tracking
- `version_tracker.py`: Tracks model versions and repo IDs
- `sync_coordinator.py`: Optional file-based synchronization for K8s

**Endpoints**:
- `GET /healthz`: Health check
- `GET /status`: Current model status (version, repo ID, update state)
- `POST /generate`: Generate text from prompt
- `POST /update-model`: Request hot model reload by HuggingFace repo ID

**Model Update Flow**:
1. Trainer sends `POST /update-model` with `model_repo_id`
2. Inference server validates request (checks if already updating)
3. Background thread downloads and loads new model
4. If load succeeds: atomically swap to new model and bump version
5. If load fails: keep old model, return error to trainer
6. Response includes model version headers (`X-Model-Version`, `X-Model-Repo-Id`)

### Trainer Server

**Location**: `trainer-server/`

**Key Files**:
- `trainer.py`: Main trainer logic with simulation workflow

**Functionality**:
- Sends prompts to all inference replicas
- Requests model updates across all replicas
- Verifies synchronization (all replicas serve same model)
- Surfaces errors when model updates fail

### Synchronization

Two synchronization mechanisms are supported:

1. **Direct API Calls** (default): Trainer calls each replica's `/update-model` endpoint directly
2. **File-Based** (optional): Trainer writes desired model to shared file; replicas watch and update automatically

File-based sync is enabled by setting `SYNC_STATE_FILE` environment variable (e.g., `/models/sync_state.json` on shared PVC).

## Model Management

### Model Loading

- Models are loaded from HuggingFace Hub using repo IDs (e.g., `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`)
- Transformers library automatically downloads and caches models
- Cache location controlled by `HF_HOME` and `TRANSFORMERS_CACHE` environment variables
- Local stage: cache in `./models/hf_home`
- Deploy stage: cache in shared PVC at `/models/hf_home`

### Version Tracking

- Each successful model swap increments `model_version` (monotonically increasing integer)
- Current `model_repo_id` is tracked and included in all responses
- Version information exposed via response headers and `/status` endpoint

### Error Handling

- Invalid repo IDs: Model load fails, old model kept, error returned
- Out of memory: Model load fails, old model kept, error returned
- Network issues: Retries with exponential backoff (via tenacity)
- Concurrent updates: Lock prevents multiple simultaneous updates

## Kubernetes Deployment

### Storage

- **PVC**: `model-storage` with `ReadWriteMany` access mode
- Stores HuggingFace model cache for all replicas
- 100Gi default size (adjustable)

### Deployments

- **Inference Deployment**: 2 replicas (configurable)
  - GPU resources: `nvidia.com/gpu: 1` per replica
  - Memory: 8Gi request, 16Gi limit
  - Health checks: Liveness and readiness probes

- **Trainer Deployment**: 1 replica
  - CPU-only, minimal resources

### Services

- **Inference Service**: ClusterIP load balancer
  - Round-robin distribution across replicas
  - Port 8000

### Configuration

- **ConfigMaps**: Model repo IDs, cache paths, service URLs
- Environment variables injected into pods

## Local vs Deploy Stages

### Local Stage

- Run inference servers as separate Python processes (ports 8001, 8002)
- Run trainer as Python script
- No Docker/Kubernetes required
- Fast iteration and debugging
- Use `scripts/run_local.sh`

### Deploy Stage

- Containerize with Docker
- Deploy to Kubernetes (minikube or cluster)
- Use `scripts/build_images.sh`, `scripts/deploy.sh`
- Production-ready with health checks, resource limits, etc.

## Security Considerations

- Models downloaded from public HuggingFace Hub (no authentication required for public repos)
- For private repos, set `HF_TOKEN` environment variable
- GPU access requires appropriate node labels/taints in K8s
- Service accounts can be added for K8s API access if needed

## Performance Considerations

- Model loading can take several minutes (download + load)
- Hot swap allows serving requests during model load (uses old model until swap)
- GPU memory: 7B-8B models typically require 14-16GB VRAM
- CPU fallback supported but much slower

## Limitations

- vLLM not used in local stage (Transformers backend only)
- File-based sync is optional (direct API calls are primary mechanism)
- No authentication/authorization (add for production)
- No model quantization by default (add if memory constrained)
