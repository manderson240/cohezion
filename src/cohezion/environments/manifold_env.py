"""ManifoldEnv — OpenAI Gymnasium environment for the 12D axiomatic manifold.

A physics-grounded agentic environment where agents navigate a 12D Riemannian
manifold governed by Lagrangian mechanics, gauge theory, and the HIHO stability
principle. Compatible with standard RL frameworks (Stable-Baselines3, TRL, etc.)
and the OpenEnv specification from Meta/HuggingFace.

Observation space (19D):
    - 12D axiomatic state (Space×3, Field×3, Control×3, Precipitation×3)
    - 3D Bloch vector (spinor rotation, precession, charge)
    - 4D fiber base (fabric norms)

Action space (12D continuous):
    - Direction of movement in the manifold (velocity vector)

Reward:
    - Coherence gain toward HIHO (δ→0) — positive when approaching 0.5
    - Surprise penalty from JEPA world model — penalize physically implausible moves
    - Energy efficiency bonus — lower Lagrangian action is better

Termination:
    - Episode ends when |δ| < 0.01 for 10 consecutive steps (HIHO stabilized)
    - Or after max_steps (default 500)

Physics engine:
    - Lagrangian dynamics with fabric-block Riemannian metric
    - HIHO Gaussian attractor potential
    - SU(2) spinor coherence tracking
    - Fiber bundle decomposition at each step

Usage:
    import gymnasium as gym
    from cohezion.environments import ManifoldEnv

    env = ManifoldEnv()
    obs, info = env.reset()
    for _ in range(1000):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated:
            obs, info = env.reset()

References:
    - OpenEnv spec: https://huggingface.co/blog/openenv
    - Gymnasium API: https://gymnasium.farama.org/
"""

from __future__ import annotations

import logging
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from cohezion.physics.fiber_bundle import FiberBundle
from cohezion.physics.gauge_theory import FourFabricGauge
from cohezion.physics.lagrangian import LagrangianDynamics, hiho_potential
from cohezion.physics.riemannian_metric import fabric_block_metric
from cohezion.physics.spinor import SpinorState


# Valid dynamics engine choices
DYNAMICS_ENGINES = ("lagrangian", "hamiltonian")

logger = logging.getLogger(__name__)


