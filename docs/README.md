# AI Infrastructure Mini Project - Documentation

This directory contains comprehensive documentation for the AI Infrastructure Mini Project.

## Documentation Index

- **[ARCHITECTURE.md](ARCHITECTURE.md)**: System architecture, component design, and technical decisions
- **[SETUP.md](SETUP.md)**: Step-by-step setup guide for local and Kubernetes deployment
- **[API.md](API.md)**: Complete API documentation for inference server endpoints

## Quick Start

1. **Local Development**: See [SETUP.md](SETUP.md#local-stage-development)
2. **Kubernetes Deployment**: See [SETUP.md](SETUP.md#deploy-stage-kubernetes)
3. **API Reference**: See [API.md](API.md)

## Project Structure

```
AI-infra-mini-project/
├── inference-server/     # Inference server code
├── trainer-server/       # Trainer server code
├── k8s/                  # Kubernetes manifests
├── docker/               # Dockerfiles
├── scripts/              # Setup and deployment scripts
├── docs/                 # Documentation (this directory)
└── models/               # Local model cache (gitignored)
```

## Key Features

- ✅ Hot model reload without server restart
- ✅ Model version tracking in response headers
- ✅ Synchronized updates across multiple replicas
- ✅ Zero-downtime model swaps
- ✅ Error handling and graceful degradation
- ✅ Local development and Kubernetes deployment support
