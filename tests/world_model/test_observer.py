"""Tests for the Observer abstraction — Hoffman/Levin unification of cohezion primitives.

Verifies that Observer composes the existing TransitionController + SurpriseRouter correctly,
nests recursively (multi-scale), widens its cognitive light cone with collective size, binds
child surprises by the most-surprised rule, and optionally gates through consensus.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from cohezion.inference.transition_controller import TransitionController
from cohezion.world_model.observer import Observer
from cohezion.world_model.surprise_router import ActionMode, SurpriseDecision


def _matrix() -> TransitionController:
    return TransitionController(matrix={"start": ["work"], "work": ["done"], "done": []})


def _observer(name: str = "agent") -> Observer:
    return Observer(name=name, state_matrix=_matrix())


# -- base agent ----------------------------------------------------------------


def test_base_agent_scale_zero():
    o = _observer()
    assert o.scale == 0
    assert o.is_collective is False
    assert o.agent_count() == 1
    assert o.leaf_count() == 1


def test_observe_delegates_and_records_window():
    o = _observer()
    d = o.observe(0.5)
    assert isinstance(d, SurpriseDecision)
    assert o.window[-1] is d
    assert len(o.window) == 1


def test_observer_window_is_bounded():
    o = _observer()
    o._window = 4
    for _ in range(10):
        o.observe(0.5)
    assert len(o.window) == 4  # bounded view, newest retained


# -- recursive nesting (multi-scale) ------------------------------------------


def test_nesting_raises_scale():
    root = _observer("collective")
    a, b = _observer("a"), _observer("b")
    root.nest(a).nest(b)
    assert root.scale == 1
    assert root.is_collective is True
    assert root.agent_count() == 3  # root + 2 leaves
    assert root.leaf_count() == 2


def test_three_level_nesting_scale():
    leaf = _observer("leaf")
    mid = _observer("mid")
    mid.nest(leaf)
    top = _observer("top")
    top.nest(mid)
    assert top.scale == 2
    assert top.agent_count() == 3
    assert top.leaf_count() == 1


def test_self_nest_rejected():
    o = _observer()
    with pytest.raises(ValueError):
        o.nest(o)


def test_walk_preorder():
    root = _observer("root")
    a, b = _observer("a"), _observer("b")
    root.nest(a).nest(b)
    names = [o.name for o in root.walk()]
    assert names == ["root", "a", "b"]


# -- cognitive light cone widens with collective size -------------------------


def test_light_cone_lone_agent_reduces_to_levin():
    o = _observer()
    cone = o.cognitive_light_cone(diffusion=4.0, temporal_horizon=1.0)
    assert cone.radius == pytest.approx(2.0)  # sqrt(4*1*1)
    assert cone.is_collective is False


def test_light_cone_widens_with_nesting():
    lone = _observer("lone")
    collective = _observer("collective")
    collective.nest(_observer("a")).nest(_observer("b")).nest(_observer("c"))
    lone_cone = lone.cognitive_light_cone()
    coll_cone = collective.cognitive_light_cone()
    assert coll_cone.radius > lone_cone.radius  # more agents -> wider horizon
    assert coll_cone.is_collective is True
    assert len(coll_cone.agent_ids) == collective.agent_count()


# -- multi-scale binding: most-surprised subsystem drives ----------------------


def test_collective_observe_attends_to_max_surprise():
    root = _observer("collective")
    root.nest(_observer("a")).nest(_observer("b"))
    # establish a low scale so the high value normalizes as a spike
    for _ in range(8):
        root.observe(0.1)
    decision = root.collective_observe([0.05, 0.1, 5.0])  # one child very surprised
    assert decision.mode is ActionMode.EXPLORE  # collective attends where prediction broke down


def test_collective_observe_empty_raises():
    with pytest.raises(ValueError):
        _observer().collective_observe([])


# -- aggregate -----------------------------------------------------------------


def test_aggregate_reports_tree():
    root = _observer("root")
    root.nest(_observer("a")).nest(_observer("b"))
    agg = root.aggregate()
    assert agg["observer_count"] == 3
    assert agg["leaf_count"] == 2
    assert agg["max_scale"] == 1
    assert agg["is_collective"] is True
    assert agg["state_count"] == 3  # start, work, done


# -- optional consensus gate ---------------------------------------------------


@pytest.mark.asyncio
async def test_act_without_gate_is_ungated():
    o = _observer()
    result = await o.act(0.5)
    assert isinstance(result["decision"], SurpriseDecision)
    assert result["gated"] is None


@pytest.mark.asyncio
async def test_act_with_gate_returns_outcome():
    @dataclass
    class _FakeOutcome:
        approved: bool

    class _FakeGate:
        def __init__(self):
            self.calls = 0

        async def gate(self, decision, *, budget_available=False):
            self.calls += 1
            return _FakeOutcome(approved=True)

    gate = _FakeGate()
    o = Observer(name="agent", state_matrix=_matrix(), gate=gate)
    result = await o.act(5.0, budget_available=True)
    assert gate.calls == 1
    assert result["gated"].approved is True
    assert isinstance(result["decision"], SurpriseDecision)
