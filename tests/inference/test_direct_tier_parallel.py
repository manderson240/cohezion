"""Tests for ParallelFleetOrchestrator and multi_node_batch in direct_tier.py.

Structural: types exist, interface correct.
Behavioural discriminating: ordering preserved, best_node selection logic, fail-open.
"""

from __future__ import annotations

import threading
from unittest.mock import patch

import pytest

from cohezion.inference.direct_tier import (
    DirectLemonadeTier,
    FleetNodeResult,
    FleetResult,
    ParallelFleetOrchestrator,
    multi_node_batch,
)


# ── Structural ──────────────────────────────────────────────────────────────────


def test_fleet_node_result_fields():
    r = FleetNodeResult(model_id="llama3.2-1b-FLM", node="npu", text="hi", latency_ms=12.0)
    assert r.model_id == "llama3.2-1b-FLM"
    assert r.node == "npu"
    assert r.error is None


def test_fleet_result_succeeded_true_when_best_text_nonempty():
    fr = FleetResult(best_text="something", best_node="npu", wall_ms=100.0)
    assert fr.succeeded is True


def test_fleet_result_succeeded_false_when_all_empty():
    fr = FleetResult(best_text="", best_node="", wall_ms=0.0)
    assert fr.succeeded is False


def test_parallel_fleet_orchestrator_has_three_nodes():
    orch = ParallelFleetOrchestrator()
    assert len(orch._nodes) == 3
    assert set(orch._nodes.keys()) == {"npu", "igpu", "cpu"}


def test_parallel_fleet_orchestrator_has_generate_and_run_batch():
    orch = ParallelFleetOrchestrator()
    assert callable(orch.generate)
    assert callable(orch.run_batch)
    assert callable(orch.generate_sync)


# ── Behavioural: multi_node_batch ordering ─────────────────────────────────────


def test_multi_node_batch_returns_results_in_original_order():
    """Results must match input order regardless of which thread finishes first.

    Discriminating: a wrong implementation that uses as_completed() without
    re-ordering by index would return results in completion order, not input order.
    We patch DirectLemonadeTier.call to echo the prompt — each task has a unique
    prompt, so result[i].text == tasks[i][0] proves ordering is preserved.
    """
    tasks = [
        ("prompt-alpha", "routine"),
        ("prompt-beta", "synthesis"),
        ("prompt-gamma", "orchestration"),
    ]
    # side_effect receives just (prompt,) — each thread has a unique prompt
    with patch.object(
        DirectLemonadeTier,
        "call",
        side_effect=lambda p: {"text": p, "cost_usd": 0.0, "error": None},
    ):
        results = multi_node_batch(tasks)

    assert len(results) == 3
    assert results[0]["text"] == "prompt-alpha"
    assert results[1]["text"] == "prompt-beta"
    assert results[2]["text"] == "prompt-gamma"


def test_multi_node_batch_empty_input_returns_empty():
    results = multi_node_batch([])
    assert results == []


def test_multi_node_batch_handles_individual_node_failure():
    """One failing call must not block others; result gets 'error' key, others succeed.

    Discriminating: a naive implementation that ignores future exceptions would
    crash or produce fewer results than the input length.

    Patches DirectLemonadeTier.call directly to avoid the urlopen mock race condition.
    A lock-protected counter ensures exactly one call raises (thread-safe).
    """
    call_count = {"n": 0}
    lock = threading.Lock()

    def mock_call(_prompt):
        with lock:
            n = call_count["n"]
            call_count["n"] += 1
        if n == 1:  # second call (any thread) raises
            raise ConnectionError("node offline")
        return {"text": "ok", "error": None, "cost_usd": 0.0}

    tasks = [("task A", "routine"), ("task B", "routine"), ("task C", "routine")]
    with patch.object(DirectLemonadeTier, "call", side_effect=mock_call):
        results = multi_node_batch(tasks)

    assert len(results) == 3
    successes = [r for r in results if r.get("text") == "ok"]
    failures = [r for r in results if r.get("error")]
    assert len(successes) == 2
    assert len(failures) == 1


# ── Behavioural: ParallelFleetOrchestrator best_node selection ─────────────────


