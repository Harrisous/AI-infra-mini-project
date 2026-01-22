from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Response

from model_manager import ModelManager
from schemas import GenerateRequest, GenerateResponse, StatusResponse, UpdateModelRequest, UpdateModelResponse


def _env(name: str, default: str) -> str:
    v = os.environ.get(name)
    return v if v else default


# Defaults are configurable. For local dev, set HF_HOME=./models/hf_home to cache under repo.
DEFAULT_INITIAL_MODEL = _env("INITIAL_MODEL_REPO_ID", "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B")

app = FastAPI(title="Inference Server", version="0.1.0")
model_manager = ModelManager(initial_repo_id=DEFAULT_INITIAL_MODEL)


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


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

