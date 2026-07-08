"""LatentGravityNavigator — N-body gravitational potential over journey waypoints.

The SWIFT/CarbonEngine analog for Cohezion (vault research
``swift-carbonengine-vacuum-analog.md``, 2026-07-02): neither external engine is
integrable (SWIFT is a C binary with read-only Python I/O; CarbonEngine is
Perforce/Windows-locked), but SWIFT's gravity-solver role over the 12D FLUME
manifold is fully served by a softened N-body potential on a KDTree — verified
<1 ms for 50 particles in 12D, no new dependencies.

Historical waypoints act as mass particles (mass = vacuum-topology l2_norm by
default); dense clusters of prior trajectories become gravity wells — learned
attractors that can bias JEPA step direction and are rendered in the Genesis
Vacuum tab as potential-depth per VizPoint.
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import KDTree

from cohezion.flume.vacuum_topology import VacuumLabel, VacuumTopologyClassifier


class LatentGravityNavigator:
    """Softened N-body gravity over 12D journey waypoints.

    Usage::

        nav = LatentGravityNavigator()
        nav.update_field(waypoints)               # list of (12,) arrays
        phi, force = nav.potential_and_force(x)   # scalar, (12,) vector
        label = nav.vacuum_label(x)               # instanton / soliton / trivial
    """

    def __init__(self, k_neighbours: int = 20, softening: float = 0.1) -> None:
        self.k = k_neighbours
        self.eps = softening
        self.classifier = VacuumTopologyClassifier()
        self._waypoints: np.ndarray | None = None  # (N, 12)
        self._masses: np.ndarray | None = None  # (N,)
        self._tree: KDTree | None = None

    @property
    def n_particles(self) -> int:
        return 0 if self._waypoints is None else int(self._waypoints.shape[0])

    def update_field(
        self,
        waypoints: list[np.ndarray],
        masses: list[float] | None = None,
    ) -> None:
        """Ingest journey waypoints and their masses (vacuum l2_norm default)."""
        if not waypoints:
            self._waypoints = None
            self._masses = None
            self._tree = None
            return
        self._waypoints = np.vstack([np.asarray(w, dtype=np.float64) for w in waypoints])
        if masses is not None:
            if len(masses) != len(waypoints):
                raise ValueError(
                    f"masses length {len(masses)} != waypoints length {len(waypoints)}"
                )
            self._masses = np.asarray(masses, dtype=np.float64)
        else:
            self._masses = np.array([self.classifier.classify(w).l2_norm for w in self._waypoints])
        self._tree = KDTree(self._waypoints)

    def potential_and_force(self, position_12d: np.ndarray) -> tuple[float, np.ndarray]:
        """Return gravitational potential Φ and force F = -∇Φ at *position_12d*.

        Φ = -Σ m_i / max(r_i, ε) over the k nearest waypoints (softened Plummer
        style); the force points toward mass concentrations. Empty field →
        (0.0, zeros(12)).
        """
        position_12d = np.asarray(position_12d, dtype=np.float64)
        if self._tree is None or self._waypoints is None or self._masses is None:
            return 0.0, np.zeros(12)
        k = min(self.k, self.n_particles)
        dists, idx = self._tree.query(position_12d, k=k)
        dists = np.atleast_1d(dists)
        idx = np.atleast_1d(idx)
        r = np.maximum(dists, self.eps)
        m = self._masses[idx]
        potential = float(-np.sum(m / r))
        offsets = self._waypoints[idx] - position_12d  # (k, 12)
        force = (m / r**3) @ offsets  # Σ m_i (r_i - x)/r³ — vectorized
        return potential, np.asarray(force, dtype=np.float64)

    def vacuum_label(self, position_12d: np.ndarray) -> VacuumLabel:
        """Classify *position_12d* as an exotic vacuum object."""
        return self.classifier.classify(np.asarray(position_12d, dtype=np.float64))
