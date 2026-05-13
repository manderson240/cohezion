"""Tests for UniverseFactory — verify end-to-end rollout + precipitation events."""

from __future__ import annotations

from pathlib import Path

import pytest

from cohezion.precipitation import (
    PrecipitationBus,
    PrecipitationEvent,
    PrecipitationKind,
    set_bus,
)
from cohezion.universe.factory import Universe, UniverseFactory, UniverseSpec


@pytest.fixture
def capture_bus():
    bus = PrecipitationBus()
    captured: list[PrecipitationEvent] = []
    bus.subscribe(captured.append, kind=None)
    set_bus(bus)
    try:
        yield captured
    finally:
        set_bus(None)


@pytest.mark.asyncio
async def test_create_universe_single_agent(capture_bus: list[PrecipitationEvent]) -> None:
    spec = UniverseSpec(
        universe_id="u-test-single",
        agent_count=1,
        max_steps=10,
        witness_interval=5,
        seed=42,
    )
    factory = UniverseFactory()
    universe = await factory.create_universe(spec)

    assert isinstance(universe, Universe)
    assert universe.spec.universe_id == "u-test-single"
    assert len(universe.evos) == 1
    assert universe.evos[0].agent_id == "u-test-single/evo-0"
    assert universe.evos[0].universe_id == "u-test-single"
    assert universe.cosmogony.universe_id == "u-test-single"
    assert universe.nexus.universe_id == "u-test-single"

    # Creation emits GENERATION_SPAWN and a pile of COSMOGONY_PHASE events.
    gen_spawns = [e for e in capture_bus if e.kind == PrecipitationKind.GENERATION_SPAWN]
    cosmogony_events = [e for e in capture_bus if e.kind == PrecipitationKind.COSMOGONY_PHASE]
    assert len(gen_spawns) == 1
    assert len(cosmogony_events) >= 5  # many phase transitions fired during cooling
    for event in gen_spawns + cosmogony_events:
        assert event.universe_id == "u-test-single"


@pytest.mark.asyncio
async def test_run_universe_produces_trajectory_and_witness_marks(
    capture_bus: list[PrecipitationEvent],
) -> None:
    spec = UniverseSpec(
        universe_id="u-run-test",
        agent_count=1,
        max_steps=30,
        witness_interval=10,
        seed=7,
    )
    factory = UniverseFactory()
    universe = await factory.create_universe(spec)

    trajectories = await factory.run(universe)

    assert len(trajectories) == 1
    traj = trajectories[0]
    assert traj.agent_id == "u-run-test/evo-0"
    assert 0 < len(traj.steps) <= 30
    assert traj.metadata["universe_id"] == "u-run-test"

    for step in traj.steps:
        assert len(step.state_12d) == 12
        assert 0.0 <= step.coherence <= 1.0

    witness_events = [e for e in capture_bus if e.kind == PrecipitationKind.WITNESS_MARK]
    # At witness_interval=10 over 30 steps there should be at least 1 witness event if coherence hits baseline.
    assert len(witness_events) >= 1
    for event in witness_events:
        assert event.universe_id == "u-run-test"
        assert event.agent_id == "u-run-test/evo-0"


@pytest.mark.asyncio
async def test_run_universe_multi_agent_spawns_separate_journeys(
    capture_bus: list[PrecipitationEvent],
) -> None:
    spec = UniverseSpec(
        universe_id="u-multi",
        agent_count=3,
        max_steps=10,
        witness_interval=50,  # high to skip witness noise in this test
        seed=11,
    )
    factory = UniverseFactory()
    universe = await factory.create_universe(spec)
    trajectories = await factory.run(universe)

    assert len(trajectories) == 3
    agent_ids = {t.agent_id for t in trajectories}
    assert agent_ids == {"u-multi/evo-0", "u-multi/evo-1", "u-multi/evo-2"}

    # One GENERATION_SPAWN for the whole universe (the factory only emits once).
    gen_spawns = [e for e in capture_bus if e.kind == PrecipitationKind.GENERATION_SPAWN]
    assert len(gen_spawns) == 1


@pytest.mark.asyncio
async def test_save_trajectories_writes_json(
    tmp_path: Path,
    capture_bus: list[PrecipitationEvent],
) -> None:
    spec = UniverseSpec(
        universe_id="u-save",
        agent_count=1,
        max_steps=5,
        witness_interval=100,  # suppress witness events in this test
        seed=1,
    )
    factory = UniverseFactory()
    universe = await factory.create_universe(spec)
    trajectories = await factory.run(universe)

    target = await factory.save_trajectories(trajectories, tmp_path)
    assert target.exists()

    import json

    payload = json.loads(target.read_text())
    assert isinstance(payload, list)
    assert payload[0]["agent_id"] == "u-save/evo-0"
    assert "steps" in payload[0]
