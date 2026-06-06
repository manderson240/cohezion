"""Discriminating tests for the cerebellum (procedural-memory) neuron (item 24, 2026-06-06).

Completes the neurogenesis triad: inference (item 15, reward-gated) / skill (item 16, value-gated)
/ cerebellum (item 24, STABILITY-gated). A cerebellum neuron = a stabilized routing PATTERN: a
task_class that routes to the SAME lane across >=N decisions at high consistency with low fallback
(procedural memory — "this task reliably goes to this lane"). Deposited via the shared
deposit_neuron_record sink (country='cerebellum', already allowlisted).

Each test fails a plausible wrong impl:
  - one that deposits on ANY corpus (ignores stability) — T_noisy / T_fallback,
  - one that ignores the sample floor (deposits from noise) — T_few,
  - one that fabricates a write under pytest (no injected store) — T_no_store,
  - one that mislabels the region — T_country.
"""

from __future__ import annotations

from cohezion.governance.knowledge_bridge import deposit_cerebellum_neuron


def _stable(task: str, lane: str, n: int = 6) -> list[dict]:
    return [
        {"task_class": task, "chosen_model": "m", "lane": lane, "fell_back": False}
        for _ in range(n)
    ]


def test_stable_pattern_deposits_exactly_one_cerebellum_neuron() -> None:
    store: list[dict] = []
    out = deposit_cerebellum_neuron(_stable("REASONING", "igpu_rocwmma"), store=store)
    assert out is not None
    assert len(store) == 1
    assert store[0]["country"] == "cerebellum"
    assert "REASONING" in store[0]["name"] and "igpu_rocwmma" in store[0]["name"]


def test_noisy_pattern_deposits_nothing() -> None:
    # Same task class but lanes scatter across npu/igpu/cpu — no stabilized routing → no neuron.
    recs = [
        {"task_class": "REASONING", "chosen_model": "m", "lane": lane, "fell_back": False}
        for lane in ("npu", "igpu_rocwmma", "cpu", "npu", "igpu_unified", "cpu")
    ]
    store: list[dict] = []
    assert deposit_cerebellum_neuron(recs, store=store) is None
    assert store == []


def test_high_fallback_deposits_nothing() -> None:
    # Consistent task class but mostly fell back to the router → not a SUCCESSFUL stable lane.
    recs = [
        {"task_class": "RERANK", "chosen_model": None, "lane": "", "fell_back": True}
        for _ in range(6)
    ]
    store: list[dict] = []
    assert deposit_cerebellum_neuron(recs, store=store) is None
    assert store == []


def test_below_min_samples_deposits_nothing() -> None:
    # 2 decisions is noise, not a procedural pattern (UNPROVEN, like propose_tuning's floor).
    store: list[dict] = []
    assert deposit_cerebellum_neuron(_stable("MATH", "cpu", n=2), store=store) is None
    assert store == []


def test_no_store_under_pytest_never_writes_real_graph() -> None:
    # Without an injected store, the production path must NO-OP under pytest (return None),
    # never touching the real SurrealDB graph.
    assert deposit_cerebellum_neuron(_stable("REASONING", "igpu_rocwmma")) is None
