from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from version_tracker import VersionTracker, VersionState

logger = logging.getLogger(__name__)


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

        # Load initial model asynchronously so server can start immediately.
        self._current: LoadedModel | None = None
        self._initial_load_thread = threading.Thread(
            target=self._initial_load_worker,
            args=(initial_repo_id,),
            daemon=True,
            name="initial-model-loader",
        )
        self._initial_load_thread.start()

    def status(self) -> tuple[VersionState, bool, str | None]:
        with self._lock:
            return (self._version.get(), self._updating, self._last_update_error)

    def is_ready(self) -> bool:
        """Check if model is loaded and ready to serve requests."""
        with self._lock:
            return self._current is not None

    def current_version(self) -> VersionState:
        with self._lock:
            return self._version.get()

    def generate(self, prompt: str, max_new_tokens: int, temperature: float, system_prompt: str | None = None) -> str:
        with self._lock:
            if self._current is None:
                raise RuntimeError("Model is not loaded yet. Please wait for initial model load to complete.")
            loaded = self._current
            tokenizer = loaded.tokenizer
            model = loaded.model
            device = self._device

        # Use chat template if available (for Qwen and other chat models)
        # Otherwise, fall back to simple concatenation
        try:
            if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template is not None:
                # Format using chat template
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                full_prompt = tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
            else:
                # Fallback: simple concatenation
                if system_prompt:
                    full_prompt = f"{system_prompt}\n\n{prompt}"
                else:
                    full_prompt = prompt
        except Exception as e:
            # If chat template fails, fall back to simple format
            logger.warning(f"Chat template failed, using simple format: {e}")
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            else:
                full_prompt = prompt

        inputs = tokenizer(full_prompt, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Get input length to extract only newly generated tokens
        input_length = inputs["input_ids"].shape[1]

        # Get EOS token ID for proper stopping
        eos_token_id = getattr(tokenizer, "eos_token_id", None)
        pad_token_id = getattr(tokenizer, "pad_token_id", eos_token_id)

        # Generation parameters with repetition penalty to reduce loops
        do_sample = temperature > 0.0
        generation_kwargs = {
            "max_new_tokens": max_new_tokens,
            "do_sample": do_sample,
            "pad_token_id": pad_token_id,
        }
        
        if eos_token_id is not None:
            generation_kwargs["eos_token_id"] = eos_token_id
        
        if do_sample:
            generation_kwargs["temperature"] = temperature
            # Add repetition penalty to reduce repetitive outputs (especially important for small models)
            generation_kwargs["repetition_penalty"] = 1.1
        
        with torch.inference_mode():
            output_ids = model.generate(
                **inputs,
                **generation_kwargs,
            )

        # Extract only the newly generated tokens (skip the input prompt)
        generated_ids = output_ids[0][input_length:]
        text = tokenizer.decode(generated_ids, skip_special_tokens=True)
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
        hf_home = os.environ.get("HF_HOME")
        logger.info(f"Loading model {repo_id} (HF_HOME={hf_home}, device={self._device})")

        logger.info(f"Loading tokenizer for {repo_id}...")
        tokenizer = AutoTokenizer.from_pretrained(repo_id, use_fast=True)
        if getattr(tokenizer, "pad_token_id", None) is None and getattr(tokenizer, "eos_token_id", None) is not None:
            tokenizer.pad_token = tokenizer.eos_token

        # For real 7B/8B this may require quantization to fit; we'll keep it simple here,
        # and rely on GPU memory + user choice of model. Failures will be surfaced.
        logger.info(f"Loading model weights for {repo_id}...")
        model = AutoModelForCausalLM.from_pretrained(
            repo_id,
            torch_dtype=torch.float16 if self._device.type == "cuda" else torch.float32,
            low_cpu_mem_usage=True,
            device_map=None,
        )
        logger.info(f"Moving model to device {self._device}...")
        model.to(self._device)
        model.eval()
        logger.info(f"Model {repo_id} loaded successfully")

        return LoadedModel(repo_id=repo_id, tokenizer=tokenizer, model=model)

    def _initial_load_worker(self, repo_id: str) -> None:
        """Background worker to load initial model."""
        logger.info(f"Starting initial model load: {repo_id}")
        try:
            loaded = self._load_repo_id(repo_id)
            with self._lock:
                self._current = loaded
                # Model is now ready, version is already set by VersionTracker
            logger.info(f"Initial model load completed successfully: {repo_id}")
        except Exception as e:
            error_msg = f"Initial model load failed: {type(e).__name__}: {e}"
            logger.error(error_msg, exc_info=True)
            with self._lock:
                self._last_update_error = error_msg
