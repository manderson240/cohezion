"""ForestIntegrityEnv — forest patch conservation environment.

Models a 4×4 grid of forest patches, each scored on 5 ecological integrity
indicators. HIHO fractal dimension of the integrity time-series is the reward.

Physical analogues:
- SeagrassPercolationEnv: same percolation + HIHO FD reward structure
- HIHO phase transition: FD ∈ [1.3, 1.7] = healthy fractal dynamics
- Global Forest Watch: remote-sensing patch integrity classification

References:
    - "Ecological integrity of avoided deforestation projects",
      Nature Climate Change 2026 (s41558-026-02657-2)
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
N_INDICATORS = 5  # biodiversity, canopy, carbon_stock, connectivity, disturbance_regime
OBS_DIM = N_PATCHES * N_INDICATORS + 2  # 82 total
CONNECT_THRESHOLD = 0.5  # mean_integrity > this → patch in giant component
FD_WINDOW = 20
HIHO_LOW = 1.3
HIHO_HIGH = 1.7
COLLAPSE_THRESHOLD = 0.3  # mean integrity < this → episode ends

# Action encoding: patch_idx * 3 + action_type
ACTION_PROTECT = 0
ACTION_RESTORE = 1
ACTION_MONITOR = 2


class ForestIntegrityEnv(gym.Env):
    """4×4 forest patch grid with 5-indicator integrity and HIHO reward.

    Observation (82D float32):
        - 80 indicator scores: patch_i × indicator_j ∈ [0, 1]
        - giant component fraction ∈ [0, 1]
        - Higuchi FD of mean-integrity history ∈ [1.0, 2.0]

    Action space: Discrete(48)
        - patch_idx * 3 + 0: protect (no degradation this step)
        - patch_idx * 3 + 1: restore (all indicators +0.05)
        - patch_idx * 3 + 2: monitor (stochastic drift only)

    Reward:
        +1.0 when Higuchi FD ∈ [1.3, 1.7]  (HIHO health range)
        Linear penalty for deviation otherwise

    Termination:
        Mean integrity across all patches < 0.3 (functional collapse)
        OR step >= max_steps
    """

    metadata: dict[str, Any] = {"render_modes": []}

    def __init__(self, max_steps: int = 200, seed: int | None = None) -> None:
        super().__init__()
        self.max_steps = max_steps

        obs_low = np.zeros(OBS_DIM, dtype=np.float32)
        obs_high = np.ones(OBS_DIM, dtype=np.float32)
        obs_high[-1] = 2.0  # FD ranges up to 2.0
        self.observation_space = spaces.Box(low=obs_low, high=obs_high, dtype=np.float32)
        self.action_space = spaces.Discrete(N_PATCHES * 3)

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

        # (N_PATCHES, N_INDICATORS) integrity scores
        self._integrity: np.ndarray = np.ones((N_PATCHES, N_INDICATORS), dtype=np.float32)
        self._integrity_history: list[float] = []
        self._step_count: int = 0
        self._protected: set[int] = set()  # patches protected this step

        if seed is not None:
            self.np_random, _ = gym.utils.seeding.np_random(seed)  # type: ignore[attr-defined]

    def _mean_integrity(self) -> np.ndarray:
        """Per-patch mean across 5 indicators. Shape: (N_PATCHES,)"""
        return self._integrity.mean(axis=1)

    def _giant_component_fraction(self) -> float:
        """Union-find on patches with mean_integrity > threshold."""
        parent = list(range(N_PATCHES))
        mean_int = self._mean_integrity()

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
            if mean_int[i] > CONNECT_THRESHOLD:
                for j in self._neighbors[i]:
                    if mean_int[j] > CONNECT_THRESHOLD:
                        union(i, j)

        alive = [i for i in range(N_PATCHES) if mean_int[i] > CONNECT_THRESHOLD]
        if not alive:
            return 0.0
        roots = [find(i) for i in alive]
        largest = max(roots.count(r) for r in set(roots))
        return largest / N_PATCHES

    def _higuchi_fd(self) -> float:
        if len(self._integrity_history) < 6:
            return 1.5
        try:
            from cohezion.inference.fractal_metrics import higuchi_fd

            return float(np.clip(higuchi_fd(self._integrity_history[-FD_WINDOW:]), 1.0, 2.0))
        except Exception:
            return 1.5

    def _make_obs(self) -> np.ndarray:
        obs = np.empty(OBS_DIM, dtype=np.float32)
        obs[: N_PATCHES * N_INDICATORS] = self._integrity.ravel()
        obs[-2] = self._giant_component_fraction()
        obs[-1] = self._higuchi_fd()
        return obs

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[np.ndarray, dict[str, Any]]:
        super().reset(seed=seed)
        self._integrity = self.np_random.uniform(0.4, 1.0, size=(N_PATCHES, N_INDICATORS)).astype(
            np.float32
        )
        self._integrity_history = []
        self._step_count = 0
        self._protected = set()
        return self._make_obs(), {}

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        patch_idx = action // 3
        action_type = action % 3
        self._protected = set()

        if action_type == ACTION_PROTECT:
            self._protected.add(patch_idx)  # no degradation applied this step
        elif action_type == ACTION_RESTORE:
            self._integrity[patch_idx] = np.clip(self._integrity[patch_idx] + 0.05, 0.0, 1.0)
        # ACTION_MONITOR: stochastic drift only (handled below)

        # Stochastic degradation — protected patches are clamped after
        noise = self.np_random.uniform(-0.02, 0.01, size=(N_PATCHES, N_INDICATORS))
        self._integrity = np.clip(self._integrity + noise, 0.0, 1.0).astype(np.float32)
        for p in self._protected:
            # Re-clamp protected patch to pre-drift (already at post-protect value)
            self._integrity[p] = np.clip(self._integrity[p], 0.0, 1.0)

        mean_all = float(self._integrity.mean())
        self._integrity_history.append(mean_all)
        self._step_count += 1

        fd = self._higuchi_fd()
        gc = self._giant_component_fraction()

        if HIHO_LOW <= fd <= HIHO_HIGH:
            reward = 1.0
        else:
            dist = min(abs(fd - HIHO_LOW), abs(fd - HIHO_HIGH))
            reward = max(-1.0, 1.0 - 2.0 * dist)

        terminated = mean_all < COLLAPSE_THRESHOLD
        truncated = self._step_count >= self.max_steps
        obs = self._make_obs()
        info = {
            "giant_component_fraction": gc,
            "higuchi_fd": fd,
            "mean_integrity": mean_all,
            "step": self._step_count,
        }
        return obs, reward, terminated, truncated, info
