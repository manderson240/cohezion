"""Incremental trainers — resume training from checkpoints with new hyperparameters.

Supports both VAE and RL incremental training for the iterative
hyperparameter search loop.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class IncrementalResult:
    """Result from an incremental training run."""

    iteration: int
    epochs_trained: int
    final_metrics: dict
    checkpoint_path: str
    improved: bool


class IncrementalVAETrainer:
    """Resume VAE training from a checkpoint with potentially new hyperparameters.

    Parameters
    ----------
    checkpoint_path : str or Path
        Path to the VAE checkpoint to resume from.
    """

    def __init__(self, checkpoint_path: str | Path) -> None:
        self.checkpoint_path = Path(checkpoint_path)

    def train_more(
        self,
        additional_epochs: int = 25,
        lr: float | None = None,
        kl_weight: float | None = None,
        data_dir: str = "data/mass_sim/artifacts",
    ) -> IncrementalResult:
        """Train additional epochs from the checkpoint.

        Parameters
        ----------
        additional_epochs : int
            Number of new epochs to train.
        lr : float, optional
            Override learning rate. If None, uses checkpoint config.
        kl_weight : float, optional
            Override KL weight. If None, uses checkpoint config.
        data_dir : str
            Training data directory.

        Returns
        -------
        IncrementalResult
            Result including whether loss improved.
        """
        from cohezion.flume.training import FlumeVAETrainer

        trainer = FlumeVAETrainer.from_checkpoint(self.checkpoint_path)
        config = trainer.config

        # Apply overrides
        if lr is not None:
            config.lr = lr
        if kl_weight is not None:
            config.kl_weight = kl_weight
        # Guard: β≥0.1 causes posterior collapse (autoresearch 2026-05-15)
        if config.kl_weight >= 0.1:
            logger.warning(
                "kl_weight=%.3f in checkpoint config is at/above the posterior-collapse threshold "
                "(β≥0.1). Clamping to 0.01 for safe incremental training. "
                "Pass kl_weight explicitly to override.",
                config.kl_weight,
            )
            config.kl_weight = 0.01
        config.epochs = additional_epochs
        config.data_dir = data_dir

        # Get baseline metrics from last JSONL entry
        baseline_total = float("inf")
        metrics_path = trainer.metrics_path
        if metrics_path.exists():
            import json

            lines = metrics_path.read_text().strip().split("\n")
            if lines:
                last = json.loads(lines[-1])
                baseline_total = last.get("total", float("inf"))

        # Rebuild trainer with updated config
        trainer = FlumeVAETrainer.from_checkpoint(self.checkpoint_path, config=config)
        metrics = trainer.train()

        if not metrics:
            return IncrementalResult(
                iteration=0,
                epochs_trained=0,
                final_metrics={},
                checkpoint_path="",
                improved=False,
            )

        final = metrics[-1]
        improved = final["total"] < baseline_total * 0.99  # 1% improvement threshold

        # Find latest checkpoint
        ckpt_dir = Path(config.checkpoint_dir)
        ckpt_files = sorted(ckpt_dir.glob("flume_vae_ep*.pt"))
        latest_ckpt = str(ckpt_files[-1]) if ckpt_files else ""

        logger.info(
            "Incremental VAE: %d epochs, total_loss %.4f → %.4f (%s)",
            additional_epochs,
            baseline_total,
            final["total"],
            "improved" if improved else "no improvement",
        )

        return IncrementalResult(
            iteration=0,
            epochs_trained=len(metrics),
            final_metrics=final,
            checkpoint_path=latest_ckpt,
            improved=improved,
        )


class IncrementalRLTrainer:
    """Resume RL training from a policy checkpoint with new hyperparameters.

    Parameters
    ----------
    checkpoint_path : str or Path
        Path to the policy checkpoint to resume from.
    """

    def __init__(self, checkpoint_path: str | Path) -> None:
        self.checkpoint_path = Path(checkpoint_path)

    def train_more(
        self,
        additional_episodes: int = 100,
        lr: float | None = None,
        gamma: float | None = None,
        hidden_dim: int = 128,
        output_dir: str = "data/rl/checkpoints",
    ) -> IncrementalResult:
        """Train additional episodes from the checkpoint.

        Parameters
        ----------
        additional_episodes : int
            Number of new episodes to train.
        lr : float, optional
            Override learning rate.
        gamma : float, optional
            Override discount factor.
        hidden_dim : int
            Hidden layer dimension (must match checkpoint).
        output_dir : str
            Directory for output checkpoints.

        Returns
        -------
        IncrementalResult
            Result including whether coherence improved.
        """
        import gymnasium as gym
        import torch

        from cohezion.rl.trainer import PolicyNetwork, TrainingConfig

        # Load existing policy
        state_dict = torch.load(self.checkpoint_path, map_location="cpu", weights_only=True)
        h, s = state_dict["shared.0.weight"].shape
        a = state_dict["mean_head.weight"].shape[0]

        policy = PolicyNetwork(s, a, h)
        policy.load_state_dict(state_dict)

        config = TrainingConfig(
            n_episodes=additional_episodes,
            lr=lr or 3e-4,
            gamma=gamma or 0.99,
            z_dim=s,
            hidden_dim=h,
            output_dir=output_dir,
        )

        env = gym.make("cohezion/FlumeNav-v0", max_steps=config.max_steps)
        optimizer = torch.optim.Adam(policy.parameters(), lr=config.lr)

        coherences: list[float] = []
        rewards: list[float] = []

        for ep in range(additional_episodes):
            obs, info = env.reset(seed=ep + 10000)
            ep_rewards: list[float] = []
            log_probs: list[torch.Tensor] = []
            ep_coherences: list[float] = []

            for _ in range(config.max_steps):
                action, log_prob = policy.get_action(obs)
                obs, reward, terminated, truncated, info = env.step(action)
                ep_rewards.append(reward)
                log_probs.append(log_prob)
                ep_coherences.append(info["coherence"])
                if terminated or truncated:
                    break

            # REINFORCE update
            returns: list[float] = []
            g = 0.0
            for r in reversed(ep_rewards):
                g = r + config.gamma * g
                returns.insert(0, g)
            returns_t = torch.FloatTensor(returns)
            if len(returns_t) > 1:
                returns_t = (returns_t - returns_t.mean()) / (returns_t.std() + 1e-8)

            loss = torch.tensor(0.0)
            for lp, ret in zip(log_probs, returns_t, strict=False):
                loss = loss - lp * ret
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(policy.parameters(), 1.0)
            optimizer.step()

            coherences.append(float(np.mean(ep_coherences)))
            rewards.append(sum(ep_rewards))

        env.close()

        # Save updated policy
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        save_path = out_dir / "policy_final.pt"
        torch.save(policy.state_dict(), save_path)

        avg_coh = float(np.mean(coherences[-50:])) if coherences else 0.0
        avg_reward = float(np.mean(rewards[-50:])) if rewards else 0.0

        logger.info(
            "Incremental RL: %d episodes, avg_coherence=%.4f, avg_reward=%.2f",
            additional_episodes,
            avg_coh,
            avg_reward,
        )

        return IncrementalResult(
            iteration=0,
            epochs_trained=additional_episodes,
            final_metrics={
                "mean_coherence": avg_coh,
                "mean_reward": avg_reward,
            },
            checkpoint_path=str(save_path),
            improved=avg_coh > 0.5,
        )
