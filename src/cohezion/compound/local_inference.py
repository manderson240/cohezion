"""Local AMD silicon inference bridge for CompoundExecutor.

Makes the Triune substrate (NPU → iGPU → CPU) the default backbone for
every compound loop cycle. Calls Lemonade HTTP endpoints; no Python-side
model weights are loaded, so OOM risk is confined to the Lemonade processes.

OOM guard: probes NPU /v1/models before first dispatch; skips local path
gracefully if Lemonade is not running.
"""

from __future__ import annotations

import asyncio
import logging
import threading

import httpx


logger = logging.getLogger(__name__)

# Thread lock guards lazy singleton creation.
_lock = threading.Lock()
_orchestrator = None  # TieredOrchestrator, created once and reused

# Session-level token usage record — aggregates across all compound loop calls.
_token_record_lock = threading.Lock()
_session_token_record = None


def _get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        with _lock:
            if _orchestrator is None:
                from cohezion.inference.triune_orchestrator import build_triune_orchestrator

                _orchestrator = build_triune_orchestrator()
    return _orchestrator


def get_session_token_record():
    """Return the session-level TokenUsageRecord singleton.

    Lazily created on first call. Aggregates all local + cloud token usage
    across every execute_fn invocation in this process lifetime.
    """
    global _session_token_record
    if _session_token_record is None:
        with _token_record_lock:
            if _session_token_record is None:
                from cohezion.inference.token_budget import TokenUsageRecord

                _session_token_record = TokenUsageRecord()
    return _session_token_record


def _is_cloud_model(model_name: str) -> bool:
    """True when the model is a metered cloud tier (Claude / Gemini API)."""
    cloud_prefixes = ("claude-", "gemini-", "gpt-", "anthropic/", "google/")
    lower = (model_name or "").lower()
    return any(lower.startswith(p) for p in cloud_prefixes)


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: 1 token ≈ 4 characters (GPT/Claude convention)."""
    return max(1, len(text) // 4)


def get_recommended_concurrency(npu_port: int = 13306, timeout_s: float = 1.5) -> int:
    """Return recommended max_concurrent for run_batch() based on live model load.

    Heuristic from exp_LLLL1: under heavy model load (9+ models), concurrent
    dispatch is slower than sequential on XDNA2 due to memory pressure.

    Returns
    -------
    int
        Recommended max_concurrent value:
        1-3 models  → 5 (full concurrent, exp_OOOO: 3.44x speedup)
        4-8 models  → 3 (partial concurrent)
        9+ models   → 1 (sequential: avoids contention)
    """
    try:
        resp = httpx.get(f"http://localhost:{npu_port}/v1/models", timeout=timeout_s)
        if resp.status_code == 200:
            n_models = len(resp.json().get("data", []))
            if n_models <= 3:
                return 5
            elif n_models <= 8:
                return 3
            else:
                logger.debug(
                    "Heavy load (%d models on port %d): recommending sequential", n_models, npu_port
                )
                return 1
    except Exception:
        pass
    return 3  # safe default when probe fails


def lemonade_available(npu_port: int = 13306, timeout_s: float = 1.5) -> bool:
    """Non-blocking liveness check for the NPU Lemonade server.

    Returns False (instead of raising) when the server is unreachable.
    Callers should fall back to their own execute_fn when this returns False.
    """
    try:
        resp = httpx.get(f"http://localhost:{npu_port}/v1/models", timeout=timeout_s)
        return resp.status_code == 200
    except Exception:
        return False


def make_local_execute_fn(task_description: str = ""):
    """Return a callable compatible with CompoundExecutor.execute_task(execute_fn=...).

    The returned function bridges the synchronous execute_fn contract
    (guidance: str) -> (output: str, metrics: dict) with the async
    TieredOrchestrator.run() API.

    Token accounting: every successful call updates the session TokenUsageRecord.
    Local silicon (NPU/iGPU/CPU) = free tokens; cloud = metered tokens.

    asyncio.run() creates a fresh event loop per call — safe because
    execute_fn is always invoked from synchronous CompoundExecutor code.
    """

    def execute_fn(guidance: str, min_tier_index: int = 0) -> tuple[str, dict]:
        orch = _get_orchestrator()
        prompt = f"{guidance}\n\n{task_description}".strip() if task_description else guidance
        try:
            # O9: difficulty-based cascade entry — a hard task starts above the cheap tiers.
            result = asyncio.run(orch.run(prompt, min_tier_index=min_tier_index))
            model = result.final_model or ""

            # --- Token accounting ---
            record = get_session_token_record()
            input_tokens = _estimate_tokens(prompt)
            output_tokens = _estimate_tokens(result.text)
            if _is_cloud_model(model):
                cost = record.add_cloud(input_tokens, output_tokens, model=model)
            else:
                record.add_local(input_tokens + output_tokens, model=model)
                cost = result.cost_usd  # already 0.0 for local

            return result.text, {
                "model": model,
                "primary_model": result.primary_model,
                "latency_ms": result.latency_ms,
                "escalation_count": result.escalation_count,
                "cost_usd": cost,
                "local_silicon": not _is_cloud_model(model),
                "tokens_input": input_tokens,
                "tokens_output": output_tokens,
                "session_local_tokens": record.local_tokens,
                "session_cloud_cost_usd": round(record.cloud_cost_usd, 6),
                "session_cloud_savings_usd": round(record.cloud_savings_usd, 4),
            }
        except Exception as exc:
            logger.warning("Local inference failed, returning empty: %s", exc)
            return "", {"error": str(exc), "local_silicon": True}

    return execute_fn
