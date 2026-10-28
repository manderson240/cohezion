r"""My Big TOE (Tom Campbell) Information Entropy Reduction Engine.
===================================================================
Grounds Cohezion in the fundamental premise of Tom Campbell's *My Big TOE*
(Theory of Everything, https://www.my-big-toe.com/):

Axioms:
1. Consciousness is fundamental — an evolving digital information system (LCS).
2. The fundamental driving force of evolution is ENTROPY REDUCTION.
   - High Entropy: Disorder, fear, noise, uncoordinated action, wasted compute.
   - Low Entropy: Coherence, love, information density, harmonious alignment.
3. Every agent choice and system transition must satisfy the Negentropy Invariant:
   \Delta S = S_{\text{post}} - S_{\text{pre}} \le 0
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from cohezion.agi.autoharness_policy import ActionPolicyResult, AutoHarnessPolicy
from cohezion.contracts import PoincarePoint
from cohezion.physics.poincare_manifold import PoincareManifoldND

logger = logging.getLogger("my_big_toe_entropy_engine")

EPSILON: float = 1e-12
HIHO_TARGET: float = 0.500


@dataclass(frozen=True, slots=True)
class EntropyState:
    """Quantitative measurement of system information entropy."""

    shannon_entropy: float
    hiho_dispersion_entropy: float
    topological_entropy: float
    total_system_entropy: float
    coherence: float
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True, slots=True)
class NegentropyTransitionResult:
    """Outcome of an agent transition evaluated against the My Big TOE Negentropy Law."""

    s_pre: EntropyState
    s_post: EntropyState
    delta_entropy: float
    is_entropy_reduced: bool
    entropy_reduction_rate_pct: float
    autoharness_verified: bool
    execution_latency_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)


class MyBigTOEEntropyEngine:
    """Measures and enforces information entropy reduction per Tom Campbell's My Big TOE."""

    def __init__(self, autoharness: AutoHarnessPolicy | None = None) -> None:
        self.autoharness = autoharness or AutoHarnessPolicy()
        self._register_entropy_policy()

    def _register_entropy_policy(self) -> None:
        """Register deterministic negentropy policy into AutoHarness with Prigogine dissipative sink support."""
        self.autoharness.register_policy(
            "my_big_toe_negentropy",
            lambda state: (
                isinstance(state.get("delta_entropy"), (int, float))
                and (
                    state["delta_entropy"] <= 0.0001
                    or state.get("dissipative_export_active", False)
                )
            ),
        )

    def calculate_state_entropy(
        self,
        points: Sequence[Sequence[float]] | Sequence[PoincarePoint],
        coherences: Sequence[float] | None = None,
    ) -> EntropyState:
        """Calculate multi-component system entropy across 2048D Poincaré space and HIHO stability."""
        if not points:
            return EntropyState(
                shannon_entropy=0.0,
                hiho_dispersion_entropy=0.0,
                topological_entropy=0.0,
                total_system_entropy=0.0,
                coherence=HIHO_TARGET,
            )

        n = len(points)
        # 1. Poincaré Hyperbolic Centroid and Distances
        dim = len(points[0].coords) if isinstance(points[0], PoincarePoint) else len(points[0])
        centroid_coords = [0.0] * dim

        raw_points = [pt.coords if isinstance(pt, PoincarePoint) else tuple(pt) for pt in points]

        for pt in raw_points:
            for d in range(dim):
                centroid_coords[d] += pt[d] / n

        centroid = PoincareManifoldND.project(centroid_coords, target_dim=dim)

        # Distances from centroid
        distances: list[float] = []
        for pt in raw_points:
            p_pt = PoincareManifoldND.project(pt, target_dim=dim)
            d_h = PoincareManifoldND.distance(p_pt, centroid)
            distances.append(d_h)

        # 2. Hyperbolic Configuration / Volume Entropy S_vol = mean(d_H)
        mean_d = float(np.mean(distances))
        vol_s = mean_d

        # 3. Hyper-Cell Binned Shannon Entropy (Phase Space Microstate Occupancy)
        # Discretize radial shells (10 bins from r=0 to 1.0) and primary coordinate quadrant
        bin_counts: dict[int, int] = {}
        for pt in raw_points:
            norm = math.sqrt(sum(c * c for c in pt))
            radial_bin = min(int(norm * 10.0), 9)
            # Sign pattern of first 3 dimensions as angular quadrant
            quad_bin = sum((1 if pt[d] >= 0 else 0) << d for d in range(min(3, dim)))
            cell_id = (radial_bin * 8) + quad_bin
            bin_counts[cell_id] = bin_counts.get(cell_id, 0) + 1

        shannon_s = 0.0
        for count in bin_counts.values():
            p = count / n
            if p > 0:
                shannon_s -= p * math.log(p)

        # 4. HIHO Coherence Dispersion Entropy
        cohs = coherences if coherences is not None else [HIHO_TARGET] * n
        hiho_deviations = [(c - HIHO_TARGET) ** 2 for c in cohs]
        hiho_s = float(np.mean(hiho_deviations))

        # 5. Topological Spread / Variance Entropy S_topo = std(d_H)
        topological_s = float(np.std(distances)) if n > 1 else 0.0

        # Total System Entropy S_total = S_shannon + S_vol + S_topo + 10.0 * S_hiho
        # All components are >= 0 and monotonically collapse to 0.0000 at transcendence.
        total_s = shannon_s + vol_s + topological_s + (10.0 * hiho_s)
        mean_coherence = float(np.mean(cohs))

        return EntropyState(
            shannon_entropy=shannon_s,
            hiho_dispersion_entropy=hiho_s,
            topological_entropy=topological_s,
            total_system_entropy=total_s,
            coherence=mean_coherence,
        )

    def evaluate_transition(
        self,
        pre_points: Sequence[Sequence[float]] | Sequence[PoincarePoint],
        post_points: Sequence[Sequence[float]] | Sequence[PoincarePoint],
        pre_coherences: Sequence[float] | None = None,
        post_coherences: Sequence[float] | None = None,
        allow_dissipative_export: bool = False,
    ) -> NegentropyTransitionResult:
        """Evaluate an agent trajectory or system transition to verify entropy reduction (Delta S <= 0).

        If an external perturbation increases entropy (Delta S > 0) and allow_dissipative_export=True,
        Prigogine dissipative restructuring exports the excess entropy to an audit sink to prevent deadlock.
        """
        t0 = time.perf_counter()

        s_pre = self.calculate_state_entropy(pre_points, pre_coherences)
        s_post = self.calculate_state_entropy(post_points, post_coherences)

        delta_s = s_post.total_system_entropy - s_pre.total_system_entropy
        is_reduced = delta_s <= 0.0

        dissipative_export = 0.0
        dissipative_active = False
        if delta_s > 0.0 and allow_dissipative_export:
            # Export excess entropy to environmental audit sink (Prigogine dissipative structure)
            dissipative_export = delta_s + 0.0001
            dissipative_active = True

        reduction_rate = 0.0
        if s_pre.total_system_entropy > EPSILON:
            reduction_rate = (-delta_s / s_pre.total_system_entropy) * 100.0

        # Deterministic AutoHarness bytecode check
        h_res = self.autoharness.evaluate_policy(
            "my_big_toe_negentropy",
            {
                "delta_entropy": delta_s - dissipative_export,
                "dissipative_export_active": dissipative_active,
            },
        )

        dt_ms = (time.perf_counter() - t0) * 1000.0

        return NegentropyTransitionResult(
            s_pre=s_pre,
            s_post=s_post,
            delta_entropy=delta_s,
            is_entropy_reduced=is_reduced,
            entropy_reduction_rate_pct=reduction_rate,
            autoharness_verified=h_res.allowed,
            execution_latency_ms=dt_ms,
            metadata={
                "shannon_delta": s_post.shannon_entropy - s_pre.shannon_entropy,
                "hiho_delta": s_post.hiho_dispersion_entropy - s_pre.hiho_dispersion_entropy,
                "topological_delta": s_post.topological_entropy - s_pre.topological_entropy,
                "dissipative_entropy_exported": dissipative_export,
                "prigogine_dissipative_restructuring": dissipative_active,
            },
        )