@pytest.mark.asyncio
async def test_generate_selects_longest_nonempty_response_as_best():
    """best_node must be the node with the LONGEST text, not the first non-empty.

    Discriminating: a wrong implementation that picks the first non-empty response
    (e.g. the fast NPU) would miss that the CPU gave a much more complete answer.
    """
    orch = ParallelFleetOrchestrator()

    async def mock_run_npu(_prompt: str, **_):
        return {"text": "short", "latency_ms": 50.0, "error": None}

    async def mock_run_igpu(_prompt: str, **_):
        return {"text": "medium response here", "latency_ms": 200.0, "error": None}

    async def mock_run_cpu(_prompt: str, **_):
        return {
            "text": "a much longer and more detailed response from the CPU tier",
            "latency_ms": 800.0,
            "error": None,
        }

    orch._nodes["npu"].run = mock_run_npu
    orch._nodes["igpu"].run = mock_run_igpu
    orch._nodes["cpu"].run = mock_run_cpu

    result = await orch.generate("explain recursion")

    assert result.best_node == "cpu"
    assert "longer" in result.best_text
    assert result.succeeded is True
    assert result.cost_usd == 0.0


@pytest.mark.asyncio
async def test_generate_wall_ms_is_max_not_sum():
    """wall_ms must be the MAXIMUM latency, not the sum (since nodes ran in parallel).

    Discriminating: a wrong implementation that sums latencies would report
    ~1050ms wall-clock for a parallel call that actually took ~800ms.
    """
    orch = ParallelFleetOrchestrator()

    async def mock_run_npu(_prompt: str, **_):
        return {"text": "a", "latency_ms": 50.0, "error": None}

    async def mock_run_igpu(_prompt: str, **_):
        return {"text": "bb", "latency_ms": 200.0, "error": None}

    async def mock_run_cpu(_prompt: str, **_):
        return {"text": "ccc", "latency_ms": 800.0, "error": None}

    orch._nodes["npu"].run = mock_run_npu
    orch._nodes["igpu"].run = mock_run_igpu
    orch._nodes["cpu"].run = mock_run_cpu

    result = await orch.generate("test")

    assert result.wall_ms == pytest.approx(800.0)  # max, not sum (1050)


@pytest.mark.asyncio
async def test_generate_is_fail_open_when_all_nodes_error():
    """All nodes failing must still return a FleetResult (never raises)."""
    orch = ParallelFleetOrchestrator()

    async def mock_run_error(_prompt: str, **_):
        raise RuntimeError("lemonade offline")

    orch._nodes["npu"].run = mock_run_error
    orch._nodes["igpu"].run = mock_run_error
    orch._nodes["cpu"].run = mock_run_error

    result = await orch.generate("test")

    assert isinstance(result, FleetResult)
    assert result.succeeded is False
    assert len(result.nodes) == 3
    assert all(r.error for r in result.nodes)


@pytest.mark.asyncio
async def test_generate_records_all_three_node_results():
    """FleetResult.nodes must include responses from all 3 nodes."""
    orch = ParallelFleetOrchestrator()

    async def mock_npu(prompt: str, **_):
        return {"text": "npu-says", "latency_ms": 50.0, "error": None}

    async def mock_igpu(prompt: str, **_):
        return {"text": "igpu-says", "latency_ms": 200.0, "error": None}

    async def mock_cpu(prompt: str, **_):
        return {"text": "cpu-says cpu-says cpu-says", "latency_ms": 800.0, "error": None}

    orch._nodes["npu"].run = mock_npu
    orch._nodes["igpu"].run = mock_igpu
    orch._nodes["cpu"].run = mock_cpu

    result = await orch.generate("multi-perspective question")

    node_names = {r.node for r in result.nodes}
    assert node_names == {"npu", "igpu", "cpu"}
    texts = {r.node: r.text for r in result.nodes}
    assert texts["npu"] == "npu-says"
    assert texts["igpu"] == "igpu-says"


# ── build_parallel_fleet_orchestrator ─────────────────────────────────────────


def test_build_parallel_fleet_orchestrator_returns_orchestrator():
    from cohezion.inference.triune_orchestrator import build_parallel_fleet_orchestrator

    orch = build_parallel_fleet_orchestrator()
    assert isinstance(orch, ParallelFleetOrchestrator)
    assert len(orch._nodes) == 3
