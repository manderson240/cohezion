"""Discriminating tests for skill→neuron deposition via the value gate (2026-06-06, item 16).

The third neurogenesis track: a distilled skill that SURVIVES the value gate becomes a
country='skill' neuron. Each test fails a plausible wrong impl:
  - one that deposits a neuron for a skill that FAILED the gate,
  - one that writes to the real graph during pytest,
  - one that mislabels the region (must be 'skill'),
  - one that deposits more (or fewer) than exactly one neuron per gate-survivor.
"""
from __future__ import annotations

from cohezion.governance.knowledge_bridge import (
    build_skill_neuron,
    deposit_neuron_record,
    deposit_skill_neuron,
)


def test_build_skill_neuron_is_skill_country() -> None:
    n = build_skill_neuron("fast-extract", "a distilled extraction skill", score=0.9)
    assert n["country"] == "skill"
    assert "fast-extract" in n["name"]
    assert "distilled extraction" in n["content"]


def test_gate_survivor_deposits_exactly_one_neuron() -> None:
    store: list[dict] = []
    n = deposit_skill_neuron("fast-extract", "skill body", gate_passed=True, store=store)
    assert n is not None and n["country"] == "skill"
    assert len(store) == 1  # exactly one


def test_gate_failure_deposits_nothing() -> None:
    store: list[dict] = []
    assert deposit_skill_neuron("weak-skill", "body", gate_passed=False, store=store) is None
    assert store == []


def test_pytest_run_writes_nothing_to_the_real_graph() -> None:
    # gate_passed but no store under pytest → no real SurrealDB write.
    assert deposit_skill_neuron("x", "body", gate_passed=True) is None


def test_inference_alias_still_resolves() -> None:
    # Item 15's import name remains valid after the DRY generalization.
    from cohezion.governance.knowledge_bridge import deposit_inference_neuron_record

    assert deposit_inference_neuron_record is deposit_neuron_record
