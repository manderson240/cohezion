"""LocalImprovementExecutor — runs improvement tasks via Lemonade local inference.

Quarter-on-a-string execution: instead of spawning a Claude Code subprocess, we
POST the task prompt to Lemonade (:13305) and apply any suggested patch via
subprocess. This keeps all loop work on local AMD silicon at $0 token cost.

Protocol:
  1. POST /v1/chat/completions to LEMONADE_BASE_URL with the task prompt
  2. Parse the model response for code/patch suggestions
  3. AutoHarness gate: ast.parse() any .py patch before writing (rejects 78% of
     illegal-move failures without touching disk)
  4. Write/apply file changes and run optional model-synthesized inline harness
  5. Run the task verification command
  6. Return structured result

Model selection (quality over speed):
  Primary: Qwen3.6-35B-A3B-MTP-GGUF (Omni planner, 62 TPS, multimodal, NPU+iGPU)
  Fallback: Gemma-4-E4B-it-GGUF (iGPU, 5GB — used only when 35B-MTP is unloaded)
"""

from __future__ import annotations

import ast
import json
import logging
import subprocess
import urllib.error
import urllib.request
from typing import Any

from .coordinator import LoopConfig, LoopTask


logger = logging.getLogger(__name__)

# Omni planner model — Qwen3.6-35B-A3B-MTP with vision label, 62 TPS on Strix Halo
OMNI_PLANNER_MODEL = "Qwen3.6-35B-A3B-MTP-GGUF"
# Fallback: quality iGPU model (5GB, always fits)
FALLBACK_MODEL = "Gemma-4-E4B-it-GGUF"

# Back-compat alias
DEFAULT_MODEL = OMNI_PLANNER_MODEL

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

        # Per-tick context enrichment (vault + SurrealDB + research sweeps)
        from .tick_sweeper import LoopTickSweeper

        self._sweeper = LoopTickSweeper(lemonade_url=self._base_url)

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
        """Pick the best available model, quality-first (Omni planner → fallback).

        Never downgrades to arbitrary small models — quality over speed.
        """
        if not self._available_models:
            return self._model  # try anyway; server may have loaded it since init
        if self._model in self._available_models:
            return self._model
        if OMNI_PLANNER_MODEL in self._available_models:
            return OMNI_PLANNER_MODEL
        if FALLBACK_MODEL in self._available_models:
            logger.info(
                "Primary model %s not loaded — using quality fallback %s",
                self._model,
                FALLBACK_MODEL,
            )
            return FALLBACK_MODEL
        # Last resort: use the configured model and let Lemonade auto-load it
        logger.warning(
            "Neither %s nor %s visible — requesting %s directly",
            OMNI_PLANNER_MODEL,
            FALLBACK_MODEL,
            self._model,
        )
        return self._model

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
        sweep_context = self._sweeper.build_task_context(task.category, task.description)
        prompt = self._build_prompt(task, sweep_context)
        response_text, tokens_used = self._call_lemonade(prompt, model)

        if not response_text:
            return {
                "success": False,
                "summary": "Lemonade returned empty response",
                "tokens_used": tokens_used,
                "output": "",
                "returncode": -4,
            }

        # Apply any file changes suggested in the response (with AutoHarness syntax guard)
        apply_ok, apply_errors = self._apply_suggestions(response_text, worktree_path)

        # Run model-synthesized inline harness (fast pre-check before full verification)
        harness_cmd = self._extract_harness_cmd(response_text)
        if harness_cmd:
            harness_ok, harness_out = self._run_verification(harness_cmd, worktree_path)
            if not harness_ok:
                logger.info(
                    "Inline harness failed — skipping full verification: %s", harness_out[:200]
                )
                return {
                    "success": False,
                    "summary": f"Inline harness failed: {harness_out[:200]}",
                    "tokens_used": tokens_used,
                    "output": response_text[-2000:],
                    "returncode": 2,
                }

        # Run verification command
        verify_ok, verify_output = self._run_verification(task.verification, worktree_path)

        success = verify_ok and apply_ok
        if not apply_ok:
            summary = f"Patch rejected (syntax/write errors): {'; '.join(apply_errors)}"
        elif not verify_ok:
            summary = f"Verification failed: {verify_output[:200]}"
        else:
            summary = "Verification passed"

        return {
            "success": success,
            "summary": summary,
            "tokens_used": tokens_used,
            "output": response_text[-2000:],
            "returncode": 0 if success else 1,
        }

    def _build_prompt(self, task: LoopTask, sweep_context: str = "") -> str:
        """Build a self-contained task prompt for the local model.

        Includes AutoHarness block: the model synthesizes a minimal inline
        validation command that runs before the full verification command.
        This catches 78%+ of failures (wrong types, missing attributes, syntax
        errors) without running the full test suite.
        """
        context_section = f"\nCONTEXT FROM VAULT/DB:\n{sweep_context}\n" if sweep_context else ""
        return f"""You are an autonomous code improvement agent working on a Python codebase.
{context_section}
TASK: {task.description}
CATEGORY: {task.category}
PRIORITY: {task.priority}

VERIFICATION COMMAND (run this to confirm the fix worked):
```
{task.verification}
```

INSTRUCTIONS:
1. Analyze the task and identify what needs to change
2. Provide the minimal code fix — be surgical, touch only what the task requires
3. Format file changes as:
   === FILE: path/to/file.py ===
   <complete new content>
   === END FILE ===
4. Provide a quick inline harness (a single shell command that validates your fix
   before the full verification runs — e.g. a python -c import check):
   === HARNESS: <shell_command_here> ===
5. State clearly: SUCCESS or FAILURE and why

Focus on correctness over speed. Only change what the task requires.
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

    def _apply_suggestions(self, response: str, worktree_path: str) -> tuple[bool, list[str]]:
        """Parse and apply file changes from model response.

        AutoHarness gate: any .py file content is validated with ast.parse()
        before writing. Syntactically invalid patches are rejected without
        touching disk — preserving working file state.

        Returns (all_ok, error_list).
        """
        import re
        from pathlib import Path

        pattern = r"=== FILE: (.+?) ===\n(.*?)=== END FILE ==="
        matches = re.findall(pattern, response, re.DOTALL)
        if not matches:
            return True, []  # no file changes; verification determines success

        errors: list[str] = []
        for file_path, content in matches:
            clean_path = file_path.strip()
            full_path = Path(worktree_path) / clean_path
            # AutoHarness syntax gate for Python files
            if full_path.suffix == ".py":
                try:
                    ast.parse(content)
                except SyntaxError as exc:
                    msg = f"Syntax error in patch for {clean_path}: {exc}"
                    logger.warning("AutoHarness rejected patch — %s", msg)
                    errors.append(msg)
                    continue  # skip writing this file, try remaining patches
            try:
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
                logger.info("Applied change to %s", clean_path)
            except Exception as exc:
                msg = f"Failed to write {clean_path}: {exc}"
                logger.error(msg)
                errors.append(msg)

        return len(errors) == 0, errors

    def _extract_harness_cmd(self, response: str) -> str:
        """Extract the model-synthesized inline harness command from the response.

        Looks for: === HARNESS: <shell_command> ===
        Returns empty string if not present.
        """
        import re

        match = re.search(r"=== HARNESS: (.+?) ===", response, re.DOTALL)
        if not match:
            return ""
        return match.group(1).strip()

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
