"""TidalPerturbationEnv — tidal flyby stress test on a bioelectric network.

Models a Fargion-style transient gravitational perturbation (arXiv:2606.17105):
a planetary-mass flyby raises the Lorentz-violation parameter ε(t) following a
Gaussian spike, perturbing the ThermodynamicGravity Otto cycle.  The bioelectric
network's gap-junction conductances respond; if connectivity collapses below the
HIHO threshold the episode ends (extinction event).

Physical chain:
    ThermodynamicGravity ε(t)  →  BioelectricNetwork conductance modulation
    →  percolation fraction (giant component)
    →  Higuchi FD of network mean potential  →  HIHO reward

Fisher metric collapse diagnostic: |dε/dt| > fisher_threshold triggers
early termination (sudden symmetry-breaking = catastrophic bifurcation).

References:
    Fargion et al. (2026): arXiv:2606.17105 — Gravitational tides and extinctions
    Isichei & Magueijo (2026): arXiv:2511.22221 — ThermodynamicGravity (PRL)
    HIHO stability principle: FD ∈ [1.3, 1.7] = healthy fractal dynamics
"""

from __future__ import annotations

import logging
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from cohezion.physics.bioelectric_model import BioelectricNetwork
from cohezion.physics.thermodynamic_gravity import OttoWorkLeg, ThermodynamicGravity

logger = logging.getLogger(__name__)

N_CELLS = 16
HIHO_LOW = 1.3
HIHO_HIGH = 1.7
FD_WINDOW = 20
COLLAPSE_GC_FRACTION = 0.10   # giant component < this → extinction
DEFAULT_EPS_MAX = 0.7          # peak Lorentz-violation during flyby
DEFAULT_SIGMA_STEPS = 30.0     # Gaussian half-width in steps
DEFAULT_FISHER_THRESHOLD = 0.05  # |dε/dt| above this = rapid symmetry break


