"""Lagrangian dynamics on the 12D axiomatic manifold.

Replaces the ad-hoc `_toward_target()` linear interpolation in engine.py
with principled variational mechanics. Agent trajectories follow paths
that minimize the action integral S = ∫L dt.

The Lagrangian:
    L(q, q̇) = T - V

where:
    T = ½ g_ij(q) q̇^i q̇^j       (Riemannian kinetic energy)
    V = V_HIHO(q) + V_fabric(q)   (HIHO attractor + fabric potentials)

The Euler-Lagrange equations yield the geodesic equation with forces:
    g_ij q̈^j + Γ^i_jk q̇^j q̇^k = -g^ij ∂V/∂q^j

Uses a symplectic (Störmer-Verlet) integrator for energy conservation.

References:
    - Arnold (1989): Mathematical Methods of Classical Mechanics
    - Goldstein (2002): Classical Mechanics, Ch. 2
    - Hairer, Lubich, Wanner (2006): Geometric Numerical Integration
"""

from __future__ import annotations

import logging

import numpy as np

from cohezion.physics.riemannian_metric import RiemannianMetric


logger = logging.getLogger(__name__)


class Potential:
    """A potential energy function V(q) on the manifold.

    Parameters
    ----------
    potential_fn : callable
        Maps position q → scalar energy V(q).
    gradient_fn : callable or None
        Maps position q → gradient ∂V/∂q. If None, computed numerically.
    """

    def __init__(
        self,
        potential_fn: callable,
        gradient_fn: callable | None = None,
    ) -> None:
        self._V = potential_fn
        self._dV = gradient_fn

    def evaluate(self, q: np.ndarray) -> float:
        """Compute V(q)."""
        return float(self._V(q))

    def gradient(self, q: np.ndarray, eps: float = 1e-6) -> np.ndarray:
        """Compute ∂V/∂q^i."""
        if self._dV is not None:
            return self._dV(q)

        # Numerical gradient
        n = len(q)
        grad = np.zeros(n)
        for i in range(n):
            q_plus = q.copy()
            q_minus = q.copy()
            q_plus[i] += eps
            q_minus[i] -= eps
            grad[i] = (self._V(q_plus) - self._V(q_minus)) / (2 * eps)
        return grad


