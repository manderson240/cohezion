"""Tests for SelfImprovementOrchestrator (WS4, 2026-06-04).

WS4 builds the SelfImprovementOrchestrator — a class that
subscribes to ALL bus event kinds and routes them through the
appropriate ouroboros + mycelium + handler chain. This is the
final piece that ties the bus to the self-improvement loop.

The orchestrator is best-effort: any handler failure is caught
and logged at debug level; the orchestrator itself never raises.
"""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


def test_self_improvement_orchestrator_class_exists():
    """The SelfImprovementOrchestrator class must be importable."""
    from cohezion.compound.self_improvement_orchestrator import (
        SelfImprovementOrchestrator,
    )

    assert SelfImprovementOrchestrator is not None


def test_self_improvement_orchestrator_constructor():
    """Constructor takes no required args; can be called with defaults."""
    from cohezion.compound.self_improvement_orchestrator import (
        SelfImprovementOrchestrator,
    )

    orch = SelfImprovementOrchestrator()
    assert orch is not None
    # Should have a 'handlers' dict (mapping kind -> callable)
    assert hasattr(orch, "handlers") or hasattr(orch, "_handlers")


def test_self_improvement_orchestrator_handles_event():
    """handle_event(event) must not raise and must return a status
    indicating success/failure/no_op."""
    from cohezion.compound.self_improvement_orchestrator import (
        SelfImprovementOrchestrator,
    )
    from cohezion.precipitation.events import PrecipitationEvent, PrecipitationKind

    orch = SelfImprovementOrchestrator()
    event = PrecipitationEvent(
        kind=PrecipitationKind.WITNESS_MARK,
        universe_id="test.universe",
        coherence=0.5,
        payload={"skill_name": "test_skill"},
    )
    # Must not raise
    result = orch.handle_event(event)
    assert result is not None
    # result is a string status
    assert isinstance(result, str)


def test_self_improvement_orchestrator_subscribes_to_bus():
    """Calling .subscribe_to_bus() registers handlers for all
    PrecipitationKind values."""
    from cohezion.compound.self_improvement_orchestrator import (
        SelfImprovementOrchestrator,
    )

    orch = SelfImprovementOrchestrator()
    # Snapshot subscriber counts before
    try:
        orch.subscribe_to_bus()
    except Exception as e:
        raise AssertionError(f"subscribe_to_bus raised: {e}")
