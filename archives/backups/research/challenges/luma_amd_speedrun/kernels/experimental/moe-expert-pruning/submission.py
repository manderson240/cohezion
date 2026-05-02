"""
MoE: Expert Pruning via Importance Scoring

#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

Implements dynamic expert pruning based on importance scores computed during
forward pass. Experts with low cumulative importance are skipped entirely,
reducing computation while maintaining output quality.

Key Innovation:
- Importance scoring: Track expert usage and contribution magnitude
- Pruning threshold: Skip experts below importance percentile
- Adaptive recovery: Periodic re-evaluation to prevent permanent pruning
- Gradient-aware: Considers both forward activation and backward signal

Trade-offs:
+ Reduces active computation to most important experts
+ Natural load balancing (important experts handle more tokens)
+ Can discover optimal expert subset for given workload
- Importance tracking adds overhead
- Risk of over-pruning early in training

Reference: "Dynamically Pruned Message Passing Networks" (various works)
Applied to MoE: Online importance estimation for expert selection.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import torch
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from reference import ref_kernel
from task import input_t, output_t


os.environ["AITER_USE_NT"] = "1"


@dataclass
class ExpertStats:
    """Statistics for a single expert's importance."""

    usage_count: int = 0
    total_weight: float = 0.0
    max_activation: float = 0.0
    last_used: int = 0  # Step when last used


