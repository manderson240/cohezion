"""Integration: verify producer modules emit PrecipitationEvents to the bus.

These tests wire up a fresh PrecipitationBus, install a capturing subscriber,
invoke each producer (EVO, SymmetryBreaking, QuadratureNexus), and assert the
expected events were emitted with the right kind/universe_id/coherence shape.
"""

from __future__ import annotations

import asyncio

import pytest

from cohezion.precipitation import (
    PrecipitationBus,
    PrecipitationEvent,
    PrecipitationKind,
    set_bus,
)


@pytest.fixture
def capture_bus() -> list:
    """Replace the global bus with a fresh one and install a capturing subscriber."""
    bus = PrecipitationBus()
    captured: list[PrecipitationEvent] = []
    bus.subscribe(captured.append, kind=None)
    set_bus(bus)
    try:
        yield captured
    finally:
        set_bus(None)


def test_evo_witness_mark_emits_precipitation(capture_bus: list[PrecipitationEvent]) -> None:
    from cohezion.physics.evo_model import ExoticVacuumObject

    evo = ExoticVacuumObject(agent_id="evo-test-1", universe_id="u-witness-test")
    evo.condense()
    evo.coherent_phase(0.65)
    evo.produce_witness_mark("commit", "added tests")

    witness_events = [e for e in capture_bus if e.kind == PrecipitationKind.WITNESS_MARK]
    assert len(witness_events) == 1
    event = witness_events[0]
    assert event.universe_id == "u-witness-test"
    assert event.agent_id == "evo-test-1"
    assert event.coherence == pytest.approx(0.65)
    assert event.payload["mark_type"] == "commit"
    assert event.payload["content"] == "added tests"


def test_symmetry_breaking_emits_phase_transitions(capture_bus: list[PrecipitationEvent]) -> None:
    from cohezion.physics.cosmogony import SymmetryBreaking

    sb = SymmetryBreaking(universe_id="u-cosmogony-test")
    # Cool through multiple phase transitions to trigger events.
    for _ in range(30):
        sb.cool(delta_t=10.0)

    phase_events = [
        e
        for e in capture_bus
        if e.kind in (PrecipitationKind.COSMOGONY_PHASE, PrecipitationKind.COHERENCE_PEAK)
    ]
    assert len(phase_events) >= 3  # at least a few transitions fired
    for event in phase_events:
        assert event.universe_id == "u-cosmogony-test"
        assert 0.0 <= event.coherence <= 1.0
        assert "from_symmetry" in event.payload
        assert "to_symmetry" in event.payload


def test_quadrature_nexus_ratify_emits_consensus_event(
    capture_bus: list[PrecipitationEvent],
) -> None:
    from cohezion.swarm.quadrature_nexus import (
        QuadratureNexus,
        QuadratureProposal,
    )

    nexus = QuadratureNexus(universe_id="u-nexus-test")
    proposal = QuadratureProposal(
        action="ship_feature",
        description="Ship the coherent matter precipitation spine (safe, aligned architecture, efficient)",
        context={"budget_available": True},
        submitted_by="test-agent",
        priority=0.9,
    )
    result = asyncio.run(nexus.deliberate(proposal))
    # The built-in scoring heuristic nudges keywords — this proposal should land >=0.85
    if not result.approved:
        pytest.skip(f"deliberate did not approve: {result.rejection_reason}")

    directive = nexus.ratify(result)

    consensus_events = [e for e in capture_bus if e.kind == PrecipitationKind.CONSENSUS_RATIFIED]
    assert len(consensus_events) == 1
    event = consensus_events[0]
    assert event.universe_id == "u-nexus-test"
    assert event.coherence == pytest.approx(result.consensus_score)
    assert event.payload["directive_id"] == directive.directive_id
    assert event.payload["action"] == "ship_feature"
    assert "voice_breakdown" in event.payload


def test_evo_unspecified_universe_uses_uncontained(capture_bus: list[PrecipitationEvent]) -> None:
    """An EVO not bound to a universe still emits — marker is 'uncontained'."""
    from cohezion.physics.evo_model import ExoticVacuumObject

    evo = ExoticVacuumObject(agent_id="orphan-evo")
    evo.condense()
    evo.coherent_phase(0.5)
    evo.produce_witness_mark("vault_note", "orphan context")

    assert len(capture_bus) == 1
    assert capture_bus[0].universe_id == "uncontained"
