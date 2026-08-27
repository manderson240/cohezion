r"""Continuous-Time Riemannian Geodesic Flow Neural ODE Engine
============================================================
Solves continuous-time geodesic differential equations on Poincaré manifolds:
  d^2 x^k / dt^2 + \Gamma^k_{ij}(x) * (dx^i / dt) * (dx^j / dt) = 0

Allows smooth, continuous trajectory prediction across 12D, 256D, and 2048D spaces.
"""

from __future__ import annotations

from dataclasses import dataclass

from cohezion.contracts import PoincarePoint
from cohezion.physics.fiber_connection import FiberConnectionEngine
from cohezion.physics.poincare_manifold import PoincareManifoldND
from cohezion.physics.tensor_calculus import VectorTensor


@dataclass(frozen=True, slots=True)
class GeodesicState:
    position: PoincarePoint
    velocity: VectorTensor
    time: float


class GeodesicFlowODE:
    """Continuous-Time Geodesic Integrator using RK4 (Runge-Kutta 4th Order)."""

    @classmethod
    def acceleration(cls, position: PoincarePoint, velocity: VectorTensor) -> VectorTensor:
        r"""Compute geodesic acceleration a^k = -\Gamma^k_{ij}(x) v^i v^j in O(D) time."""
        cov_step = FiberConnectionEngine.covariant_derivative_step(velocity, position, velocity)
        return VectorTensor(tuple(-c for c in cov_step.components), is_covariant=False)

    @classmethod
    def step_rk4(cls, state: GeodesicState, dt: float = 0.01) -> GeodesicState:
        """Advance geodesic state by dt using RK4 numerical integration."""
        x = state.position
        v = state.velocity

        # k1
        a1 = cls.acceleration(x, v)
        v1_step = tuple(v.components[i] + 0.5 * dt * a1.components[i] for i in range(x.dim))
        x1_coords = tuple(x.coords[i] + 0.5 * dt * v.components[i] for i in range(x.dim))
        x1 = PoincareManifoldND.project(x1_coords, target_dim=x.dim)

        # k2
        v1 = VectorTensor(v1_step)
        a2 = cls.acceleration(x1, v1)
        v2_step = tuple(v.components[i] + 0.5 * dt * a2.components[i] for i in range(x.dim))
        x2_coords = tuple(x.coords[i] + 0.5 * dt * v1.components[i] for i in range(x.dim))
        x2 = PoincareManifoldND.project(x2_coords, target_dim=x.dim)

        # k3
        v2 = VectorTensor(v2_step)
        a3 = cls.acceleration(x2, v2)
        v3_step = tuple(v.components[i] + dt * a3.components[i] for i in range(x.dim))
        x3_coords = tuple(x.coords[i] + dt * v2.components[i] for i in range(x.dim))
        x3 = PoincareManifoldND.project(x3_coords, target_dim=x.dim)

        # k4
        v3 = VectorTensor(v3_step)
        a4 = cls.acceleration(x3, v3)

        # Combine RK4 for velocity and position
        new_v_coords = tuple(
            v.components[i]
            + (dt / 6.0)
            * (a1.components[i] + 2 * a2.components[i] + 2 * a3.components[i] + a4.components[i])
            for i in range(x.dim)
        )
        new_x_coords = tuple(
            x.coords[i]
            + (dt / 6.0)
            * (v.components[i] + 2 * v1.components[i] + 2 * v2.components[i] + v3.components[i])
            for i in range(x.dim)
        )

        new_x = PoincareManifoldND.project(new_x_coords, target_dim=x.dim)
        new_v = VectorTensor(new_v_coords)

        return GeodesicState(position=new_x, velocity=new_v, time=state.time + dt)
