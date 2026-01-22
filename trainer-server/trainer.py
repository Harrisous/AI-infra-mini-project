from __future__ import annotations

import os
import time
from typing import List

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


def _env(name: str, default: str) -> str:
    v = os.environ.get(name)
    return v if v else default


# Default inference service URLs (local stage: two separate processes)
# In deploy stage, this would be a single service URL that load-balances
DEFAULT_INFERENCE_URLS = _env(
    "INFERENCE_URLS",
    "http://localhost:8001,http://localhost:8002"
).split(",")


class Trainer:
    """
    Fake trainer that:
    1. Sends prompts to inference cluster
    2. Requests model updates by HuggingFace repo ID
    3. Verifies all replicas converge to the same model
    """

    def __init__(self, inference_urls: List[str]) -> None:
        self.inference_urls = [url.strip() for url in inference_urls if url.strip()]
        self.client = httpx.Client(timeout=300.0)  # Long timeout for model loads

    def send_prompt(self, prompt: str, inference_url: str) -> dict:
        """Send a single prompt to one inference server."""
        try:
            resp = self.client.post(
                f"{inference_url}/generate",
                json={"prompt": prompt, "max_new_tokens": 50, "temperature": 0.7},
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "success": True,
                "text": data.get("text", ""),
                "model_version": resp.headers.get("X-Model-Version", "unknown"),
                "model_repo_id": resp.headers.get("X-Model-Repo-Id", "unknown"),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_prompts_to_all(self, prompt: str) -> List[dict]:
        """Send the same prompt to all inference replicas."""
        results = []
        for url in self.inference_urls:
            result = self.send_prompt(prompt, url)
            result["inference_url"] = url
            results.append(result)
        return results

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def update_model(self, model_repo_id: str, inference_url: str) -> dict:
        """Request a model update on one inference server."""
        try:
            resp = self.client.post(
                f"{inference_url}/update-model",
                json={"model_repo_id": model_repo_id},
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "success": data.get("success", False),
                "message": data.get("message", ""),
                "error": data.get("error"),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_all_replicas(self, model_repo_id: str, max_wait_seconds: int = 600) -> dict:
        """
        Request model update on all replicas and wait for completion.
        Returns success only if ALL replicas succeed.
        """
        # Step 1: Request updates on all replicas
        results = []
        for url in self.inference_urls:
            result = self.update_model(model_repo_id, url)
            result["inference_url"] = url
            results.append(result)

        # If any request failed immediately, return early
        immediate_failures = [r for r in results if not r.get("success", False)]
        if immediate_failures:
            errors = [r.get("error", "Unknown error") for r in immediate_failures]
            return {
                "success": False,
                "model_repo_id": model_repo_id,
                "replica_results": results,
                "errors": errors,
            }

        # Step 2: Wait a moment for update to start, then poll status
        print(f"  Waiting for model load to complete (max {max_wait_seconds}s)...")
        time.sleep(2)  # Give update request time to start
        start_time = time.time()
        check_interval = 5  # Check every 5 seconds
        last_progress_time = 0

        while time.time() - start_time < max_wait_seconds:
            all_done = True
            all_succeeded = True
            errors = []
            still_updating = []

            for url in self.inference_urls:
                try:
                    resp = self.client.get(f"{url}/status")
                    resp.raise_for_status()
                    status_data = resp.json()

                    # Check if still updating
                    if status_data.get("updating", False):
                        all_done = False
                        still_updating.append(url)
                        continue

                    # Update is done, check if it succeeded
                    current_repo_id = status_data.get("model_repo_id", "")
                    if current_repo_id == model_repo_id:
                        # Success - model matches
                        continue
                    else:
                        # Update completed but model doesn't match - it failed
                        all_succeeded = False
                        last_error = status_data.get("last_update_error")
                        if last_error:
                            errors.append(f"{url}: {last_error}")
                        else:
                            errors.append(f"{url}: Update completed but model is '{current_repo_id}', expected '{model_repo_id}'")

                except Exception as e:
                    all_done = False
                    errors.append(f"{url}: Status check failed - {str(e)}")

            # If all done and all succeeded, we're good
            if all_done and all_succeeded:
                elapsed = int(time.time() - start_time)
                print(f"  ✓ All replicas updated successfully (took {elapsed}s)")
                return {
                    "success": True,
                    "model_repo_id": model_repo_id,
                    "replica_results": results,
                    "errors": [],
                }

            # If all done but not all succeeded, break and report errors
            if all_done and not all_succeeded:
                break

            # Show progress
            elapsed = int(time.time() - start_time)
            if elapsed - last_progress_time >= 30:
                if still_updating:
                    print(f"    Still loading on {len(still_updating)} replica(s)... ({elapsed}s elapsed)")
                last_progress_time = elapsed

            time.sleep(check_interval)

        # Timeout or failure - collect final status
        if not all_done:
            errors.append(f"Timeout: Model loading did not complete within {max_wait_seconds}s")
            # Get final status for all replicas to show current state
            print("  Checking final status of all replicas...")
            for url in self.inference_urls:
                try:
                    resp = self.client.get(f"{url}/status")
                    resp.raise_for_status()
                    status_data = resp.json()
                    current_repo_id = status_data.get("model_repo_id", "unknown")
                    is_updating = status_data.get("updating", False)
                    last_error = status_data.get("last_update_error")
                    
                    if is_updating:
                        errors.append(f"{url}: Still updating (current: {current_repo_id})")
                    elif current_repo_id != model_repo_id:
                        if last_error:
                            errors.append(f"{url}: {last_error}")
                        else:
                            errors.append(f"{url}: Model is '{current_repo_id}', expected '{model_repo_id}'")
                except Exception as e:
                    errors.append(f"{url}: Could not get status - {str(e)}")
        elif not all_succeeded:
            # Updates completed but failed - errors already collected above
            pass

        return {
            "success": False,
            "model_repo_id": model_repo_id,
            "replica_results": results,
            "errors": errors if errors else ["Unknown error occurred"],
        }

    def check_all_status(self) -> List[dict]:
        """Check status of all inference replicas."""
        results = []
        for url in self.inference_urls:
            try:
                resp = self.client.get(f"{url}/status")
                resp.raise_for_status()
                data = resp.json()
                results.append({"inference_url": url, "status": data, "success": True})
            except Exception as e:
                results.append({"inference_url": url, "success": False, "error": str(e)})
        return results

    def verify_synchronization(self, expected_repo_id: str) -> bool:
        """Verify all replicas are serving the same model."""
        statuses = self.check_all_status()
        if not all(s.get("success", False) for s in statuses):
            return False

        repo_ids = [s["status"].get("model_repo_id") for s in statuses]
        return all(rid == expected_repo_id for rid in repo_ids)

    def run_training_simulation(self, initial_model: str, substitute_model: str, num_prompts: int = 5):
        """
        Simulate a training workflow:
        1. Send prompts with initial model
        2. Request model update
        3. Verify synchronization
        4. Send prompts with new model
        """
        print(f"=== Training Simulation ===")
        print(f"Inference URLs: {self.inference_urls}")
        print(f"Initial model: {initial_model}")
        print(f"Substitute model: {substitute_model}\n")

        # Step 1: Send prompts with initial model
        print("Step 1: Sending prompts with initial model...")
        for i in range(num_prompts):
            prompt = f"Test prompt {i+1}: What is machine learning?"
            results = self.send_prompts_to_all(prompt)
            for r in results:
                if r["success"]:
                    print(f"  {r['inference_url']}: v{r['model_version']} ({r['model_repo_id']})")
                else:
                    print(f"  {r['inference_url']}: ERROR - {r.get('error')}")
            time.sleep(1)

        # Step 2: Request model update
        print(f"\nStep 2: Requesting model update to {substitute_model}...")
        update_result = self.update_all_replicas(substitute_model)
        if update_result["success"]:
            print(f"  ✓ All replicas updated successfully")
        else:
            print(f"  ✗ Update failed on some replicas:")
            errors = update_result.get("errors", [])
            if errors:
                for err in errors:
                    if err:  # Skip None/empty errors
                        print(f"    - {err}")
            else:
                # If no errors in list, check replica results
                for result in update_result.get("replica_results", []):
                    if not result.get("success", False):
                        error_msg = result.get("error") or result.get("message") or "Unknown error"
                        print(f"    - {result.get('inference_url', 'Unknown')}: {error_msg}")
            # Don't return - continue to show what models are actually loaded

        # Step 3: Wait a bit and verify synchronization
        print("\nStep 3: Verifying synchronization...")
        time.sleep(2)
        if self.verify_synchronization(substitute_model):
            print(f"  ✓ All replicas synchronized on {substitute_model}")
        else:
            print(f"  ✗ Replicas are not synchronized")
            statuses = self.check_all_status()
            for s in statuses:
                if s.get("success"):
                    st = s["status"]
                    print(f"    {s['inference_url']}: {st.get('model_repo_id')}")

        # Step 4: Send prompts with new model
        print(f"\nStep 4: Sending prompts with new model...")
        for i in range(num_prompts):
            prompt = f"Test prompt {i+1}: Explain neural networks."
            results = self.send_prompts_to_all(prompt)
            for r in results:
                if r["success"]:
                    print(f"  {r['inference_url']}: v{r['model_version']} ({r['model_repo_id']})")
                else:
                    print(f"  {r['inference_url']}: ERROR - {r.get('error')}")
            time.sleep(1)

        print("\n=== Simulation Complete ===")


def main():
    """Main entry point for trainer server."""
    import sys

    inference_urls = DEFAULT_INFERENCE_URLS
    if len(sys.argv) > 1:
        inference_urls = sys.argv[1].split(",")

    trainer = Trainer(inference_urls=inference_urls)

    # Default test models (can be overridden via env)
    initial_model = os.environ.get("INITIAL_MODEL", "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")
    substitute_model = os.environ.get("SUBSTITUTE_MODEL", "Qwen/Qwen2.5-7B-Instruct")

    print("Starting trainer simulation...")
    trainer.run_training_simulation(
        initial_model=initial_model,
        substitute_model=substitute_model,
        num_prompts=3,
    )


if __name__ == "__main__":
    main()
