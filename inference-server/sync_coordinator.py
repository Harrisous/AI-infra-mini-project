from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path


class SyncCoordinator:
    """
    File-based synchronization coordinator for model updates across replicas.
    Uses a shared file (e.g., on PVC) to coordinate desired model state.
    """

    def __init__(self, state_file_path: str | None = None):
        self.state_file = Path(state_file_path) if state_file_path else None
        self._watch_thread: threading.Thread | None = None
        self._stop_watching = threading.Event()
        self._callback = None

    def set_update_callback(self, callback):
        """Set callback function to call when model update is requested."""
        self._callback = callback

    def write_desired_state(self, model_repo_id: str) -> bool:
        """
        Write desired model state to shared file.
        Returns True if successful.
        """
        if not self.state_file:
            return False

        try:
            state = {
                "desired_model_repo_id": model_repo_id,
                "timestamp": time.time(),
            }
            # Write atomically
            tmp_file = self.state_file.with_suffix(".tmp")
            with open(tmp_file, "w") as f:
                json.dump(state, f)
            tmp_file.replace(self.state_file)
            return True
        except Exception as e:
            print(f"Error writing desired state: {e}")
            return False

    def read_desired_state(self) -> str | None:
        """Read desired model repo ID from shared file."""
        if not self.state_file or not self.state_file.exists():
            return None

        try:
            with open(self.state_file, "r") as f:
                state = json.load(f)
            return state.get("desired_model_repo_id")
        except Exception:
            return None

    def start_watching(self, check_interval: float = 2.0):
        """Start background thread that watches for state file changes."""
        if not self.state_file or self._watch_thread:
            return

        self._stop_watching.clear()

        def watch_loop():
            last_repo_id = None
            while not self._stop_watching.is_set():
                desired = self.read_desired_state()
                if desired and desired != last_repo_id and self._callback:
                    print(f"SyncCoordinator: Detected desired model change to {desired}")
                    try:
                        self._callback(desired)
                    except Exception as e:
                        print(f"SyncCoordinator: Callback error: {e}")
                    last_repo_id = desired
                time.sleep(check_interval)

        self._watch_thread = threading.Thread(target=watch_loop, daemon=True, name="sync-watcher")
        self._watch_thread.start()

    def stop_watching(self):
        """Stop the watch thread."""
        if self._watch_thread:
            self._stop_watching.set()
            self._watch_thread.join(timeout=5.0)
            self._watch_thread = None
