"""LocalImprovementExecutor — triune silicon executor for the autonomous loop.

All inference routes through the single Lemonade OmniRouter on :13305.
Model selection follows task_classifier node routing:
  npu       → llama3.2-1b-FLM       (XDNA2 NPU, 42 TPS, short tasks)
  gpu/igpu  → Gemma-4-E4B-it-GGUF  (RDNA 3.5 / vulkan, 6GB, balanced)
  cpu       → Gemma-4-E2B-it-GGUF  (x86 AVX-512/AMX, 4.1GB, offload)
  reasoning → Qwen3.5-35B-A3B-GGUF (vulkan, 23GB, deep analysis)

Since FLM (NPU) and llamacpp (iGPU/CPU) run on separate silicon, concurrent
requests to different model names execute truly in parallel through the OmniRouter.
Call warmup_tiers() before the loop to pre-load all tiers and fix stale NPU context.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from cohezion.config.defaults import LEMONADE_BASE_URL
from cohezion.inference.oom_guard import check_ram

logger = logging.getLogger(__name__)

# Model tier map: classifier node → OmniRouter model name
# All model names must exist in the OmniRouter catalog at /api/v1/models.
_TIER_MODEL: dict[str, str] = {
    "npu": "llama3.2-1b-FLM",  # XDNA2 NPU via FLM backend
    "gpu": "Gemma-4-E4B-it-GGUF",  # RDNA 3.5 iGPU via vulkan
    "igpu": "Gemma-4-E4B-it-GGUF",  # same
    "cpu": "Gemma-4-E2B-it-GGUF",  # x86 CPU via llamacpp cpu backend
    "reasoning": "Qwen3.5-35B-A3B-GGUF",  # iGPU vulkan, heavy reasoning
}
_DEFAULT_MODEL = "Gemma-4-E4B-it-GGUF"
_MIN_FREE_RAM_GB = 8.0

# Tiers to pre-load at warmup: (logical_name, model_name, extra_lemonade_flags)
_WARMUP_TIERS: list[tuple[str, str, list[str]]] = [
    ("npu", "llama3.2-1b-FLM", ["--ctx-size", "16384"]),
    ("igpu", "Gemma-4-E4B-it-GGUF", ["--ctx-size", "16384", "--llamacpp", "vulkan"]),
    ("cpu", "Gemma-4-E2B-it-GGUF", ["--ctx-size", "16384", "--llamacpp", "cpu"]),
]


def warmup_tiers(base_url: str = LEMONADE_BASE_URL) -> dict[str, bool]:
    """Pre-load NPU/iGPU/CPU tiers via the lemonade CLI.

    The lemonade CLI is the correct interface for model loading — the OmniRouter
    does not expose a /v1/load REST endpoint. Reloading the FLM model also
    resets any stale NPU context (fixes HTTP 500 'logits computation' errors).

    Returns {tier_name: success}.
    """
    port = base_url.rstrip("/").rsplit(":", 1)[-1]
    results: dict[str, bool] = {}
    for tier_name, model_name, flags in _WARMUP_TIERS:
        cmd = ["lemonade", "--port", port, "load", model_name] + flags
        logger.info("warmup: loading %s tier (%s) …", tier_name, model_name)
        try:
            ret = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            ok = ret.returncode == 0
            if not ok:
                logger.warning(
                    "warmup %s failed (rc=%d): %s", tier_name, ret.returncode, ret.stderr[:200]
                )
            results[tier_name] = ok
        except subprocess.TimeoutExpired:
            logger.warning("warmup %s timed out", tier_name)
            results[tier_name] = False
        except Exception as exc:
            logger.warning("warmup %s error: %s", tier_name, exc)
            results[tier_name] = False
    return results


def get_tier_health(base_url: str = LEMONADE_BASE_URL) -> dict[str, str]:
    """Return {model_name: device} from /v1/health for all currently loaded models."""
    try:
        req = urllib.request.Request(f"{base_url.rstrip('/')}/v1/health")  # noqa: S310
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
            h = json.loads(resp.read())
        return {m["model_name"]: m["device"] for m in h.get("all_models_loaded", [])}
    except Exception as exc:
        logger.debug("get_tier_health: %s", exc)
        return {}


def _classify_node(task_description: str) -> str:
    """Return classifier node for a task description."""
    try:
        from cohezion.inference.task_classifier import classify

        return classify(task_description).node
    except Exception:
        return "gpu"


def _chat_complete(
    base_url: str,
    model: str,
    prompt: str,
    max_tokens: int = 512,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """POST /v1/chat/completions to the OmniRouter. Returns parsed JSON.

    Thinking-mode models (Gemma-4-*) return content="" with reasoning_content set;
    we promote reasoning_content → content when the latter is empty.
    """
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
    ).encode()
    req = urllib.request.Request(  # noqa: S310
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        data = json.loads(resp.read())

    # Promote reasoning_content → content for thinking-mode models
    for choice in data.get("choices", []):
        msg = choice.get("message", {})
        if not msg.get("content") and msg.get("reasoning_content"):
            msg["content"] = msg["reasoning_content"]

    return data


class LoopTickSweeper:
    """Periodically corrects the loop's course based on sprint statistics."""

    def course_correct(
        self, sprint_results: list[Any], category_stats: dict[str, Any]
    ) -> list[str]:
        failed_cats = [
            cat for cat, s in category_stats.items() if s.get("failed", 0) > s.get("done", 0)
        ]
        if failed_cats:
            logger.info("LoopTickSweeper: high-fail categories: %s", failed_cats)
        return failed_cats


