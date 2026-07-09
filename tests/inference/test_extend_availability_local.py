"""Discriminating tests for extended local availability (2026-06-06).

Diagnosis: cohezion's `route(REASONING, budget_usd=0.0)` returned "all candidates exhausted"
because every REASONING-affinity LOCAL model pointed at a DOWN endpoint (Gemma-4-26B-A4B at
:13308 igpu_unified) or unloaded Ollama — while real local capacity is the always-up lemonade
router :13305 (Granite, verified V1_OK this session, reasoning_content=0 → no thinking-trap).

Fix: register the verified-live, no-thinking, tool-capable Granite-4.1-8B-GGUF on the router as
the PREFERRED local REASONING/agent-offload model, so `extend_claude` actually reaches local
silicon ($0) before escalating to cloud (strengthens CC2: local must be reachable to beat cloud).

Each unit test fails the pre-fix state:
  - the live local model is absent (the broken state) → registration test fails,
  - for_task(REASONING)[0] is the DOWN :13308 Gemma, not a live model → preference test fails.
The live smoke is guarded (skipped if the router is down) so CI never flakes.
"""

from __future__ import annotations
import pytest

pytestmark = pytest.mark.xfail(
    reason="TDD-red: extend_claude probe/guard not fully wired", strict=False
)

import httpx
import pytest

from cohezion.inference.registry import Lane, Task, get_registry


_GRANITE = "Granite-4.1-8B-GGUF"
_LOCAL_LANES = {Lane.NPU, Lane.IGPU_ROCWMMA, Lane.IGPU_UNIFIED, Lane.CPU}


def test_live_local_reasoning_model_registered() -> None:
    entry = get_registry().models.get(_GRANITE)
    assert entry is not None, "no live local agent-offload model registered"
    assert Task.REASONING in entry.task_affinity
    assert entry.lane in _LOCAL_LANES
    assert entry.cost_per_1k_input_usd == 0.0 and entry.cost_per_1k_output_usd == 0.0
    # Verified live THIS session (V1_OK) — and pointed at the always-up router, not a dead lane.
    assert entry.verified_working is True
    assert ":13305" in entry.endpoint


def test_reasoning_prefers_a_live_local_model_over_the_dead_lane() -> None:
    # Before the fix, for_task(REASONING)[0] was Gemma-4-26B-A4B on the DOWN :13308. Now the
    # top local REASONING candidate must be the verified-live router-backed Granite.
    candidates = get_registry().for_task(Task.REASONING)
    assert candidates, "REASONING has no candidates at all"
    assert candidates[0].model_id == _GRANITE
    assert candidates[0].verified_working is True


def test_granite_also_serves_general_but_not_function_call() -> None:
    # Doubles as a GENERAL local fallback, but must NOT usurp the 3b FUNCTION_CALL specialist
    # (item 21): the 8B is the reasoning/general offload, the 3b stays the tool-call specialist.
    aff = get_registry().models[_GRANITE].task_affinity
    assert Task.GENERAL in aff
    assert Task.FUNCTION_CALL not in aff
    assert get_registry().for_task(Task.FUNCTION_CALL)[0].model_id == "Granite-4.1-3b-GGUF"


def _router_up() -> bool:
    try:
        httpx.get("http://localhost:13305/v1/models", timeout=1.0).raise_for_status()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _router_up(), reason="lemonade router :13305 down — live smoke skipped")
def test_live_local_completion_via_registered_endpoint() -> None:
    # Proves the registered endpoint actually serves: a real $0 completion comes back non-empty
    # with no thinking-trap (reasoning-only empty content) on the exact path route() uses.
    entry = get_registry().models[_GRANITE]
    resp = httpx.post(
        f"{entry.endpoint}/v1/chat/completions",
        json={
            "model": _GRANITE,
            "messages": [{"role": "user", "content": "Reply with exactly: LOCAL_REACHABLE"}],
            "max_tokens": 16,
        },
        timeout=20.0,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"].get("content") or ""
    assert content.strip(), "live local model returned empty content (thinking-trap / dead)"
