"""End-to-end integration test: run N generations and verify the loop closes.

This test exercises UniverseFactory + PrecipitationBus + sinks + MyceliumRegistry
+ PrecipitationOrchestrator in one go. It does NOT invoke real training (uses
mock mode) so CI can run it in seconds.

Marked `slow` so it's opt-in via `pytest --run-slow` or the Phase-9 regression
suite. Default test runs skip it.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from cohezion.mycelium.registry import MyceliumRegistry
from cohezion.precipitation import (
    PrecipitationBus,
    PrecipitationEvent,
    PrecipitationKind,
    set_bus,
)
from cohezion.precipitation.orchestrator import (
    OrchestratorConfig,
    PrecipitationOrchestrator,
)
from cohezion.universe.factory import UniverseFactory, UniverseSpec


@pytest.mark.asyncio
@pytest.mark.slow
async def test_two_generation_loop_closes(tmp_path: Path) -> None:
    """Run 2 generations of 2 agents × 10 steps. Assert the full loop produces:
    - at least one precipitation event of each major kind
    - at least one orchestrator-driven training generation
    - at least one mycelium pattern (from clustered witness marks)
    - no sink failures
    """
    bus = PrecipitationBus()
    try:
        await _run_loop_test_body(bus, tmp_path)
    finally:
        # Critical: reset the global singleton so later tests don't inherit
        # this test's (now-stopped) bus holding a dead asyncio queue.
        set_bus(None)


async def _run_loop_test_body(bus: PrecipitationBus, tmp_path: Path) -> None:
    await bus.start()
    set_bus(bus)

    captured: list[PrecipitationEvent] = []
    bus.subscribe(captured.append, kind=None)

    # Mycelium registry with a low threshold so it emits patterns on small runs.
    mycelium = MyceliumRegistry(
        bus=bus,
        pattern_size_threshold=2,
        radius=1.0,
        fabric_radius=1.0,
    )
    mycelium.subscribe()

    # Orchestrator in mock mode
    orch = PrecipitationOrchestrator(
        config=OrchestratorConfig(
            min_coherent_witness_marks=2,
            min_cosmogony_phases=3,
            output_dir=tmp_path / "models",
            trajectory_dir=tmp_path / "trajectories",
            training_data_dir=tmp_path / "training",
            enable_real_training=False,
        ),
        bus=bus,
    )
    orch.subscribe()

    factory = UniverseFactory(bus=bus)

    current_checkpoint: str | None = None
    for generation in range(2):
        spec = UniverseSpec(
            universe_id=f"gen-{generation}",
            agent_count=2,
            max_steps=10,
            witness_interval=3,
            seed=42 + generation,
            model_checkpoint=current_checkpoint,
        )
        universe = await factory.create_universe(spec)
        trajectories = await factory.run(universe)
        await factory.save_trajectories(trajectories, tmp_path / "trajectories")
        await bus.flush()
        await asyncio.sleep(0.05)

        if orch.generations:
            current_checkpoint = str(orch.generations[-1].checkpoint_path)

    await bus.flush()
    await bus.stop()

    # Assertions
    kinds_seen = {e.kind for e in captured}
    assert PrecipitationKind.GENERATION_SPAWN in kinds_seen
    assert PrecipitationKind.COSMOGONY_PHASE in kinds_seen
    assert PrecipitationKind.WITNESS_MARK in kinds_seen

    # Orchestrator should have fired at least once.
    assert len(orch.generations) >= 1
    for record in orch.generations:
        assert record.checkpoint_path.exists()
        assert record.succeeded

    # Mycelium should produce at least one pattern (low threshold + many marks).
    mycelium_patterns = [e for e in captured if e.kind == PrecipitationKind.MYCELIUM_PATTERN]
    assert len(mycelium_patterns) >= 1

    # Gen 1 should use a checkpoint from Gen 0's orchestrator firing.
    gen_spawn_events = [e for e in captured if e.kind == PrecipitationKind.GENERATION_SPAWN]
    assert len(gen_spawn_events) == 2
    # First gen has model_checkpoint=None; second inherits a non-None path.
    assert gen_spawn_events[0].payload["model_checkpoint"] is None
    gen1_checkpoint = gen_spawn_events[1].payload["model_checkpoint"]
    assert gen1_checkpoint is not None
    assert "gen-0" in gen1_checkpoint, (
        f"Gen 1 should spawn with Gen 0's checkpoint, got {gen1_checkpoint}"
    )

    # Bus should have zero sink failures.
    assert bus.stats["failures"] == 0


@pytest.mark.asyncio
@pytest.mark.slow
async def test_driver_script_exists_and_imports() -> None:
    """Regression guard: the CLI driver must be importable from a clean Python session."""
    import importlib.util
    from pathlib import Path

    script = Path("scripts/drivers/run_coherent_precipitation.py")
    assert script.exists()

    spec = importlib.util.spec_from_file_location("run_coherent_precipitation", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "main")
    assert hasattr(module, "parse_args")
