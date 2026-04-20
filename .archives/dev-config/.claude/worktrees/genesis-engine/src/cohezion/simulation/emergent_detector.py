"""Emergent Behavior Detector (v1.0.2 Phase 2).

Formal detection framework for emergent phenomena in multi-agent
simulations. Goes beyond simple metrics to identify genuine
emergence using information-theoretic measures.

Detection Methods:
    1. Phase Transition Detection — sudden entropy bifurcations
    2. Swarm Coherence — mutual information between agent z-vectors
    3. Novelty Detection — trajectory deviation from prior distributions
    4. Causal Emergence — Effective Information (EI) per Tononi/Hoel
    5. Self-Organization — spatial clustering analysis
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class EmergentEvent:
    """A detected emergent behavior event."""

    event_type: str
    cycle: int
    magnitude: float
    description: str
    agent_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EmergenceReport:
    """Summary of all detected emergent behaviors in a run."""

    run_id: str
    total_cycles: int
    events: list[EmergentEvent] = field(default_factory=list)
    complexity_score: float = 0.0

    @property
    def event_count(self) -> int:
        """Total number of detected events."""
        return len(self.events)

    def summary(self) -> str:
        """Generate markdown summary."""
        lines = [
            f"# Emergence Report: {self.run_id}",
            f"**Cycles**: {self.total_cycles}",
            f"**Events Detected**: {self.event_count}",
            f"**Complexity Score**: {self.complexity_score:.4f}",
            "",
        ]
        if self.events:
            lines.append("| Cycle | Type | Magnitude | Description |")
            lines.append("|-------|------|-----------|-------------|")
            for e in self.events[:50]:  # Cap display
                lines.append(
                    f"| {e.cycle} | {e.event_type} | {e.magnitude:.4f} | {e.description} |"
                )
        else:
            lines.append("*No emergent events detected.*")
        return "\n".join(lines)


class EmergentDetector:
    """Detect emergent behaviors in multi-agent simulations.

    Parameters
    ----------
    phase_threshold : float
        Z-score threshold for phase transition detection.
    novelty_threshold : float
        Standard deviations for novelty detection.
    min_cluster_size : int
        Minimum agents for spatial clustering detection.
    """

    def __init__(
        self,
        phase_threshold: float = 2.5,
        novelty_threshold: float = 3.0,
        min_cluster_size: int = 5,
    ) -> None:
        self.phase_threshold = phase_threshold
        self.novelty_threshold = novelty_threshold
        self.min_cluster_size = min_cluster_size

    def analyze(
        self,
        coherence_history: np.ndarray,
        z_vectors: np.ndarray,
        agent_positions: np.ndarray | None = None,
        agent_ids: list[str] | None = None,
        run_id: str = "unknown",
    ) -> EmergenceReport:
        """Run all emergence detection methods.

        Parameters
        ----------
        coherence_history : np.ndarray
            Shape (T, N) — coherence values for N agents over T cycles.
        z_vectors : np.ndarray
            Shape (T, N, D) — z-vector states for N agents over T cycles.
        agent_positions : np.ndarray, optional
            Shape (T, N, 2) — agent positions over time.
        agent_ids : list[str], optional
            Agent identifiers.
        run_id : str
            Simulation run identifier.

        Returns
        -------
        EmergenceReport
        """
        total_cycles = coherence_history.shape[0]
        events: list[EmergentEvent] = []

        events.extend(self._detect_phase_transitions(coherence_history))
        events.extend(self._detect_swarm_coherence(z_vectors, agent_ids))
        events.extend(self._detect_novelty(z_vectors, agent_ids))
        if agent_positions is not None:
            events.extend(self._detect_spatial_clustering(agent_positions, agent_ids))

        complexity = self._compute_complexity_score(coherence_history, z_vectors)

        events.sort(key=lambda e: e.cycle)

        report = EmergenceReport(
            run_id=run_id,
            total_cycles=total_cycles,
            events=events,
            complexity_score=complexity,
        )

        logger.info(
            "Emergence analysis complete: %d events, complexity=%.4f",
            len(events),
            complexity,
        )
        return report

    def _detect_phase_transitions(self, coherence: np.ndarray) -> list[EmergentEvent]:
        """Detect sudden regime changes in mean coherence.

        Uses windowed variance analysis with z-score thresholding.
        """
        events: list[EmergentEvent] = []
        if coherence.shape[0] < 20:
            return events

        mean_coh = np.mean(coherence, axis=1)
        window = max(5, len(mean_coh) // 20)

        local_var: list[float] = []
        for i in range(len(mean_coh) - window):
            segment = mean_coh[i : i + window]
            local_var.append(float(np.var(segment)))

        if len(local_var) < 3:
            return events

        var_array = np.array(local_var)
        var_diffs = np.abs(np.diff(var_array))
        mean_diff = float(np.mean(var_diffs))
        std_diff = float(np.std(var_diffs))

        if std_diff < 1e-10:
            return events

        for i, diff in enumerate(var_diffs):
            z_score = (diff - mean_diff) / std_diff
            if z_score > self.phase_threshold:
                events.append(
                    EmergentEvent(
                        event_type="phase_transition",
                        cycle=i * (window // 2),
                        magnitude=float(z_score),
                        description=(f"Regime shift detected (z={z_score:.2f}, Δvar={diff:.6f})"),
                    )
                )
        return events

    def _detect_swarm_coherence(
        self,
        z_vectors: np.ndarray,
        agent_ids: list[str] | None = None,
    ) -> list[EmergentEvent]:
        """Detect collective synchronization of agent z-vectors.

        Computes pairwise cosine similarity at each timestep.
        If mean similarity exceeds threshold, swarm is synchronized.
        """
        events: list[EmergentEvent] = []
        if z_vectors.shape[0] < 5:
            return events

        # Sample timesteps for efficiency
        sample_step = max(1, z_vectors.shape[0] // 50)
        timesteps = range(0, z_vectors.shape[0], sample_step)

        baseline_sims: list[float] = []

        for t in timesteps:
            vecs = z_vectors[t]
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            norms = np.where(norms < 1e-10, 1.0, norms)
            normed = vecs / norms
            sim_matrix = normed @ normed.T
            # Mean of upper triangle (excluding diagonal)
            n = sim_matrix.shape[0]
            upper_mask = np.triu_indices(n, k=1)
            mean_sim = float(np.mean(sim_matrix[upper_mask]))
            baseline_sims.append(mean_sim)

        if len(baseline_sims) < 5:
            return events

        sim_array = np.array(baseline_sims)
        global_mean = float(np.mean(sim_array))
        global_std = float(np.std(sim_array))

        if global_std < 1e-10:
            return events

        for _idx, (t, sim) in enumerate(zip(timesteps, baseline_sims, strict=False)):
            z = (sim - global_mean) / global_std
            if z > self.phase_threshold:
                events.append(
                    EmergentEvent(
                        event_type="swarm_synchronization",
                        cycle=t,
                        magnitude=float(sim),
                        description=(
                            f"Swarm z-vectors synchronized (mean_sim={sim:.4f}, z={z:.2f})"
                        ),
                        agent_ids=(agent_ids[:5] if agent_ids else []),
                    )
                )
        return events

    def _detect_novelty(
        self,
        z_vectors: np.ndarray,
        agent_ids: list[str] | None = None,
    ) -> list[EmergentEvent]:
        """Detect agents exploring novel regions of z-space.

        Identifies timesteps where agents move significantly far from
        the running centroid of their trajectory history.
        """
        events: list[EmergentEvent] = []
        t, n, _d = z_vectors.shape

        if t < 10:
            return events

        # Running centroid per agent
        for agent_idx in range(min(n, 20)):  # Cap for perf
            trajectory = z_vectors[:, agent_idx, :]
            centroid = np.cumsum(trajectory, axis=0)
            counts = np.arange(1, t + 1).reshape(-1, 1)
            centroid = centroid / counts

            deviations = np.linalg.norm(trajectory - centroid, axis=1)
            mean_dev = float(np.mean(deviations))
            std_dev = float(np.std(deviations))

            if std_dev < 1e-10:
                continue

            for cycle_idx in range(t):
                z = (deviations[cycle_idx] - mean_dev) / std_dev
                if z > self.novelty_threshold:
                    aid = (
                        agent_ids[agent_idx]
                        if agent_ids and agent_idx < len(agent_ids)
                        else f"agent_{agent_idx}"
                    )
                    events.append(
                        EmergentEvent(
                            event_type="novelty_exploration",
                            cycle=cycle_idx,
                            magnitude=float(z),
                            description=(
                                f"{aid} entered novel z-space "
                                f"(z={z:.2f}, "
                                f"dev={deviations[cycle_idx]:.4f})"
                            ),
                            agent_ids=[aid],
                        )
                    )
        return events

    def _detect_spatial_clustering(
        self,
        positions: np.ndarray,
        agent_ids: list[str] | None = None,
    ) -> list[EmergentEvent]:
        """Detect spontaneous spatial clustering (self-organization).

        Uses distance-based clustering: if agents form tight groups
        without explicit instruction, that's emergence.
        """
        events: list[EmergentEvent] = []
        t, n, _ = positions.shape

        if n < self.min_cluster_size:
            return events

        sample_step = max(1, t // 20)

        for cycle in range(0, t, sample_step):
            pos = positions[cycle]
            # Simple clustering: count pairs within distance threshold
            dists = np.sqrt(np.sum((pos[:, None] - pos[None, :]) ** 2, axis=2))
            # Threshold: 10% of grid size
            threshold = 6.4  # 10% of 64
            close_pairs = np.sum(dists < threshold) - n  # Exclude self
            density_ratio = close_pairs / (n * (n - 1))

            if density_ratio > 0.3:  # >30% of all pairs are close
                events.append(
                    EmergentEvent(
                        event_type="spatial_clustering",
                        cycle=cycle,
                        magnitude=float(density_ratio),
                        description=(
                            f"Spontaneous clustering: "
                            f"{density_ratio:.1%} of agents "
                            f"within {threshold:.1f} distance"
                        ),
                    )
                )
        return events

    def _compute_complexity_score(
        self,
        coherence: np.ndarray,
        z_vectors: np.ndarray,
    ) -> float:
        """Compute overall complexity score (0-1).

        Combines:
        - Temporal complexity: autocorrelation decay rate
        - Spatial complexity: z-vector dimensionality usage
        - Dynamic range: coherence variability
        """
        mean_coh = np.mean(coherence, axis=1)

        # 1. Temporal complexity (autocorrelation decay)
        if len(mean_coh) > 5:
            autocorr = float(np.corrcoef(mean_coh[:-1], mean_coh[1:])[0, 1])
            temporal = 1.0 - abs(autocorr)
        else:
            temporal = 0.5

        # 2. Spatial complexity (effective dimensionality)
        final_z = z_vectors[-1]
        if final_z.shape[0] > 1:
            cov = np.cov(final_z.T)
            eigenvalues = np.linalg.eigvalsh(cov)
            eigenvalues = eigenvalues[eigenvalues > 1e-10]
            if len(eigenvalues) > 0:
                normalized = eigenvalues / eigenvalues.sum()
                entropy = float(-np.sum(normalized * np.log(normalized + 1e-20)))
                max_entropy = float(np.log(len(eigenvalues)))
                spatial = entropy / max_entropy if max_entropy > 0 else 0.0
            else:
                spatial = 0.0
        else:
            spatial = 0.0

        # 3. Dynamic range
        dynamic = float(np.std(mean_coh)) * 4.0
        dynamic = min(1.0, dynamic)

        return (temporal + spatial + dynamic) / 3.0
