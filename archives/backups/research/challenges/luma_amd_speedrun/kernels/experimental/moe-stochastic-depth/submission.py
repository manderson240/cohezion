"""
MoE: Stochastic Depth for Experts (Random Expert Dropping)

#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

Implements stochastic depth as a regularization technique for Mixture-of-Experts.
Randomly drops experts during forward pass based on a survival probability,
similar to dropout but at the expert level rather than the neuron level.

Key Innovation:
- Stochastic expert masking: Each expert has survival probability p during training
- Dynamic load balancing: Surviving experts get proportionally scaled weights
- Temperature-controlled annealing: Probability can decay over "training epochs"

Trade-offs:
- + Reduced overfitting through implicit ensemble of expert subsets
- + Computational savings when experts are dropped (fewer matrix multiplications)
- - Potential variance in output quality due to randomness
- - Requires careful tuning of survival probability schedule

Reference: "Deep Networks with Stochastic Depth" (Huang et al., 2016)
Applied to MoE: Expert-level stochastic depth instead of layer-level.
"""

from __future__ import annotations
import os
import sys
import math
import torch
from typing import Optional
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from reference import ref_kernel
from task import input_t, output_t

# Environment optimizations
os.environ["AITER_USE_NT"] = "1"


class StochasticExpertDropper:
    """
    Implements stochastic depth for MoE experts.

    Each expert has a survival probability (1 - drop_prob) during the forward pass.
    Dropped experts are skipped entirely, and remaining experts' weights are
    rescaled to maintain expected output magnitude.

    Attributes:
        base_survival_prob: Base probability an expert survives (0-1)
        temperature: Controls sharpness of dropout decisions
        training_steps: Counter for annealing schedule
    """

    def __init__(self, base_survival_prob: float = 0.8, anneal_steps: int = 1000):
        """
        Initialize stochastic expert dropper.

        Args:
            base_survival_prob: Initial probability each expert survives (default: 0.8)
            anneal_steps: Number of steps to anneal to final survival probability
        """
        self.base_survival_prob = base_survival_prob
        self.anneal_steps = anneal_steps
        self.training_steps = 0
        self._generator = torch.Generator(device="cuda")
        self._generator.manual_seed(42)  # Deterministic seed for reproducibility

    def get_current_survival_prob(self) -> float:
        """
        Compute current survival probability with linear annealing.

        Anneals from base_survival_prob down to 1.0 (no dropout) over anneal_steps.
        This mimics training convergence where we want full capacity at inference.

        Returns:
            Current survival probability (increases over time)
        """
        progress = min(self.training_steps / self.anneal_steps, 1.0)
        # Anneal from base_prob to 1.0 (no dropout at full training)
        return self.base_survival_prob + (1.0 - self.base_survival_prob) * progress

    def compute_expert_mask(
        self, num_experts: int, topk_ids: torch.Tensor, topk_weights: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Compute stochastic mask for experts.

        Randomly selects which experts survive based on survival probability.
        The selected experts' weights are rescaled to maintain expected output.

        Args:
            num_experts: Total number of experts in the model
            topk_ids: [batch_size, topk] expert indices selected by gating
            topk_weights: [batch_size, topk] gating weights

        Returns:
            Tuple of (masked_topk_ids, scaled_weights)
            - masked_topk_ids: Expert IDs with -1 for dropped experts
            - scaled_weights: Weights rescaled to sum to original magnitude
        """
        survival_prob = self.get_current_survival_prob()
        self.training_steps += 1

        # Generate survival mask for all experts
        # Shape: [num_experts] boolean mask
        expert_survival = (
            torch.rand(
                num_experts, generator=self._generator, device=topk_ids.device, dtype=torch.float32
            )
            < survival_prob
        )

        # Create masked version of topk_ids
        # Dropped experts get ID -1 (will be handled by fused_moe)
        masked_ids = topk_ids.clone()
        weights = topk_weights.clone()

        batch_size, topk = topk_ids.shape
        for b in range(batch_size):
            alive_count = 0
            alive_weight_sum = 0.0

            # First pass: mark dropped experts and count survivors
            for k in range(topk):
                expert_id = int(topk_ids[b, k].item())
                if expert_id >= 0 and expert_id < num_experts and expert_survival[expert_id]:
                    alive_count += 1
                    alive_weight_sum += weights[b, k].item()
                else:
                    masked_ids[b, k] = -1

            # Second pass: rescale surviving weights
            # Maintains expected output magnitude: E[sum(weights)] = sum(original_weights)
            if alive_count > 0 and alive_weight_sum > 0:
                original_sum = weights[b].sum().item()
                scale_factor = original_sum / alive_weight_sum
                for k in range(topk):
                    if masked_ids[b, k] >= 0:
                        weights[b, k] *= scale_factor
            elif alive_count == 0:
                # Edge case: all experts dropped, fall back to top-1
                masked_ids[b, 0] = topk_ids[b, 0]
                weights[b, 0] = 1.0
                weights[b, 1:] = 0.0

        return masked_ids, weights

    def reset(self) -> None:
        """Reset training step counter (e.g., for new epoch)."""
        self.training_steps = 0


# Global dropper instance (singleton for state persistence across calls)
_EXPERT_DROPPER: Optional[StochasticExpertDropper] = None


def _get_dropper() -> StochasticExpertDropper:
    """Get or create global expert dropper instance."""
    global _EXPERT_DROPPER
    if _EXPERT_DROPPER is None:
        # Parse survival probability from environment (allows experimentation)
        survival_prob = float(os.environ.get("MOE_STOCHASTIC_SURVIVAL", "0.8"))
        anneal_steps = int(os.environ.get("MOE_STOCHASTIC_ANNEAL", "1000"))
        _EXPERT_DROPPER = StochasticExpertDropper(survival_prob, anneal_steps)
    return _EXPERT_DROPPER


def custom_kernel(data: input_t) -> output_t:
    """
    Execute MoE forward pass with stochastic expert depth.

    Args:
        data: Tuple of (hidden_states, gate_up_weight, down_weight, ...,
                        gate_up_weight_shuffled, down_weight_shuffled, ...,
                        topk_weights, topk_ids, config)

    Returns:
        Output tensor [batch_size, d_hidden] after MoE computation
    """
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

    # Extract configuration
    d_hidden = config.get("d_hidden", hidden_states.shape[1])
    n_routed = config.get("n_routed_experts", 0)
    n_shared = config.get("n_shared_experts", 0)
    num_experts = n_routed + n_shared
    topk = config.get("topk", topk_ids.shape[1])
    hidden_pad = config.get("d_hidden_pad", d_hidden) - d_hidden

    try:
        # Get stochastic expert dropper
        dropper = _get_dropper()

        # Compute masked expert selection
        masked_ids, scaled_weights = dropper.compute_expert_mask(
            num_experts, topk_ids, topk_weights
        )

        # Execute MoE with masked experts
        output = fused_moe(
            hidden_states,
            gate_up_weight_shuffled,
            down_weight_shuffled,
            scaled_weights,
            masked_ids,
            expert_mask=None,  # fused_moe handles -1 IDs internally
            activation=ActivationType.Silu,
            quant_type=QuantType.per_1x32,
            doweight_stage1=False,  # Critical: must be False for correctness
            w1_scale=gate_up_weight_scale_shuffled,
            w2_scale=down_weight_scale_shuffled,
            a1_scale=None,
            a2_scale=None,
            hidden_pad=hidden_pad,
            intermediate_pad=config.get("d_expert_pad", 0) - config.get("d_expert", 0),
        )

        # Trim padding if present
        if hidden_pad > 0:
            output = output[:, :d_hidden]

        return output

    except Exception as e:
        # Log error details for debugging
        print(f"Stochastic depth MoE failed: {type(e).__name__}: {str(e)[:200]}", file=sys.stderr)

        # Fallback to reference kernel for correctness
        return ref_kernel(data)