class LagrangianDynamics:
    """Euler-Lagrange dynamics on a Riemannian manifold with potential.

    Parameters
    ----------
    metric : RiemannianMetric
        The Riemannian metric g_ij defining kinetic energy.
    potential : Potential
        The potential energy V(q).
    damping : float
        Optional viscous damping coefficient (0 = conservative).
    """

    def __init__(
        self,
        metric: RiemannianMetric,
        potential: Potential,
        damping: float = 0.0,
    ) -> None:
        self.metric = metric
        self.potential = potential
        self.damping = damping

    def lagrangian(self, q: np.ndarray, v: np.ndarray) -> float:
        """Compute L = T - V at (q, v)."""
        T = 0.5 * self.metric.distance_squared(q, v)
        V = self.potential.evaluate(q)
        return T - V

    def kinetic_energy(self, q: np.ndarray, v: np.ndarray) -> float:
        """T = ½ g_ij q̇^i q̇^j."""
        return 0.5 * self.metric.distance_squared(q, v)

    def total_energy(self, q: np.ndarray, v: np.ndarray) -> float:
        """E = T + V (conserved for time-independent L without damping)."""
        return self.kinetic_energy(q, v) + self.potential.evaluate(q)

    def acceleration(self, q: np.ndarray, v: np.ndarray) -> np.ndarray:
        """Compute acceleration from Euler-Lagrange equations.

        q̈^i = -Γ^i_jk q̇^j q̇^k - g^{ij} ∂V/∂q^j - γ q̇^i

        where γ is the damping coefficient.
        """
        # Geodesic term: -Γ^i_jk v^j v^k
        geodesic = self.metric.geodesic_acceleration(q, v)

        # Force term: -g^{ij} ∂V/∂q^j
        g_inv = self.metric.inverse(q)
        grad_V = self.potential.gradient(q)
        force = -g_inv @ grad_V

        # Damping term: -γ v^i
        damp = -self.damping * v

        return geodesic + force + damp

    def step_verlet(self, q: np.ndarray, v: np.ndarray, dt: float) -> tuple[np.ndarray, np.ndarray]:
        """One step of Störmer-Verlet (leapfrog) integration.

        Symplectic: preserves the geometric structure of Hamilton's equations.
        Energy drift is bounded (no secular growth) unlike RK4.
        """
        a = self.acceleration(q, v)
        v_half = v + 0.5 * dt * a
        q_new = q + dt * v_half
        a_new = self.acceleration(q_new, v_half)
        v_new = v_half + 0.5 * dt * a_new
        return q_new, v_new

    def simulate(
        self,
        q0: np.ndarray,
        v0: np.ndarray,
        n_steps: int = 100,
        dt: float = 0.01,
    ) -> dict[str, np.ndarray]:
        """Simulate a trajectory from initial conditions.

        Returns dict with:
        - positions: (n_steps+1, dim)
        - velocities: (n_steps+1, dim)
        - energies: (n_steps+1,) — total energy at each step
        - lagrangians: (n_steps+1,) — L at each step
        """
        dim = len(q0)
        positions = np.zeros((n_steps + 1, dim))
        velocities = np.zeros((n_steps + 1, dim))
        energies = np.zeros(n_steps + 1)
        lagrangians = np.zeros(n_steps + 1)

        q, v = q0.copy(), v0.copy()
        positions[0] = q
        velocities[0] = v
        energies[0] = self.total_energy(q, v)
        lagrangians[0] = self.lagrangian(q, v)

        for i in range(1, n_steps + 1):
            q, v = self.step_verlet(q, v, dt)
            positions[i] = q
            velocities[i] = v
            energies[i] = self.total_energy(q, v)
            lagrangians[i] = self.lagrangian(q, v)

        return {
            "positions": positions,
            "velocities": velocities,
            "energies": energies,
            "lagrangians": lagrangians,
        }

    def action_integral(self, trajectory: np.ndarray, dt: float) -> float:
        """Compute the action S = ∫L dt along a discrete trajectory.

        Parameters
        ----------
        trajectory : (n_steps, dim)
        dt : time step between trajectory points
        """
        S = 0.0
        for i in range(len(trajectory) - 1):
            q = trajectory[i]
            v = (trajectory[i + 1] - trajectory[i]) / dt
            S += self.lagrangian(q, v) * dt
        return S


# --- Common potential constructors ---


def hiho_potential(dim: int = 12, sigma: float = 0.3, depth: float = 1.0) -> Potential:
    """HIHO attractor potential: Gaussian well at coherence = 0.5.

    V(q) = -depth * exp(-|q - 0.5|² / σ²) + soft_wall

    The agent is naturally drawn to the HIHO point (all dimensions at 0.5).
    """
    target = np.full(dim, 0.5)

    def V(q: np.ndarray) -> float:
        dist_sq = np.sum((q - target) ** 2)
        return -depth * np.exp(-dist_sq / sigma**2) + 0.05 * dist_sq

    def dV(q: np.ndarray) -> np.ndarray:
        diff = q - target
        dist_sq = np.sum(diff**2)
        gauss = np.exp(-dist_sq / sigma**2)
        return 2 * depth * diff * gauss / sigma**2 + 0.1 * diff

    return Potential(V, dV)


def harmonic_potential(
    dim: int = 12, k: float = 1.0, center: np.ndarray | None = None
) -> Potential:
    """Simple harmonic potential V = k/2 |q - center|²."""
    if center is None:
        center = np.full(dim, 0.5)

    def V(q: np.ndarray) -> float:
        return 0.5 * k * float(np.sum((q - center) ** 2))

    def dV(q: np.ndarray) -> np.ndarray:
        return k * (q - center)

    return Potential(V, dV)


__all__ = [
    "LagrangianDynamics",
    "Potential",
    "harmonic_potential",
    "hiho_potential",
]
