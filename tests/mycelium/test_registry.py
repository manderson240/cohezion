"""Tests for the MyceliumRegistry cross-agent pattern aggregator."""

from __future__ import annotations

import pytest

from cohezion.mycelium.registry import MyceliumRegistry
from cohezion.precipitation import (
    PrecipitationBus,
    PrecipitationEvent,
    PrecipitationKind,
)
from cohezion.precipitation.events import TWELVE_D_DIMS


def _witness(
    *,
    universe_id: str = "u",
    agent_id: str = "u/evo-0",
    twelve_d: dict[str, float] | None = None,
    coherence: float = 0.6,
) -> PrecipitationEvent:
    point = twelve_d if twelve_d is not None else dict.fromkeys(TWELVE_D_DIMS, 0.5)
    return PrecipitationEvent(
        kind=PrecipitationKind.WITNESS_MARK,
        universe_id=universe_id,
        agent_id=agent_id,
        coherence=coherence,
        twelve_d=point,
        payload={"mark_type": "test"},
    )


def test_registry_creates_cluster_on_first_event() -> None:
    bus = PrecipitationBus()
    registry = MyceliumRegistry(bus=bus)
    registry.subscribe()

    bus.emit(_witness())
    assert len(registry.clusters) == 1
    assert registry.clusters[0].size == 1
    assert not registry.clusters[0].pattern_emitted  # below threshold


def test_registry_groups_nearby_events_into_one_cluster() -> None:
    bus = PrecipitationBus()
    registry = MyceliumRegistry(bus=bus, pattern_size_threshold=2)
    registry.subscribe()

    # Three events at the same 12D point but different agents — one cluster.
    for i in range(3):
        bus.emit(_witness(agent_id=f"agent-{i}"))

    assert len(registry.clusters) == 1
    assert registry.clusters[0].size == 3
    assert registry.clusters[0].pattern_emitted
    assert len(registry.clusters[0].member_agent_ids) == 3


def test_registry_separates_distant_events() -> None:
    bus = PrecipitationBus()
    registry = MyceliumRegistry(bus=bus, radius=0.1)
    registry.subscribe()

    near = dict.fromkeys(TWELVE_D_DIMS, 0.3)
    far = dict.fromkeys(TWELVE_D_DIMS, 0.9)

    bus.emit(_witness(twelve_d=near))
    bus.emit(_witness(twelve_d=far))

    assert len(registry.clusters) == 2


def test_registry_emits_pattern_event_on_threshold() -> None:
    bus = PrecipitationBus()
    registry = MyceliumRegistry(bus=bus, pattern_size_threshold=3)

    captured: list[PrecipitationEvent] = []
    bus.subscribe(captured.append, kind=PrecipitationKind.MYCELIUM_PATTERN)
    registry.subscribe()

    for i in range(4):  # 4 > threshold
        bus.emit(_witness(agent_id=f"agent-{i}"))

    patterns = [e for e in captured if e.kind == PrecipitationKind.MYCELIUM_PATTERN]
    assert len(patterns) == 1
    p = patterns[0]
    assert p.payload["size"] == 3  # threshold reached at 3rd add
    assert p.payload["agent_count"] == 3
    assert p.payload["universe_count"] == 1


def test_cross_universe_cluster_gets_coherence_boost() -> None:
    bus = PrecipitationBus()
    registry = MyceliumRegistry(bus=bus, pattern_size_threshold=2)

    captured: list[PrecipitationEvent] = []
    bus.subscribe(captured.append, kind=PrecipitationKind.MYCELIUM_PATTERN)
    registry.subscribe()

    bus.emit(_witness(universe_id="u-A", coherence=0.5))
    bus.emit(_witness(universe_id="u-B", coherence=0.5))

    patterns = [e for e in captured if e.kind == PrecipitationKind.MYCELIUM_PATTERN]
    assert len(patterns) == 1
    assert patterns[0].payload["cross_universe"]
    assert patterns[0].coherence == pytest.approx(0.6, abs=1e-6)  # 0.5 + 0.1 boost


def test_ouroboros_emits_healing_event() -> None:
    """Verify the wiring added in ouroboros.py _trigger_rewrite_cycle."""
    from cohezion.learning.ouroboros import ExecutionExhaust, OuroborosEngine

    bus = PrecipitationBus()
    captured: list[PrecipitationEvent] = []
    bus.subscribe(captured.append, kind=PrecipitationKind.HEALING_EVENT)
    from cohezion.precipitation import set_bus

    set_bus(bus)
    try:
        engine = OuroborosEngine()
        exhaust = ExecutionExhaust(
            task_id="t-fail-1",
            error_message="context overflow",
            coherence_drop=0.6,
            token_usage=12345,
            diagnostics={"reason": "bloat"},
        )
        import asyncio

        result = asyncio.run(engine.consume_exhaust(exhaust))
        assert result is True

        healing = [e for e in captured if e.kind == PrecipitationKind.HEALING_EVENT]
        assert len(healing) == 1
        event = healing[0]
        assert event.payload["source_task"] == "t-fail-1"
        assert event.payload["coherence_drop"] == pytest.approx(0.6)
        assert event.coherence == pytest.approx(0.4)  # 1 - 0.6
    finally:
        set_bus(None)
