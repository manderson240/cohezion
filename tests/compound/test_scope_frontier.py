"""Discriminating tests for the scope-frontier proposer (item 26, 2026-06-06).

Operationalizes "expand scope each tick": a REPORT-ONLY function that inspects the system's
remaining gaps (empty Task slots, unused neuron countries, unswept wiring packages) and emits the
next falsifiable frontier item stubs. PROPOSES, never auto-appends (human-gated, like item 14).

The item's falsifiable check: all gaps closed → proposes 0; an open gap → proposes exactly that.
Each test fails a plausible wrong impl:
  - one that ALWAYS proposes something (ignores a fully-closed frontier) — T_none,
  - one that ignores the input / proposes extras — T_one,
  - one that mislabels the gap kind — T_each.
"""

from __future__ import annotations

from cohezion.compound.scope_frontier import ScopeProposal, propose_scope_frontier


def test_all_gaps_closed_proposes_nothing() -> None:
    out = propose_scope_frontier(
        empty_task_slots=[], unused_neuron_countries=[], unswept_packages=[]
    )
    assert out == []


def test_one_empty_task_slot_proposes_exactly_that() -> None:
    out = propose_scope_frontier(
        empty_task_slots=["FIM"], unused_neuron_countries=[], unswept_packages=[]
    )
    assert len(out) == 1
    assert isinstance(out[0], ScopeProposal)
    assert out[0].kind == "empty_task_slot"
    assert out[0].target == "FIM"
    assert "FIM" in out[0].falsifiable_stub


def test_each_gap_type_emitted_with_correct_kind() -> None:
    out = propose_scope_frontier(
        empty_task_slots=["FIM"],
        unused_neuron_countries=["cortex"],
        unswept_packages=["api"],
    )
    by_kind = {p.kind: p.target for p in out}
    assert by_kind == {
        "empty_task_slot": "FIM",
        "unused_neuron_country": "cortex",
        "unswept_package": "api",
    }
    # every proposal carries a non-empty falsifiable stub (so the appended item is testable)
    assert all(p.falsifiable_stub.strip() for p in out)
