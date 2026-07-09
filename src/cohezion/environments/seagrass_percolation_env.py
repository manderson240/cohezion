"""SeagrassPercolationEnv — seagrass meadow percolation environment.

Models a 4×4 grid of seagrass patches. Percolation threshold governs
meadow-scale connectivity; HIHO fractal dimension serves as the reward signal.

Physical analogues:
- Gap junction percolation in BioelectricNetwork (bioelectric_model.py)
- HIHO phase transition: FD ∈ [1.3, 1.7] = healthy fractal dynamics
- Allen Coral Atlas: remote-sensing patch state classification

References:
    - Duarte et al. (2022): Seagrass meadow connectivity and resilience
    - HIHO stability principle (COHEZION_CHARTER.md): FD ∈ [1.3, 1.7]
"""

from __future__ import annotations

import logging
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces


logger = logging.getLogger(__name__)

N_PATCHES = 16
GRID_SIDE = 4
CONNECT_THRESHOLD = 0.5  # health > this means patch contributes to connectivity
FD_WINDOW = 20  # steps of mean-health history for Higuchi FD
HIHO_LOW = 1.3
HIHO_HIGH = 1.7
COLLAPSE_FRACTION = 0.10  # giant component < this → meadow collapse → episode ends


class SeagrassPercolationEnv(gym.Env):
    """4×4 seagrass patch meadow with percolation-based HIHO reward.

    Observation (18D float32):
        - 16 patch health values ∈ [0, 1]
        - giant component fraction ∈ [0, 1]
        - Higuchi FD of mean-health history ∈ [1.0, 2.0]

    Action space: Discrete(32)
        - 0-15:  protect patch i (health += 0.1)
        - 16-31: disturb patch i-16 (health -= 0.2)

    Reward:
        +1.0 when Higuchi FD ∈ [1.3, 1.7]  (HIHO health range)
        Linear penalty for deviation otherwise

    Termination:
        Giant component < 10% of patches OR step >= max_steps
    """

    metadata: dict[str, Any] = {"render_modes": []}

    def __init__(self, max_steps: int = 200, seed: int | None = None) -> None:
        super().__init__()
        self.max_steps = max_steps

        obs_low = np.zeros(N_PATCHES + 2, dtype=np.float32)
        obs_high = np.ones(N_PATCHES + 2, dtype=np.float32)
        obs_high[-1] = 2.0  # FD ranges up to 2.0
        self.observation_space = spaces.Box(low=obs_low, high=obs_high, dtype=np.float32)
        self.action_space = spaces.Discrete(N_PATCHES * 2)

        # Precompute 4-neighbor adjacency (4×4 grid)
        self._neighbors: list[list[int]] = []
        for idx in range(N_PATCHES):
            row, col = divmod(idx, GRID_SIDE)
            nbrs: list[int] = []
            if row > 0:
                nbrs.append((row - 1) * GRID_SIDE + col)
            if row < GRID_SIDE - 1:
                nbrs.append((row + 1) * GRID_SIDE + col)
            if col > 0:
                nbrs.append(row * GRID_SIDE + col - 1)
            if col < GRID_SIDE - 1:
                nbrs.append(row * GRID_SIDE + col + 1)
            self._neighbors.append(nbrs)

        self._patch_health: np.ndarray = np.ones(N_PATCHES, dtype=np.float32)
        self._health_history: list[float] = []
        self._step_count: int = 0

        if seed is not None:
            self.np_random, _ = gym.utils.seeding.np_random(seed)  # type: ignore[attr-defined]

    def _giant_component_fraction(self) -> float:
        """Union-find percolation on 4×4 grid; mirrors BioelectricNetwork logic."""
        parent = list(range(N_PATCHES))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for i in range(N_PATCHES):
            if self._patch_health[i] > CONNECT_THRESHOLD:
                for j in self._neighbors[i]:
                    if self._patch_health[j] > CONNECT_THRESHOLD:
                        union(i, j)

        alive = [i for i in range(N_PATCHES) if self._patch_health[i] > CONNECT_THRESHOLD]
        if not alive:
            return 0.0
        roots = [find(i) for i in alive]
        largest = max(roots.count(r) for r in set(roots))
        return largest / N_PATCHES

    def _higuchi_fd(self) -> float:
        if len(self._health_history) < 6:
            return 1.5  # neutral before window fills
        try:
            from cohezion.inference.fractal_metrics import higuchi_fd

            return float(np.clip(higuchi_fd(self._health_history[-FD_WINDOW:]), 1.0, 2.0))
        except Exception:
            return 1.5

    def _make_obs(self) -> np.ndarray:
        obs = np.empty(N_PATCHES + 2, dtype=np.float32)
        obs[:N_PATCHES] = self._patch_health
        obs[N_PATCHES] = self._giant_component_fraction()
        obs[N_PATCHES + 1] = self._higuchi_fd()
        return obs

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[np.ndarray, dict[str, Any]]:
        super().reset(seed=seed)
        # Start with a partially established meadow so connectivity varies
        self._patch_health = self.np_random.uniform(0.4, 1.0, size=N_PATCHES).astype(np.float32)
        self._health_history = []
        self._step_count = 0
        return self._make_obs(), {}

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        if action < N_PATCHES:
            self._patch_health[action] = min(1.0, float(self._patch_health[action]) + 0.1)
        else:
            patch = action - N_PATCHES
            self._patch_health[patch] = max(0.0, float(self._patch_health[patch]) - 0.2)

        # Small stochastic drift (grazing, nutrient flux, temperature)
        self._patch_health = np.clip(
            self._patch_health + self.np_random.normal(0.0, 0.02, N_PATCHES),
            0.0,
            1.0,
        ).astype(np.float32)

        self._health_history.append(float(np.mean(self._patch_health)))
        self._step_count += 1

        fd = self._higuchi_fd()
        gc = self._giant_component_fraction()

        # HIHO reward: full +1 inside [1.3, 1.7]; linear decay outside
        if HIHO_LOW <= fd <= HIHO_HIGH:
            reward = 1.0
        else:
            dist = min(abs(fd - HIHO_LOW), abs(fd - HIHO_HIGH))
            reward = max(-1.0, 1.0 - 2.0 * dist)

        terminated = gc < COLLAPSE_FRACTION
        truncated = self._step_count >= self.max_steps
        obs = self._make_obs()
        info = {
            "giant_component_fraction": gc,
            "higuchi_fd": fd,
            "step": self._step_count,
        }
        return obs, reward, terminated, truncated, info
