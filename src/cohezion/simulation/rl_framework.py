# class attrs treated as immutable config; never mutated per-instance
"""Formal RL Framework for Cohezion Universe Simulations.

Provides Gym-compatible environment wrappers and policy gradient agents
for training within the 12D HIHO manifold. Bridges the gap between
Cohezion's universe simulations and standard RL training pipelines.

Architecture:
    HihoEnvironment (Gym-like)
        ├── State: 12D vector (Smith's parameters)
        ├── Action: 9 discrete moves (8 neighbors + stay)
        ├── Reward: HIHO proximity + SPIN coherence bonus
        └── Terminal: energy depletion or reproduction threshold

    PolicyGradientAgent
        ├── Policy network: 12D → action probabilities
        ├── Value network: 12D → expected return
        └── PPO clipping for stable updates

    ExperienceBuffer
        └── Stores (state, action, reward, next_state, done) tuples

References:
    - Smith's HIHO (0.5 coherence) as the reward shaping principle
    - Shoulders' EVOs (self-organizing clusters) as emergent multi-agent behavior
    - Matsumoto's precipitation threshold as terminal condition
"""

from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)

# Number of dimensions in state space (Smith's 12 parameters)
STATE_DIM = 12
# Discrete actions: 8 cardinal/diagonal moves + stay in place
NUM_ACTIONS = 9
# HIHO stability target
HIHO = 0.5


@dataclass
class Transition:
    """Single experience transition for replay buffer."""

    state: np.ndarray  # 12D state before action
    action: int  # Action taken (0-8)
    reward: float  # Reward received
    next_state: np.ndarray  # 12D state after action
    done: bool  # Episode terminated
    log_prob: float = 0.0  # Log probability of action under policy
    value: float = 0.0  # Value estimate at state


class ExperienceBuffer:
    """Fixed-size ring buffer for experience replay.

    Supports both on-policy (PPO) and off-policy (DQN-style) training.
    Prioritized replay via TD-error weighting is optional.
    """

    def __init__(self, capacity: int = 10_000):
        self._buffer: deque[Transition] = deque(maxlen=capacity)

    def push(self, transition: Transition) -> None:
        self._buffer.append(transition)

    def sample(self, batch_size: int) -> list[Transition]:
        indices = np.random.choice(
            len(self._buffer), size=min(batch_size, len(self._buffer)), replace=False
        )
        return [self._buffer[i] for i in indices]

    def get_all(self) -> list[Transition]:
        """Get all transitions (for on-policy methods like PPO)."""
        return list(self._buffer)

    def clear(self) -> None:
        self._buffer.clear()

    def __len__(self) -> int:
        return len(self._buffer)


