"""Cohezion EVO — Experiential Voyage Objects.

Bridges the physics-simulation layer (universe/agentic_evo_swift.py) with the
compound/journey layer (compound/journey_tracker.py) for continuous self-improvement
via multimodal EVO-as-agentic-journey demonstrations.

Key types:
- ExperientialVoyage: completed EVO journey stored in SurrealDB + Obsidian vault
- PhiDistribution: distributional phi score over rubric-aligned bins (Z-Reward style)
- phi_from_coherence: HIHO 4x(1-x) kernel for trajectory quality scoring

Storage pattern (dual-write):
  SurrealDB  → structured queries, bi-temporal evo_journey table
  Obsidian   → human-readable notes via vault MCP (vault_log_experiment)
  Both writes go through JourneyTracker.emit_evo_voyage() — never direct file I/O.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class PhiDistribution:
    """Distributional phi score over rubric-aligned coherence bins.

    Replaces the scalar phi point estimate with a probability distribution that
    preserves uncertainty across the full trace-step series (Z-Reward §3.2 style).
    Two voyages at the same final phi can have very different gate probabilities when
    one arrived there from variance and the other from stable sub-threshold drift.

    Bins partition the HIHO coherence regimes:
      [0.0, 0.1)  — fully degenerate
      [0.1, 0.2)  — severely degenerate
      [0.2, 0.3)  — below Constitution gate
      [0.3, 0.5)  — above gate, converging toward HIHO attractor
      [0.5, 0.7)  — at/above HIHO attractor
      [0.7, 1.0]  — near-maximum coherence
    """

    bins: tuple[float, ...]
    probs: tuple[float, ...]
    point_estimate: float  # final-step 4·c·(1-c) — backwards compat with scalar path

    _DEFAULT_BINS: ClassVar[tuple[float, ...]] = (0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0)

    def gate_probability(self, threshold: float = 0.3) -> float:
        """P(phi >= threshold) — soft gate replacing the hard binary is_degenerate check.

        Returns a value in [0, 1]. A voyage at phi=0.249 that spent several steps above
        0.3 returns a meaningful probability; one that monotonically decayed returns ~0.
        """
        return sum(p for b, p in zip(self.bins, self.probs) if b >= threshold)

    def expected_phi(self) -> float:
        """E[phi] using bin midpoints as representatives."""
        midpoints = [(self.bins[i] + self.bins[i + 1]) / 2.0 for i in range(len(self.bins) - 1)]
        return sum(m * p for m, p in zip(midpoints, self.probs))

    def as_dict(self) -> dict:
        return {
            "bins": list(self.bins),
            "probs": [round(p, 6) for p in self.probs],
            "point_estimate": round(self.point_estimate, 6),
            "gate_prob": round(self.gate_probability(), 6),
            "expected_phi": round(self.expected_phi(), 6),
        }

    @classmethod
    def from_phi_series(cls, phi_values: list[float]) -> "PhiDistribution":
        """Build distribution from the phi values observed across all trace steps.

        Uses Laplace (add-0.5) smoothing so every bin has non-zero probability —
        the teacher's reasoning uncertainty propagates even for short traces.
        """
        bins = cls._DEFAULT_BINS
        n_bins = len(bins) - 1
        counts: list[float] = [0.5] * n_bins  # Laplace prior
        for phi in phi_values:
            phi = max(0.0, min(1.0, phi))
            placed = False
            for i in range(n_bins - 1):
                if bins[i] <= phi < bins[i + 1]:
                    counts[i] += 1.0
                    placed = True
                    break
            if not placed:
                counts[n_bins - 1] += 1.0
        total = sum(counts)
        probs = tuple(c / total for c in counts)
        return cls(
            bins=bins,
            probs=probs,
            point_estimate=phi_values[-1] if phi_values else 0.0,
        )


@dataclass
class ExperientialVoyage:
    """Completed EVO journey linking latent physics to compound trajectory.

    Created by RecursiveTracer.complete_journey() after all trace steps are done.
    Persisted by JourneyTracker.emit_evo_voyage() to both SurrealDB and the
    Obsidian vault (via vault MCP).

    Fields:
        voyage_id:        UUID for this voyage (unique per run)
        agent_id:         AgenticEVO agent identifier
        journey_id:       JourneyTracker execution ID (links to journey_transition records)
        phi_score:        HIHO trajectory quality: 4 * c * (1 - c) at final coherence.
                          Peaks at 1.0 when c=0.5 (HIHO attractor). Below 0.3 = degenerate.
        modalities_used:  Sorted list of modalities touched (["audio","image","text"])
        skill_refinements: Skill IDs whose PRIME files were updated post-journey
        latent_snapshot:  First 16 dimensions of final latent_vector (serializable summary)
        started_at:       Unix timestamp of first trace_step call
        completed_at:     Unix timestamp of complete_journey call
        valid_from:       SurrealDB bi-temporal valid start (set at creation)
        valid_to:         SurrealDB bi-temporal valid end (None = currently valid)
    """

    voyage_id: str
    agent_id: str
    journey_id: str
    phi_score: float
    modalities_used: list[str]
    skill_refinements: list[str]
    latent_snapshot: list[float]
    started_at: float
    completed_at: float
    valid_from: float = field(default_factory=time.time)
    valid_to: float | None = None
    phi_distribution: PhiDistribution | None = None  # distributional score; None = scalar-only path

    @property
    def duration_seconds(self) -> float:
        return self.completed_at - self.started_at

    @property
    def is_degenerate(self) -> bool:
        """True when phi < 0.3 — Constitution gate blocks self-modification at this level."""
        return self.phi_score < 0.3

    @property
    def is_multimodal(self) -> bool:
        return len(self.modalities_used) > 1


def phi_from_coherence(coherence: float) -> float:
    """HIHO 4x(1-x) kernel — trajectory quality score from raw coherence.

    Peaks at 1.0 when coherence = 0.5 (stable HIHO attractor). Returns 0.0
    at both extremes (c=0 or c=1 = degenerate basins). Clamps input to [0, 1].
    """
    c = max(0.0, min(1.0, coherence))
    return 4.0 * c * (1.0 - c)
