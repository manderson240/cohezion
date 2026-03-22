"""Simple REINFORCE trainer for FLUME navigation policy.

Trains a small policy network to navigate the FLUME latent space
toward HIHO coherence using the FlumeNav-v0 Gymnasium environment.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Normal


logger = logging.getLogger(__name__)


class PolicyNetwork(nn.Module):
    """Simple Gaussian policy for continuous FLUME navigation.

    Outputs mean and log_std for a diagonal Gaussian over actions.
    """

    def __init__(self, state_dim: int = 256, action_dim: int = 256, hidden: int = 128):
        super().__init__()
        self.shared = nn.Sequential(
            nn.Linear(state_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
        )
        self.mean_head = nn.Linear(hidden, action_dim)
        self.log_std = nn.Parameter(torch.zeros(action_dim))

    def forward(self, state: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        h = self.shared(state)
        mean = torch.tanh(self.mean_head(h))  # Actions in [-1, 1]
        std = self.log_std.exp().expand_as(mean)
        return mean, std

    def get_action(self, state: np.ndarray) -> tuple[np.ndarray, torch.Tensor]:
        """Sample action and return (action, log_prob)."""
        state_t = torch.FloatTensor(state).unsqueeze(0)
        mean, std = self.forward(state_t)
        dist = Normal(mean, std)
        action_t = dist.sample()
        log_prob = dist.log_prob(action_t).sum(dim=-1)
        action = action_t.squeeze(0).detach().numpy()
        return np.clip(action, -1.0, 1.0), log_prob


@dataclass
class TrainingConfig:
    """Configuration for REINFORCE training."""

    n_episodes: int = 100
    max_steps: int = 200
    lr: float = 3e-4
    gamma: float = 0.99
    z_dim: int = 256
    hidden_dim: int = 128
    save_interval: int = 25
    output_dir: str = "data/rl/checkpoints"
    log_interval: int = 10


@dataclass
class EpisodeResult:
    """Result of a single training episode."""

    episode: int
    total_reward: float
    mean_coherence: float
    final_coherence: float
    steps: int


def train(config: TrainingConfig | None = None) -> list[EpisodeResult]:
    """Run REINFORCE training on FlumeNav-v0.

    Parameters
    ----------
    config : TrainingConfig
        Training hyperparameters.

    Returns
    -------
    list[EpisodeResult]
        Per-episode training results.
    """
    import gymnasium as gym

    # Ensure environment is registered

    if config is None:
        config = TrainingConfig()

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    env = gym.make("cohezion/FlumeNav-v0", max_steps=config.max_steps)
    policy = PolicyNetwork(config.z_dim, config.z_dim, config.hidden_dim)
    optimizer = optim.Adam(policy.parameters(), lr=config.lr)

    results: list[EpisodeResult] = []

    for ep in range(config.n_episodes):
        obs, info = env.reset(seed=ep)
        log_probs: list[torch.Tensor] = []
        rewards: list[float] = []
        coherences: list[float] = []

        for _step in range(config.max_steps):
            action, log_prob = policy.get_action(obs)
            obs, reward, terminated, truncated, info = env.step(action)

            log_probs.append(log_prob)
            rewards.append(reward)
            coherences.append(info["coherence"])

            if terminated or truncated:
                break

        # Compute discounted returns
        returns: list[float] = []
        G = 0.0
        for r in reversed(rewards):
            G = r + config.gamma * G
            returns.insert(0, G)

        returns_t = torch.FloatTensor(returns)
        if len(returns_t) > 1:
            returns_t = (returns_t - returns_t.mean()) / (returns_t.std() + 1e-8)

        # Policy gradient update
        policy_loss = torch.tensor(0.0)
        for lp, ret in zip(log_probs, returns_t, strict=False):
            policy_loss = policy_loss - lp * ret

        optimizer.zero_grad()
        policy_loss.backward()
        torch.nn.utils.clip_grad_norm_(policy.parameters(), max_norm=1.0)
        optimizer.step()

        result = EpisodeResult(
            episode=ep,
            total_reward=sum(rewards),
            mean_coherence=float(np.mean(coherences)),
            final_coherence=coherences[-1] if coherences else 0.0,
            steps=len(rewards),
        )
        results.append(result)

        if (ep + 1) % config.log_interval == 0:
            recent = results[-config.log_interval :]
            avg_reward = np.mean([r.total_reward for r in recent])
            avg_coh = np.mean([r.mean_coherence for r in recent])
            logger.info(
                f"Episode {ep + 1}/{config.n_episodes} | Avg Reward: {avg_reward:.2f} | Avg Coherence: {avg_coh:.3f}"
            )

        if (ep + 1) % config.save_interval == 0:
            ckpt_path = output_dir / f"policy_ep{ep + 1}.pt"
            torch.save(policy.state_dict(), ckpt_path)

    # Save final policy
    final_path = output_dir / "policy_final.pt"
    torch.save(policy.state_dict(), final_path)
    logger.info(f"Training complete. Final policy saved to {final_path}")

    env.close()
    return results
