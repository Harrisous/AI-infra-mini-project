from __future__ import annotations

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    max_new_tokens: int = Field(128, ge=1, le=2048)
    temperature: float = Field(0.7, ge=0.0, le=2.0)


class GenerateResponse(BaseModel):
    text: str


class UpdateModelRequest(BaseModel):
    model_repo_id: str = Field(..., min_length=1)


class UpdateModelResponse(BaseModel):
    ok: bool
    requested_model_repo_id: str
    message: str


class StatusResponse(BaseModel):
    model_version: int
    model_repo_id: str
    updating: bool
    last_update_error: str | None

