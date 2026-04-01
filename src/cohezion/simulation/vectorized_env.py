"""Vectorized Environment for Parallel RL Training.

Wraps multiple HihoEnvironment instances for batched stepping,
enabling efficient multi-agent training on the 12D HIHO manifold.

This is the standard pattern for scaling RL training:
- N environments run in parallel (one per agent or per seed)
- Observations, rewards, and dones are returned as batched arrays
- Compatible with PPO, A2C, and other on-policy algorithms

Architecture:
    VectorizedHihoEnv
        ├── Maintains N independent HihoEnvironment instances
        ├── step_batch(): vectorized action → vectorized (obs, reward, done, info)
        ├── reset_batch(): vectorized seed → vectorized initial observations
        └── Auto-resets terminated environments

    AsyncVectorizedEnv
        ├── Runs environments in separate processes via multiprocessing
        └── True parallelism for CPU-bound physics stepping

    CurriculumScheduler
        ├── Adjusts environment difficulty based on agent performance
        ├── Supports linear, exponential, and adaptive schedules
        └── Integrates with R-Zero difficulty scaling

References:
    - OpenAI Gym VectorEnv pattern
    - Stable-Baselines3 SubprocVecEnv
    - Smith's HIHO: reward shaping at 0.5 coherence stability point
"""

from __future__ import annotations

import logging
import multiprocessing as mp
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from cohezion.simulation.rl_framework import (
    NUM_ACTIONS,
    STATE_DIM,
    HihoEnvironment,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Vectorized environment
# ---------------------------------------------------------------------------


class VectorizedHihoEnv:
    """Vectorized wrapper for N parallel HIHO environments.

    All observations, actions, and rewards are batched into numpy arrays
    for efficient processing. Terminated environments are auto-reset.

    Parameters
    ----------
    num_envs : int
        Number of parallel environments.
    grid_size : int
        Grid size for each environment.
    max_steps : int
        Max steps per episode.
    base_seed : int
        Base random seed (each env gets base_seed + i).
    """

    def __init__(
        self,
        num_envs: int = 8,
        grid_size: int = 64,
        max_steps: int = 1000,
        base_seed: int = 42,
    ):
        self.num_envs = num_envs
        self.envs = [
            HihoEnvironment(grid_size=grid_size, max_steps=max_steps) for _ in range(num_envs)
        ]
        self.base_seed = base_seed
        self._episode_counts = np.zeros(num_envs, dtype=np.int32)
        self._episode_rewards = np.zeros(num_envs)
        self._episode_lengths = np.zeros(num_envs, dtype=np.int32)

    @property
    def observation_shape(self) -> tuple[int, ...]:
        return (STATE_DIM,)

    @property
    def num_actions(self) -> int:
        return NUM_ACTIONS

    def reset(self) -> np.ndarray:
        """Reset all environments.

        Returns
        -------
        np.ndarray
            Batched observations, shape (num_envs, STATE_DIM).
        """
        observations = np.zeros((self.num_envs, STATE_DIM))
        for i, env in enumerate(self.envs):
            observations[i] = env.reset(seed=self.base_seed + i)
        self._episode_rewards[:] = 0.0
        self._episode_lengths[:] = 0
        return observations

    def step(
        self, actions: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, Any]]]:
        """Step all environments with batched actions.

        Parameters
        ----------
        actions : np.ndarray
            Action for each environment, shape (num_envs,).

        Returns
        -------
        tuple
            (observations, rewards, dones, infos)
            observations: shape (num_envs, STATE_DIM)
            rewards: shape (num_envs,)
            dones: shape (num_envs,) boolean
            infos: list of dicts per environment
        """
        observations = np.zeros((self.num_envs, STATE_DIM))
        rewards = np.zeros(self.num_envs)
        dones = np.zeros(self.num_envs, dtype=bool)
        infos: list[dict[str, Any]] = []

        for i, env in enumerate(self.envs):
            obs, reward, done, info = env.step(int(actions[i]))
            observations[i] = obs
            rewards[i] = reward
            dones[i] = done
            self._episode_rewards[i] += reward
            self._episode_lengths[i] += 1

            if done:
                # Record episode stats before auto-reset
                info["episode_reward"] = self._episode_rewards[i]
                info["episode_length"] = int(self._episode_lengths[i])
                info["episode_count"] = int(self._episode_counts[i])
                self._episode_counts[i] += 1
                self._episode_rewards[i] = 0.0
                self._episode_lengths[i] = 0
                # Auto-reset
                observations[i] = env.reset(
                    seed=self.base_seed + i + int(self._episode_counts[i]) * 1000
                )

            infos.append(info)

        return observations, rewards, dones, infos

    def get_episode_stats(self) -> dict[str, Any]:
        """Get aggregate episode statistics."""
        return {
            "episode_counts": self._episode_counts.tolist(),
            "total_episodes": int(self._episode_counts.sum()),
            "current_rewards": self._episode_rewards.tolist(),
            "current_lengths": self._episode_lengths.tolist(),
        }


