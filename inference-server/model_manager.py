from __future__ import annotations

import os
import threading
from dataclasses import dataclass

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from version_tracker import VersionTracker, VersionState


@dataclass
class LoadedModel:
    repo_id: str
    tokenizer: object
    model: object


def _default_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


class ModelManager:
    """
    Safe model swap contract:
    - /generate always serves using the last successfully loaded model
    - /update-model loads the new model first; only swaps if load succeeds
    """

    def __init__(self, initial_repo_id: str) -> None:
        self._lock = threading.RLock()
        self._updating = False
        self._last_update_error: str | None = None
        self._device = _default_device()
        self._version = VersionTracker(initial_repo_id=initial_repo_id)

        # Load initial model synchronously at startup.
        self._current = self._load_repo_id(initial_repo_id)

    def status(self) -> tuple[VersionState, bool, str | None]:
        with self._lock:
            return (self._version.get(), self._updating, self._last_update_error)

    def current_version(self) -> VersionState:
        with self._lock:
            return self._version.get()

    def generate(self, prompt: str, max_new_tokens: int, temperature: float) -> str:
        with self._lock:
            loaded = self._current
            tokenizer = loaded.tokenizer
            model = loaded.model
            device = self._device

        inputs = tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # Keep generation simple and deterministic-ish; trainer can control temperature.
        do_sample = temperature > 0.0
        with torch.inference_mode():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=do_sample,
                temperature=temperature if do_sample else None,
                pad_token_id=getattr(tokenizer, "eos_token_id", None),
            )

        text = tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return text

    def request_update_async(self, model_repo_id: str) -> tuple[bool, str]:
        with self._lock:
            if self._updating:
                return False, "update already in progress"
            self._updating = True
            self._last_update_error = None

        t = threading.Thread(
            target=self._update_worker,
            args=(model_repo_id,),
            daemon=True,
            name="model-update-worker",
        )
        t.start()
        return True, "update started"

    def _update_worker(self, model_repo_id: str) -> None:
        try:
            candidate = self._load_repo_id(model_repo_id)
            with self._lock:
                old = self._current
                self._current = candidate
                self._version.bump(model_repo_id)

            # Best-effort free old model memory.
            try:
                del old
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
        except Exception as e:
            with self._lock:
                self._last_update_error = f"{type(e).__name__}: {e}"
        finally:
            with self._lock:
                self._updating = False

    def _load_repo_id(self, repo_id: str) -> LoadedModel:
        # Keep HF cache relocatable (local stage uses ./models/hf_home).
        # Users can also set HF_HOME externally; we just respect it.
        _ = os.environ.get("HF_HOME")

        tokenizer = AutoTokenizer.from_pretrained(repo_id, use_fast=True)
        if getattr(tokenizer, "pad_token_id", None) is None and getattr(tokenizer, "eos_token_id", None) is not None:
            tokenizer.pad_token = tokenizer.eos_token

        # For real 7B/8B this may require quantization to fit; we'll keep it simple here,
        # and rely on GPU memory + user choice of model. Failures will be surfaced.
        model = AutoModelForCausalLM.from_pretrained(
            repo_id,
            torch_dtype=torch.float16 if self._device.type == "cuda" else torch.float32,
            low_cpu_mem_usage=True,
            device_map=None,
        )
        model.to(self._device)
        model.eval()

        return LoadedModel(repo_id=repo_id, tokenizer=tokenizer, model=model)

