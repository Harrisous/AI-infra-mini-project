# API Documentation

## Inference Server API

Base URL: `http://localhost:8000` (local) or `http://inference-service:8000` (K8s)

### Health Check

**GET** `/healthz`

Check if server is healthy.

**Response**:
```json
{
  "ok": true
}
```

**Status Codes**:
- `200`: Server is healthy

---

### Status

**GET** `/status`

Get current model status and update state.

**Response**:
```json
{
  "model_version": 1,
  "model_repo_id": "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
  "updating": false,
  "last_update_error": null
}
```

**Fields**:
- `model_version`: Monotonically increasing integer, increments on each successful model swap
- `model_repo_id`: HuggingFace repo ID of currently loaded model
- `updating`: `true` if a model update is in progress
- `last_update_error`: Error message from last failed update, or `null` if no error

**Status Codes**:
- `200`: Success

---

### Generate

**POST** `/generate`

Generate text from a prompt using the current model.

**Request Body**:
```json
{
  "prompt": "What is machine learning?",
  "max_new_tokens": 100,
  "temperature": 0.7
}
```

**Fields**:
- `prompt` (required): Input text prompt
- `max_new_tokens` (optional, default: 50): Maximum number of tokens to generate
- `temperature` (optional, default: 0.7): Sampling temperature (0.0-2.0)

**Response**:
```json
{
  "text": "Machine learning is a subset of artificial intelligence..."
}
```

**Response Headers**:
- `X-Model-Version`: Current model version (integer)
- `X-Model-Repo-Id`: Current model repo ID

**Status Codes**:
- `200`: Success
- `500`: Generation error (model not loaded, OOM, etc.)

**Example**:
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain neural networks",
    "max_new_tokens": 50,
    "temperature": 0.7
  }'
```

---

### Update Model

**POST** `/update-model`

Request a hot model reload by HuggingFace repo ID.

**Request Body**:
```json
{
  "model_repo_id": "Qwen/Qwen2.5-7B-Instruct"
}
```

**Fields**:
- `model_repo_id` (required): HuggingFace model repository ID (e.g., `org/model-name`)

**Response (Success)**:
```json
{
  "success": true,
  "requested_model_repo_id": "Qwen/Qwen2.5-7B-Instruct",
  "message": "update started"
}
```

**Response (Error)**:
```json
{
  "success": false,
  "requested_model_repo_id": "invalid/repo-id",
  "message": "update already in progress"
}
```

**Status Codes**:
- `200`: Update request accepted (update happens asynchronously)
- `409`: Update cannot start (already updating, invalid request, etc.)
- `500`: Server error

**Behavior**:
1. If update is already in progress, returns `409`
2. Otherwise, starts background thread to download and load new model
3. If load succeeds: atomically swaps to new model and increments version
4. If load fails: keeps old model, sets `last_update_error`, returns error in response
5. Check `/status` endpoint to monitor update progress

**Example**:
```bash
curl -X POST http://localhost:8000/update-model \
  -H "Content-Type: application/json" \
  -d '{
    "model_repo_id": "Qwen/Qwen2.5-7B-Instruct"
  }'
```

**Error Cases**:
- Invalid repo ID: Model doesn't exist on HuggingFace Hub
- Out of memory: Model too large for available GPU memory
- Network error: Cannot download model
- Incompatible model: Model format not supported

In all error cases, the previous model remains active and serving requests.

---

## Trainer Server

The trainer server is a Python script that orchestrates prompts and model updates. It doesn't expose an HTTP API, but can be run as a script.

### Usage

```bash
python -m trainer_server.trainer
```

### Environment Variables

- `INFERENCE_URLS`: Comma-separated list of inference server URLs
- `INITIAL_MODEL`: Initial model repo ID for simulation
- `SUBSTITUTE_MODEL`: Model to switch to during simulation

### Methods

The trainer provides these methods (used internally):

- `send_prompt(prompt, inference_url)`: Send prompt to one server
- `send_prompts_to_all(prompt)`: Send prompt to all replicas
- `update_model(model_repo_id, inference_url)`: Request update on one server
- `update_all_replicas(model_repo_id)`: Request update on all replicas
- `check_all_status()`: Get status from all replicas
- `verify_synchronization(expected_repo_id)`: Verify all replicas serve same model

---

## Data Models

### GenerateRequest

```python
{
  "prompt": str,           # Required
  "max_new_tokens": int,   # Optional, default: 50
  "temperature": float     # Optional, default: 0.7
}
```

### GenerateResponse

```python
{
  "text": str
}
```

### UpdateModelRequest

```python
{
  "model_repo_id": str     # Required, e.g., "Qwen/Qwen2.5-7B-Instruct"
}
```

### UpdateModelResponse

```python
{
  "success": bool,
  "requested_model_repo_id": str,
  "message": str,
  "error": str | None       # Present if success is false
}
```

### StatusResponse

```python
{
  "model_version": int,
  "model_repo_id": str,
  "updating": bool,
  "last_update_error": str | None
}
```

---

## Response Headers

All `/generate` responses include:

- `X-Model-Version`: Current model version (integer as string)
- `X-Model-Repo-Id`: Current model HuggingFace repo ID

These headers allow clients to verify which model version generated each response.

---

## Error Handling

### HTTP Status Codes

- `200`: Success
- `409`: Conflict (e.g., update already in progress)
- `500`: Internal server error (generation failure, model load failure, etc.)

### Error Response Format

```json
{
  "detail": "ErrorType: error message"
}
```

### Common Errors

- `ModelNotFoundError`: HuggingFace repo ID doesn't exist
- `OutOfMemoryError`: Model too large for available memory
- `UpdateInProgressError`: Cannot start new update while one is in progress
- `GenerationError`: Text generation failed (model not loaded, etc.)

---

## Rate Limiting

No rate limiting is implemented by default. Add rate limiting middleware for production use.

---

## Authentication

No authentication is implemented by default. Add authentication middleware for production use.