class ManifoldEnv(gym.Env):
    """12D Riemannian manifold environment for agentic RL.

    Parameters
    ----------
    dim : int
        Manifold dimension (default: 12).
    max_steps : int
        Maximum steps per episode (default: 500).
    dt : float
        Physics timestep (default: 0.01).
    damping : float
        Viscous damping coefficient (default: 0.1).
    hiho_threshold : float
        HIHO convergence threshold |δ| < threshold (default: 0.01).
    hiho_stability_window : int
        Steps at HIHO before termination (default: 10).
    reward_coherence_weight : float
        Weight for coherence reward component (default: 1.0).
    reward_energy_weight : float
        Weight for energy efficiency reward (default: 0.1).
    seed : int or None
        Random seed for reproducibility.
    """

    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 30}

    def __init__(
        self,
        dim: int = 12,
        max_steps: int = 500,
        dt: float = 0.01,
        damping: float = 0.1,
        hiho_threshold: float = 0.01,
        hiho_stability_window: int = 10,
        reward_coherence_weight: float = 1.0,
        reward_energy_weight: float = 0.1,
        render_mode: str | None = None,
        seed: int | None = None,
        dynamics_engine: str = "lagrangian",
    ) -> None:
        super().__init__()

        self.dim = dim
        self.max_steps = max_steps
        self.dt = dt
        self.damping = damping
        self.hiho_threshold = hiho_threshold
        self.hiho_stability_window = hiho_stability_window
        self.reward_coherence_weight = reward_coherence_weight
        self.reward_energy_weight = reward_energy_weight
        self.render_mode = render_mode

        # Observation: 12D state + 3D Bloch + 4D fiber base = 19D
        self.observation_space = spaces.Box(low=-2.0, high=2.0, shape=(19,), dtype=np.float32)

        # Action: 12D continuous velocity vector
        self.action_space = spaces.Box(low=-0.5, high=0.5, shape=(dim,), dtype=np.float32)

        # Physics engine selection
        if dynamics_engine not in DYNAMICS_ENGINES:
            raise ValueError(
                f"dynamics_engine must be one of {DYNAMICS_ENGINES}, got '{dynamics_engine}'"
            )
        self.dynamics_engine = dynamics_engine

        self._metric = fabric_block_metric(dim)
        self._potential = hiho_potential(dim)
        self._fiber_bundle = FiberBundle(dim)
        self._gauge = FourFabricGauge()

        if dynamics_engine == "hamiltonian":
            from cohezion.physics.hamiltonian import HamiltonianDynamics

            self._hamiltonian = HamiltonianDynamics(dt=dt, temperature=damping)
            self._dynamics = None  # type: ignore[assignment]
        else:
            self._hamiltonian = None
            self._dynamics = LagrangianDynamics(self._metric, self._potential, damping=damping)

        # State
        self._position = np.full(dim, 0.5, dtype=np.float32)
        self._velocity = np.zeros(dim, dtype=np.float32)
        self._step_count = 0
        self._hiho_streak = 0
        self._prev_coherence = 0.5
        self._episode_reward = 0.0
        self._trajectory: list[np.ndarray] = []

        # RNG
        self._rng = np.random.default_rng(seed)

    def reset(
        self,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Reset environment to a random initial state.

        Returns observation and info dict.
        """
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)

        # Random initial position (uniform in [0.2, 0.8] — near HIHO but not at it)
        self._position = self._rng.uniform(0.2, 0.8, self.dim).astype(np.float32)
        self._velocity = self._rng.normal(0, 0.02, self.dim).astype(np.float32)
        self._step_count = 0
        self._hiho_streak = 0
        self._prev_coherence = self._compute_coherence()
        self._episode_reward = 0.0
        self._trajectory = [self._position.copy()]

        return self._get_obs(), self._get_info()

    def step(self, action: np.ndarray) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        """Execute one step: apply action as velocity, evolve via Lagrangian dynamics.

        Returns (observation, reward, terminated, truncated, info).
        """
        action = np.asarray(action, dtype=np.float32).clip(-0.5, 0.5)
        self._step_count += 1

        # Apply action as velocity perturbation
        self._velocity = self._velocity * 0.9 + action * 0.1  # Smooth velocity update

        # Evolve via selected dynamics engine
        if self.dynamics_engine == "hamiltonian":
            z = self._position.astype(np.float32).reshape(1, -1)
            z_new = self._hamiltonian.step(z, rng=self._rng)
            new_pos = z_new.flatten()
            new_vel = (new_pos - self._position) / self.dt
        else:
            new_pos, new_vel = self._dynamics.step_verlet(
                self._position.astype(np.float64),
                self._velocity.astype(np.float64),
                self.dt,
            )
        self._position = np.clip(new_pos, -1.5, 2.0).astype(np.float32)
        self._velocity = new_vel.astype(np.float32)

        # Track trajectory
        self._trajectory.append(self._position.copy())

        # Compute reward
        coherence = self._compute_coherence()
        reward = self._compute_reward(coherence)
        self._prev_coherence = coherence
        self._episode_reward += reward

        # Check HIHO convergence
        deviation = self._compute_hiho_deviation()
        if deviation < self.hiho_threshold:
            self._hiho_streak += 1
        else:
            self._hiho_streak = 0

        # Termination conditions
        terminated = self._hiho_streak >= self.hiho_stability_window
        truncated = self._step_count >= self.max_steps

        return self._get_obs(), float(reward), terminated, truncated, self._get_info()

    def _get_obs(self) -> np.ndarray:
        """Construct 19D observation vector."""
        # Spinor state
        spinor = SpinorState.from_coherence_values(
            float(np.clip(self._position[6], 0, 1)),  # logic
            float(np.clip(self._position[7], 0, 1)),  # quantum
        )
        bloch = spinor.bloch_vector.astype(np.float32)

        # Fiber base
        fiber_base = self._fiber_bundle.project_to_base(self._position.astype(np.float64)).astype(
            np.float32
        )

        return np.concatenate([self._position, bloch, fiber_base])

    def _get_info(self) -> dict[str, Any]:
        """Compute info dict with physics quantities."""
        spinor = SpinorState.from_coherence_values(
            float(np.clip(self._position[6], 0, 1)),
            float(np.clip(self._position[7], 0, 1)),
        )

        self._gauge.set_from_12d_state(self._position.astype(np.float64))

        return {
            "step": self._step_count,
            "coherence": self._compute_coherence(),
            "hiho_deviation": self._compute_hiho_deviation(),
            "hiho_streak": self._hiho_streak,
            "charge_polarity": spinor.charge_polarity,
            "spin_rotation": spinor.spin_rotation,
            "spin_precession": spinor.spin_precession,
            "yang_mills_action": self._gauge.yang_mills_action(),
            "is_hiho": self._gauge.is_hiho(tol=0.1),
            "potential_energy": self._potential.evaluate(self._position.astype(np.float64)),
            "kinetic_energy": self._dynamics.kinetic_energy(
                self._position.astype(np.float64),
                self._velocity.astype(np.float64),
            )
            if self._dynamics is not None
            else 0.5 * float(np.sum(self._velocity**2)),
            "episode_reward": self._episode_reward,
            "trajectory_length": len(self._trajectory),
        }

    def _compute_coherence(self) -> float:
        """Compute HIHO coherence from current state."""
        brane_dims = self._position[4:11]  # physics through novelty
        variance = float(np.mean((brane_dims - 0.5) ** 2))
        return 1.0 - min(variance * 4, 1.0)

    def _compute_hiho_deviation(self) -> float:
        """Compute |δ| = deviation from HIHO equilibrium."""
        brane_dims = self._position[4:11]
        return float(np.mean(np.abs(brane_dims - 0.5)))

    def _compute_reward(self, coherence: float) -> float:
        """Compute reward from coherence change + energy efficiency.

        Reward = coherence_gain * w_c - energy * w_e
        """
        # Coherence improvement (positive when approaching HIHO)
        coherence_gain = coherence - self._prev_coherence
        coherence_reward = coherence_gain * self.reward_coherence_weight

        # Energy efficiency (lower potential energy = better)
        energy = self._potential.evaluate(self._position.astype(np.float64))
        energy_reward = -abs(energy) * self.reward_energy_weight

        # Bonus for being at HIHO
        deviation = self._compute_hiho_deviation()
        hiho_bonus = 0.1 if deviation < self.hiho_threshold else 0.0

        return coherence_reward + energy_reward + hiho_bonus

    def get_trajectory(self) -> np.ndarray:
        """Return the full trajectory as (n_steps, 12) array."""
        return np.array(self._trajectory)


# Register with gymnasium
gym.register(
    id="Cohezion/ManifoldEnv-v0",
    entry_point="cohezion.environments.manifold_env:ManifoldEnv",
    max_episode_steps=500,
)


__all__ = ["DYNAMICS_ENGINES", "ManifoldEnv"]
