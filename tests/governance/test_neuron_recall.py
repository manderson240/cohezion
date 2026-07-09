"""Discriminating tests for item 29 — neuron recall (closes the deposit->recall loop).

`recall_neurons(country, key)` is the read side of the neurogenesis triad. The deposit
helpers (items 15/16/24) only WROTE neurons; nothing read them. Each test below fails a
plausible-wrong implementation:
  - ignore the key (return every neuron) → T_key (two task classes, recall one),
  - ignore the country (mix skill/cerebellum) → T_country,
  - read the real graph under pytest → T_no_graph (patched graph helper must never fire),
  - hand-built object instead of the production one → T_roundtrip uses deposit_*'s own output.
"""

from __future__ import annotations

from unittest.mock import patch

from cohezion.governance import knowledge_bridge as kb
from cohezion.governance.knowledge_bridge import (
    deposit_cerebellum_neuron,
    deposit_skill_neuron,
    recall_neurons,
)


def _stable_corpus(task_class: str, lane: str, n: int = 6) -> list[dict]:
    return [{"task_class": task_class, "lane": lane, "fell_back": False} for _ in range(n)]


def test_recall_returns_only_the_keyed_neuron() -> None:
    # Deposit two DISTINCT cerebellum patterns into one store via the production deposit path.
    store: list[dict] = []
    deposit_cerebellum_neuron(_stable_corpus("CODE_GEN", "igpu"), store=store)
    deposit_cerebellum_neuron(_stable_corpus("RERANK", "npu"), store=store)
    assert len(store) == 2  # both stabilized → both deposited

    hits = recall_neurons("cerebellum", "CODE_GEN", store=store)
    # Wrong impl that ignores the key would return BOTH (2) → fails this.
    assert len(hits) == 1
    assert hits[0]["name"] == "cerebellum:CODE_GEN->igpu"
    assert hits[0] is store[0]  # the EXACT object the deposit path constructed (wiring guard)


def test_recall_filters_by_country() -> None:
    store: list[dict] = []
    deposit_cerebellum_neuron(_stable_corpus("CODE_GEN", "igpu"), store=store)
    deposit_skill_neuron("CODE_GEN", "a distilled CODE_GEN skill", gate_passed=True, store=store)
    # Both neurons are tagged "CODE_GEN" but live in different countries.
    assert {n["country"] for n in store} == {"cerebellum", "skill"}

    cere = recall_neurons("cerebellum", "CODE_GEN", store=store)
    skill = recall_neurons("skill", "CODE_GEN", store=store)
    # Wrong impl ignoring country would return both for each call → fails.
    assert len(cere) == 1 and cere[0]["country"] == "cerebellum"
    assert len(skill) == 1 and skill[0]["country"] == "skill"


def test_recall_missing_key_returns_empty() -> None:
    store: list[dict] = []
    deposit_cerebellum_neuron(_stable_corpus("CODE_GEN", "igpu"), store=store)
    # A key with no deposited neuron → [] (wrong impl returning all → fails).
    assert recall_neurons("cerebellum", "NOSUCH_TASK", store=store) == []


def test_recall_unknown_country_returns_empty() -> None:
    store: list[dict] = []
    deposit_cerebellum_neuron(_stable_corpus("CODE_GEN", "igpu"), store=store)
    # Country outside the allowlist → [] (guards the interpolation; wrong impl that skips the
    # allowlist check would still return the cerebellum neuron via tag match → fails).
    assert recall_neurons("bogus_country", "CODE_GEN", store=store) == []


def test_recall_no_store_never_reads_real_graph_under_pytest() -> None:
    # store=None under pytest MUST short-circuit to [] before any graph access. Patch the graph
    # helper to explode — a wrong impl that reads the graph in tests would trip it.
    with patch.object(kb, "_select_neurons_from_graph", side_effect=AssertionError("graph read!")):
        assert recall_neurons("cerebellum", "CODE_GEN", store=None) == []
