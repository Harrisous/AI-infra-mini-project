from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Infra Mini Project UI", version="1.0.0")

# Templates - use absolute path to ui-server/templates
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Default URLs (can be overridden via env)
DEFAULT_INFERENCE_URLS = os.environ.get(
    "INFERENCE_URLS", "http://localhost:8001,http://localhost:8002"
).split(",")
DEFAULT_TRAINER_URL = os.environ.get("TRAINER_URL", "http://localhost:8080")

client = httpx.Client(timeout=300.0)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main UI page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/inference/status")
async def get_inference_status():
    """Get status from all inference servers."""
    results = []
    for url in DEFAULT_INFERENCE_URLS:
        try:
            resp = client.get(f"{url.strip()}/status")
            resp.raise_for_status()
            data = resp.json()
            results.append({"url": url.strip(), "status": data, "success": True})
        except Exception as e:
            results.append({"url": url.strip(), "success": False, "error": str(e)})
    return {"replicas": results}


@app.post("/api/inference/generate")
async def generate(prompt: str, system_prompt: str | None = None, max_tokens: int = 50, temperature: float = 0.7):
    """Generate text from a prompt (sends to first available inference server)."""
    for url in DEFAULT_INFERENCE_URLS:
        try:
            request_data = {
                "prompt": prompt,
                "max_new_tokens": max_tokens,
                "temperature": temperature,
            }
            if system_prompt:
                request_data["system_prompt"] = system_prompt
            
            resp = client.post(
                f"{url.strip()}/generate",
                json=request_data,
            )
            resp.raise_for_status()
            data = resp.json()
            
            # Extract headers - httpx headers are case-insensitive, access them directly
            # Headers dict keys are lowercase in httpx
            model_version = resp.headers.get("x-model-version", "unknown")
            model_repo_id = resp.headers.get("x-model-repo-id", "unknown")
            
            # Debug: log headers if model info is unknown
            if model_version == "unknown" or model_repo_id == "unknown":
                logger.warning(f"Headers not found. Available headers: {list(resp.headers.keys())}")
            
            return {
                "success": True,
                "text": data.get("text", ""),
                "model_version": model_version,
                "model_repo_id": model_repo_id,
                "inference_url": url.strip(),
            }
        except Exception as e:
            continue
    
    raise HTTPException(status_code=500, detail="All inference servers unavailable")


@app.post("/api/inference/update-model")
async def update_model(model_repo_id: str):
    """Request model update on all inference replicas."""
    results = []
    for url in DEFAULT_INFERENCE_URLS:
        try:
            resp = client.post(
                f"{url.strip()}/update-model",
                json={"model_repo_id": model_repo_id},
            )
            resp.raise_for_status()
            data = resp.json()
            results.append({"url": url.strip(), "success": True, "data": data})
        except Exception as e:
            results.append({"url": url.strip(), "success": False, "error": str(e)})
    
    all_success = all(r.get("success", False) for r in results)
    return {
        "success": all_success,
        "model_repo_id": model_repo_id,
        "replica_results": results,
    }


@app.get("/api/inference/check-ready")
async def check_ready():
    """Check if all inference servers are ready."""
    results = []
    for url in DEFAULT_INFERENCE_URLS:
        try:
            resp = client.get(f"{url.strip()}/ready")
            is_ready = resp.status_code == 200
            data = resp.json() if resp.status_code == 200 else {}
            results.append({
                "url": url.strip(),
                "ready": is_ready,
                "data": data,
            })
        except Exception as e:
            results.append({"url": url.strip(), "ready": False, "error": str(e)})
    
    all_ready = all(r.get("ready", False) for r in results)
    return {"all_ready": all_ready, "replicas": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
