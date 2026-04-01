"""Fiber bundle structure for the 12D axiomatic manifold.

The 12D manifold M¹² has a natural principal fiber bundle structure:

  P(B⁴, G) where G = SO(3)⁴

  Total space: M¹² = Space(3) × Field(3) × Control(3) × Precipitation(3)
  Base space:  B⁴  = (‖Space‖, ‖Field‖, ‖Control‖, ‖Precip‖)
  Fiber:       F⁸  = internal directions within each fabric

The base projection π maps each 12D point to its 4D "macroscopic" state
(how much of each fabric), while the fiber encodes the internal configuration
(which direction within each fabric).

The connection 1-form ω defines parallel transport — how internal states
evolve as agents move through the base space. The curvature Ω = dω + ω∧ω
measures field strength (deviation from HIHO flat connection).

References:
  - Nakahara (2003): Geometry, Topology and Physics, Ch. 9-10
  - Kobayashi & Nomizu (1963): Foundations of Differential Geometry
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np


logger = logging.getLogger(__name__)

# Fabric indices: which 3 of the 12 dimensions belong to each fabric
FABRIC_SLICES = {
    "Space": slice(0, 3),
    "Field": slice(3, 6),
    "Control": slice(6, 9),
    "Precipitation": slice(9, 12),
}

FABRIC_NAMES = list(FABRIC_SLICES.keys())


@dataclass
class FiberBundleState:
    """Decomposed state showing base-space and fiber components.

    Attributes
    ----------
    base : np.ndarray, shape (4,)
        Base-space coordinates (fabric norms): [‖Space‖, ‖Field‖, ‖Control‖, ‖Precip‖]
    fiber : np.ndarray, shape (4, 3)
        Fiber state: unit direction vectors within each fabric.
        fiber[i] = normalized direction in fabric i.
    raw : np.ndarray, shape (12,)
        Original 12D state.
    """

    base: np.ndarray
    fiber: np.ndarray
    raw: np.ndarray

    def to_dict(self) -> dict:
        """Serialize for API/SurrealDB."""
        return {
            "base": self.base.tolist(),
            "fiber": self.fiber.tolist(),
            "fabric_norms": {name: float(self.base[i]) for i, name in enumerate(FABRIC_NAMES)},
            "fabric_directions": {
                name: self.fiber[i].tolist() for i, name in enumerate(FABRIC_NAMES)
            },
        }


class FiberBundle:
    """Principal fiber bundle P(B⁴, SO(3)⁴) over the fabric base space.

    Provides decomposition, projection, parallel transport, and
    curvature computation for the 12D axiomatic manifold.
    """

    def __init__(self, dim: int = 12, n_fabrics: int = 4) -> None:
        if dim != n_fabrics * 3:
            raise ValueError(f"dim must be n_fabrics * 3, got {dim} and {n_fabrics}")
        self.dim = dim
        self.n_fabrics = n_fabrics
        self.fabric_dim = 3

    def decompose(self, state_12d: np.ndarray) -> FiberBundleState:
        """Decompose a 12D state into base-space + fiber components.

        Base: π(q) = (‖q_Space‖, ‖q_Field‖, ‖q_Control‖, ‖q_Precip‖)
        Fiber: normalized direction within each fabric triplet.
        """
        state = np.asarray(state_12d, dtype=np.float64)
        base = np.zeros(self.n_fabrics)
        fiber = np.zeros((self.n_fabrics, self.fabric_dim))

        for i, (name, sl) in enumerate(FABRIC_SLICES.items()):
            block = state[sl]
            norm = np.linalg.norm(block)
            base[i] = norm
            fiber[i] = block / norm if norm > 1e-15 else np.array([1.0, 0.0, 0.0])

        return FiberBundleState(base=base, fiber=fiber, raw=state.copy())

    def project_to_base(self, state_12d: np.ndarray) -> np.ndarray:
        """Canonical projection π: M¹² → B⁴.

        Returns the four fabric norms.
        """
        return self.decompose(state_12d).base

    def reconstruct(self, base: np.ndarray, fiber: np.ndarray) -> np.ndarray:
        """Reconstruct 12D state from base + fiber.

        state[fabric_i] = base[i] * fiber[i]
        """
        state = np.zeros(self.dim)
        for i, (_name, sl) in enumerate(FABRIC_SLICES.items()):
            direction = (
                fiber[i] / np.linalg.norm(fiber[i])
                if np.linalg.norm(fiber[i]) > 1e-15
                else np.array([1.0, 0.0, 0.0])
            )
            state[sl] = base[i] * direction
        return state

    def horizontal_component(self, state_12d: np.ndarray, tangent_12d: np.ndarray) -> np.ndarray:
        """Extract horizontal (base-space) component of a tangent vector.

        The horizontal component changes the fabric norms (base coordinates)
        without changing the internal directions (fiber coordinates).

        For a flat connection, the horizontal component of v at q is:
        v_H = sum_i (v_i · n_i) * n_i   (projection onto fabric directions)
        """
        decomp = self.decompose(state_12d)
        h = np.zeros(self.dim)

        for i, (_name, sl) in enumerate(FABRIC_SLICES.items()):
            v_block = tangent_12d[sl]
            n = decomp.fiber[i]  # Unit direction in this fabric
            # Horizontal part: component along the current fabric direction
            h[sl] = np.dot(v_block, n) * n

        return h

    def vertical_component(self, state_12d: np.ndarray, tangent_12d: np.ndarray) -> np.ndarray:
        """Extract vertical (fiber) component of a tangent vector.

        The vertical component changes internal directions without
        changing fabric norms. v_V = v - v_H.
        """
        return tangent_12d - self.horizontal_component(state_12d, tangent_12d)

    def connection_form(self, state_12d: np.ndarray, tangent_12d: np.ndarray) -> np.ndarray:
        """Evaluate the connection 1-form ω(v) at a point.

        For a flat connection: ω(v) = v_V (the vertical component).
        Returns a (4, 3) array — one so(3) element per fabric.

        For a non-flat connection (gauge field active), this would include
        the gauge potential A_μ. Currently implements the flat case.
        """
        v_vert = self.vertical_component(state_12d, tangent_12d)
        # Reshape into per-fabric Lie algebra elements
        return v_vert.reshape(self.n_fabrics, self.fabric_dim)

    def curvature_norm(
        self,
        state_12d: np.ndarray,
        v1: np.ndarray,
        v2: np.ndarray,
    ) -> float:
        """Compute the norm of the curvature 2-form Ω(v1, v2).

        For a flat connection, Ω = 0. Non-zero curvature indicates
        that parallel transport is path-dependent — the gauge field
        is active. This is the "force" that deflects agent trajectories.

        Approximated as ‖[ω(v1), ω(v2)]‖ (Lie bracket of connection values).
        """
        omega1 = self.connection_form(state_12d, v1)
        omega2 = self.connection_form(state_12d, v2)

        # Lie bracket [ω1, ω2] per fabric (cross product for so(3))
        total_curvature = 0.0
        for i in range(self.n_fabrics):
            bracket = np.cross(omega1[i], omega2[i])
            total_curvature += np.linalg.norm(bracket)

        return total_curvature

    def parallel_transport(
        self,
        fiber_state: np.ndarray,
        base_curve: np.ndarray,
    ) -> list[np.ndarray]:
        """Parallel transport fiber state along a base-space curve.

        For a flat connection, parallel transport preserves the fiber
        direction — the transported state is identical everywhere.

        Parameters
        ----------
        fiber_state : (4, 3)
            Initial fiber configuration (unit directions per fabric).
        base_curve : (n_steps, 4)
            Curve in base space to transport along.

        Returns
        -------
        list of (4, 3) fiber states at each point of the curve.
        """
        # For flat connection: fiber is constant along the curve
        return [fiber_state.copy() for _ in range(len(base_curve))]

    def fabric_curvature_per_fabric(
        self,
        trajectory_12d: np.ndarray,
    ) -> dict[str, float]:
        """Compute per-fabric curvature from a 12D trajectory.

        Measures how much the fiber direction changes along the trajectory
        for each fabric. High curvature = the agent's internal state
        is rotating rapidly within that fabric.
        """
        n = len(trajectory_12d)
        if n < 2:
            return {name: 0.0 for name in FABRIC_NAMES}

        curvatures = {}
        for i, name in enumerate(FABRIC_NAMES):
            sl = list(FABRIC_SLICES.values())[i]
            total_angle = 0.0
            for t in range(n - 1):
                d1 = trajectory_12d[t, sl]
                d2 = trajectory_12d[t + 1, sl]
                n1 = np.linalg.norm(d1)
                n2 = np.linalg.norm(d2)
                if n1 > 1e-15 and n2 > 1e-15:
                    cos_angle = np.clip(np.dot(d1, d2) / (n1 * n2), -1, 1)
                    total_angle += np.arccos(cos_angle)

            curvatures[name] = float(total_angle / max(n - 1, 1))

        return curvatures


__all__ = [
    "FABRIC_NAMES",
    "FABRIC_SLICES",
    "FiberBundle",
    "FiberBundleState",
]
