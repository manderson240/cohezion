"""Tests for SkillAdaptor step-level fault attribution (paper 2606.01311)."""

from __future__ import annotations

from types import SimpleNamespace

from cohezion.agent.skill_adaptor import (
    AcceptanceCheck,
    FaultAttribution,
    adapt_skill,
    attribute_fault,
    propose_targeted_update,
)
from cohezion.memory.trust_hierarchy import GroundTruthHierarchy


def _tc(name, *, error=None, result=None):
    return SimpleNamespace(tool_name=name, error=error, result=result or {})


def _node(task_id, depth, tool_calls, children=None):
    n = SimpleNamespace(
        task_id=task_id, depth=depth, tool_calls=tool_calls, _children=children or []
    )
    return n


def _trace(root_node, all_nodes):
    """Wrap nodes with a walk() that yields pre-order."""
    root_node.walk = lambda: iter(all_nodes)
    return root_node


# -- fault attribution ---------------------------------------------------------


def test_no_fault_on_clean_trajectory():
    n = _node("t0", 0, [_tc("bash"), _tc("read")])
    assert attribute_fault(_trace(n, [n])) is None


def test_attributes_first_error_via_error_field():
    n = _node("t0", 0, [_tc("bash"), _tc("write", error="disk full"), _tc("read", error="late")])
    fa = attribute_fault(_trace(n, [n]))
    assert fa is not None
    assert fa.skill == "write" and fa.reason == "disk full" and fa.tool_index == 1


def test_attributes_error_via_result_dict():
    n = _node("t0", 0, [_tc("api", result={"error": "429 rate limit"})])
    fa = attribute_fault(_trace(n, [n]))
    assert fa.skill == "api" and "429" in fa.reason


def test_first_fault_in_execution_order_across_children():
    parent = _node("root", 0, [_tc("bash"), _tc("plan", error="parent fault")])
    child = _node("sub", 1, [_tc("compile", error="child fault")])
    fa = attribute_fault(_trace(parent, [parent, child]))
    # pre-order: parent scanned before child -> parent's error is the FIRST fault step
    assert fa.skill == "plan" and fa.task_id == "root" and fa.depth == 0


def test_fault_found_in_child_when_parent_clean():
    parent = _node("root", 0, [_tc("bash")])
    child = _node("sub", 1, [_tc("compile", error="child fault")])
    fa = attribute_fault(_trace(parent, [parent, child]))
    assert fa.skill == "compile" and fa.task_id == "sub" and fa.depth == 1


# -- targeted update -----------------------------------------------------------


def test_proposed_update_is_targeted_to_faulting_skill():
    fa = FaultAttribution(skill="write", reason="disk full", task_id="t0", depth=0, tool_index=1)
    up = propose_targeted_update(fa)
    assert up.skill == "write" and up.scope == "targeted" and "disk full" in up.revision


# -- acceptance check (paper's stability gate) --------------------------------


def test_acceptance_rejects_broad_scope():
    fa = FaultAttribution(skill="w", reason="r", task_id="t", depth=0, tool_index=0)
    from cohezion.agent.skill_adaptor import SkillUpdate

    broad = SkillUpdate(skill="w", revision="rewrite everything", scope="broad")
    assert AcceptanceCheck().accepts(broad, fa) is False


def test_acceptance_rejects_wrong_skill():
    fa = FaultAttribution(skill="w", reason="r", task_id="t", depth=0, tool_index=0)
    up = propose_targeted_update(FaultAttribution("other", "r", "t", 0, 0))
    assert AcceptanceCheck().accepts(up, fa) is False  # update targets a different skill


def test_acceptance_accepts_targeted_and_honors_predicate():
    fa = FaultAttribution(skill="w", reason="r", task_id="t", depth=0, tool_index=0)
    up = propose_targeted_update(fa)
    assert AcceptanceCheck().accepts(up, fa) is True
    # custom predicate (e.g. a Nexus consensus that votes no) overrides
    veto = AcceptanceCheck(predicate=lambda u, a: False)
    assert veto.accepts(up, fa) is False


# -- full adaptation + trust composition --------------------------------------


def test_adapt_clean_trajectory_is_noop():
    n = _node("t0", 0, [_tc("bash")])
    out = adapt_skill(_trace(n, [n]))
    assert out["adapted"] is False and out["attribution"] is None


def test_adapt_accepts_and_corroborates_trust():
    n = _node("t0", 0, [_tc("write", error="disk full")])
    trust = GroundTruthHierarchy()
    out = adapt_skill(_trace(n, [n]), trust=trust)
    assert out["adapted"] is True
    assert out["attribution"]["skill"] == "write"
    assert len(trust) == 1  # the guard recorded as a fact


def test_adapt_rejected_records_contradiction():
    n = _node("t0", 0, [_tc("write", error="disk full")])
    trust = GroundTruthHierarchy()
    out = adapt_skill(
        _trace(n, [n]), acceptance=AcceptanceCheck(predicate=lambda u, a: False), trust=trust
    )
    assert out["adapted"] is False
    fact = trust.rank()[0]
    assert fact.contradictions == 1 and fact.trust < 0.5  # rejection lowered trust


def test_adapt_partial_trust_without_corroborate_does_not_crash():
    """A trust object exposing add() but NOT corroborate() must not crash a rejected adaptation.

    Latent before the guard: the rejected branch called trust.corroborate() unconditionally, so a
    partial trust object + a rejecting AcceptanceCheck raised AttributeError up through reflect().
    """

    class _PartialTrust:
        def __init__(self):
            self.facts = []

        def add(self, fact):
            self.facts.append(fact)

        # deliberately NO corroborate()

    n = _node("t0", 0, [_tc("write", error="disk full")])
    trust = _PartialTrust()
    out = adapt_skill(
        _trace(n, [n]), acceptance=AcceptanceCheck(predicate=lambda u, a: False), trust=trust
    )
    assert out["adapted"] is False  # rejected, but no crash
    assert trust.facts == ["skill 'write' guarded against: disk full"]  # add() still recorded it
