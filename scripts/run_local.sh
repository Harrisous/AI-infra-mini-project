#!/bin/bash
# Local stage runner: starts 2 inference servers + trainer

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Activate venv
if [ ! -d ".venv" ]; then
    echo "Error: .venv not found. Run setup first."
    exit 1
fi

source .venv/bin/activate

# Set HF cache to local models/ directory for reproducibility
export HF_HOME="${PROJECT_ROOT}/models/hf_home"
export TRANSFORMERS_CACHE="${PROJECT_ROOT}/models/transformers_cache"

# Default models (can override via env)
export INITIAL_MODEL="${INITIAL_MODEL:-deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B}"
export SUBSTITUTE_MODEL="${SUBSTITUTE_MODEL:-Qwen/Qwen2.5-7B-Instruct}"

echo "=== Starting Local Stage ==="
echo "Project root: $PROJECT_ROOT"
echo "HF cache: $HF_HOME"
echo "Initial model: $INITIAL_MODEL"
echo "Substitute model: $SUBSTITUTE_MODEL"
echo ""

# Create models directory if it doesn't exist
mkdir -p "$HF_HOME" "$TRANSFORMERS_CACHE"

# Start inference server 1 (port 8001)
echo "Starting inference server 1 on port 8001..."
PYTHONPATH="$PROJECT_ROOT/inference-server" python -m uvicorn server:app --host 0.0.0.0 --port 8001 &
INFERENCE_PID1=$!

# Wait a bit for server to start
sleep 3

# Start inference server 2 (port 8002)
echo "Starting inference server 2 on port 8002..."
PYTHONPATH="$PROJECT_ROOT/inference-server" python -m uvicorn server:app --host 0.0.0.0 --port 8002 &
INFERENCE_PID2=$!

# Wait for both servers to start (health check)
echo "Waiting for inference servers to start..."
for i in {1..10}; do
    if curl -s http://localhost:8001/healthz > /dev/null && \
       curl -s http://localhost:8002/healthz > /dev/null; then
        echo "✓ Both inference servers started"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "Error: Inference servers did not start"
        kill $INFERENCE_PID1 $INFERENCE_PID2 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

# Wait for models to load (readiness check)
echo "Waiting for models to load (this may take several minutes for first-time download)..."
SERVER1_READY=false
SERVER2_READY=false
for i in {1..600}; do
    HTTP_CODE1=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/ready)
    HTTP_CODE2=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8002/ready)
    
    # Update ready status
    if [ "$HTTP_CODE1" = "200" ] && [ "$SERVER1_READY" = false ]; then
        echo "  ✓ Server 1 (port 8001) is ready"
        SERVER1_READY=true
    fi
    if [ "$HTTP_CODE2" = "200" ] && [ "$SERVER2_READY" = false ]; then
        echo "  ✓ Server 2 (port 8002) is ready"
        SERVER2_READY=true
    fi
    
    # Check if both are ready
    if [ "$HTTP_CODE1" = "200" ] && [ "$HTTP_CODE2" = "200" ]; then
        echo "✓ Both models are loaded and ready"
        break
    fi
    
    # Show progress every 30 seconds
    if [ $((i % 30)) -eq 0 ]; then
        STATUS_MSG="  Still loading"
        if [ "$SERVER1_READY" = true ]; then
            STATUS_MSG="$STATUS_MSG (Server 1 ready"
        else
            STATUS_MSG="$STATUS_MSG (Server 1 loading"
        fi
        if [ "$SERVER2_READY" = true ]; then
            STATUS_MSG="$STATUS_MSG, Server 2 ready)"
        else
            STATUS_MSG="$STATUS_MSG, Server 2 loading)"
        fi
        echo "$STATUS_MSG... ($i seconds elapsed)"
    fi
    
    if [ $i -eq 600 ]; then
        echo "Warning: Models did not finish loading within 10 minutes"
        echo "  This is normal for large models on slow connections"
        echo "  You can check status manually:"
        echo "    curl http://localhost:8001/status"
        echo "    curl http://localhost:8002/status"
    fi
    sleep 1
done

# Run trainer simulation
echo ""
echo "=== Running Trainer Simulation ==="
export INFERENCE_URLS="http://localhost:8001,http://localhost:8002"
PYTHONPATH="$PROJECT_ROOT/trainer-server" python -m trainer

# Cleanup
echo ""
echo "=== Shutting down ==="
kill $INFERENCE_PID1 $INFERENCE_PID2 2>/dev/null || true
wait $INFERENCE_PID1 $INFERENCE_PID2 2>/dev/null || true
echo "Done"
