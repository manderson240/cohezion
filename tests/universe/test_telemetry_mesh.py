import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.core.journey_worker import get_journey_worker
from cohezion.core.telemetry_bus import get_telemetry_bus
from cohezion.data_mesh.universe_telemetry import UniverseStateEvent
from cohezion.universe.engine import AxiomaticState, UniverseJourney, UniverseSimulationEngine


@pytest.mark.asyncio
async def test_journey_worker_processes_universe_event():
    """
    RED PHASE: Verify that JourneyWorker handles UniverseStateEvent.
    """
    worker = get_journey_worker()

    # Mock dependencies to avoid real DB/Bridge calls
    worker._db = MagicMock()
    worker._db.insert_universe_state = AsyncMock()  # We expect this new method
    worker._bridge = MagicMock()
    worker._bridge.check_coherence = AsyncMock()

    event = UniverseStateEvent(
        event_id="ue_test",
        universe_id="uni_test",
        state_12d=[0.5] * 12,
        coherence=0.4,  # Drop from 0.5
        stability_shift=0.1,
        trigger_journey_id="j_test",
    )

    # Manually trigger processing
    await worker.process_event(event)

    # Verify DB persistence
    assert worker._db.insert_universe_state.called

    # Verify Ouroboros notification
    worker._bridge.check_coherence.assert_called_with(0.1, task_id="j_test")


@pytest.mark.asyncio
async def test_universe_engine_emits_telemetry_on_shift():
    """
    GREEN PHASE: Verify that UniverseSimulationEngine emits telemetry when a shift occurs.
    """
    bus = get_telemetry_bus()
    captured_events = []

    def subscriber(event):
        captured_events.append(event)

    bus.subscribe(subscriber)
    await bus.start()

    engine = UniverseSimulationEngine()
    journey = UniverseJourney(
        id="test_j",
        agent_name="test_a",
        intent="test_i",
        initial_axiomatic=AxiomaticState(
            physics=0.5, biology=0.5, logic=0.5, quantum=0.5, field=0.5, control=0.5, novelty=0.5
        ),
    )

    # Mock the physics engine to return a state with < 0.45 coherence (shift > 0.05)
    shifted_state = AxiomaticState(
        physics=0.1, biology=0.1, logic=0.1, quantum=0.5, field=0.5, control=0.5, novelty=0.5
    )

    with patch(
        "cohezion.universe.spatial_phonons.SpatialPhononsEngine.evolve_state",
        return_value=shifted_state,
    ):
        # Trigger a shift by evolving.
        await engine.evolve_trajectory(journey, action="Significant Shift Action")

    # Wait for async bus
    for _ in range(20):
        await asyncio.sleep(0.1)
        if len(captured_events) > 0:
            break

    try:
        assert len(captured_events) > 0, "No telemetry event emitted by UniverseSimulationEngine"
    finally:
        await bus.stop()