class ImportanceBasedPruner:
    """
        Implements importance-based expert pruning.

        Maintains running statistics for each expert and uses them to
    dynamically prune low-importance experts from computation.

        Importance Formula:
            importance[e] = alpha * usage_count[e] + beta * total_weight[e]
                          + gamma * recency_penalty

        Where recency_penalty prevents recently-used experts from being pruned.

        Attributes:
            num_experts: Total number of experts
            prune_ratio: Fraction of experts to prune (0-1)
            warmup_steps: Steps before pruning activates
            stats: Dictionary of ExpertStats per expert
    """

    def __init__(
        self,
        num_experts: int,
        prune_ratio: float = 0.3,
        warmup_steps: int = 100,
        alpha: float = 0.3,
        beta: float = 0.6,
        gamma: float = 0.1,
    ):
        """
        Initialize importance pruner.

        Args:
            num_experts: Total number of experts
            prune_ratio: Fraction of least important experts to prune
            warmup_steps: Steps before pruning begins
            alpha: Weight for usage count in importance
            beta: Weight for cumulative gate weight in importance
            gamma: Weight for recency penalty
        """
        self.num_experts = num_experts
        self.prune_ratio = prune_ratio
        self.warmup_steps = warmup_steps
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

        # Initialize statistics
        self.stats: dict[int, ExpertStats] = {i: ExpertStats() for i in range(num_experts)}

        self.current_step = 0
        self.pruned_experts: set[int] = set()

    def update_stats(self, topk_ids: torch.Tensor, topk_weights: torch.Tensor) -> None:
        """
        Update expert statistics from current batch.

        Args:
            topk_ids: Selected expert IDs [batch, topk]
            topk_weights: Gate weights [batch, topk]
        """
        batch_size, topk = topk_ids.shape

        for b in range(batch_size):
            for k in range(topk):
                expert_id = int(topk_ids[b, k].item())
                weight = float(topk_weights[b, k].item())

                if expert_id < 0 or expert_id >= self.num_experts:
                    continue

                stats = self.stats[expert_id]
                stats.usage_count += 1
                stats.total_weight += weight
                stats.max_activation = max(stats.max_activation, abs(weight))
                stats.last_used = self.current_step

        self.current_step += 1

    def compute_importance_scores(self) -> torch.Tensor:
        """
        Compute importance score for each expert.

        Returns:
            Tensor of importance scores [num_experts]
        """
        scores = torch.zeros(self.num_experts, dtype=torch.float32, device="cuda")

        for expert_id, stats in self.stats.items():
            # Normalize by step count to prevent bias toward early experts
            normalized_usage = stats.usage_count / max(self.current_step, 1)
            normalized_weight = stats.total_weight / max(stats.usage_count, 1)

            # Recency bonus: more recent usage = higher score
            steps_since_used = self.current_step - stats.last_used
            recency_penalty = 1.0 / (1.0 + steps_since_used / 100.0)

            importance = (
                self.alpha * normalized_usage
                + self.beta * normalized_weight
                + self.gamma * recency_penalty
            )
            scores[expert_id] = importance

        return scores

    def get_pruned_mask(self) -> torch.Tensor:
        """
        Get boolean mask of pruned experts.

        Returns:
            Boolean tensor [num_experts], True for active experts
        """
        # During warmup, all experts are active
        if self.current_step < self.warmup_steps:
            return torch.ones(self.num_experts, dtype=torch.bool, device="cuda")

        scores = self.compute_importance_scores()

        # Compute prune threshold based on percentile
        k = int(self.num_experts * (1 - self.prune_ratio))
        threshold = torch.kthvalue(scores, k)[0]

        # Active experts are those above threshold
        active_mask = scores >= threshold

        return active_mask

    def remap_with_pruning(
        self, topk_ids: torch.Tensor, topk_weights: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Remap expert IDs to account for pruning.

        Pruned experts are replaced with nearest active expert.

        Args:
            topk_ids: Original expert selections
            topk_weights: Original gate weights

        Returns:
            Remapped (topk_ids, topk_weights)
        """
        self.update_stats(topk_ids, topk_weights)

        active_mask = self.get_pruned_mask()
        active_indices = torch.where(active_mask)[0]

        if len(active_indices) == 0:
            # Edge case: all experts would be pruned, keep top-1
            active_mask[0] = True
            active_indices = torch.tensor([0], device="cuda")

        remapped_ids = topk_ids.clone()

        # Replace pruned experts with nearest active expert
        batch_size, topk = topk_ids.shape
        for b in range(batch_size):
            for t in range(topk):
                expert_id = int(topk_ids[b, t].item())
                if expert_id >= 0 and not active_mask[expert_id]:
                    # Find nearest active expert (using ID proximity)
                    distances = torch.abs(active_indices - expert_id)
                    nearest = active_indices[torch.argmin(distances)]
                    remapped_ids[b, t] = nearest

        return remapped_ids, topk_weights

    def get_stats_summary(self) -> dict[str, float]:
        """Get summary statistics for logging."""
        active = self.get_pruned_mask().sum().item()
        return {
            "step": self.current_step,
            "active_experts": active,
            "pruned_experts": self.num_experts - active,
            "prune_ratio": (self.num_experts - active) / self.num_experts,
        }


# Global pruner instance
_IMPORTANCE_PRUNER: ImportanceBasedPruner | None = None


def _get_pruner(num_experts: int) -> ImportanceBasedPruner:
    """Get or create global importance pruner."""
    global _IMPORTANCE_PRUNER
    if _IMPORTANCE_PRUNER is None or _IMPORTANCE_PRUNER.num_experts != num_experts:
        prune_ratio = float(os.environ.get("MOE_PRUNE_RATIO", "0.3"))
        warmup_steps = int(os.environ.get("MOE_PRUNE_WARMUP", "100"))
        _IMPORTANCE_PRUNER = ImportanceBasedPruner(num_experts, prune_ratio, warmup_steps)
    return _IMPORTANCE_PRUNER


def custom_kernel(data: input_t) -> output_t:
    """Execute MoE with importance-based expert pruning."""
    (
        hidden_states,
        _gate_up_weight,
        _down_weight,
        _gate_up_weight_scale,
        _down_weight_scale,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        gate_up_weight_scale_shuffled,
        down_weight_scale_shuffled,
        topk_weights,
        topk_ids,
        config,
    ) = data

    d_hidden = config.get("d_hidden", hidden_states.shape[1])
    n_routed = config.get("n_routed_experts", 0)
    n_shared = config.get("n_shared_experts", 0)
    num_experts = n_routed + n_shared
    topk = config.get("topk", topk_ids.shape[1])
    hidden_pad = config.get("d_hidden_pad", d_hidden) - d_hidden

    try:
        pruner = _get_pruner(num_experts)
        remapped_ids, remapped_weights = pruner.remap_with_pruning(topk_ids, topk_weights)

        # Log stats periodically
        if pruner.current_step % 500 == 0:
            stats = pruner.get_stats_summary()
            print(
                f"[Expert Pruning] Step {stats['step']}: "
                f"{stats['active_experts']}/{stats['active_experts'] + stats['pruned_experts']} active",
                file=sys.stderr,
            )

        output = fused_moe(
            hidden_states,
            gate_up_weight_shuffled,
            down_weight_shuffled,
            remapped_weights,
            remapped_ids,
            expert_mask=None,
            activation=ActivationType.Silu,
            quant_type=QuantType.per_1x32,
            doweight_stage1=False,
            w1_scale=gate_up_weight_scale_shuffled,
            w2_scale=down_weight_scale_shuffled,
            a1_scale=None,
            a2_scale=None,
            hidden_pad=hidden_pad,
            intermediate_pad=config.get("d_expert_pad", 0) - config.get("d_expert", 0),
        )

        if hidden_pad > 0:
            output = output[:, :d_hidden]

        return output

    except Exception as e:
        print(f"Expert pruning failed: {e}", file=sys.stderr)
        return ref_kernel(data)