class LocalImprovementExecutor:
    """Triune local silicon executor routing through the Lemonade OmniRouter on :13305.

    Supports both sequential (execute_task) and concurrent (execute_batch) dispatch.
    Concurrent dispatch fans tasks out across NPU/iGPU/CPU tiers in parallel —
    since each tier runs on separate silicon, they do not contend for compute.
    """

    def __init__(self, base_url: str = LEMONADE_BASE_URL) -> None:
        self._base_url = base_url
        self._started = False
        self._sweeper = LoopTickSweeper()

    def start(self, worktree_path: str) -> None:
        safe, free_gb = check_ram(_MIN_FREE_RAM_GB)
        if not safe:
            logger.warning(
                "LocalImprovementExecutor: low RAM (%.1f GiB free < %.0f GiB floor) — proceeding with caution",
                free_gb,
                _MIN_FREE_RAM_GB,
            )
        self._started = True
        logger.info("LocalImprovementExecutor started (OmniRouter: %s)", self._base_url)

    def stop(self) -> None:
        self._started = False
        logger.info("LocalImprovementExecutor stopped")

    def execute_task(self, task: Any, worktree_path: str) -> dict[str, Any]:
        """Route a single task through the OmniRouter and return a result dict."""
        description: str = getattr(task, "description", str(task))
        task_id: str = getattr(task, "id", "unknown")
        category: str = getattr(task, "category", "general")
        verification: str = getattr(task, "verification", "")

        node = _classify_node(description)
        model = _TIER_MODEL.get(node, _DEFAULT_MODEL)

        prompt = (
            f"You are a compound engineering assistant. Complete this task concisely.\n\n"
            f"Task [{category}]: {description}\n"
            f"Verification: {verification}\n\n"
            f"Respond with: a brief action taken, key result, and verification status."
        )

        t0 = time.monotonic()
        tried_models = [model]
        try:
            resp = _chat_complete(self._base_url, model, prompt, max_tokens=400, timeout=90.0)
        except urllib.error.HTTPError as exc:
            # NPU FLM backend can return 500 if context is stale post-warmup.
            # Fall back to default iGPU model rather than failing.
            if exc.code == 500 and node == "npu" and model != _DEFAULT_MODEL:
                logger.warning(
                    "task %s: %s HTTP 500 (NPU stale), falling back to %s",
                    task_id,
                    model,
                    _DEFAULT_MODEL,
                )
                model = _DEFAULT_MODEL
                tried_models.append(model)
                try:
                    resp = _chat_complete(
                        self._base_url, model, prompt, max_tokens=400, timeout=90.0
                    )
                except Exception as exc2:
                    logger.error("execute_task %s fallback failed: %s", task_id, exc2)
                    return _error_result(task_id, model, node, str(exc2), returncode=1)
            else:
                logger.warning("OmniRouter HTTP %d for task %s: %s", exc.code, task_id, exc)
                return _error_result(task_id, model, node, f"HTTP {exc.code}: {exc}", returncode=2)
        except urllib.error.URLError as exc:
            logger.warning("OmniRouter unreachable for task %s: %s", task_id, exc)
            return _error_result(task_id, model, node, f"URLError: {exc}", returncode=2)
        except Exception as exc:
            logger.error("execute_task %s failed: %s", task_id, exc)
            return _error_result(task_id, model, node, str(exc), returncode=1)

        elapsed_ms = (time.monotonic() - t0) * 1000

        try:
            choice = resp.get("choices", [{}])[0]
            output = choice.get("message", {}).get("content", "")
            usage = resp.get("usage", {})
            tokens = usage.get(
                "total_tokens", usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
            )
        except Exception as exc:
            logger.error("execute_task %s response parse failed: %s", task_id, exc)
            return _error_result(task_id, model, node, str(exc), returncode=1)

        success = bool(output.strip())
        tried_str = "→".join(m[:20] for m in tried_models)
        logger.info(
            "task %s [%s→%s] %s in %.0fms (%d tokens)",
            task_id,
            node,
            tried_str,
            "OK" if success else "EMPTY",
            elapsed_ms,
            tokens,
        )
        return {
            "task_id": task_id,
            "success": success,
            "summary": output[:200],
            "tokens_used": tokens,
            "output": output,
            "model": model,
            "node": node,
            "elapsed_ms": elapsed_ms,
            "returncode": 0 if success else 1,
        }

    def execute_batch(
        self, tasks: list[Any], worktree_path: str, max_workers: int = 3
    ) -> list[dict[str, Any]]:
        """Dispatch tasks concurrently across NPU/iGPU/CPU tiers.

        Tasks classified as different nodes (npu/igpu/cpu) execute in parallel
        since the OmniRouter routes them to independent hardware. max_workers=3
        matches the three compute tiers — increase only if you have additional
        models loaded on the same tier.

        Results are returned in completion order (fastest tier first).
        Each result dict includes 'task_id' for caller-side association.
        """
        if not tasks:
            return []

        results: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_map = {
                pool.submit(self.execute_task, task, worktree_path): task for task in tasks
            }
            for future in as_completed(future_map):
                task = future_map[future]
                try:
                    result = future.result()
                except Exception as exc:
                    tid = getattr(task, "id", "unknown")
                    logger.error("execute_batch: task %s raised: %s", tid, exc)
                    result = _error_result(tid, _DEFAULT_MODEL, "unknown", str(exc), returncode=1)
                results.append(result)

        return results


def _error_result(
    task_id: str, model: str, node: str, message: str, *, returncode: int
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "success": False,
        "summary": message,
        "tokens_used": 0,
        "output": "",
        "model": model,
        "node": node,
        "returncode": returncode,
    }
