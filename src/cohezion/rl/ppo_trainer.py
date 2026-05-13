"""TRIUNE PPO Trainer for Phase 4.

A PyTorch PPO trainer with a 3-tier TRIUNE policy head (Knower→Thinker→Doer)
and full checkpointing support.

Architecture:
- Knower: 256D → 2048D (maps VAE latent to abstract representation)
- Thinker: 2048D → 512D (refines to structured reasoning)
- Doer: 512D → 12D (outputs low-level action bounds)
- Value Head: 256D → 1D (state value estimation)

PPO Config:
- Clip epsilon: 0.2
- 4 epochs per update
- Adam optimizer (lr=3e-4, eps=1e-5)
- GAE (lambda=0.95)
- 80GB memory ceiling with 32-bit float buffers
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Normal


if TYPE_CHECKING:
    import numpy as np


logger = logging.getLogger(__name__)


class TRIUNEPolicy(nn.Module):
    """3-tier TRIUNE policy network.

    Maps a 256D VAE latent vector through three progressively
    specialized layers:
    - Knower: abstract feature extraction (256 → 2048)
    - Thinker: structured reasoning (2048 → 512)
    - Doer: action emission (512 → 12)

    The 12D output represents bounded action parameters via Tanh.
    """

    def __init__(self, z_dim: int = 256) -> None:
        """Initialize TRIUNE policy.

        Parameters
        ----------
        z_dim : int
            Input VAE latent dimension (default 256).
        """
        super().__init__()
        self.z_dim = z_dim
        self.knower = nn.Sequential(
            nn.Linear(z_dim, 2048),
            nn.ReLU(),
        )
        self.thinker = nn.Sequential(
            nn.Linear(2048, 512),
            nn.ReLU(),
            nn.Linear(512, 512),
            nn.ReLU(),
        )
        self.doer = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, z_dim),
            nn.Tanh(),
        )

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """Compute action from latent state.

        Parameters
        ----------
        z : torch.Tensor
            VAE latent state, shape (batch, z_dim).

        Returns
        -------
        torch.Tensor
            Bounded action vector, shape (batch, z_dim) in [-1, 1].
        """
        return self.doer(self.thinker(self.knower(z)))


class ValueNetwork(nn.Module):
    """Separate value head for state value estimation.

    Maps 256D VAE latent to a single scalar value estimate.
    Used for GAE advantage computation in PPO.
    """

    def __init__(self, z_dim: int = 256) -> None:
        """Initialize value network.

        Parameters
        ----------
        z_dim : int
            Input VAE latent dimension (default 256).
        """
        super().__init__()
        self.z_dim = z_dim
        self.net = nn.Sequential(
            nn.Linear(z_dim, 512),
            nn.ReLU(),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, 1),
        )

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """Compute state value.

        Parameters
        ----------
        z : torch.Tensor
            VAE latent state, shape (batch, z_dim).

        Returns
        -------
        torch.Tensor
            State value estimate, shape (batch, 1).
        """
        return self.net(z)


@dataclass
class PPOConfig:
    """Configuration for PPO training.

    Attributes
    ----------
    clip_epsilon : float
        PPO clip ratio epsilon (default 0.2).
    n_epochs : int
        Number of epochs per update (default 4).
    lr : float
        Adam learning rate (default 3e-4).
    eps : float
        Adam epsilon (default 1e-5).
    gamma : float
        Discount factor (default 0.99).
    gae_lambda : float
        GAE lambda for advantage estimation (default 0.95).
    entropy_coef : float
        Entropy bonus coefficient (default 0.01).
    value_coef : float
        Value loss coefficient (default 0.5).
    max_grad_norm : float
        Gradient clipping norm (default 0.5).
    min_samples : int
        Minimum samples required for update (default 64).
    z_dim : int
        VAE latent dimension (default 256).
    """

    clip_epsilon: float = 0.2
    n_epochs: int = 4
    lr: float = 3e-4
    eps: float = 1e-5
    gamma: float = 0.99
    gae_lambda: float = 0.95
    entropy_coef: float = 0.01
    value_coef: float = 0.5
    max_grad_norm: float = 0.5
    min_samples: int = 64
    z_dim: int = 256
    action_dim: int = field(init=False)
    log_std: float = -0.5

    def __post_init__(self) -> None:
        object.__setattr__(self, "action_dim", self.z_dim)


class PPOTrainer:
    """PPO trainer with TRIUNE policy head.

    Implements Proximal Policy Optimization with:
    - 3-tier TRIUNE policy (Knower→Thinker→Doer)
    - Separate value network
    - GAE advantage estimation
    - Clip objective
    - Checkpoint save/load

    Buffer stores transitions as 32-bit floats for memory efficiency.
    """

    buffer: list[dict]
    config: PPOConfig

    def __init__(self, config: PPOConfig | None = None) -> None:
        """Initialize PPO trainer.

        Parameters
        ----------
        config : PPOConfig, optional
            Training configuration. Uses defaults if None.
        """
        self.config = config if config is not None else PPOConfig()
        self.z_dim = self.config.z_dim

        self.policy = TRIUNEPolicy(z_dim=self.z_dim)
        self.value_network = ValueNetwork(z_dim=self.z_dim)

        self.log_std = nn.Parameter(torch.full((self.config.action_dim,), self.config.log_std))

        self.optimizer = optim.Adam(
            [*list(self.policy.parameters()), self.log_std],
            lr=self.config.lr,
            eps=self.config.eps,
        )
        self.value_optimizer = optim.Adam(
            self.value_network.parameters(),
            lr=self.config.lr,
            eps=self.config.eps,
        )
        self.scheduler = optim.lr_scheduler.LambdaLR(
            self.optimizer,
            lambda _: 1.0,
        )

        self.buffer = []

    def get_action(self, state: np.ndarray) -> tuple[np.ndarray, float, float]:
        """Sample action from policy for given state.

        Parameters
        ----------
        state : np.ndarray
            VAE latent state, shape (z_dim,).

        Returns
        -------
        tuple[np.ndarray, float, float]
            - action: sampled action in [-1, 1], shape (z_dim,)
            - log_prob: log probability of action
            - value: state value estimate
        """
        state_t = torch.FloatTensor(state).unsqueeze(0)
        with torch.no_grad():
            mean = self.policy(state_t)
            std = self.log_std.exp().expand_as(mean)
            dist = Normal(mean, std)
            action_t = dist.sample()
            log_prob = dist.log_prob(action_t).sum(dim=-1).item()
            value = self.value_network(state_t).item()

        action = action_t.squeeze(0).clamp(-1.0, 1.0).numpy()
        return action, log_prob, value

    def compute_gae(
        self,
        rewards: torch.Tensor,
        values: torch.Tensor,
        dones: torch.Tensor,
        gamma: float,
        gae_lambda: float,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Compute GAE advantages and returns.

        Parameters
        ----------
        rewards : torch.Tensor
            Rewards tensor, shape (T,).
        values : torch.Tensor
            Value estimates tensor, shape (T,).
        dones : torch.Tensor
            Done flags tensor, shape (T,).
        gamma : float
            Discount factor.
        gae_lambda : float
            GAE lambda.

        Returns
        -------
        tuple[torch.Tensor, torch.Tensor]
            - advantages: GAE advantage estimates, shape (T,)
            - returns: computed returns, shape (T,)
        """
        advantages = torch.zeros_like(rewards)
        returns = torch.zeros_like(rewards)
        gae = 0.0

        next_value = 0.0
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_non_terminal = 1.0 - dones[t].item()
                next_val = next_value
            else:
                next_non_terminal = 1.0 - dones[t].item()
                next_val = values[t + 1].item()

            delta = rewards[t].item() + gamma * next_val * next_non_terminal - values[t].item()
            gae = delta + gamma * gae_lambda * next_non_terminal * gae
            advantages[t] = gae
            returns[t] = gae + values[t].item()

        return advantages, returns

    def update(self) -> dict:
        """Run PPO update on current buffer.

        Requires at least min_samples transitions in buffer.
        Performs n_epochs of PPO updates with clip objective.

        Returns
        -------
        dict
            Training metrics including policy_loss, value_loss,
            entropy, approx_kl, and n_epochs_run.
        """
        if len(self.buffer) < self.config.min_samples:
            return {
                "status": "insufficient_samples",
                "n_samples": len(self.buffer),
                "required": self.config.min_samples,
            }

        states = torch.stack([torch.FloatTensor(t["state"]) for t in self.buffer])
        actions = torch.stack([torch.FloatTensor(t["action"]) for t in self.buffer])
        old_log_probs = torch.FloatTensor([t["log_prob"] for t in self.buffer])
        old_values = torch.FloatTensor([t["value"] for t in self.buffer])
        rewards = torch.FloatTensor([t["reward"] for t in self.buffer])
        dones = torch.BoolTensor([t["done"] for t in self.buffer])

        advantages, returns = self.compute_gae(
            rewards,
            old_values,
            dones,
            self.config.gamma,
            self.config.gae_lambda,
        )
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        total_policy_loss = 0.0
        total_value_loss = 0.0
        total_entropy = 0.0
        total_kl = 0.0

        for _epoch in range(self.config.n_epochs):
            mean = self.policy(states)
            std = self.log_std.exp().expand_as(mean)
            dist = Normal(mean, std)

            new_log_probs = dist.log_prob(actions).sum(dim=-1)
            entropy = dist.entropy().sum(dim=-1).mean()

            ratio = torch.exp(new_log_probs - old_log_probs)
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 1.0 - self.config.clip_epsilon, 1.0 + self.config.clip_epsilon) * advantages
            policy_loss = -torch.min(surr1, surr2).mean()
            entropy_loss = -self.config.entropy_coef * entropy

            values = self.value_network(states).squeeze(-1)
            value_loss = self.config.value_coef * torch.nn.functional.mse_loss(values, returns)

            self.optimizer.zero_grad()
            (policy_loss + entropy_loss).backward()
            torch.nn.utils.clip_grad_norm_(
                [*list(self.policy.parameters()), self.log_std],
                self.config.max_grad_norm,
            )
            self.optimizer.step()

            self.value_optimizer.zero_grad()
            value_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.value_network.parameters(), self.config.max_grad_norm)
            self.value_optimizer.step()

            with torch.no_grad():
                approx_kl = (old_log_probs - new_log_probs).mean()
                total_kl += approx_kl.item()
                total_policy_loss += policy_loss.item()
                total_value_loss += value_loss.item()
                total_entropy += entropy.item()

        self.scheduler.step()
        self.buffer.clear()

        n = self.config.n_epochs
        return {
            "status": "updated",
            "policy_loss": total_policy_loss / n,
            "value_loss": total_value_loss / n,
            "entropy": total_entropy / n,
            "approx_kl": total_kl / n,
            "n_epochs_run": self.config.n_epochs,
            "n_samples": len(states),
            "lr": self.optimizer.param_groups[0]["lr"],
        }

    def checkpoint(self, path: Path | str) -> None:
        """Save trainer state to checkpoint.

        Saves policy state, value network state, optimizer state,
        scheduler state, log_std parameter, and config.

        Parameters
        ----------
        path : Path or str
            Path to save checkpoint.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        torch.save(
            {
                "policy_state": self.policy.state_dict(),
                "value_state": self.value_network.state_dict(),
                "optimizer_state": self.optimizer.state_dict(),
                "scheduler_state": self.scheduler.state_dict(),
                "log_std": self.log_std.data,
                "config": self.config,
            },
            path,
        )
        logger.info(f"Checkpoint saved to {path}")

    def load(self, path: Path | str) -> None:
        """Load trainer state from checkpoint.

        Parameters
        ----------
        path : Path or str
            Path to checkpoint file.

        Raises
        ------
        FileNotFoundError
            If checkpoint file does not exist.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {path}")

        checkpoint = torch.load(path, weights_only=False)
        self.policy.load_state_dict(checkpoint["policy_state"])
        self.value_network.load_state_dict(checkpoint["value_state"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state"])
        self.scheduler.load_state_dict(checkpoint["scheduler_state"])
        self.log_std.data = checkpoint["log_std"]

        if "config" in checkpoint:
            self.config = checkpoint["config"]

        logger.info(f"Checkpoint loaded from {path}")


@dataclass
class EpisodeResult:
    """Result of a single PPO training episode.

    Attributes
    ----------
    episode : int
        Episode number (0-indexed).
    total_reward : float
        Sum of rewards over the episode.
    mean_coherence : float
        Average coherence during the episode.
    final_coherence : float
        Coherence at the final step.
    steps : int
        Number of steps taken.
    policy_loss : float
        Policy loss for the update after this episode (0.0 if no update).
    value_loss : float
        Value loss for the update after this episode (0.0 if no update).
    entropy : float
        Policy entropy for the update (0.0 if no update).
    approx_kl : float
        Approximate KL divergence for the update (0.0 if no update).
    """

    episode: int
    total_reward: float
    mean_coherence: float
    final_coherence: float
    steps: int
    policy_loss: float = 0.0
    value_loss: float = 0.0
    entropy: float = 0.0
    approx_kl: float = 0.0


def train(
    config: PPOConfig | None = None,
    n_episodes: int = 200,
    task_specs: list | None = None,
    output_dir: str = "data/rl/checkpoints",
    save_interval: int = 50,
    log_interval: int = 10,
    seed: int | None = None,
) -> list[EpisodeResult]:
    """Run PPO training on FlumeNav-v0 with TaskSpec environments.

    Parameters
    ----------
    config : PPOConfig, optional
        PPO training hyperparameters. Uses defaults if None.
    n_episodes : int
        Number of episodes to train (default 200).
    task_specs : list of TaskSpec, optional
        Task specifications to sample from during training.
        If None, uses the default untyped FlumeNav-v0 environment.
    output_dir : str
        Directory for checkpoints (default "data/rl/checkpoints").
    save_interval : int
        Checkpoint every N episodes (default 50).
    log_interval : int
        Log every N episodes (default 10).
    seed : int, optional
        Global random seed for reproducibility.

    Returns
    -------
    list[EpisodeResult]
        Per-episode training results.
    """
    import gymnasium as gym

    if config is None:
        config = PPOConfig()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    trainer = PPOTrainer(config)

    if seed is not None:
        torch.manual_seed(seed)

    import numpy as np

    env = gym.make("cohezion/FlumeNav-v0", max_steps=200)
    task_generator = None
    if task_specs is not None:
        from cohezion.rl.task_generator import TaskGenerator

        task_generator = TaskGenerator(task_specs)

    results: list[EpisodeResult] = []

    for ep in range(n_episodes):
        task_spec = None
        if task_generator is not None:
            task_spec = task_generator.sample()

        obs, info = env.reset(seed=(seed + ep) if seed is not None else None, task_spec=task_spec)
        episode_rewards: list[float] = []
        episode_dones: list[bool] = []
        coherences: list[float] = []

        state_before_step = obs.copy()
        for _step in range(env.max_steps or 200):
            action, log_prob, value = trainer.get_action(obs)

            obs, reward, terminated, truncated, info = env.step(action)

            trainer.buffer.append(
                {
                    "state": state_before_step,
                    "action": action.copy(),
                    "log_prob": log_prob,
                    "value": value,
                    "reward": float(reward),
                    "done": bool(terminated or truncated),
                }
            )

            episode_rewards.append(float(reward))
            episode_dones.append(bool(terminated or truncated))
            coherences.append(float(info.get("coherence", 0.0)))
            state_before_step = obs.copy()

            if terminated or truncated:
                break

        n_steps = len(episode_rewards)
        update_metrics = trainer.update()
        if update_metrics["status"] == "updated":
            policy_loss = float(update_metrics["policy_loss"])
            value_loss = float(update_metrics["value_loss"])
            entropy = float(update_metrics["entropy"])
            approx_kl = float(update_metrics["approx_kl"])
        else:
            policy_loss = value_loss = entropy = approx_kl = 0.0

        result = EpisodeResult(
            episode=ep,
            total_reward=float(sum(episode_rewards)),
            mean_coherence=float(np.mean(coherences)) if coherences else 0.0,
            final_coherence=float(coherences[-1]) if coherences else 0.0,
            steps=n_steps,
            policy_loss=policy_loss,
            value_loss=value_loss,
            entropy=entropy,
            approx_kl=approx_kl,
        )
        results.append(result)

        if (ep + 1) % log_interval == 0:
            recent = results[-log_interval:]
            avg_reward = np.mean([r.total_reward for r in recent])
            avg_coh = np.mean([r.mean_coherence for r in recent])
            logger.info(
                f"Episode {ep + 1}/{n_episodes} | "
                f"Avg Reward: {avg_reward:.2f} | "
                f"Avg Coherence: {avg_coh:.3f} | "
                f"Policy Loss: {policy_loss:.4f}"
            )

        if (ep + 1) % save_interval == 0:
            ckpt_path = output_path / f"ppo_ep{ep + 1}.pt"
            trainer.checkpoint(ckpt_path)

    final_path = output_path / "ppo_final.pt"
    trainer.checkpoint(final_path)
    logger.info(f"Training complete. Final policy saved to {final_path}")

    env.close()
    return results
