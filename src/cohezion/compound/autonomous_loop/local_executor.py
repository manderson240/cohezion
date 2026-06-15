"""LocalImprovementExecutor — runs improvement tasks via Lemonade local inference.

Quarter-on-a-string execution: instead of spawning a Claude Code subprocess, we
POST the task prompt to Lemonade (:13305) and apply any suggested patch via
subprocess. This keeps all loop work on local AMD silicon at $0 token cost.

Protocol:
  1. POST /v1/chat/completions to LEMONADE_BASE_URL with the task prompt
  2. Parse the model response for code/patch suggestions
  3. Write/apply any file changes via subprocess (git apply or direct write)
  4. Run the verification command
  5. Return structured result
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any

from .coordinator import LoopConfig, LoopTask


logger = logging.getLogger(__name__)

DEFAULT_MODEL = "Qwen3.6-35B-A3B-MTP-GGUF"
FALLBACK_MODEL = "Gemma-4-E4B-it-GGUF"

# Timeout for a single Lemonade inference call (seconds)
INFERENCE_TIMEOUT = 120
# Timeout for the verification subprocess (seconds)
VERIFICATION_TIMEOUT = 60


class LocalImprovementExecutor:
    """Execute improvement tasks via Lemonade local inference instead of Claude CLI.

    Falls back to FALLBACK_MODEL when DEFAULT_MODEL is not available.
    Includes pre-call RAM guard (C1) to avoid OOM on heavy models.
    """

    def __init__(self, config: LoopConfig | None = None):
        self.config = config or LoopConfig()
        self._base_url = self.config.local_base_url
        self._model = self.config.local_model
        self._started = False
        self._worktree_path = self.config.worktree_path

        # C1: check memory and server availability at init
        self._available_models: list[str] = []
        self._check_server()

    def _check_server(self) -> None:
        """Check Lemonade server and discover available models."""
        try:
            req = urllib.request.Request(f"{self._base_url}/v1/models", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                self._available_models = [m.get("id", "") for m in data.get("data", [])]
                logger.info(
                    "Lemonade server online at %s — %d models available",
                    self._base_url,
                    len(self._available_models),
                )
        except Exception as exc:
            logger.warning("Lemonade server not reachable at %s: %s", self._base_url, exc)
            self._available_models = []

    def _select_model(self) -> str:
        """Pick the best available model, falling back when needed."""
        if not self._available_models:
            return self._model  # try anyway; server may have loaded it since init
        if self._model in self._available_models:
            return self._model
        if FALLBACK_MODEL in self._available_models:
            logger.info(
                "Primary model %s not loaded — using fallback %s", self._model, FALLBACK_MODEL
            )
            return FALLBACK_MODEL
        # Use whatever is available (prefer larger models)
        return self._available_models[-1]

    def start(self, worktree_path: str) -> None:
        """Initialize the executor."""
        self._worktree_path = worktree_path
        self._started = True
        logger.info("LocalImprovementExecutor started at %s", worktree_path)

    def stop(self) -> None:
        """Clean up."""
        self._started = False
        logger.info("LocalImprovementExecutor stopped")

    def execute_task(self, task: LoopTask, worktree_path: str) -> dict[str, Any]:
        """Execute one improvement task via Lemonade local inference.

        Returns dict with:
        - success: bool
        - summary: str
        - tokens_used: int (from API usage field)
        - output: str (model response, last 2000 chars)
        """
        if not self._started:
            raise RuntimeError("Executor not started. Call start() first.")

        # B4: RAM guard before heavy inference
        from .coordinator import LoopCoordinator

        if not LoopCoordinator._check_ram_before_load(self.config.min_free_ram_gb):
            return {
                "success": False,
                "summary": f"Skipped — RAM below {self.config.min_free_ram_gb:.0f} GB threshold",
                "tokens_used": 0,
                "output": "",
                "returncode": -3,
            }

        model = self._select_model()
        prompt = self._build_prompt(task)
        response_text, tokens_used = self._call_lemonade(prompt, model)

        if not response_text:
            return {
                "success": False,
                "summary": "Lemonade returned empty response",
                "tokens_used": tokens_used,
                "output": "",
                "returncode": -4,
            }

        # Apply any file changes suggested in the response
        apply_ok = self._apply_suggestions(response_text, worktree_path)

        # Run verification command
        verify_ok, verify_output = self._run_verification(task.verification, worktree_path)

        success = verify_ok and apply_ok
        summary = (
            "Verification passed" if verify_ok else f"Verification failed: {verify_output[:200]}"
        )

        return {
            "success": success,
            "summary": summary,
            "tokens_used": tokens_used,
            "output": response_text[-2000:],
            "returncode": 0 if verify_ok else 1,
        }

    def _build_prompt(self, task: LoopTask) -> str:
        """Build a self-contained task prompt for the local model."""
        return f"""You are an autonomous code improvement agent working on a Python codebase.

TASK: {task.description}
CATEGORY: {task.category}
PRIORITY: {task.priority}

VERIFICATION COMMAND (run this to confirm the fix worked):
```
{task.verification}
```

INSTRUCTIONS:
1. Analyze the task and identify what needs to change
2. Provide the minimal code fix as a unified diff or complete file replacement
3. Format file changes as:
   === FILE: path/to/file.py ===
   <complete new content>
   === END FILE ===
4. State clearly: SUCCESS or FAILURE and why

Focus on correctness. Be surgical — only change what the task requires.
"""

    def _call_lemonade(self, prompt: str, model: str) -> tuple[str, int]:
        """POST to Lemonade /v1/chat/completions and return (response_text, tokens_used)."""
        payload = json.dumps(
            {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self.config.claude_max_tokens,
                "temperature": 0.1,
                "stream": False,
            }
        ).encode()

        req = urllib.request.Request(
            f"{self._base_url}/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=INFERENCE_TIMEOUT) as resp:
                data = json.loads(resp.read())
                content = data["choices"][0]["message"].get("content", "")
                usage = data.get("usage", {})
                tokens = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
                return content, tokens
        except urllib.error.HTTPError as exc:
            logger.error("Lemonade HTTP %d: %s", exc.code, exc.read()[:200])
            return "", 0
        except Exception as exc:
            logger.error("Lemonade call failed: %s", exc)
            return "", 0

    def _apply_suggestions(self, response: str, worktree_path: str) -> bool:
        """Parse and apply file changes from model response.

        Looks for blocks delimited by:
          === FILE: path/to/file.py ===
          <content>
          === END FILE ===
        """
        import re
        from pathlib import Path

        pattern = r"=== FILE: (.+?) ===\n(.*?)=== END FILE ==="
        matches = re.findall(pattern, response, re.DOTALL)
        if not matches:
            return True  # no file changes suggested; verification determines success

        for file_path, content in matches:
            full_path = Path(worktree_path) / file_path.strip()
            try:
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
                logger.info("Applied change to %s", file_path.strip())
            except Exception as exc:
                logger.error("Failed to write %s: %s", file_path.strip(), exc)
                return False

        return True

    def _run_verification(self, verification_cmd: str, worktree_path: str) -> tuple[bool, str]:
        """Run the task verification command and return (passed, output)."""
        if not verification_cmd.strip():
            return True, ""

        try:
            result = subprocess.run(
                verification_cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=worktree_path,
                timeout=VERIFICATION_TIMEOUT,
            )
            output = result.stdout + result.stderr
            return result.returncode == 0, output[-500:]
        except subprocess.TimeoutExpired:
            return False, "Verification timed out"
        except Exception as exc:
            return False, str(exc)
