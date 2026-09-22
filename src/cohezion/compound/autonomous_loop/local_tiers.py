"""Tier/model operations for the local executor: tier map, warmup, health, recovery, chat.

Split out of ``local_executor`` (2026-09-22) to keep that module under the 500-line limit.
Every name here is re-exported from ``local_executor``, and every CALLER of these names stays
in ``local_executor`` -- so ``monkeypatch.setattr(local_executor, "<name>", ...)`` keeps
working (the caller resolves the name in ``local_executor``'s globals). Do not move a caller
of a patched name into this module; see ``test_local_executor_patch_seams.py``.
"""

from __future__ import annotations

import json
import logging
import subprocess
import urllib.request
from typing import Any

from cohezion.config.defaults import LEMONADE_BASE_URL


logger = logging.getLogger("cohezion.compound.autonomous_loop.local_executor")

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

# Tiers to pre-load at warmup: (logical_name, model_name, extra_lemonade_flags)
_WARMUP_TIERS: list[tuple[str, str, list[str]]] = [
    ("npu", "llama3.2-1b-FLM", ["--ctx-size", "16384"]),
    ("igpu", "Gemma-4-E4B-it-GGUF", ["--ctx-size", "16384", "--llamacpp", "vulkan"]),
    ("cpu", "Gemma-4-E2B-it-GGUF", ["--ctx-size", "16384", "--llamacpp", "cpu"]),
]


def warmup_tiers(base_url: str = LEMONADE_BASE_URL) -> dict[str, bool]:
    """Pre-load NPU/iGPU/CPU tiers via the lemonade CLI.

    Uses the lemonade CLI for bulk tier pre-loading at startup. For in-flight
    NPU recovery after a 500 error, use _recover_model() (REST API, no subprocess).
    Reloading the FLM model resets stale NPU context (fixes HTTP 500 errors).

    Returns {tier_name: success}.
    """
    port = base_url.rstrip("/").rsplit(":", 1)[-1]
    results: dict[str, bool] = {}
    for tier_name, model_name, flags in _WARMUP_TIERS:
        cmd = ["lemonade", "--port", port, "load", model_name, *flags]
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


def _recover_model(base_url: str, model_name: str, ctx_size: int = 16384) -> bool:
    """API-first tier recovery: unload then reload with bounded ctx_size.

    Works for any model tier (NPU/FLM, iGPU/vulkan, CPU/llamacpp).
    Uses POST /api/v1/unload + POST /api/v1/load rather than a subprocess call
    so it works from PID-namespaced environments (sandboxes, systemd units).
    See skill: flm-npu-context-recovery v1.1.0.

    GPU-tier 500s are typically caused by LRU eviction triggering a vulkan driver
    cleanup that transiently takes the iGPU backend offline. Unload+reload brings
    it back to a known-good state.

    Returns True if reload succeeded and the model is ready to serve.
    """
    base = base_url.rstrip("/")
    try:
        # Step 1: unload stale/crashed context
        unload_payload = json.dumps({"model_name": model_name}).encode()
        req = urllib.request.Request(  # noqa: S310
            f"{base}/api/v1/unload",
            data=unload_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10.0) as resp:  # noqa: S310
            resp.read()
        logger.debug("model recovery: unloaded %s", model_name)
    except Exception as exc:
        logger.warning("model recovery: unload failed (%s): %s", model_name, exc)
        # Non-fatal — proceed to load anyway (model may already be unloaded)

    try:
        # Step 2: reload with bounded ctx_size to prevent KV-cache OOM (N3)
        load_payload = json.dumps({"model_name": model_name, "ctx_size": ctx_size}).encode()
        req = urllib.request.Request(  # noqa: S310
            f"{base}/api/v1/load",
            data=load_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30.0) as resp:  # noqa: S310
            resp.read()
        logger.info("model recovery: reloaded %s (ctx_size=%d)", model_name, ctx_size)
        return True
    except Exception as exc:
        logger.warning("model recovery: load failed (%s): %s", model_name, exc)
        return False


def _compute_slp(resp: dict[str, Any]) -> float | None:
    """Compute S_LP (Learning Potential) score from a chat completion response.

    S_LP = -mean(logprobs) across output tokens — higher means more surprising
    output (greater learning signal). Returns None when logprobs are unavailable
    (FLM / NPU tier does not expose per-token log-probabilities).
    """
    choices = resp.get("choices", [])
    if not choices:
        return None
    logprobs_obj = choices[0].get("logprobs")
    if logprobs_obj is None:
        return None
    content = logprobs_obj.get("content")
    if not content:
        return None
    logprob_vals = [tok["logprob"] for tok in content if "logprob" in tok]
    if not logprob_vals:
        return None
    return -sum(logprob_vals) / len(logprob_vals)


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