class TidalPerturbationEnv(gym.Env):
    """16-cell bioelectric network stressed by a Gaussian tidal ε(t) spike.

    Observation (19D float32):
        - 16 normalised membrane potentials V_i ∈ [0, 1]
        - giant component fraction ∈ [0, 1]
        - current ε(t) ∈ [0, 1]
        - Higuchi FD of mean-potential history ∈ [1.0, 2.0]

    Action space: Discrete(32)
        -  0–15: strengthen gap junction for cell i (+0.05 conductance)
        - 16–31: weaken gap junction for cell i-16 (-0.10 conductance)

    Reward:
        +1.0 when Higuchi FD ∈ [1.3, 1.7]  (HIHO healthy dynamics)
        Linear penalty for deviation outside the window.
        Fisher collapse penalty: -2.0 when |dε/dt| > fisher_threshold.

    Termination:
        - Giant component fraction < 10% (bioelectric collapse)
        - Fisher metric collapse: rapid ε change beyond threshold (catastrophic)
        - step >= max_steps
    """

    metadata: dict[str, Any] = {"render_modes": []}

    def __init__(
        self,
        max_steps: int = 200,
        eps_max: float = DEFAULT_EPS_MAX,
        sigma_steps: float = DEFAULT_SIGMA_STEPS,
        fisher_threshold: float = DEFAULT_FISHER_THRESHOLD,
        seed: int | None = None,
    ) -> None:
        super().__init__()
        self.max_steps = max_steps
        self.eps_max = eps_max
        self.sigma_steps = sigma_steps
        self.fisher_threshold = fisher_threshold

        # Observation: 16 V_mem + gc_fraction + eps + FD
        obs_low = np.zeros(N_CELLS + 3, dtype=np.float32)
        obs_high = np.ones(N_CELLS + 3, dtype=np.float32)
        obs_high[N_CELLS + 2] = 2.0  # FD up to 2.0
        self.observation_space = spaces.Box(low=obs_low, high=obs_high, dtype=np.float32)
        self.action_space = spaces.Discrete(N_CELLS * 2)

        self._net = BioelectricNetwork(n_cells=N_CELLS)
        self._tg = ThermodynamicGravity()
        self._step_count: int = 0
        self._peak_step: int = max_steps // 2
        self._v_history: list[float] = []
        self._eps_prev: float = 0.0

        if seed is not None:
            self.np_random, _ = gym.utils.seeding.np_random(seed)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Physics helpers
    # ------------------------------------------------------------------

    def _eps_at(self, t: int) -> float:
        """Gaussian tidal spike ε(t) centred on peak_step."""
        return float(
            self.eps_max
            * np.exp(-((t - self._peak_step) ** 2) / (2.0 * self.sigma_steps ** 2))
        )

    def _update_thermodynamic_gravity(self, t: int) -> float:
        """Sync ThermodynamicGravity ε to the tidal spike value at step t."""
        eps = self._eps_at(t)
        self._tg.work_legs = [OttoWorkLeg(lorentz_violation=eps, entropy_flux=eps * 0.1)]
        return eps

    def _giant_component_fraction(self) -> float:
        """Fraction of cells in the largest connected component."""
        result = self._net.percolation_analysis(threshold=0.01)
        if not result.clusters:
            return 0.0
        largest = max(len(c) for c in result.clusters)
        return largest / N_CELLS

    def _higuchi_fd(self) -> float:
        if len(self._v_history) < 6:
            return 1.5
        try:
            from cohezion.inference.fractal_metrics import higuchi_fd

            return float(np.clip(higuchi_fd(self._v_history[-FD_WINDOW:]), 1.0, 2.0))
        except Exception:
            return 1.5

    def _make_obs(self, eps: float) -> np.ndarray:
        v_norm = np.clip((self._net.v_mem + 1.0) / 2.0, 0.0, 1.0).astype(np.float32)
        obs = np.empty(N_CELLS + 3, dtype=np.float32)
        obs[:N_CELLS] = v_norm
        obs[N_CELLS] = self._giant_component_fraction()
        obs[N_CELLS + 1] = float(eps)
        obs[N_CELLS + 2] = self._higuchi_fd()
        return obs

    # ------------------------------------------------------------------
    # Gymnasium interface
    # ------------------------------------------------------------------

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[np.ndarray, dict[str, Any]]:
        super().reset(seed=seed)
        # Re-initialise network with warm conductances and noisy potentials
        self._net = BioelectricNetwork(n_cells=N_CELLS)
        base_g = float(self.np_random.uniform(0.2, 0.5))
        self._net.set_uniform_conductance(base_g)
        self._net.v_mem += self.np_random.standard_normal(N_CELLS) * 0.05

        self._tg = ThermodynamicGravity()
        self._step_count = 0
        self._peak_step = int(self.np_random.integers(self.max_steps // 3, 2 * self.max_steps // 3))
        self._v_history = []
        eps = self._update_thermodynamic_gravity(0)
        self._eps_prev = eps
        return self._make_obs(eps), {}

    def step(
        self, action: int
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        # Apply agent action: strengthen or weaken a cell's junction
        if action < N_CELLS:
            # Strengthen: raise all conductances to this cell's neighbours
            for j in range(N_CELLS):
                if j != action:
                    g = float(self._net.conductance[action, j])
                    self._net.set_conductance(action, j, min(1.0, g + 0.05))
        else:
            cell = action - N_CELLS
            for j in range(N_CELLS):
                if j != cell:
                    g = float(self._net.conductance[cell, j])
                    self._net.set_conductance(cell, j, max(0.0, g - 0.10))

        # Tidal perturbation: ε(t) modulates network noise
        eps = self._update_thermodynamic_gravity(self._step_count)
        noise_scale = 0.02 + 0.08 * eps          # more noise near tidal peak
        self._net.v_mem += self.np_random.standard_normal(N_CELLS) * noise_scale
        self._net.v_mem = np.clip(self._net.v_mem, -1.0, 1.0)

        self._net.step()
        self._v_history.append(float(np.mean(self._net.v_mem)))
        self._step_count += 1

        fd = self._higuchi_fd()
        gc = self._giant_component_fraction()

        # Fisher metric collapse: |dε/dt|
        d_eps = abs(eps - self._eps_prev)
        self._eps_prev = eps
        fisher_collapse = d_eps > self.fisher_threshold

        # Reward
        if HIHO_LOW <= fd <= HIHO_HIGH:
            reward = 1.0
        else:
            dist = min(abs(fd - HIHO_LOW), abs(fd - HIHO_HIGH))
            reward = max(-1.0, 1.0 - 2.0 * dist)
        if fisher_collapse:
            reward -= 2.0

        # Termination
        terminated = gc < COLLAPSE_GC_FRACTION or fisher_collapse
        truncated = self._step_count >= self.max_steps

        info: dict[str, Any] = {
            "gc_fraction": gc,
            "fd": fd,
            "eps": eps,
            "d_eps": d_eps,
            "fisher_collapse": fisher_collapse,
            "acceleration_term": self._tg.acceleration_term(),
        }
        obs = self._make_obs(eps)
        return obs, reward, terminated, truncated, info
