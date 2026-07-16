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
                # Use build_reasoning_orchestrator (not build_triune_omni_orchestrator):
                # - NPU: deepseek-r1-0528-8b-FLM (10.6 TPS, reasoning-capable FLM)
                # - iGPU: Gemma-4-E4B-it-GGUF (max_tokens=2048, min_chars=200)
                # - CPU: Bonsai-8B-gguf (fast non-thinking fallback, <60s vs 380s for 31B)
                # build_triune_omni_orchestrator had min_chars=500/2000 quality gates that
                # guaranteed 100% escalation to Gemma-4-31B-it-GGUF (thinking model that
                # exhausts max_tokens=512 in <think> phase and returns empty content).
                from cohezion.inference.triune_orchestrator import build_reasoning_orchestrator

                _orchestrator = build_reasoning_orchestrator()
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


def get_recommended_concurrency(npu_port: int = 13305, timeout_s: float = 1.5) -> int:
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


def lemonade_available(npu_port: int = 13305, timeout_s: float = 1.5) -> bool:
    """Non-blocking liveness check for the NPU Lemonade server.

    Returns False (instead of raising) when the server is unreachable.
    Callers should fall back to their own execute_fn when this returns False.
    """
    try:
        resp = httpx.get(f"http://localhost:{npu_port}/v1/models", timeout=timeout_s)
        return resp.status_code == 200
    except Exception:
        return False


# The OmniRouter triune cascade order — index = engine. The final tier reached is
# (entry + escalations), so this maps a cascade outcome to the ENGINE that actually ran.
_OMNI_TIERS = ("npu", "igpu", "cpu")


def _engine_for(min_tier_index: int, escalation_count: int, is_cloud: bool) -> str:
    """Which compute engine the cascade landed on — the feedback the GIC's DifficultyEstimator
    needs to LEARN per-skill engine allocation (closes the multi-engine compounding loop).
    Cloud short-circuits to 'cloud'; otherwise NPU(0)→iGPU(1)→CPU(2) by (entry + escalations)."""
    if is_cloud:
        return "cloud"
    idx = min(max(0, int(min_tier_index) + int(escalation_count)), len(_OMNI_TIERS) - 1)
    return _OMNI_TIERS[idx]


def make_local_execute_fn(task_description: str = "", context_prefix: str = "", orchestrator=None):
    """Return a callable compatible with CompoundExecutor.execute_task(execute_fn=...).

    The returned function bridges the synchronous execute_fn contract
    (guidance: str) -> (output: str, metrics: dict) with the async
    TieredOrchestrator.run() API.

    Token accounting: every successful call updates the session TokenUsageRecord.
    Local silicon (NPU/iGPU/CPU) = free tokens; cloud = metered tokens.

    asyncio.run() creates a fresh event loop per call — safe because
    execute_fn is always invoked from synchronous CompoundExecutor code.

    Args:
        task_description: The task to perform (appended after guidance).
        context_prefix: Static codebase context injected BEFORE guidance — use
            to give CPU-tier models (31B) enough domain knowledge to answer
            Cohesion-specific questions without SurrealDB or vault access.
        orchestrator: Optional pre-built TieredOrchestrator to use. When None,
            falls back to the module-level singleton (``_get_orchestrator()``).
            Pass ``executor.inference_provider`` to share the executor's wired
            provider — this closes the CB inference_provider consumption gap.
    """

    def execute_fn(
        guidance: str, min_tier_index: int = 0, inference_provider=None
    ) -> tuple[str, dict]:
        # Priority: injected inference_provider > caller-supplied orchestrator > module singleton
        orch = inference_provider or orchestrator or _get_orchestrator()
        # Normalize guidance: executor may pass a dict from get_experience_guidance().
        # str(dict) produces repr noise in the prompt; extract the human-readable text.
        if isinstance(guidance, dict):
            guidance_text = guidance.get("guidance", "") or ""
        else:
            guidance_text = str(guidance) if guidance else ""
        parts = [p for p in [context_prefix, guidance_text, task_description] if p]
        prompt = "\n\n".join(parts).strip()
        # Lever 1 (correctness-review fix): override the orchestrator's escalation floor with the
        # task's quality_gate_chars ONLY for genuinely SHORT outputs (categorical/short answers) — so a
        # correct "POSITIVE" passes at NPU instead of escalating. The classifier returns gate_chars≈0
        # for long_generation/code/medium TOO, so a BLANKET override would let an essay pass at the 1B
        # NPU and never escalate (under-routing). Those types keep the 500/2000 floors → None here.
        try:
            from cohezion.inference.task_classifier import classify

            _d = classify(prompt)
            gate_chars = (
                _d.quality_gate_chars
                if _d.output_type in ("short_categorical", "short_answer")
                else None
            )
        except Exception:
            gate_chars = None
        try:
            # O9: difficulty-based cascade entry — a hard task starts above the cheap tiers.
            result = asyncio.run(
                orch.run(prompt, min_tier_index=min_tier_index, gate_chars=gate_chars)
            )
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

            tier_used = _engine_for(min_tier_index, result.escalation_count, _is_cloud_model(model))
            try:
                # TRACE wiring (2026-07-15): feed the tier-flow observer — entry tier ->
                # engine that ran, quality penalized per escalation. Never blocks execution.
                from cohezion.world_model.observer_world_model import get_default_observer_model

                entry = "cloud" if _is_cloud_model(model) else _OMNI_TIERS[min(min_tier_index, len(_OMNI_TIERS) - 1)]
                get_default_observer_model().record(
                    entry, tier_used, max(0.2, 1.0 - 0.25 * result.escalation_count)
                )
            except Exception:  # noqa: BLE001 — observability must not break inference
                pass

            return result.text, {
                "model": model,
                # which ENGINE ran — feeds the GIC DifficultyEstimator so it learns per-skill
                # engine allocation (multi-engine compounding; CB16 reads top-level tier_used).
                "tier_used": tier_used,
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
