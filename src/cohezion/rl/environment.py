"""Gymnasium-compatible RL environment for FLUME manifold navigation.

State:  256D latent vector (agent position in FLUME space)
Action: 256D delta vector (continuous action space)
Reward: Coherence score (peak at HIHO 0.5 target)

Register as: cohezion/FlumeNav-v0

Phase 3 Integration:
    - TaskSpec configures env at reset()
    - Interruption injection via pause()/resume()
    - Context injection via inject_drift()
    - Open-ended mode (max_steps=None, exotic_charge_density termination)
    - EVO emission after each episode

Reference: docs/phases/PHASE_3_ENV.md
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

import gymnasium as gym
import numpy as np
from gymnasium import spaces


if TYPE_CHECKING:
    from cohezion.rl.evo import EthericVariantOscillator
    from cohezion.rl.task_generator import TaskSpec


logger = logging.getLogger(__name__)


class FlumeNavEnv(gym.Env):
    """Navigate a 256D FLUME manifold toward HIHO 0.5 coherence.

    The agent controls a position in latent space. Each step applies
    the agent's action as a delta, then runs one epoch of physics
    (either Hamiltonian or jitter). The reward is the coherence score
    relative to the HIHO 0.5 target.

    Phase 3 adds TaskSpec integration, interruption handling, context injection,
    open-ended mode, and EVO emission.

    Parameters
    ----------
    z_dim : int
        Latent space dimensionality (default 256).
    max_steps : int
        Maximum steps per episode (default 200). Use None for open-ended mode.
    dt : float
        Physics timestep (default 0.01).
    temperature : float
        Thermal noise magnitude (default 0.01).
    use_hamiltonian : bool
        If True, apply double-well Hamiltonian dynamics (default True).
    action_scale : float
        Scale factor for actions (default 0.01).
    use_composite_reward : bool
        If True, use CompositeReward for shaped rewards (default True).
    evo_tracker : EVOTracker, optional
        Tracker for managing EVO lifecycle and disk spillover.
    """

    metadata: ClassVar[dict[str, Any]] = {"render_modes": ["human", "ansi"], "render_fps": 10}

    def __init__(
        self,
        z_dim: int = 256,
        max_steps: int = 200,
        dt: float = 0.01,
        temperature: float = 0.01,
        use_hamiltonian: bool = True,
        action_scale: float = 0.01,
        render_mode: str | None = None,
        use_composite_reward: bool = True,
        evo_tracker: EthericVariantOscillator | None = None,
    ):
        super().__init__()
        self.z_dim = z_dim
        self.max_steps = max_steps
        self.dt = dt
        self.temperature = temperature
        self.use_hamiltonian = use_hamiltonian
        self.action_scale = action_scale
        self.render_mode = render_mode
        self.use_composite_reward = use_composite_reward

        self._state: np.ndarray | None = None
        self._prev_state: np.ndarray | None = None
        self._step_count = 0
        self._episode_coherences: list[float] = []

        self._is_paused = False
        self._interruption_points: list[int] = []
        self._current_task_spec: TaskSpec | None = None
        self._triune_weights = {"doer": 1.0 / 3.0, "thinker": 1.0 / 3.0, "knower": 1.0 / 3.0}
        self._noise_level: float = 0.05
        self._drift_injected: dict[str, bool] = {"doer": False, "thinker": False, "knower": False}
        self._evo_tracker = evo_tracker
        self._current_evo: EthericVariantOscillator | None = None

        if use_composite_reward:
            from cohezion.rl.reward_shaping import CompositeReward

            self._reward_fn = CompositeReward(hamiltonian_weight=0.3)
        else:
            self._reward_fn = None

        self.observation_space = spaces.Box(low=-2.0, high=2.0, shape=(z_dim,), dtype=np.float32)
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(z_dim,), dtype=np.float32)

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
        task_spec: TaskSpec | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Reset environment to initial state near HIHO target.

        Parameters
        ----------
        seed : int, optional
            Random seed for reproducibility.
        options : dict, optional
            Additional options (unused for now).
        task_spec : TaskSpec, optional
            Task specification that configures the environment:
            - horizon: max steps per episode (overrides self.max_steps if not None)
            - interruption_points: steps where env pauses
            - noise_level: action noise multiplier
            - doer_dominance, thinker_dominance, knower_dominance: TRIUNE weights

        Returns
        -------
        tuple[np.ndarray, dict]
            Observation and info dict with coherence.
        """
        super().reset(seed=seed)

        self._state = self.np_random.normal(0.5, 0.1, (self.z_dim,)).astype(np.float32)
        self._state = np.clip(self._state, -2.0, 2.0)
        self._prev_state = None
        self._step_count = 0
        self._episode_coherences = []
        self._is_paused = False
        self._drift_injected = {"doer": False, "thinker": False, "knower": False}

        if task_spec is not None:
            self._current_task_spec = task_spec
            self._interruption_points = list(task_spec.interruption_points)
            self._noise_level = task_spec.noise_level
            self._triune_weights = {
                "doer": task_spec.doer_dominance,
                "thinker": task_spec.thinker_dominance,
                "knower": task_spec.knower_dominance,
            }
            if task_spec.horizon > 0:
                self.max_steps = task_spec.horizon
        else:
            self._current_task_spec = None
            self._interruption_points = []
            self._noise_level = 0.05
            self._triune_weights = {"doer": 1.0 / 3.0, "thinker": 1.0 / 3.0, "knower": 1.0 / 3.0}

        if self._evo_tracker is not None:
            self._current_evo = self._evo_tracker.create_evo()
            self._current_evo.stability_well = task_spec.stability_well if task_spec else "HIHO_Origin"
            self._current_evo.kordylewski_cloud_id = task_spec.kordylewski_cloud_id if task_spec else "none"
        else:
            self._current_evo = None

        info = {"coherence": self._compute_coherence(self._state)}
        return self._state.copy(), info

    def step(self, action: np.ndarray) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        """Apply action + physics, return (obs, reward, terminated, truncated, info).

        Handles pause/resume at interruption points, context injection, and
        open-ended mode termination based on exotic_charge_density.

        Parameters
        ----------
        action : np.ndarray
            Action vector in [-1, 1]^z_dim.

        Returns
        -------
        tuple[np.ndarray, float, bool, bool, dict]
            Observation, reward, terminated, truncated, info.
        """
        assert self._state is not None, "Call reset() before step()"  # noqa: S101
        self._step_count += 1
        self._prev_state = self._state.copy()

        if self._is_paused:
            info = {
                "coherence": self._compute_coherence(self._state),
                "step": self._step_count,
                "paused": True,
                "mean_episode_coherence": np.mean(self._episode_coherences) if self._episode_coherences else 0.0,
            }
            return self._state.copy(), 0.0, False, False, info

        delta = action.astype(np.float32) * self.action_scale
        self._state = self._state + delta

        if self.use_hamiltonian:
            self._state = self._apply_hamiltonian(self._state)
        else:
            jitter = np.sin(self._state * 0.01) * 0.001
            self._state = self._state + jitter

        self._state = np.clip(self._state, -2.0, 2.0).astype(np.float32)

        coherence = self._compute_coherence(self._state)
        self._episode_coherences.append(coherence)

        reward = self._compute_reward(coherence)

        exotic_charge = self._compute_exotic_charge_density(self._state)
        terminated = False
        truncated = False

        if self.max_steps is None:
            if exotic_charge > 0.95:
                terminated = True
        else:
            truncated = self._step_count >= self.max_steps

        if self._current_evo is not None:
            self._current_evo.update_physics(
                coherence=coherence,
                step=self._step_count,
                doer_state=self._state[:12] if len(self._state) >= 12 else self._state,
            )
            self._current_evo.record_step(
                {
                    "step": self._step_count,
                    "doer_state": self._state[:12].copy() if len(self._state) >= 12 else self._state.copy(),
                    "coherence": coherence,
                    "reward": reward,
                    "exotic_charge_density": exotic_charge,
                }
            )

        info = {
            "coherence": coherence,
            "step": self._step_count,
            "mean_episode_coherence": np.mean(self._episode_coherences),
            "exotic_charge_density": exotic_charge,
        }

        return self._state.copy(), reward, terminated, truncated, info

    def _compute_exotic_charge_density(self, z: np.ndarray) -> float:
        """Compute exotic charge density from state variance.

        Parameters
        ----------
        z : np.ndarray
            State vector.

        Returns
        -------
        float
            Exotic charge density in [0.0, 1.0].
        """
        variance = np.var(z)
        return float(np.clip(variance * 4.0, 0.0, 1.0))

    def _apply_hamiltonian(self, z: np.ndarray) -> np.ndarray:
        """Apply double-well Hamiltonian dynamics centered at 0.5.

        V(x) = (x - 0.5)^2 * (x - 0.5 - 0.3)^2 + (x - 0.5 + 0.3)^2
        Simplified to: grad = 4 * (x-0.5) * ((x-0.5)^2 - 0.09)

        This creates energy minima at x=0.5, with barriers at 0.2 and 0.8.
        """
        x = z - 0.5  # Center at origin for cleaner math
        grad = 4.0 * x * (x * x - 0.09)
        noise_scale = np.sqrt(2 * self.temperature * self.dt)
        noise = self.np_random.normal(0, 1, z.shape).astype(np.float32)

        z_new = z - self.dt * grad + noise_scale * noise
        return z_new

    def _compute_coherence(self, z: np.ndarray) -> float:
        """Compute HIHO coherence using TRIUNE-weighted chunk averaging.

        Uses TRIUNE dominance weights to compute weighted coherence across
        doer/thinker/knower fabric chunks.

        Parameters
        ----------
        z : np.ndarray
            State vector.

        Returns
        -------
        float
            Coherence in [0.0, 1.0], peak at 0.5 mean per chunk.
        """
        doer_chunk = z[:12] if len(z) >= 12 else z
        thinker_chunk = z[12:524] if len(z) >= 524 else z[:0]
        knower_chunk = z[524:2572] if len(z) >= 2572 else z[:0]

        doer_mean = float(np.mean(doer_chunk)) if len(doer_chunk) > 0 else 0.5
        thinker_mean = float(np.mean(thinker_chunk)) if len(thinker_chunk) > 0 else 0.5
        knower_mean = float(np.mean(knower_chunk)) if len(knower_chunk) > 0 else 0.5

        doer_variance = (doer_mean - 0.5) ** 2
        thinker_variance = (thinker_mean - 0.5) ** 2
        knower_variance = (knower_mean - 0.5) ** 2

        weighted_variance = (
            self._triune_weights["doer"] * doer_variance
            + self._triune_weights["thinker"] * thinker_variance
            + self._triune_weights["knower"] * knower_variance
        )

        coherence = max(0.0, 1.0 - min(weighted_variance * 4.0, 1.0))
        return coherence

    def _compute_reward(self, coherence: float) -> float:
        """Compute reward using CompositeReward or legacy logic."""
        if self._reward_fn is not None:
            return self._reward_fn(
                coherence=coherence,
                state=self._state,
                prev_state=self._prev_state,
            )

        # Legacy reward: bonus for coherence in [0.3, 0.7], penalty outside
        reward = coherence
        if 0.3 <= coherence <= 0.7:
            reward += 0.5
        if coherence < 0.1:
            reward -= 1.0
        return reward

    def pause(self) -> None:
        """Pause physics at an interruption point.

        When paused, step() returns the current state with zero reward
        and no physics applied. Use resume() to continue.
        """
        self._is_paused = True

    def resume(self) -> None:
        """Resume physics after interruption."""
        self._is_paused = False

    def inject_drift(self, vector: np.ndarray, layer: str) -> None:
        """Inject drift noise into a specific TRIUNE layer.

        Parameters
        ----------
        vector : np.ndarray
            Drift vector to inject. Shape must match layer size.
        layer : str
            TRIUNE layer: "doer", "thinker", or "knower".

        Raises
        ------
        ValueError
            If layer is not one of doer/thinker/knower.
        """
        if layer not in ("doer", "thinker", "knower"):
            raise ValueError(f"Invalid layer: {layer}. Must be doer, thinker, or knower.")

        if self._state is None:
            return

        if layer == "doer":
            idx = 0
            size = min(12, len(self._state))
        elif layer == "thinker":
            idx = 12
            size = min(512, len(self._state) - 12)
        else:
            idx = 524
            size = min(2048, len(self._state) - 524)

        if size > 0 and len(vector) >= size:
            drift = vector[:size].astype(np.float32) * self._noise_level
            self._state[idx : idx + size] = self._state[idx : idx + size] + drift
            self._state = np.clip(self._state, -2.0, 2.0).astype(np.float32)

        self._drift_injected[layer] = True

    def emit_evo(self) -> EthericVariantOscillator | None:
        """Emit the current EVO with full physics biography.

        Returns the current EVO if one exists and has a non-empty trajectory,
        otherwise returns None. The EVO is unregistered from tracking after
        emission.

        Returns
        -------
        EthericVariantOscillator or None
            The completed EVO with biography, or None if no EVO exists.
        """
        if self._current_evo is None:
            return None

        evo = self._current_evo
        self._current_evo = None

        if self._evo_tracker is not None:
            self._evo_tracker.unregister(evo.journey_id)

        return evo

    @property
    def is_paused(self) -> bool:
        """Return True if physics is paused at an interruption point."""
        return self._is_paused

    @property
    def interruption_points(self) -> list[int]:
        """Return list of interruption points for current episode."""
        return list(self._interruption_points)

    @property
    def current_task_spec(self) -> TaskSpec | None:
        """Return the current TaskSpec if one is configured."""
        return self._current_task_spec

    @property
    def current_evo(self) -> EthericVariantOscillator | None:
        """Return the current EVO being tracked, or None."""
        return self._current_evo

    def render(self) -> str | None:
        """Render current state."""
        if self._state is None:
            return None

        coherence = self._compute_coherence(self._state)
        mean_val = float(np.mean(self._state))
        std_val = float(np.std(self._state))

        text = (
            f"Step {self._step_count}/{self.max_steps} | "
            f"Coherence: {coherence:.3f} | "
            f"Mean: {mean_val:.3f} | Std: {std_val:.3f}"
        )

        if self.render_mode == "human":
            print(text)
        return text


# Register the environment
gym.register(
    id="cohezion/FlumeNav-v0",
    entry_point="cohezion.rl.environment:FlumeNavEnv",
    max_episode_steps=200,
)
