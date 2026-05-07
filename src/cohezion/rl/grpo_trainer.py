"""GRPO Trainer for Cohezion - DeepSeek-R1 style Group Relative Policy Optimization.

Implementation based on "DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via
Reinforcement Learning" (2025). Key innovation: eliminates critic model entirely by
using group-based baseline (mean of group rewards).

Key differences from PPO:
- No critic model (2x memory savings)
- Group-based advantage instead of GAE
- Simpler, more stable training

Usage:
    trainer = GRPOTrainer(
        model=model,
        ref_model=ref_model,
        group_size=16,
        learning_rate=1e-6,
    )

    for batch in dataloader:
        metrics = trainer.train_step(batch)

Architecture:
    ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
    │   Prompt    │────→│ Policy Model │────→│  Group of   │
    └─────────────┘     └──────────────┘     │  N samples  │
                                             └──────┬──────┘
                                                    │
                          ┌─────────────────────────┘
                          ▼
                    ┌────────────┐
                    │   Reward   │
                    │  Model     │
                    └─────┬──────┘
                          │
                          ▼
                    ┌──────────────┐
                    │Group baseline│
                    │(mean reward) │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ GRPO Loss    │
                    │ (no critic!) │
                    └──────────────┘
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from torch.optim import AdamW
from torch.utils.data import DataLoader


logger = logging.getLogger(__name__)


@dataclass
class GRPOConfig:
    """Configuration for GRPO training.

    Reference: DeepSeek-R1 technical report (2025)
    """

    # Group sampling
    group_size: int = 16  # Number of samples per prompt
    max_new_tokens: int = 1024
    temperature: float = 0.9

    # Training
    learning_rate: float = 1e-6
    batch_size: int = 1  # One prompt per batch (with group_size samples)
    num_epochs: int = 3
    gradient_accumulation_steps: int = 4

    # GRPO specific
    beta: float = 0.04  # KL penalty coefficient (DeepSeek-R1 default)
    epsilon: float = 0.2  # Clipping parameter (like PPO)

    # Advantage normalization
    normalize_advantage: bool = True

    # Logging
    log_interval: int = 10

    def __post_init__(self):
        logger.info(
            f"GRPO Config: group_size={self.group_size}, beta={self.beta}, lr={self.learning_rate}"
        )


@dataclass
class GRPOMetrics:
    """Training metrics for GRPO."""

    step: int
    loss: float
    policy_loss: float
    kl_loss: float
    mean_reward: float
    std_reward: float
    mean_advantage: float
    grad_norm: float | None = None

    def to_dict(self) -> dict[str, float]:
        return {
            "step": self.step,
            "loss": self.loss,
            "policy_loss": self.policy_loss,
            "kl_loss": self.kl_loss,
            "mean_reward": self.mean_reward,
            "std_reward": self.std_reward,
            "mean_advantage": self.mean_advantage,
            "grad_norm": self.grad_norm or 0.0,
        }


class GRPOTrainer:
    """Group Relative Policy Optimization trainer.

    Eliminates critic model by using group-level baseline - simply the
    mean reward of the group. This is the key innovation from DeepSeek-R1.

    Args:
        model: Policy model (typically LoRA-adapted)
        ref_model: Reference model for KL penalty (frozen)
        config: GRPOConfig instance
        reward_fn: Function to compute rewards from completions
    """

    def __init__(
        self,
        model: torch.nn.Module,
        ref_model: torch.nn.Module,
        config: GRPOConfig | None = None,
        reward_fn: Callable[[list[str]], torch.Tensor] | None = None,
    ):
        self.model = model
        self.ref_model = ref_model
        self.config = config or GRPOConfig()
        self.reward_fn = reward_fn

        # Freeze reference model
        for param in self.ref_model.parameters():
            param.requires_grad = False

        # Optimizer
        self.optimizer = AdamW(
            self.model.parameters(),
            lr=self.config.learning_rate,
        )

        self.global_step = 0

    async def train_step(
        self,
        batch: dict[str, Any],
    ) -> GRPOMetrics:
        """Single GRPO training step.

        Args:
            batch: Dict with keys:
                - "prompts": List of prompt strings
                - "completions": List of completion strings (group_size per prompt)
                - "rewards": Tensor of rewards [batch_size * group_size]

        Returns:
            GRPOMetrics with training stats
        """
        self.model.train()

        prompts = batch["prompts"]
        completions = batch["completions"]  # Flattened: [batch * group]
        rewards = batch["rewards"].to(self.model.device)

        batch_size = len(prompts)
        group_size = self.config.group_size

        # Compute group-based advantages (the key innovation)
        advantages = self._compute_group_advantages(rewards, batch_size, group_size)

        # Compute log probabilities under current policy
        log_probs = self._compute_log_probs(prompts, completions, batch_size, group_size)

        # Compute log probs under reference policy
        with torch.no_grad():
            ref_log_probs = self._compute_ref_log_probs(
                prompts, completions, batch_size, group_size
            )

        # Compute KL penalty
        kl_penalty = log_probs - ref_log_probs  # log(π/π_ref)

        # GRPO objective: clipped policy gradient + KL penalty
        # Ratio for clipping
        ratio = torch.exp(log_probs - log_probs.detach())  # π_θ / π_old ≈ 1 in first iter

        # Surrogate loss with clipping
        surr1 = ratio * advantages
        surr2 = torch.clamp(ratio, 1 - self.config.epsilon, 1 + self.config.epsilon) * advantages
        policy_loss = -torch.min(surr1, surr2).mean()

        # KL penalty (from DeepSeek-R1)
        kl_loss = self.config.beta * kl_penalty.mean()

        # Total loss
        loss = policy_loss + kl_loss

        # Backward pass
        self.optimizer.zero_grad()
        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
        self.optimizer.step()

        self.global_step += 1

        return GRPOMetrics(
            step=self.global_step,
            loss=loss.item(),
            policy_loss=policy_loss.item(),
            kl_loss=kl_loss.item(),
            mean_reward=rewards.mean().item(),
            std_reward=rewards.std().item(),
            mean_advantage=advantages.mean().item(),
            grad_norm=grad_norm.item(),
        )

    def _compute_group_advantages(
        self,
        rewards: torch.Tensor,
        batch_size: int,
        group_size: int,
    ) -> torch.Tensor:
        """Compute advantages using group mean as baseline.

        This eliminates the need for a critic model - we simply use
        the mean reward of the group as the value estimate.

        Args:
            rewards: [batch_size * group_size] tensor

        Returns:
            advantages: [batch_size * group_size] tensor
        """
        # Reshape to [batch_size, group_size]
        rewards_grouped = rewards.view(batch_size, group_size)

        # Group mean as baseline
        group_means = rewards_grouped.mean(dim=1, keepdim=True)

        # Advantage = reward - baseline
        advantages = rewards_grouped - group_means

        # Normalize (optional but recommended)
        if self.config.normalize_advantage:
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        return advantages.view(-1)

    def _compute_log_probs(
        self,
        prompts: list[str],
        completions: list[str],
        batch_size: int,
        group_size: int,
    ) -> torch.Tensor:
        """Compute log probabilities of completions under policy."""
        # This is a simplified version - real implementation would tokenize
        # and compute log probs properly

        # Placeholder: return random log probs for structure
        # Real implementation needs model forward pass
        return torch.randn(batch_size * group_size, device=self.model.device) * 0.1

    def _compute_ref_log_probs(
        self,
        prompts: list[str],
        completions: list[str],
        batch_size: int,
        group_size: int,
    ) -> torch.Tensor:
        """Compute log probabilities under reference model."""
        # Same as above but with frozen ref_model
        with torch.no_grad():
            return torch.randn(batch_size * group_size, device=self.ref_model.device) * 0.1

    async def generate_group_samples(
        self,
        prompt: str,
        tokenizer: Any,
    ) -> tuple[list[str], torch.Tensor]:
        """Generate N samples from prompt for group training.

        Args:
            prompt: Input prompt string
            tokenizer: Tokenizer for the model

        Returns:
            completions: List of N completion strings
            log_probs: Log probabilities of completions
        """
        # Tokenize
        inputs = tokenizer(prompt, return_tensors="pt").to(self.model.device)

        completions = []
        log_probs_list = []

        for _ in range(self.config.group_size):
            with torch.no_grad():
                # Generate with temperature
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=self.config.max_new_tokens,
                    temperature=self.config.temperature,
                    do_sample=True,
                )

                # Decode
                completion = tokenizer.decode(outputs[0], skip_special_tokens=True)
                completions.append(completion)

                # Approximate log prob
                log_probs_list.append(torch.tensor(0.0))

        return completions, torch.stack(log_probs_list)

    def save_checkpoint(self, path: str | Path) -> None:
        """Save model checkpoint."""
        torch.save(
            {
                "model_state_dict": self.model.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
                "global_step": self.global_step,
                "config": self.config,
            },
            path,
        )
        logger.info(f"Checkpoint saved: {path}")

    def load_checkpoint(self, path: str | Path) -> None:
        """Load model checkpoint."""
        checkpoint = torch.load(path, map_location="cpu")
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.global_step = checkpoint["global_step"]
        logger.info(f"Checkpoint loaded: {path}")


class AsyncGRPOTrainer(GRPOTrainer):
    """Async-compatible GRPO trainer for Cohezion integration."""

    async def train_epoch(
        self,
        dataloader: DataLoader,
        reward_fn: Callable[[list[str]], torch.Tensor],
    ) -> dict[str, float]:
        """Train for one epoch asynchronously.

        Args:
            dataloader: DataLoader yielding (prompt, completion_groups, reward_groups)
            reward_fn: Function to compute rewards

        Returns:
            Epoch metrics
        """
        epoch_metrics = {
            "loss": [],
            "mean_reward": [],
            "kl_div": [],
        }

        for batch_idx, batch in enumerate(dataloader):
            # Async-friendly batch processing
            metrics = await self.train_step(batch)

            epoch_metrics["loss"].append(metrics.loss)
            epoch_metrics["mean_reward"].append(metrics.mean_reward)
            epoch_metrics["kl_div"].append(metrics.kl_loss)

            if batch_idx % self.config.log_interval == 0:
                logger.info(
                    f"Step {metrics.step}: "
                    f"loss={metrics.loss:.4f}, "
                    f"reward={metrics.mean_reward:.4f}"
                )

        return {k: sum(v) / len(v) for k, v in epoch_metrics.items()}


# Factory for Cohezion integration
def create_grpo_trainer(
    model: torch.nn.Module,
    ref_model: torch.nn.Module,
    **config_overrides,
) -> AsyncGRPOTrainer:
    """Factory function for Cohezion integration.

    Usage:
        trainer = create_grpo_trainer(
            model=lora_model,
            ref_model=base_model,
            group_size=16,
            learning_rate=1e-6,
        )
    """
    config = GRPOConfig(**config_overrides)
    return AsyncGRPOTrainer(model, ref_model, config)


# Backwards compatibility
default_grpo = None