# ---------------------------------------------------------------------------
# Async (multiprocess) vectorized environment
# ---------------------------------------------------------------------------


def _env_worker(
    pipe: mp.connection.Connection,
    env_idx: int,
    grid_size: int,
    max_steps: int,
    base_seed: int,
) -> None:
    """Worker process for a single environment.

    Receives commands via pipe and sends back results.
    """
    env = HihoEnvironment(grid_size=grid_size, max_steps=max_steps)
    episode_count = 0

    while True:
        try:
            cmd, data = pipe.recv()
        except EOFError:
            break

        if cmd == "step":
            obs, reward, done, info = env.step(data)
            if done:
                episode_count += 1
                info["episode_count"] = episode_count
                obs = env.reset(seed=base_seed + env_idx + episode_count * 1000)
            pipe.send(("step", obs, reward, done, info))

        elif cmd == "reset":
            seed = data if data is not None else base_seed + env_idx
            obs = env.reset(seed=seed)
            pipe.send(("reset", obs))

        elif cmd == "close":
            pipe.close()
            break


class AsyncVectorizedHihoEnv:
    """Multiprocess vectorized environment for true parallel stepping.

    Each environment runs in its own process, communicating via pipes.
    This provides real parallelism for CPU-bound environment stepping.

    Parameters
    ----------
    num_envs : int
        Number of parallel environments.
    grid_size : int
        Grid size for each environment.
    max_steps : int
        Max steps per episode.
    base_seed : int
        Base random seed.
    """

    def __init__(
        self,
        num_envs: int = 8,
        grid_size: int = 64,
        max_steps: int = 1000,
        base_seed: int = 42,
    ):
        self.num_envs = num_envs
        self.base_seed = base_seed
        self._closed = False

        # Create pipes and worker processes
        self._parent_pipes: list[mp.connection.Connection] = []
        self._child_pipes: list[mp.connection.Connection] = []
        self._processes: list[mp.Process] = []

        for i in range(num_envs):
            parent_conn, child_conn = mp.Pipe()
            self._parent_pipes.append(parent_conn)
            self._child_pipes.append(child_conn)

            p = mp.Process(
                target=_env_worker,
                args=(child_conn, i, grid_size, max_steps, base_seed),
                daemon=True,
            )
            p.start()
            self._processes.append(p)

    @property
    def observation_shape(self) -> tuple[int, ...]:
        return (STATE_DIM,)

    @property
    def num_actions(self) -> int:
        return NUM_ACTIONS

    def reset(self) -> np.ndarray:
        """Reset all environments in parallel."""
        for i, pipe in enumerate(self._parent_pipes):
            pipe.send(("reset", self.base_seed + i))

        observations = np.zeros((self.num_envs, STATE_DIM))
        for i, pipe in enumerate(self._parent_pipes):
            _, obs = pipe.recv()
            observations[i] = obs

        return observations

    def step(
        self, actions: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, Any]]]:
        """Step all environments in parallel."""
        # Send actions
        for i, pipe in enumerate(self._parent_pipes):
            pipe.send(("step", int(actions[i])))

        # Collect results
        observations = np.zeros((self.num_envs, STATE_DIM))
        rewards = np.zeros(self.num_envs)
        dones = np.zeros(self.num_envs, dtype=bool)
        infos: list[dict[str, Any]] = []

        for i, pipe in enumerate(self._parent_pipes):
            _, obs, reward, done, info = pipe.recv()
            observations[i] = obs
            rewards[i] = reward
            dones[i] = done
            infos.append(info)

        return observations, rewards, dones, infos

    def close(self) -> None:
        """Shutdown all worker processes."""
        if self._closed:
            return

        for pipe in self._parent_pipes:
            try:
                pipe.send(("close", None))
            except BrokenPipeError:
                pass

        for p in self._processes:
            p.join(timeout=5)
            if p.is_alive():
                p.terminate()

        self._closed = True

    def __del__(self):
        self.close()


