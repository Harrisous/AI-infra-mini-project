# Inference Server Dockerfile
# Uses vLLM for production-grade inference (GPU required)

FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04

WORKDIR /app

# Install Python and system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install vLLM and dependencies
RUN pip3 install --no-cache-dir \
    "vllm>=0.7.0" \
    fastapi==0.115.6 \
    uvicorn[standard]==0.34.0 \
    pydantic==2.10.4 \
    transformers==4.48.3 \
    huggingface_hub==0.27.1 \
    requests==2.32.3

# Copy inference server code
COPY inference-server/ /app/inference-server/
WORKDIR /app/inference-server

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Run server
CMD ["python3", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
