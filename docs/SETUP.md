# Setup Guide

## Prerequisites

- Python 3.11+
- CUDA 12.4+ (for GPU support)
- Docker (for deploy stage)
- Kubernetes cluster or minikube (for deploy stage)
- 16GB+ GPU memory (for 7B-8B models)

## Initial Setup

### 1. Clone and Setup Virtual Environment

```bash
cd AI-infra-mini-project
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
```

### 2. Install PyTorch (GPU)

```bash
pip install --index-url https://download.pytorch.org/whl/cu124 torch torchvision torchaudio
```

### 3. Install Project Dependencies

```bash
pip install -r requirements.txt
```

## Local Stage (Development)

### Quick Start

```bash
# Run local simulation (2 inference servers + trainer)
./scripts/run_local.sh
```

This will:
1. Start inference server on port 8001
2. Start inference server on port 8002
3. Run trainer simulation that sends prompts and requests model updates

### Manual Start

```bash
# Terminal 1: Inference server 1
export HF_HOME=./models/hf_home
export INITIAL_MODEL_REPO_ID=deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
PYTHONPATH=./inference-server python -m uvicorn server:app --host 0.0.0.0 --port 8001

# Terminal 2: Inference server 2
export HF_HOME=./models/hf_home
export INITIAL_MODEL_REPO_ID=deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
PYTHONPATH=./inference-server python -m uvicorn server:app --host 0.0.0.0 --port 8002

# Terminal 3: Trainer
export INFERENCE_URLS=http://localhost:8001,http://localhost:8002
export INITIAL_MODEL=deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
export SUBSTITUTE_MODEL=Qwen/Qwen2.5-7B-Instruct
python -m trainer_server.trainer
```

### Environment Variables

- `HF_HOME`: HuggingFace cache directory (default: `~/.cache/huggingface`)
- `TRANSFORMERS_CACHE`: Transformers cache directory
- `INITIAL_MODEL_REPO_ID`: Initial model to load (inference server)
- `INITIAL_MODEL`: Initial model for trainer simulation
- `SUBSTITUTE_MODEL`: Model to switch to during simulation
- `INFERENCE_URLS`: Comma-separated list of inference server URLs

## Deploy Stage (Kubernetes)

### 1. Build Docker Images

```bash
./scripts/build_images.sh
```

This builds:
- `inference-server:latest`
- `trainer-server:latest`

### 2. Setup Minikube (Local K8s)

```bash
./scripts/setup_minikube.sh
```

This will:
- Start minikube if not running
- Enable storage provisioner
- Load Docker images into minikube

### 3. Deploy to Kubernetes

```bash
./scripts/deploy.sh
```

This applies all Kubernetes manifests:
- Storage (PVC)
- ConfigMaps
- Inference deployment (2 replicas)
- Inference service
- Trainer deployment

### 4. Check Status

```bash
kubectl get pods
kubectl get services
kubectl logs -l app=inference-server
kubectl logs -l app=trainer-server
```

### 5. Test

```bash
./scripts/test.sh
```

Or manually:

```bash
# Get service URL (minikube)
minikube service inference-service --url

# Test health
curl $(minikube service inference-service --url)/healthz

# Test generate
curl -X POST $(minikube service inference-service --url)/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello!", "max_new_tokens": 20}'
```

## Model Selection

### Default Models

- **Initial**: `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`
- **Substitute**: `Qwen/Qwen2.5-7B-Instruct`

### Using Different Models

Set environment variables before running:

```bash
export INITIAL_MODEL_REPO_ID=your-org/your-model-7b
export SUBSTITUTE_MODEL=your-org/your-model-8b
```

Or update `k8s/config.yaml` for Kubernetes deployment.

### Model Requirements

- Must be compatible with Transformers library
- Must fit in available GPU memory (or use CPU mode)
- Public repos work automatically; private repos require `HF_TOKEN`

## Troubleshooting

### Model Loading Fails

- Check GPU memory: `nvidia-smi`
- Try smaller model or enable quantization
- Check HuggingFace Hub access: `curl https://huggingface.co/api/models/your-model`

### Inference Servers Not Ready

- Check logs: `kubectl logs -l app=inference-server`
- Check resources: `kubectl describe pod <pod-name>`
- Verify GPU access: `kubectl get nodes -o yaml | grep nvidia.com/gpu`

### Port Conflicts

- Change ports in `scripts/run_local.sh` or use different ports
- For K8s, ports are configured in service manifests

### Minikube Issues

- Restart minikube: `minikube delete && minikube start`
- Check addons: `minikube addons list`
- Use Docker driver: `minikube start --driver=docker`

## Next Steps

- See [ARCHITECTURE.md](ARCHITECTURE.md) for system design details
- See [API.md](API.md) for API documentation
- Customize models, resource limits, and replica counts as needed
