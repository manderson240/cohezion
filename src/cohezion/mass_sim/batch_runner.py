"""Batch simulation runner - calls Rust FlumePhysics for the heavy lifting.

Processes agents in memory-bounded batches with OOM protection.
Collects checkpoint statistics without storing full agent state histories.
"""

from __future__ import annotations

import logging
import time

import numpy as np

from cohezion.mass_sim.config import (
    CheckpointData,
    SimulationConfig,
    UniverseResult,
    UniverseSpec,
)
from cohezion.mass_sim.exporter import CheckpointExporter
from cohezion.mass_sim.system_monitor import MemoryGuard
from cohezion.mass_sim.universe_factory import UniverseFactory


logger = logging.getLogger(__name__)


class BatchSimulationRunner:
    """Runs simulation batches through the Rust FLUME engine."""

    def __init__(
        self,
        config: SimulationConfig,
        trained_navigator: object | None = None,
    ):
        self.config = config
        self.guard = MemoryGuard(max_memory_gb=config.max_memory_gb)
        self.trained_navigator = trained_navigator
        self._exporter: CheckpointExporter | None = None
        if config.export_npy:
            self._exporter = CheckpointExporter(config.artifact_dir)

    def simulate_universe(
        self,
        universe_spec: UniverseSpec,
        agents: np.ndarray,
    ) -> UniverseResult:
        """Simulate all agents through one universe.

        Parameters
        ----------
        universe_spec : UniverseSpec
            Universe weight configuration.
        agents : np.ndarray
            Shape [n_agents, z_dim], initial latent states.

        Returns
        -------
        UniverseResult
            Complete results with checkpoints and statistics.
        """
        t0 = time.time()
        n_agents = agents.shape[0]
        z_dim = agents.shape[1]
        cfg = self.config
        batch_size = cfg.scale.batch_size
        checkpoint_interval = cfg.scale.checkpoint_interval
        total_epochs = cfg.scale.n_epochs

        # Create universe-specific physics engine with tuning params
        physics = UniverseFactory.create(
            universe_spec,
            delta_scale=cfg.delta_scale,
            hiho_damping=cfg.hiho_damping,
        )

        # Compute initial statistics
        initial_stats = physics.compute_batch_stats(agents)

        logger.info(
            f"  Universe {universe_spec.universe_id}: "
            f"{n_agents} agents x {total_epochs} epochs "
            f"(batch={batch_size}, ckpt every {checkpoint_interval})"
        )

        # Working copy of agent states
        current = agents.copy()
        checkpoints: list[CheckpointData] = []

        # Process in epoch chunks aligned to checkpoint intervals
        epochs_completed = 0
        while epochs_completed < total_epochs:
            # OOM check
            if self.guard.should_abort():
                logger.error(
                    f"  Aborting universe {universe_spec.universe_id} at epoch {epochs_completed} (memory)"
                )
                break

            # Adaptive batch size
            safe_batch = self.guard.safe_batch_size(batch_size, z_dim)

            # Epochs in this chunk
            epochs_this_chunk = min(checkpoint_interval, total_epochs - epochs_completed)

            # Process agents in memory-bounded batches
            evolved_parts: list[np.ndarray] = []
            for batch_start in range(0, n_agents, safe_batch):
                batch_end = min(batch_start + safe_batch, n_agents)
                batch = current[batch_start:batch_end]

                if self.trained_navigator is not None:
                    evolved = self._navigate_with_policy(batch, epochs_this_chunk)
                elif cfg.use_navigator:
                    evolved = physics.simulate_epochs_navigated(batch, epochs_this_chunk)
                else:
                    evolved = physics.simulate_epochs_batch(batch, epochs_this_chunk)
                evolved_parts.append(np.asarray(evolved))

            current = np.vstack(evolved_parts)
            epochs_completed += epochs_this_chunk

            # Checkpoint: compute statistics (in Rust, fast)
            stats = physics.compute_batch_stats(current)
            sample = (
                current[: cfg.checkpoint_sample_size].tolist()
                if cfg.checkpoint_sample_size > 0
                else None
            )
            checkpoints.append(
                CheckpointData(
                    epoch=epochs_completed,
                    stats=stats,
                    sample_states=sample,
                )
            )

            # Progress logging (sparse)
            pct = (epochs_completed / total_epochs) * 100
            if len(checkpoints) % 5 == 0 or epochs_completed == total_epochs:
                logger.info(
                    f"    {pct:.0f}% ({epochs_completed}/{total_epochs}) "
                    f"coherence={float(stats.get('mean_coherence', 0)):.3f} "
                    f"within_bounds={float(stats.get('pct_within_bounds', 0)):.1%}"
                )

        # Final statistics
        final_stats = physics.compute_batch_stats(current)

        elapsed = time.time() - t0
        logger.info(
            f"  Universe {universe_spec.universe_id} complete: "
            f"{elapsed:.1f}s, final coherence={final_stats.get('mean_coherence', 0):.3f}"
        )

        # Export final states as .npy for training pipeline
        if self._exporter is not None:
            self._exporter.export_final_states(universe_spec.universe_id, current)

        return UniverseResult(
            universe_id=universe_spec.universe_id,
            seed=universe_spec.seed,
            n_agents=n_agents,
            n_epochs=epochs_completed,
            initial_stats=initial_stats,
            final_stats=final_stats,
            checkpoints=checkpoints,
            elapsed_seconds=elapsed,
        )

    def _navigate_with_policy(self, batch: np.ndarray, n_epochs: int) -> np.ndarray:
        """Apply trained Python RL policy for navigation."""
        current = batch.copy()
        for _ in range(n_epochs):
            deltas = self.trained_navigator.navigate_batch(current)
            current = current + deltas * self.config.delta_scale
        return current
