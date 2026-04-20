"""Hamiltonian dynamics for FLUME latent space simulation.

Replaces cosmetic jitter with real physics: potential energy gradients,
Langevin thermal noise, and configurable potential landscapes.

The double-well potential creates energy minima at HIHO target (0.5)
with barriers that prevent trivial collapse.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np


if TYPE_CHECKING:
    from collections.abc import Callable


logger = logging.getLogger(__name__)


class PotentialType(Enum):
    """Available potential energy landscapes."""

    DOUBLE_WELL = "double_well"
    HARMONIC = "harmonic"
    HIHO_WELL = "hiho_well"


class HamiltonianDynamics:
    """Langevin dynamics on configurable potential energy surfaces.

    Implements overdamped Langevin:
        dz = -dt * grad(V(z)) + sqrt(2*T*dt) * noise

    Parameters
    ----------
    potential : PotentialType or callable
        Potential energy function. If callable, must accept ndarray and
        return (energy, gradient) tuple.
    dt : float
        Integration timestep (default 0.01).
    temperature : float
        Thermal noise magnitude (default 0.01).
    target : float
        Center of the potential well (default 0.5, HIHO target).
    """

    def __init__(
        self,
        potential: PotentialType | Callable = PotentialType.DOUBLE_WELL,
        dt: float = 0.01,
        temperature: float = 0.01,
        target: float = 0.5,
    ) -> None:
        self.dt = dt
        self.temperature = temperature
        self.target = target

        if callable(potential) and not isinstance(potential, PotentialType):
            self._potential_fn = potential
        elif potential == PotentialType.DOUBLE_WELL:
            self._potential_fn = self._double_well
        elif potential == PotentialType.HARMONIC:
            self._potential_fn = self._harmonic
        elif potential == PotentialType.HIHO_WELL:
            self._potential_fn = self._hiho_well
        else:
            raise ValueError(f"Unknown potential: {potential}")

    def step(self, z: np.ndarray, rng: np.random.Generator | None = None) -> np.ndarray:
        """Advance one timestep of Langevin dynamics.

        Parameters
        ----------
        z : np.ndarray
            Current state, shape [n_agents, z_dim] or [z_dim].
        rng : np.random.Generator, optional
            Random number generator.

        Returns
        -------
        np.ndarray
            Updated state, same shape as input.
        """
        if rng is None:
            rng = np.random.default_rng()

        _energy, grad = self._potential_fn(z)
        noise = rng.normal(0, 1, z.shape).astype(z.dtype)
        noise_scale = np.sqrt(2 * self.temperature * self.dt)

        z_new = z - self.dt * grad + noise_scale * noise
        return z_new.astype(np.float32)

    def simulate(
        self,
        z0: np.ndarray,
        epochs: int,
        seed: int = 42,
        clamp: tuple[float, float] = (-2.0, 2.0),
    ) -> np.ndarray:
        """Run multiple epochs of dynamics.

        Parameters
        ----------
        z0 : np.ndarray
            Initial state [n_agents, z_dim].
        epochs : int
            Number of integration steps.
        seed : int
            RNG seed.
        clamp : tuple
            Min/max clamp values.

        Returns
        -------
        np.ndarray
            Final state.
        """
        rng = np.random.default_rng(seed)
        z = z0.copy()

        for _ in range(epochs):
            z = self.step(z, rng)
            z = np.clip(z, clamp[0], clamp[1])

        return z

    def simulate_with_trajectory(
        self,
        z0: np.ndarray,
        epochs: int,
        checkpoint_interval: int = 10,
        seed: int = 42,
    ) -> list[tuple[int, np.ndarray]]:
        """Simulate and record trajectory checkpoints.

        Returns list of (epoch, state_snapshot) tuples.
        """
        rng = np.random.default_rng(seed)
        z = z0.copy()
        trajectory = [(0, z.copy())]

        for epoch in range(1, epochs + 1):
            z = self.step(z, rng)
            z = np.clip(z, -2.0, 2.0)

            if epoch % checkpoint_interval == 0 or epoch == epochs:
                trajectory.append((epoch, z.copy()))

        return trajectory

    def energy(self, z: np.ndarray) -> np.ndarray:
        """Compute potential energy at position z."""
        e, _ = self._potential_fn(z)
        return e

    def _double_well(self, z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Double-well potential centered at target.

        V(x) = (x - target)^2 * ((x - target)^2 - a^2)
        grad = 4(x - target) * ((x - target)^2 - a^2 / 2)

        Creates minima at target +/- a/sqrt(2), with barrier at target.
        """
        x = z - self.target
        a_sq = 0.09  # a = 0.3, wells at +-0.21 from target
        energy = x * x * (x * x - a_sq)
        gradient = 4.0 * x * (x * x - a_sq / 2.0)
        return energy, gradient

    def _harmonic(self, z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Simple harmonic potential V(x) = k/2 * (x - target)^2."""
        k = 1.0
        x = z - self.target
        energy = 0.5 * k * x * x
        gradient = k * x
        return energy, gradient

    def _hiho_well(self, z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """HIHO stability well: Gaussian well at 0.5 with soft walls.

        V(x) = -exp(-(x-0.5)^2/sigma^2) + wall_penalty
        This creates a strong attractor at 0.5 with bounded domain.
        """
        sigma_sq = 0.1
        x = z - self.target
        gauss = np.exp(-x * x / sigma_sq)
        energy = -gauss + 0.1 * x * x  # Gaussian well + soft walls
        gradient = 2.0 * x * gauss / sigma_sq + 0.2 * x
        return energy, gradient