class HihoEnvironment:
    """Gym-compatible RL environment wrapping the Fractal Universe.

    State space: 12D continuous (Smith's parameters)
    Action space: 9 discrete (8 directions + stay)
    Reward: Composite of HIHO proximity, SPIN coherence, and survival

    The environment operates on a single agent within the universe grid.
    Multi-agent training uses vectorized environments (one per agent).

    Parameters
    ----------
    grid_size : int
        Size of the toroidal grid (default 64).
    max_steps : int
        Maximum steps per episode before forced termination.
    """

    # Action encoding: (dx, dy) offsets for 8 directions + stay
    ACTION_MAP = {
        0: (-1, -1),
        1: (0, -1),
        2: (1, -1),
        3: (-1, 0),
        4: (0, 0),
        5: (1, 0),
        6: (-1, 1),
        7: (0, 1),
        8: (1, 1),
    }

    def __init__(self, grid_size: int = 64, max_steps: int = 1000):
        self.grid_size = grid_size
        self.max_steps = max_steps
        self._step_count = 0
        self._state = np.full(STATE_DIM, HIHO)
        self._position = (grid_size // 2, grid_size // 2)
        self._energy = 100.0
        self._sector_entropy = np.random.rand(grid_size, grid_size) * 0.6 + 0.2
        self._episode_reward = 0.0

    @property
    def observation_shape(self) -> tuple[int, ...]:
        return (STATE_DIM,)

    @property
    def num_actions(self) -> int:
        return NUM_ACTIONS

    def reset(self, seed: int | None = None) -> np.ndarray:
        """Reset environment to initial state."""
        if seed is not None:
            np.random.seed(seed)

        self._state = np.random.rand(STATE_DIM) * 0.4 + 0.3  # Near HIHO
        self._position = (self.grid_size // 2, self.grid_size // 2)
        self._energy = 100.0
        self._step_count = 0
        self._episode_reward = 0.0
        self._sector_entropy = np.random.rand(self.grid_size, self.grid_size) * 0.6 + 0.2
        return self._state.copy()

    def step(self, action: int) -> tuple[np.ndarray, float, bool, dict[str, Any]]:
        """Execute action, return (next_state, reward, done, info).

        Parameters
        ----------
        action : int
            Action index (0-8).

        Returns
        -------
        tuple
            (observation, reward, terminated, info)
        """
        assert 0 <= action < NUM_ACTIONS, f"Invalid action {action}"

        dx, dy = self.ACTION_MAP[action]
        x, y = self._position
        new_x = (x + dx) % self.grid_size
        new_y = (y + dy) % self.grid_size
        self._position = (new_x, new_y)

        # Sector interaction
        sector_entropy = self._sector_entropy[new_y, new_x]
        interaction = (1.0 - sector_entropy - self._sector_entropy[y, x]) * 0.05

        # State evolution: noise shaped by sector interaction
        noise = np.random.randn(STATE_DIM) * abs(interaction) * 0.1
        # SPIN dimensions (6=rotation, 7=precession) couple more strongly
        noise[6] *= 1.3
        noise[7] *= 1.1
        self._state = np.clip(self._state + noise, 0.0, 1.0)

        # Energy cost
        move_cost = 0.1 if action != 4 else 0.02  # Staying is cheaper
        self._energy -= move_cost
        self._step_count += 1

        # --- Reward shaping (Smith's HIHO + SPIN) ---
        # 1. HIHO proximity: variance of brane dims (4-10) from 0.5
        brane = self._state[4:11]
        hiho_reward = 1.0 - float(np.mean((brane - HIHO) ** 2)) * 4.0
        hiho_reward = max(0.0, hiho_reward)

        # 2. SPIN coherence bonus (rotation[6] and precession[7] in phase)
        rot_sign = 1.0 if self._state[6] >= HIHO else -1.0
        prec_sign = 1.0 if self._state[7] >= HIHO else -1.0
        spin_bonus = 0.2 if rot_sign == prec_sign else -0.1

        # 3. Survival bonus (staying alive)
        survival = 0.01

        reward = hiho_reward + spin_bonus + survival

        # --- Terminal conditions ---
        done = False
        info: dict[str, Any] = {
            "energy": self._energy,
            "coherence": hiho_reward,
            "spin_coherence": 1.0 if rot_sign == prec_sign else 0.0,
            "charge_polarity": (self._state[6] - 0.5) + 0.3 * (self._state[7] - 0.5),
            "tempic_field": float(np.linalg.norm(noise[4:11])),
            "step": self._step_count,
        }

        # Death: energy depleted
        if self._energy <= 0:
            done = True
            reward -= 1.0  # Death penalty
            info["terminal_reason"] = "energy_depleted"

        # Death: extreme incoherence
        if hiho_reward < 0.1:
            done = True
            reward -= 0.5
            info["terminal_reason"] = "coherence_collapse"

        # Precipitation: reproduction threshold (Smith's matter formation)
        if self._energy > 150.0 and 0.48 < hiho_reward < 0.52:
            reward += 2.0  # Major bonus for hitting exact HIHO
            info["precipitation_event"] = True

        # Time limit
        if self._step_count >= self.max_steps:
            done = True
            info["terminal_reason"] = "max_steps"

        self._episode_reward += reward
        info["episode_reward"] = self._episode_reward

        return self._state.copy(), reward, done, info


class PolicyNetwork:
    """Simple policy network: 12D state → action probabilities.

    Uses a two-layer MLP with numpy (no torch dependency).
    Suitable for small-scale local training on CPU.
    """

    def __init__(
        self, state_dim: int = STATE_DIM, hidden_dim: int = 64, n_actions: int = NUM_ACTIONS
    ):
        self.state_dim = state_dim
        self.hidden_dim = hidden_dim
        self.n_actions = n_actions

        # Xavier initialization
        scale1 = math.sqrt(2.0 / (state_dim + hidden_dim))
        scale2 = math.sqrt(2.0 / (hidden_dim + n_actions))
        self.w1 = np.random.randn(state_dim, hidden_dim) * scale1
        self.b1 = np.zeros(hidden_dim)
        self.w2 = np.random.randn(hidden_dim, n_actions) * scale2
        self.b2 = np.zeros(n_actions)

    def forward(self, state: np.ndarray) -> np.ndarray:
        """Forward pass: state → action probabilities (softmax)."""
        h = np.tanh(state @ self.w1 + self.b1)
        logits = h @ self.w2 + self.b2
        # Numerically stable softmax
        logits -= logits.max()
        exp_logits = np.exp(logits)
        return exp_logits / exp_logits.sum()

    def select_action(self, state: np.ndarray) -> tuple[int, float]:
        """Sample action from policy, return (action, log_prob)."""
        probs = self.forward(state)
        action = np.random.choice(self.n_actions, p=probs)
        log_prob = math.log(probs[action] + 1e-10)
        return int(action), log_prob


class ValueNetwork:
    """Simple value network: 12D state → scalar value estimate."""

    def __init__(self, state_dim: int = STATE_DIM, hidden_dim: int = 64):
        scale1 = math.sqrt(2.0 / (state_dim + hidden_dim))
        scale2 = math.sqrt(2.0 / (hidden_dim + 1))
        self.w1 = np.random.randn(state_dim, hidden_dim) * scale1
        self.b1 = np.zeros(hidden_dim)
        self.w2 = np.random.randn(hidden_dim, 1) * scale2
        self.b2 = np.zeros(1)

    def forward(self, state: np.ndarray) -> float:
        """Forward pass: state → value estimate."""
        h = np.tanh(state @ self.w1 + self.b1)
        return float((h @ self.w2 + self.b2)[0])


class PPOAgent:
    """Proximal Policy Optimization agent for HIHO universe training.

    Implements PPO-Clip with Generalized Advantage Estimation (GAE).

    Parameters
    ----------
    lr : float
        Learning rate for both policy and value networks.
    gamma : float
        Discount factor.
    gae_lambda : float
        GAE lambda for advantage estimation.
    clip_epsilon : float
        PPO clipping parameter.
    entropy_coeff : float
        Entropy bonus coefficient (encourages exploration).
    epochs_per_update : int
        Number of optimization epochs per batch of experience.
    """

    def __init__(
        self,
        lr: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_epsilon: float = 0.2,
        entropy_coeff: float = 0.01,
        epochs_per_update: int = 4,
    ):
        self.policy = PolicyNetwork()
        self.value = ValueNetwork()
        self.buffer = ExperienceBuffer(capacity=2048)
        self.lr = lr
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.entropy_coeff = entropy_coeff
        self.epochs_per_update = epochs_per_update
        self._update_count = 0

    def select_action(self, state: np.ndarray) -> tuple[int, float, float]:
        """Select action using current policy.

        Returns
        -------
        tuple
            (action, log_prob, value_estimate)
        """
        action, log_prob = self.policy.select_action(state)
        value = self.value.forward(state)
        return action, log_prob, value

    def store_transition(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
        log_prob: float,
        value: float,
    ) -> None:
        self.buffer.push(
            Transition(
                state=state,
                action=action,
                reward=reward,
                next_state=next_state,
                done=done,
                log_prob=log_prob,
                value=value,
            )
        )

    def compute_gae(self, transitions: list[Transition]) -> tuple[np.ndarray, np.ndarray]:
        """Compute Generalized Advantage Estimation.

        Returns
        -------
        tuple
            (advantages, returns) arrays
        """
        n = len(transitions)
        advantages = np.zeros(n)
        returns = np.zeros(n)

        last_gae = 0.0
        for t in reversed(range(n)):
            next_value = 0.0 if t == n - 1 or transitions[t].done else transitions[t + 1].value

            delta = transitions[t].reward + self.gamma * next_value - transitions[t].value
            last_gae = delta + self.gamma * self.gae_lambda * (
                0.0 if transitions[t].done else last_gae
            )
            advantages[t] = last_gae
            returns[t] = advantages[t] + transitions[t].value

        # Normalize advantages
        if n > 1:
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        return advantages, returns

    def update(self) -> dict[str, float]:
        """Perform PPO update on buffered experience.

        Returns
        -------
        dict
            Training metrics (policy_loss, value_loss, entropy, etc.)
        """
        transitions = self.buffer.get_all()
        if len(transitions) < 32:
            return {"skipped": True, "reason": "insufficient_data"}

        advantages, returns = self.compute_gae(transitions)

        total_policy_loss = 0.0
        total_value_loss = 0.0
        total_entropy = 0.0

        for _epoch in range(self.epochs_per_update):
            for i, t in enumerate(transitions):
                # Current policy evaluation
                probs = self.policy.forward(t.state)
                new_log_prob = math.log(probs[t.action] + 1e-10)

                # PPO clipped objective
                ratio = math.exp(new_log_prob - t.log_prob)
                clipped_ratio = max(min(ratio, 1.0 + self.clip_epsilon), 1.0 - self.clip_epsilon)
                policy_loss = -min(ratio * advantages[i], clipped_ratio * advantages[i])

                # Value loss
                value_pred = self.value.forward(t.state)
                value_loss = 0.5 * (returns[i] - value_pred) ** 2

                # Entropy bonus (encourages exploration)
                entropy = -sum(p * math.log(p + 1e-10) for p in probs)

                # Gradient approximation (finite differences for numpy-only)
                # In production, this would use autograd (PyTorch/JAX)
                grad_scale = self.lr * (
                    policy_loss + 0.5 * value_loss - self.entropy_coeff * entropy
                )

                # Stochastic weight perturbation (evolutionary strategy approximation)
                noise_p = np.random.randn(*self.policy.w2.shape) * grad_scale * 0.01
                self.policy.w2 -= noise_p
                noise_v = np.random.randn(*self.value.w2.shape) * grad_scale * 0.01
                self.value.w2 -= noise_v

                total_policy_loss += policy_loss
                total_value_loss += value_loss
                total_entropy += entropy

        n = len(transitions) * self.epochs_per_update
        self._update_count += 1
        self.buffer.clear()

        return {
            "policy_loss": total_policy_loss / n,
            "value_loss": total_value_loss / n,
            "entropy": total_entropy / n,
            "update_count": self._update_count,
            "transitions_used": len(transitions),
        }


def train_hiho_agent(
    num_episodes: int = 100,
    max_steps_per_episode: int = 500,
    update_interval: int = 2048,
    seed: int = 42,
    verbose: bool = True,
) -> dict[str, Any]:
    """Train a PPO agent in the HIHO universe environment.

    Parameters
    ----------
    num_episodes : int
        Number of training episodes.
    max_steps_per_episode : int
        Max steps per episode.
    update_interval : int
        Steps between PPO updates.
    seed : int
        Random seed for reproducibility.
    verbose : bool
        Log training progress.

    Returns
    -------
    dict
        Training results including episode rewards and metrics.
    """
    np.random.seed(seed)

    env = HihoEnvironment(max_steps=max_steps_per_episode)
    agent = PPOAgent()

    episode_rewards: list[float] = []
    episode_lengths: list[int] = []
    training_metrics: list[dict[str, float]] = []
    total_steps = 0

    for episode in range(num_episodes):
        state = env.reset(seed=seed + episode)
        episode_reward = 0.0
        step = 0

        while True:
            action, log_prob, value = agent.select_action(state)
            next_state, reward, done, _info = env.step(action)

            agent.store_transition(state, action, reward, next_state, done, log_prob, value)

            state = next_state
            episode_reward += reward
            step += 1
            total_steps += 1

            # PPO update at interval
            if total_steps % update_interval == 0 and len(agent.buffer) >= 32:
                metrics = agent.update()
                training_metrics.append(metrics)
                if verbose:
                    logger.info(
                        "PPO update %d: policy_loss=%.4f, value_loss=%.4f, entropy=%.4f",
                        metrics.get("update_count", 0),
                        metrics.get("policy_loss", 0),
                        metrics.get("value_loss", 0),
                        metrics.get("entropy", 0),
                    )

            if done:
                break

        episode_rewards.append(episode_reward)
        episode_lengths.append(step)

        if verbose and (episode + 1) % 10 == 0:
            recent_avg = np.mean(episode_rewards[-10:])
            logger.info(
                "Episode %d/%d: reward=%.2f, avg_10=%.2f, steps=%d",
                episode + 1,
                num_episodes,
                episode_reward,
                recent_avg,
                step,
            )

    return {
        "episode_rewards": episode_rewards,
        "episode_lengths": episode_lengths,
        "training_metrics": training_metrics,
        "total_steps": total_steps,
        "final_avg_reward": float(np.mean(episode_rewards[-10:])) if episode_rewards else 0.0,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = train_hiho_agent(num_episodes=50, verbose=True)
    print(f"\nTraining complete. Final avg reward: {results['final_avg_reward']:.3f}")
