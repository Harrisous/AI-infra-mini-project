from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException, Response
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from model_manager import ModelManager
from schemas import GenerateRequest, GenerateResponse, StatusResponse, UpdateModelRequest, UpdateModelResponse
from sync_coordinator import SyncCoordinator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _env(name: str, default: str) -> str:
    v = os.environ.get(name)
    return v if v else default


# Defaults are configurable. For local dev, set HF_HOME=./models/hf_home to cache under repo.
DEFAULT_INITIAL_MODEL = _env("INITIAL_MODEL_REPO_ID", "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")

app = FastAPI(title="Inference Server", version="0.1.0")
logger.info(f"Initializing inference server with model: {DEFAULT_INITIAL_MODEL}")
model_manager = ModelManager(initial_repo_id=DEFAULT_INITIAL_MODEL)
logger.info("Inference server initialized, model loading in background...")

# Optional file-based synchronization (for K8s with shared PVC)
SYNC_STATE_FILE = _env("SYNC_STATE_FILE", "")
sync_coordinator = None
if SYNC_STATE_FILE:
    sync_coordinator = SyncCoordinator(state_file_path=SYNC_STATE_FILE)
    sync_coordinator.set_update_callback(lambda repo_id: model_manager.request_update_async(repo_id))
    sync_coordinator.start_watching()


@app.get("/healthz")
def healthz() -> dict:
    """Health check - server is up (model may still be loading)."""
    return {"ok": True}


@app.get("/ready", response_model=None)
def ready() -> Response:
    """Readiness check - model is loaded and ready to serve."""
    is_ready = model_manager.is_ready()
    v, updating, last_err = model_manager.status()
    
    if is_ready:
        return JSONResponse(content={"ready": True})
    else:
        # Include error information if available
        content = {
            "ready": False,
            "message": "Model is still loading",
            "model_repo_id": v.model_repo_id,
        }
        if last_err:
            content["error"] = last_err
        return JSONResponse(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            content=content
        )


@app.get("/status", response_model=StatusResponse)
def status() -> StatusResponse:
    v, updating, last_err = model_manager.status()
    return StatusResponse(
        model_version=v.model_version,
        model_repo_id=v.model_repo_id,
        updating=updating,
        last_update_error=last_err,
    )


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest, response: Response) -> GenerateResponse:
    v = model_manager.current_version()
    response.headers["X-Model-Version"] = str(v.model_version)
    response.headers["X-Model-Repo-Id"] = v.model_repo_id

    try:
        text = model_manager.generate(
            prompt=req.prompt,
            max_new_tokens=req.max_new_tokens,
            temperature=req.temperature,
            system_prompt=req.system_prompt,
        )
        return GenerateResponse(text=text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@app.post("/update-model", response_model=UpdateModelResponse)
def update_model(req: UpdateModelRequest) -> UpdateModelResponse:
    ok, msg = model_manager.request_update_async(req.model_repo_id)
    if not ok:
        raise HTTPException(status_code=409, detail=msg)
    return UpdateModelResponse(ok=True, requested_model_repo_id=req.model_repo_id, message=msg)

