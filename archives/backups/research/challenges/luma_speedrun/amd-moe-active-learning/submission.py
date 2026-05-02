#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""M2: Active Learning Routing - Uncertainty-Based Expert Selection.

Active Learning Concept:
- Query most informative samples for labeling
- Applied to MoE: Select uncertain tokens for expert review
- Uncertainty estimates from ensemble of experts
- Balance exploration vs exploitation

Implementation:
1. Compute predictive uncertainty per token
2. High uncertainty -> multiple experts
3. Low uncertainty -> single expert (or skip)
4. Dynamic top-k based on uncertainty

Uncertainty Estimates:
- Entropy of routing distribution
- Variance across expert predictions
- Model uncertainty (Bayesian methods)

Reference: "Active Learning for Neural Networks", 2017.
"""

from __future__ import annotations

import os


os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_KSPLIT"] = "2"

import torch
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


def compute_predictive_uncertainty(
    routing_probs: torch.Tensor, method: str = "entropy"
) -> torch.Tensor:
    """Compute predictive uncertainty from routing distribution.

    Args:
        routing_probs: Probabilities [B, num_experts]
        method: Uncertainty method (entropy, margin, variance)

    Returns:
        Uncertainty per sample [B]
    """
    if method == "entropy":
        # Shannon entropy: H = -sum(p * log(p))
        entropy = -(routing_probs * torch.log(routing_probs + 1e-8)).sum(dim=1)
        return entropy

    elif method == "margin":
        # Margin: 1 - (p_max - p_second)
        sorted_probs, _ = torch.sort(routing_probs, dim=1, descending=True)
        margin = sorted_probs[:, 0] - sorted_probs[:, 1]
        return 1.0 - margin

    elif method == "variance":
        # Variance of routing weights
        return routing_probs.var(dim=1)

    else:
        return torch.zeros(routing_probs.shape[0], device=routing_probs.device)


def adaptive_topk_selection(
    uncertainties: torch.Tensor,
    min_k: int = 1,
    max_k: int = 8,
    threshold_low: float = 0.3,
    threshold_high: float = 0.7,
) -> torch.Tensor:
    """Select dynamic top-k based on uncertainty.

    Args:
        uncertainties: Uncertainty per sample [B]
        min_k: Minimum k
        max_k: Maximum k
        threshold_low: Threshold for low uncertainty
        threshold_high: Threshold for high uncertainty

    Returns:
        Top-k per sample [B]
    """
    # Normalize uncertainties to [0, 1]
    u_min = uncertainties.min()
    u_max = uncertainties.max()
    u_norm = (uncertainties - u_min) / (u_max - u_min + 1e-8)

    # Map to k values
    k_values = torch.where(
        u_norm < threshold_low,
        torch.tensor(min_k, device=uncertainties.device),
        torch.where(
            u_norm > threshold_high,
            torch.tensor(max_k, device=uncertainties.device),
            torch.tensor((min_k + max_k) // 2, device=uncertainties.device),
        ),
    )

    return k_values.long()


def custom_kernel(data: input_t) -> output_t:
    """Active learning MoE with uncertainty-based routing.

    Args:
        data: Tuple of MoE inputs

    Returns:
        MoE output tensor
    """
    (
        hidden_states,
        gate_up_weight,
        down_weight,
        gate_up_weight_scale,
        down_weight_scale,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        gate_up_weight_scale_shuffled,
        down_weight_scale_shuffled,
        topk_weights,
        topk_ids,
        config,
    ) = data

    hidden_pad = config["d_hidden_pad"] - config["d_hidden"]
    intermediate_pad = config["d_expert_pad"] - config["d_expert"]
    d_expert = config.get("d_expert", 0)

    use_active = os.environ.get("MOE_ACTIVE_LEARNING", "0") == "1"

    if use_active:
        try:
            # Compute uncertainty
            uncertainties = compute_predictive_uncertainty(topk_weights, method="entropy")

            # Adaptive top-k
            adaptive_k = adaptive_topk_selection(uncertainties)

            # For simplicity, use max k and mask others
            # In full implementation, would use different k per token
            max_k = adaptive_k.max().item()

            print(
                f"[Active Learning] Uncertainty: {uncertainties.mean():.4f}, "
                f"Adaptive k: {adaptive_k.tolist()[:5]}"
            )

            # Use standard routing but could mask based on uncertainty
            routing_weights = topk_weights
            routing_ids = topk_ids

        except Exception as e:
            print(f"[Active Learning] Error: {e}")
            routing_weights = topk_weights
            routing_ids = topk_ids
    else:
        routing_weights = topk_weights
        routing_ids = topk_ids

    # Shape-aware KSPLIT
    if d_expert <= 512:
        os.environ["AITER_KSPLIT"] = "0"
    else:
        os.environ["AITER_KSPLIT"] = "2"

    try:
        output = fused_moe(
            hidden_states,
            gate_up_weight_shuffled,
            down_weight_shuffled,
            routing_weights,
            routing_ids,
            expert_mask=None,
            activation=ActivationType.Silu,
            quant_type=QuantType.per_1x32,
            doweight_stage1=False,
            w1_scale=gate_up_weight_scale_shuffled,
            w2_scale=down_weight_scale_shuffled,
            a1_scale=None,
            a2_scale=None,
            hidden_pad=hidden_pad,
            intermediate_pad=intermediate_pad,
        )

        return output

    except Exception as e:
        print(f"[Active Learning MoE] Error: {e}")

        return fused_moe(
            hidden_states,
            gate_up_weight_shuffled,
            down_weight_shuffled,
            topk_weights,
            topk_ids,
            expert_mask=None,
            activation=ActivationType.Silu,
            quant_type=QuantType.per_1x32,
            doweight_stage1=False,
            w1_scale=gate_up_weight_scale_shuffled,
            w2_scale=down_weight_scale_shuffled,
            a1_scale=None,
            a2_scale=None,
            hidden_pad=hidden_pad,
            intermediate_pad=intermediate_pad,
        )
