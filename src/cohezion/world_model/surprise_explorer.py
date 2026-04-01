"""Surprise-driven exploration of the 12D manifold.

After the JEPA world model is trained, identifies high-surprise regions
where the model's predictions diverge from reality — these are the
most interesting regions to explore.

The self-improving loop:
  journey → SurrealDB → train world model → compute surprise →
  identify gaps → suggest exploration tasks → new journey → ...

This creates an autonomous curiosity mechanism grounded in physics:
agents naturally explore regions where the Lagrangian dynamics produce
unexpected behavior (e.g., near phase transition boundaries, high-curvature
regions of the gauge field, unstable fiber directions).

References:
    - Burda et al. (2019): Exploration by Random Network Distillation
    - Pathak et al. (2017): Curiosity-Driven Exploration
    - Our JEPA world model (M5) provides the prediction baseline
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class SurpriseRegion:
    """A region of the 12D manifold with high surprise score."""

    center: np.ndarray  # 12D center of the high-surprise region
    surprise_score: float  # Mean surprise in this region
    suggested_action: np.ndarray  # Direction to explore
    description: str  # Human-readable explanation
    physics_context: dict  # Gauge curvature, coherence, etc.

    def to_dict(self) -> dict:
        return {
            "center": self.center.tolist(),
            "surprise_score": self.surprise_score,
            "suggested_action": self.suggested_action.tolist(),
            "description": self.description,
            "physics_context": self.physics_context,
        }


class SurpriseExplorer:
    """Identifies and suggests exploration of high-surprise manifold regions.

    Parameters
    ----------
    world_model : JEPAWorldModel
        Trained JEPA world model for surprise computation.
    n_samples : int
        Number of sample points to probe (default: 100).
    top_k : int
        Number of high-surprise regions to return (default: 5).
    """

    def __init__(
        self,
        world_model: object | None = None,
        n_samples: int = 100,
        top_k: int = 5,
    ) -> None:
        self._world_model = world_model
        self.n_samples = n_samples
        self.top_k = top_k
        self._rng = np.random.default_rng(42)

    def set_world_model(self, world_model: object) -> None:
        """Set or update the world model."""
        self._world_model = world_model

    def scan_manifold(
        self,
        trajectory_history: list[np.ndarray] | None = None,
    ) -> list[SurpriseRegion]:
        """Scan the manifold for high-surprise regions.

        Probes sample points across the 12D space, computes surprise
        for random actions at each point, and returns the top-k most
        surprising regions.

        Parameters
        ----------
        trajectory_history : list of 12D arrays, optional
            Historical trajectory points. If provided, samples near
            these points (focused exploration). Otherwise samples
            uniformly.
        """
        if self._world_model is None:
            logger.warning("No world model set — returning empty regions")
            return []

        # Generate probe points
        if trajectory_history and len(trajectory_history) > 0:
            probes = self._generate_focused_probes(trajectory_history)
        else:
            probes = self._generate_uniform_probes()

        # Compute surprise at each probe
        surprises = []
        for probe in probes:
            action = self._rng.normal(0, 0.05, 12).astype(np.float32)
            next_state = probe + action  # Simple physics approximation

            try:
                surprise = self._world_model.surprise_score(probe, action, next_state)
            except Exception:
                surprise = 0.0

            surprises.append((probe, action, next_state, surprise))

        # Sort by surprise (descending)
        surprises.sort(key=lambda x: x[3], reverse=True)

        # Build top-k surprise regions
        regions = []
        for probe, action, next_state, surprise in surprises[: self.top_k]:
            # Compute physics context
            physics_ctx = self._compute_physics_context(probe)

            # Generate human-readable description
            desc = self._describe_region(probe, surprise, physics_ctx)

            regions.append(
                SurpriseRegion(
                    center=probe,
                    surprise_score=surprise,
                    suggested_action=action,
                    description=desc,
                    physics_context=physics_ctx,
                )
            )

        return regions

    def _generate_uniform_probes(self) -> list[np.ndarray]:
        """Generate uniformly distributed probe points."""
        return [self._rng.uniform(0.1, 0.9, 12).astype(np.float32) for _ in range(self.n_samples)]

    def _generate_focused_probes(self, history: list[np.ndarray]) -> list[np.ndarray]:
        """Generate probes near historical trajectories + some uniform.

        70% near history (exploit known interesting regions),
        30% uniform (explore unknown regions).
        """
        n_focused = int(self.n_samples * 0.7)
        n_uniform = self.n_samples - n_focused

        probes = []

        # Focused: perturb historical points
        for _ in range(n_focused):
            idx = self._rng.integers(len(history))
            base = history[idx]
            perturbation = self._rng.normal(0, 0.1, 12)
            probe = np.clip(base + perturbation, 0.0, 1.0).astype(np.float32)
            probes.append(probe)

        # Uniform: random points
        probes.extend(self._generate_uniform_probes()[:n_uniform])

        return probes

    def _compute_physics_context(self, point: np.ndarray) -> dict:
        """Compute physics quantities at a manifold point."""
        try:
            from cohezion.physics.fiber_bundle import FiberBundle
            from cohezion.physics.gauge_theory import FourFabricGauge
            from cohezion.physics.spinor import SpinorState

            fb = FiberBundle()
            decomp = fb.decompose(point.astype(np.float64))

            gauge = FourFabricGauge()
            gauge.set_from_12d_state(point.astype(np.float64))

            spinor = SpinorState.from_coherence_values(
                float(np.clip(point[6], 0, 1)),
                float(np.clip(point[7], 0, 1)),
            )

            return {
                "fiber_base": decomp.base.tolist(),
                "yang_mills_action": gauge.yang_mills_action(),
                "is_hiho": gauge.is_hiho(tol=0.1),
                "charge_polarity": spinor.charge_polarity,
                "coherence": spinor.coherence,
                "hiho_deviation": spinor.hiho_deviation,
            }
        except Exception as e:
            return {"error": str(e)}

    def _describe_region(self, point: np.ndarray, surprise: float, physics: dict) -> str:
        """Generate human-readable description of a surprise region."""
        parts = [f"Surprise={surprise:.4f}"]

        if physics.get("is_hiho"):
            parts.append("near HIHO equilibrium")
        elif physics.get("hiho_deviation", 1) > 0.3:
            parts.append("far from HIHO (high deviation)")

        ym = physics.get("yang_mills_action", 0)
        if ym > 0.01:
            parts.append(f"strong gauge field (YM={ym:.4f})")

        charge = physics.get("charge_polarity", 0)
        if abs(charge) > 0.5:
            parts.append(f"strong charge polarity ({charge:.2f})")

        return "; ".join(parts)

    def suggest_exploration_tasks(self, regions: list[SurpriseRegion] | None = None) -> list[dict]:
        """Convert surprise regions into actionable exploration tasks.

        Returns a list of task descriptions that can be fed back into
        the compound executor to explore these regions.
        """
        if regions is None:
            regions = self.scan_manifold()

        tasks = []
        for i, region in enumerate(regions):
            tasks.append(
                {
                    "task_id": f"explore_{i}",
                    "type": "manifold_exploration",
                    "target_state": region.center.tolist(),
                    "suggested_action": region.suggested_action.tolist(),
                    "surprise_score": region.surprise_score,
                    "description": f"Explore high-surprise region: {region.description}",
                    "priority": max(0, min(1, region.surprise_score)),
                }
            )

        return tasks


__all__ = ["SurpriseExplorer", "SurpriseRegion"]
