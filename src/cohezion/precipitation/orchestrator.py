"""PrecipitationOrchestrator — closes the recursive self-improvement loop.

Watches the PrecipitationBus. When enough coherent events have accumulated from
a generation of rollouts, it:

  1. Exports the generation's journeys via ExperienceDataset (DPO + rewards +
     judgments) to data/training/.
  2. Kicks off scripts/training/run_sft_lora.py as a subprocess — the actual
     trl.SFTTrainer call happens there.
  3. On success: emits TRAINING_CHECKPOINT with the new weights path and
     registers the checkpoint so the next-generation UniverseFactory call can
     use it.
  4. Optionally calls UniverseFactory.create_universe(...) with the new
     checkpoint to spawn the next generation — emits GENERATION_SPAWN.

The orchestrator is deliberately decoupled from the model training itself
(which runs in a subprocess) so unit tests can mock the subprocess and verify
orchestration independently of whether `trl` is installed.
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable

from cohezion.precipitation.bus import PrecipitationBus, get_bus
from cohezion.precipitation.events import (
    PrecipitationEvent,
    PrecipitationKind,
)


logger = logging.getLogger(__name__)


@dataclass
class OrchestratorConfig:
    """Thresholds and parameters controlling the orchestrator."""

    min_coherent_witness_marks: int = 20  # WITNESS_MARKs with coherence >= 0.5
    min_cosmogony_phases: int = 5  # symmetry breaks observed
    base_model: str = "Qwen/Qwen2.5-0.5B-Instruct"
    lora_r: int = 32
    lora_alpha: int = 64
    epochs: int = 1
    output_dir: Path = Path("models/cohezion-gen")
    training_script: Path = Path("scripts/training/run_sft_lora.py")
    trajectory_dir: Path = Path("data/trajectories")
    training_data_dir: Path = Path("data/training")
    subprocess_timeout_s: int = 3600
    # When True, the orchestrator shells out to the training script. When False
    # (default for tests), the orchestrator writes a metadata-only checkpoint
    # marker and skips the real training call — useful for unit tests that
    # don't want to spin up trl/peft.
    enable_real_training: bool = False


@dataclass
class GenerationRecord:
    """What the orchestrator produced for one generation."""

    generation: int
    checkpoint_path: Path
    witness_mark_count: int
    cosmogony_phase_count: int
    base_model: str
    started_at: datetime
    finished_at: datetime | None = None
    succeeded: bool = False
    details: dict = field(default_factory=dict)


class PrecipitationOrchestrator:
    """Threshold-gated generational training loop.

    Usage:
        orchestrator = PrecipitationOrchestrator(config)
        orchestrator.subscribe_to(bus)
        # ... rollouts happen, events fire ...
        # When thresholds cross, orchestrator.on_threshold_reached is called
        # and a new GenerationRecord is added to orchestrator.generations.
    """

    def __init__(
        self,
        config: OrchestratorConfig | None = None,
        bus: PrecipitationBus | None = None,
        on_generation: Callable[[GenerationRecord], Awaitable[None]] | None = None,
    ) -> None:
        self.config = config or OrchestratorConfig()
        self.bus = bus or get_bus()
        self.on_generation = on_generation
        self._witness_coherent = 0
        self._cosmogony_phases = 0
        self._universe_trajectories: dict[str, list[str]] = {}
        self.generations: list[GenerationRecord] = []
        self._fired_for_threshold = False

    def subscribe(self) -> None:
        """Attach the orchestrator's tally handler to the bus."""
        self.bus.subscribe(self._on_event, kind=None)

    def _on_event(self, event: PrecipitationEvent) -> None:
        """Count qualifying events; fire training at threshold."""
        if event.kind == PrecipitationKind.WITNESS_MARK and event.coherence >= 0.5:
            self._witness_coherent += 1
        elif event.kind == PrecipitationKind.COSMOGONY_PHASE:
            self._cosmogony_phases += 1
        elif event.kind == PrecipitationKind.COHERENCE_PEAK:
            self._cosmogony_phases += 1  # also counts as a phase-class event

        # Track per-universe identity so we know what to train on.
        self._universe_trajectories.setdefault(event.universe_id, []).append(event.event_id)

        if (
            not self._fired_for_threshold
            and self._witness_coherent >= self.config.min_coherent_witness_marks
            and self._cosmogony_phases >= self.config.min_cosmogony_phases
        ):
            self._fired_for_threshold = True
            try:
                # Try to schedule on a running loop; fall back to sync execution.
                loop = asyncio.get_running_loop()
                loop.create_task(self._run_generation())
            except RuntimeError:
                asyncio.run(self._run_generation())

    async def _run_generation(self) -> GenerationRecord:
        """Export DPO data, invoke training, emit checkpoint event."""
        generation = len(self.generations)
        started_at = datetime.now(timezone.utc)
        output_dir = self.config.output_dir / f"gen-{generation}"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Export DPO data from persisted trajectories (if any present on disk).
        exported = self._export_training_data()

        checkpoint_path = output_dir / "lora.safetensors"

        if self.config.enable_real_training:
            result = self._invoke_trainer(
                dataset_path=exported.get("preferences"),
                output_dir=output_dir,
            )
            succeeded = result["returncode"] == 0
            details = result
            if not checkpoint_path.exists():
                # Training script didn't produce the expected artifact. Write a marker.
                checkpoint_path.write_text(
                    json.dumps({"note": "no real checkpoint produced", "result": result})
                )
        else:
            # Test/no-deps mode: write a metadata marker so the orchestration
            # can still hand off a 'checkpoint path' to the next generation.
            checkpoint_path.write_text(
                json.dumps(
                    {
                        "generation": generation,
                        "base_model": self.config.base_model,
                        "witness_marks": self._witness_coherent,
                        "cosmogony_phases": self._cosmogony_phases,
                        "mode": "mock",
                    },
                    indent=2,
                )
            )
            succeeded = True
            details = {"mode": "mock", "exported": {k: str(v) for k, v in exported.items()}}

        finished_at = datetime.now(timezone.utc)
        record = GenerationRecord(
            generation=generation,
            checkpoint_path=checkpoint_path,
            witness_mark_count=self._witness_coherent,
            cosmogony_phase_count=self._cosmogony_phases,
            base_model=self.config.base_model,
            started_at=started_at,
            finished_at=finished_at,
            succeeded=succeeded,
            details=details,
        )
        self.generations.append(record)

        # Emit TRAINING_CHECKPOINT for the artifact.
        await self._emit_training_checkpoint(record)

        # Reset thresholds so the next generation can accumulate.
        self._witness_coherent = 0
        self._cosmogony_phases = 0
        self._fired_for_threshold = False

        if self.on_generation is not None:
            await self.on_generation(record)

        return record

    def _export_training_data(self) -> dict[str, Path]:
        """Read persisted trajectories and export via ExperienceDataset.

        Returns a dict of {"preferences": path, "rewards": path, "judgments": path}.
        Empty dict if no trajectory files exist.
        """
        self.config.training_data_dir.mkdir(parents=True, exist_ok=True)

        trajectory_files = list(self.config.trajectory_dir.glob("trajectories-*.json"))
        if not trajectory_files:
            return {}

        # Lazy import — only needed if we actually have data to export.
        from cohezion.universe.llm_training_bridge import (
            AgentTrajectory,
            ExperienceDataset,
            TrajectoryStep,
        )

        trajectories: list[AgentTrajectory] = []
        for path in trajectory_files:
            try:
                raw = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                logger.warning("orchestrator: could not read %s", path)
                continue
            for item in raw:
                trajectories.append(
                    AgentTrajectory(
                        agent_id=item["agent_id"],
                        task_description=item["task_description"],
                        steps=[TrajectoryStep(**s) for s in item["steps"]],
                        final_coherence=item["final_coherence"],
                        total_reward=item["total_reward"],
                        precipitation_achieved=item.get("precipitation_achieved", False),
                        metadata=item.get("metadata", {}),
                    )
                )

        if not trajectories:
            return {}

        dataset = ExperienceDataset(output_dir=self.config.training_data_dir)
        results: dict[str, Path] = {
            "preferences": dataset.export_preference_data(trajectories),
            "rewards": dataset.export_reward_data(trajectories),
        }
        return results

    def _invoke_trainer(
        self,
        *,
        dataset_path: Path | None,
        output_dir: Path,
    ) -> dict:
        """Run scripts/training/run_sft_lora.py as a subprocess."""
        if dataset_path is None:
            return {"returncode": 1, "stderr": "no dataset exported", "stdout": ""}
        cmd = [
            sys.executable,
            str(self.config.training_script),
            "--dataset",
            str(dataset_path),
            "--base-model",
            self.config.base_model,
            "--output-dir",
            str(output_dir),
            "--lora-r",
            str(self.config.lora_r),
            "--lora-alpha",
            str(self.config.lora_alpha),
            "--epochs",
            str(self.config.epochs),
        ]
        logger.info("orchestrator invoking trainer: %s", " ".join(cmd))
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.subprocess_timeout_s,
                check=False,
            )
            return {
                "returncode": completed.returncode,
                "stdout": completed.stdout[-2000:],
                "stderr": completed.stderr[-2000:],
            }
        except subprocess.TimeoutExpired as exc:
            return {"returncode": 124, "stdout": "", "stderr": f"timeout: {exc}"}
        except Exception as exc:  # noqa: BLE001 — subprocess failures are logged, not raised
            return {"returncode": 125, "stdout": "", "stderr": str(exc)}

    async def _emit_training_checkpoint(self, record: GenerationRecord) -> None:
        """Emit TRAINING_CHECKPOINT for a completed generation."""
        coherence = 1.0 if record.succeeded else 0.3
        try:
            await self.bus.aemit(
                PrecipitationEvent(
                    kind=PrecipitationKind.TRAINING_CHECKPOINT,
                    universe_id=f"orchestrator-gen-{record.generation}",
                    coherence=coherence,
                    payload={
                        "generation": record.generation,
                        "checkpoint_path": str(record.checkpoint_path),
                        "base_model": record.base_model,
                        "witness_marks": record.witness_mark_count,
                        "cosmogony_phases": record.cosmogony_phase_count,
                        "started_at": record.started_at.isoformat(),
                        "finished_at": (record.finished_at or record.started_at).isoformat(),
                        "succeeded": record.succeeded,
                        "details": record.details,
                    },
                )
            )
        except Exception:  # noqa: BLE001
            logger.debug("Precipitation emit failed for TRAINING_CHECKPOINT", exc_info=True)


__all__ = [
    "GenerationRecord",
    "OrchestratorConfig",
    "PrecipitationOrchestrator",
]
