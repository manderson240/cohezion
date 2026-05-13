"""Tests for PrecipitationOrchestrator — threshold firing + training invocation."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cohezion.precipitation import (
    PrecipitationBus,
    PrecipitationEvent,
    PrecipitationKind,
)
from cohezion.precipitation.orchestrator import (
    OrchestratorConfig,
    PrecipitationOrchestrator,
)


def _witness(coherence: float = 0.7, uid: str = "u") -> PrecipitationEvent:
    return PrecipitationEvent(
        kind=PrecipitationKind.WITNESS_MARK,
        universe_id=uid,
        agent_id=f"{uid}/evo-0",
        coherence=coherence,
        payload={"mark_type": "rollout_step"},
    )


def _phase(uid: str = "u") -> PrecipitationEvent:
    return PrecipitationEvent(
        kind=PrecipitationKind.COSMOGONY_PHASE,
        universe_id=uid,
        coherence=0.6,
        payload={"from_symmetry": "SO(12)", "to_symmetry": "SO(3)^4"},
    )


@pytest.mark.asyncio
async def test_orchestrator_fires_at_threshold_in_mock_mode(tmp_path: Path) -> None:
    bus = PrecipitationBus()
    await bus.start()

    config = OrchestratorConfig(
        min_coherent_witness_marks=3,
        min_cosmogony_phases=2,
        output_dir=tmp_path / "gen",
        trajectory_dir=tmp_path / "traj",
        training_data_dir=tmp_path / "training",
        enable_real_training=False,
    )
    orch = PrecipitationOrchestrator(config=config, bus=bus)
    orch.subscribe()

    # Emit 3 coherent witness marks and 2 phase events — should trigger one generation.
    for _ in range(3):
        await bus.aemit(_witness(coherence=0.7))
    for _ in range(2):
        await bus.aemit(_phase())

    await bus.flush()
    # Orchestrator scheduled an asyncio task; let it complete.
    for _ in range(5):
        if orch.generations:
            break
        await asyncio.sleep(0.05)

    assert len(orch.generations) == 1
    gen0 = orch.generations[0]
    assert gen0.succeeded
    assert gen0.checkpoint_path.exists()
    assert gen0.witness_mark_count == 3
    assert gen0.cosmogony_phase_count == 2

    await bus.stop()


@pytest.mark.asyncio
async def test_orchestrator_invokes_subprocess_when_real_training_enabled(
    tmp_path: Path,
) -> None:
    bus = PrecipitationBus()
    await bus.start()

    # Seed a fake trajectory file so _export_training_data returns a dataset path.
    traj_dir = tmp_path / "traj"
    traj_dir.mkdir()
    (traj_dir / "trajectories-test.json").write_text(
        json.dumps(
            [
                {
                    "agent_id": "test/evo-0",
                    "task_description": "t",
                    "steps": [
                        {
                            "state_12d": [0.5] * 12,
                            "action": "x",
                            "coherence": 0.6,
                            "spin_coherence": 0.5,
                            "tempic_field": 0.4,
                            "reward": 0.1,
                            "timestamp": 0.0,
                        }
                    ],
                    "final_coherence": 0.6,
                    "total_reward": 0.1,
                    "precipitation_achieved": True,
                    "metadata": {},
                }
            ]
        )
    )

    config = OrchestratorConfig(
        min_coherent_witness_marks=1,
        min_cosmogony_phases=1,
        output_dir=tmp_path / "gen",
        trajectory_dir=traj_dir,
        training_data_dir=tmp_path / "training",
        training_script=Path("/nonexistent/run_sft_lora.py"),
        enable_real_training=True,
    )
    orch = PrecipitationOrchestrator(config=config, bus=bus)
    orch.subscribe()

    called_with_args: list[list[str]] = []

    class FakeCompleted:
        returncode = 0
        stdout = "fake ok"
        stderr = ""

    def fake_run(cmd, **kwargs):  # noqa: ANN001
        called_with_args.append(list(cmd))
        # Simulate the trainer producing the expected artifact.
        output_dir = Path(cmd[cmd.index("--output-dir") + 1])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "lora.safetensors").write_text("fake-weights")
        return FakeCompleted()

    with patch("cohezion.precipitation.orchestrator.subprocess.run", side_effect=fake_run):
        await bus.aemit(_witness(coherence=0.8))
        await bus.aemit(_phase())
        await bus.flush()
        for _ in range(5):
            if orch.generations:
                break
            await asyncio.sleep(0.05)

    assert len(called_with_args) == 1
    cmd = called_with_args[0]
    assert "--dataset" in cmd
    assert "--base-model" in cmd
    assert orch.generations[0].succeeded

    await bus.stop()


@pytest.mark.asyncio
async def test_orchestrator_does_not_fire_below_threshold(tmp_path: Path) -> None:
    bus = PrecipitationBus()
    await bus.start()

    config = OrchestratorConfig(
        min_coherent_witness_marks=10,
        min_cosmogony_phases=5,
        output_dir=tmp_path / "gen",
        trajectory_dir=tmp_path / "traj",
        training_data_dir=tmp_path / "training",
        enable_real_training=False,
    )
    orch = PrecipitationOrchestrator(config=config, bus=bus)
    orch.subscribe()

    for _ in range(3):
        await bus.aemit(_witness(coherence=0.8))
    await bus.aemit(_phase())

    await bus.flush()
    await asyncio.sleep(0.1)
    assert orch.generations == []

    await bus.stop()


@pytest.mark.asyncio
async def test_orchestrator_ignores_low_coherence_witness_marks(tmp_path: Path) -> None:
    bus = PrecipitationBus()
    await bus.start()

    config = OrchestratorConfig(
        min_coherent_witness_marks=2,
        min_cosmogony_phases=2,
        output_dir=tmp_path / "gen",
        trajectory_dir=tmp_path / "traj",
        training_data_dir=tmp_path / "training",
        enable_real_training=False,
    )
    orch = PrecipitationOrchestrator(config=config, bus=bus)
    orch.subscribe()

    # Below-HIHO witness marks do not count.
    for _ in range(5):
        await bus.aemit(_witness(coherence=0.3))
    for _ in range(5):
        await bus.aemit(_phase())

    await bus.flush()
    await asyncio.sleep(0.1)
    assert orch.generations == []

    await bus.stop()