# ---------------------------------------------------------------------------
# Curriculum scheduler
# ---------------------------------------------------------------------------


class ScheduleType(str, Enum):
    """Curriculum difficulty schedule types."""

    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    ADAPTIVE = "adaptive"
    STEP = "step"


@dataclass
class CurriculumConfig:
    """Configuration for curriculum scheduling.

    Parameters
    ----------
    schedule_type : ScheduleType
        How difficulty progresses.
    initial_difficulty : float
        Starting difficulty (0.0 = easiest, 1.0 = hardest).
    max_difficulty : float
        Maximum difficulty.
    warmup_episodes : int
        Episodes before difficulty starts increasing.
    performance_window : int
        Number of recent episodes to average for adaptive scheduling.
    target_success_rate : float
        For adaptive: target success rate that triggers difficulty increase.
    """

    schedule_type: ScheduleType = ScheduleType.ADAPTIVE
    initial_difficulty: float = 0.1
    max_difficulty: float = 1.0
    warmup_episodes: int = 50
    performance_window: int = 20
    target_success_rate: float = 0.7
    step_size: float = 0.1


class CurriculumScheduler:
    """Manages difficulty progression for training environments.

    Adjusts environment parameters (grid size, max steps, noise level)
    based on agent performance, implementing a curriculum that gradually
    increases challenge as the agent improves.

    Parameters
    ----------
    config : CurriculumConfig
        Curriculum configuration.
    """

    def __init__(self, config: CurriculumConfig | None = None):
        self.config = config or CurriculumConfig()
        self._current_difficulty = self.config.initial_difficulty
        self._episode_count = 0
        self._reward_history: list[float] = []
        self._success_history: list[bool] = []
        self._difficulty_history: list[tuple[int, float]] = []

    @property
    def current_difficulty(self) -> float:
        return self._current_difficulty

    def record_episode(self, reward: float, success: bool) -> None:
        """Record an episode result for adaptive scheduling.

        Parameters
        ----------
        reward : float
            Total episode reward.
        success : bool
            Whether the episode was "successful" (e.g., survived to end).
        """
        self._episode_count += 1
        self._reward_history.append(reward)
        self._success_history.append(success)

        if self._episode_count >= self.config.warmup_episodes:
            self._update_difficulty()

    def _update_difficulty(self) -> None:
        """Update difficulty based on schedule type."""
        schedule = self.config.schedule_type

        if schedule == ScheduleType.LINEAR:
            progress = (self._episode_count - self.config.warmup_episodes) / max(
                1, 1000 - self.config.warmup_episodes
            )
            self._current_difficulty = min(
                self.config.max_difficulty,
                self.config.initial_difficulty
                + progress * (self.config.max_difficulty - self.config.initial_difficulty),
            )

        elif schedule == ScheduleType.EXPONENTIAL:
            progress = (self._episode_count - self.config.warmup_episodes) / max(
                1, 1000 - self.config.warmup_episodes
            )
            self._current_difficulty = min(
                self.config.max_difficulty,
                self.config.initial_difficulty
                + (1.0 - np.exp(-3.0 * progress))
                * (self.config.max_difficulty - self.config.initial_difficulty),
            )

        elif schedule == ScheduleType.STEP:
            # Increase by step_size every N episodes
            steps = (self._episode_count - self.config.warmup_episodes) // 100
            self._current_difficulty = min(
                self.config.max_difficulty,
                self.config.initial_difficulty + steps * self.config.step_size,
            )

        elif schedule == ScheduleType.ADAPTIVE:
            window = self.config.performance_window
            if len(self._success_history) >= window:
                recent_success_rate = sum(self._success_history[-window:]) / window

                if recent_success_rate >= self.config.target_success_rate:
                    # Agent is doing well, increase difficulty
                    self._current_difficulty = min(
                        self.config.max_difficulty,
                        self._current_difficulty + self.config.step_size,
                    )
                elif recent_success_rate < 0.3:
                    # Agent is struggling, decrease difficulty
                    self._current_difficulty = max(
                        self.config.initial_difficulty,
                        self._current_difficulty - self.config.step_size * 0.5,
                    )

        self._difficulty_history.append((self._episode_count, self._current_difficulty))

    def get_env_params(self) -> dict[str, Any]:
        """Get environment parameters for current difficulty.

        Maps difficulty (0.0-1.0) to concrete environment parameters.

        Returns
        -------
        dict
            Environment parameters adjusted for current difficulty.
        """
        d = self._current_difficulty

        return {
            "grid_size": int(32 + d * 96),  # 32-128
            "max_steps": int(1000 - d * 700),  # 1000-300 (harder = less time)
            "noise_scale": 0.05 + d * 0.15,  # 0.05-0.20 (harder = more noise)
            "energy_drain": 0.1 + d * 0.3,  # 0.1-0.4 (harder = faster drain)
            "hiho_tolerance": 0.1 - d * 0.08,  # 0.10-0.02 (harder = tighter band)
        }

    def get_stats(self) -> dict[str, Any]:
        """Get curriculum statistics."""
        return {
            "current_difficulty": self._current_difficulty,
            "episode_count": self._episode_count,
            "recent_success_rate": (
                sum(self._success_history[-20:]) / min(20, len(self._success_history))
                if self._success_history
                else 0.0
            ),
            "recent_avg_reward": (
                float(np.mean(self._reward_history[-20:])) if self._reward_history else 0.0
            ),
            "difficulty_changes": len(self._difficulty_history),
        }


# ---------------------------------------------------------------------------
# Batched PPO training with vectorized env
# ---------------------------------------------------------------------------


def train_vectorized_ppo(
    num_envs: int = 8,
    num_episodes: int = 100,
    max_steps_per_episode: int = 500,
    use_curriculum: bool = True,
    seed: int = 42,
    verbose: bool = True,
) -> dict[str, Any]:
    """Train PPO agent using vectorized environments.

    Parameters
    ----------
    num_envs : int
        Number of parallel environments.
    num_episodes : int
        Total training episodes per environment.
    max_steps_per_episode : int
        Max steps per episode.
    use_curriculum : bool
        Whether to use curriculum learning.
    seed : int
        Random seed.
    verbose : bool
        Log progress.

    Returns
    -------
    dict
        Training results.
    """
    from cohezion.simulation.rl_framework import PPOAgent

    np.random.seed(seed)

    vec_env = VectorizedHihoEnv(
        num_envs=num_envs,
        max_steps=max_steps_per_episode,
        base_seed=seed,
    )
    agent = PPOAgent()
    curriculum = CurriculumScheduler() if use_curriculum else None

    episode_rewards: list[float] = []
    training_metrics: list[dict[str, float]] = []
    total_steps = 0
    completed_episodes = 0

    # Reset all environments
    observations = vec_env.reset()

    while completed_episodes < num_episodes * num_envs:
        # Select actions for all environments
        actions = np.zeros(num_envs, dtype=np.int32)
        log_probs = np.zeros(num_envs)
        values = np.zeros(num_envs)

        for i in range(num_envs):
            action, log_prob, value = agent.select_action(observations[i])
            actions[i] = action
            log_probs[i] = log_prob
            values[i] = value

        # Step all environments
        next_observations, rewards, dones, infos = vec_env.step(actions)

        # Store transitions
        for i in range(num_envs):
            agent.store_transition(
                observations[i],
                int(actions[i]),
                rewards[i],
                next_observations[i],
                bool(dones[i]),
                log_probs[i],
                values[i],
            )

            if dones[i]:
                ep_reward = infos[i].get("episode_reward", 0.0)
                episode_rewards.append(ep_reward)
                completed_episodes += 1

                if curriculum:
                    curriculum.record_episode(ep_reward, ep_reward > 0)

        observations = next_observations
        total_steps += num_envs

        # PPO update
        if total_steps % 2048 == 0 and len(agent.buffer) >= 32:
            metrics = agent.update()
            training_metrics.append(metrics)

        if verbose and completed_episodes > 0 and completed_episodes % (num_envs * 10) == 0:
            recent = (
                episode_rewards[-num_envs * 10 :]
                if len(episode_rewards) >= num_envs * 10
                else episode_rewards
            )
            avg_reward = float(np.mean(recent)) if recent else 0.0
            curr_diff = curriculum.current_difficulty if curriculum else 0.0
            logger.info(
                "Episodes %d: avg_reward=%.2f, total_steps=%d, difficulty=%.2f",
                completed_episodes,
                avg_reward,
                total_steps,
                curr_diff,
            )

        if completed_episodes >= num_episodes * num_envs:
            break

    return {
        "episode_rewards": episode_rewards,
        "training_metrics": training_metrics,
        "total_steps": total_steps,
        "completed_episodes": completed_episodes,
        "final_avg_reward": float(np.mean(episode_rewards[-50:])) if episode_rewards else 0.0,
        "curriculum_stats": curriculum.get_stats() if curriculum else None,
        "env_stats": vec_env.get_episode_stats(),
    }
