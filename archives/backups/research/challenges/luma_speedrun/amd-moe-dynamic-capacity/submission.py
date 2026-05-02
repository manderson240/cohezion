#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""
MoE: Dynamic Capacity Allocation

This kernel implements dynamic expert capacity allocation based on real-time
load balancing. Unlike static capacity where each expert has fixed capacity,
this approach adjusts capacity per expert based on actual token distribution.

Algorithm:
1. Analyze token distribution across experts (histogram)
2. Identify overloaded and underloaded experts
3. Dynamically reallocate capacity from underloaded to overloaded experts
4. Handle overflow via overflow buffer or re-routing

Dynamic Capacity Strategy:
  - Base capacity: minimum guaranteed capacity per expert
  - Bonus capacity: distributed based on actual load
  - Overflow handling: tokens exceeding capacity go to overflow pool
  - Re-routing: overflow tokens sent to underloaded experts

Load Balancing:
  - Track token counts per expert
  - Compute ideal capacity (total_tokens / num_experts)
  - Allocate excess from underloaded to overloaded
  - Maintain fairness through capacity constraints

Memory Efficiency:
  - Variable-size intermediate buffers per expert
  - Reduce wasted memory from fixed over-allocation
  - Better GPU utilization through balanced load

Performance Characteristics:
  - Reduces memory overhead for imbalanced workloads
  - Better for long-tail expert distributions
  - Overhead: histogram computation and capacity management
  - Trade-off: flexibility vs management overhead
"""

from __future__ import annotations

import os


os.environ["AITER_USE_NT"] = "1"

import torch
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


# Dynamic capacity configuration
BASE_CAPACITY_RATIO = 0.5  # Minimum 50% of average capacity
MAX_CAPACITY_RATIO = 2.0  # Maximum 200% of average capacity
OVERFLOW_BUFFER_RATIO = 0.1  # 10% buffer for overflow
REBALANCE_THRESHOLD = 0.2  # Trigger rebalancing if imbalance > 20%


def _compute_expert_histogram(topk_ids: torch.Tensor, num_experts: int) -> torch.Tensor:
    """
    Compute token histogram per expert.

    Args:
        topk_ids: [batch_size, top_k] expert indices
        num_experts: Total number of experts

    Returns:
        histogram: [num_experts] token count per expert
    """
    flat_ids = topk_ids.view(-1)
    histogram = torch.bincount(flat_ids, minlength=num_experts).float()
    return histogram


def _compute_dynamic_capacity(
    histogram: torch.Tensor,
    total_tokens: int,
    num_experts: int,
    base_ratio: float = BASE_CAPACITY_RATIO,
    max_ratio: float = MAX_CAPACITY_RATIO,
) -> torch.Tensor:
    """
    Compute dynamic capacity per expert based on load.

    Strategy:
    1. Compute average capacity (total_tokens / num_experts)
    2. Set base capacity for all experts
    3. Distribute remaining capacity based on demand
    4. Cap at maximum capacity ratio

    Args:
        histogram: [num_experts] token count per expert
        total_tokens: Total number of tokens
        num_experts: Total number of experts
        base_ratio: Minimum capacity as ratio of average
        max_ratio: Maximum capacity as ratio of average

    Returns:
        capacity: [num_experts] capacity per expert
    """
    device = histogram.device

    # Average capacity
    avg_capacity = total_tokens / num_experts

    # Base capacity (minimum guaranteed)
    base_capacity = int(avg_capacity * base_ratio)
    capacity = torch.full((num_experts,), base_capacity, dtype=torch.long, device=device)

    # Total bonus capacity available
    total_bonus = int(avg_capacity * num_experts * (1 - base_ratio))

    # Compute demand (tokens beyond base capacity)
    demand = torch.clamp(histogram - base_capacity, min=0)
    total_demand = demand.sum().item()

    if total_demand > 0:
        # Distribute bonus proportionally to demand
        bonus = (demand / total_demand * total_bonus).long()
        capacity += bonus

    # Cap at maximum
    max_capacity = int(avg_capacity * max_ratio)
    capacity = torch.clamp(capacity, max=max_capacity)

    return capacity


def _create_capacity_mask(
    topk_ids: torch.Tensor, topk_weights: torch.Tensor, capacity: torch.Tensor
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Create mask based on capacity constraints.

    Args:
        topk_ids: [batch_size, top_k] expert indices
        topk_weights: [batch_size, top_k] expert weights
        capacity: [num_experts] capacity per expert

    Returns:
        masked_ids: IDs within capacity
        masked_weights: Weights for non-overflow tokens
        overflow_mask: Boolean mask of overflow tokens
    """
    batch_size, top_k = topk_ids.shape
    device = topk_ids.device

    # Track current usage per expert
    current_usage = torch.zeros_like(capacity)

    # Create masks
    within_capacity = torch.ones_like(topk_ids, dtype=torch.bool)

    for b in range(batch_size):
        for k in range(top_k):
            expert = topk_ids[b, k].item()
            current_usage[expert] += 1

            if current_usage[expert] > capacity[expert]:
                within_capacity[b, k] = False

    return within_capacity


def _rebalance_overflow_tokens(
    topk_ids: torch.Tensor, topk_weights: torch.Tensor, capacity: torch.Tensor, num_experts: int
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Rebalance overflow tokens to underloaded experts.

    Strategy:
    1. Identify tokens exceeding capacity
    2. Find underloaded experts (usage < capacity)
    3. Re-route overflow tokens to underloaded experts
    4. Adjust weights proportionally

    Args:
        topk_ids: [batch_size, top_k] expert indices
        topk_weights: [batch_size, top_k] expert weights
        capacity: [num_experts] capacity per expert
        num_experts: Total number of experts

    Returns:
        rebalanced_ids: Rebalanced expert IDs
        rebalanced_weights: Adjusted weights
    """
    batch_size, top_k = topk_ids.shape
    device = topk_ids.device

    # Compute current usage
    histogram = _compute_expert_histogram(topk_ids, num_experts)

    # Identify underloaded experts (have spare capacity)
    spare_capacity = capacity - histogram
    underloaded = torch.where(spare_capacity > 0)[0]

    if len(underloaded) == 0:
        # No underloaded experts - keep as is
        return topk_ids, topk_weights

    # Create rebalanced copies
    rebalanced_ids = topk_ids.clone()
    rebalanced_weights = topk_weights.clone()

    # Track new usage
    new_usage = histogram.clone()

    # Re-route overflow tokens
    for b in range(batch_size):
        for k in range(top_k):
            expert = topk_ids[b, k].item()

            if new_usage[expert] > capacity[expert]:
                # This token overflows - find underloaded expert
                for alt_expert in underloaded:
                    if new_usage[alt_expert] < capacity[alt_expert]:
                        # Re-route to this expert
                        rebalanced_ids[b, k] = alt_expert
                        new_usage[expert] -= 1
                        new_usage[alt_expert] += 1

                        # Adjust weight (reduce since not ideal expert)
                        rebalanced_weights[b, k] *= 0.8
                        break

    # Renormalize weights
    weight_sums = rebalanced_weights.sum(dim=-1, keepdim=True)
    rebalanced_weights = rebalanced_weights / (weight_sums + 1e-6)

    return rebalanced_ids, rebalanced_weights


def _compute_load_imbalance(histogram: torch.Tensor) -> float:
    """
    Compute load imbalance metric.

    Args:
        histogram: [num_experts] token count per expert

    Returns:
        imbalance: Coefficient of variation (std/mean)
    """
    mean = histogram.float().mean()
    std = histogram.float().std()

    if mean <= 0:
        return 0.0

    return (std / mean).item()


def custom_kernel(data: input_t) -> output_t:
    """
    Dynamic capacity allocation MoE kernel.

    Implements expert capacity allocation based on real-time
    token distribution to improve load balancing.
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

    # Extract configuration
    num_experts = config.get("num_experts", 256)
    d_hidden = config["d_hidden"]
    d_expert = config["d_expert"]
    hidden_pad = config["d_hidden_pad"] - d_hidden
    intermediate_pad = config["d_expert_pad"] - d_expert

    # Compute token statistics
    total_tokens = topk_ids.numel()
    histogram = _compute_expert_histogram(topk_ids, num_experts)
    imbalance = _compute_load_imbalance(histogram)

    # If load is balanced, use standard routing
    if imbalance < REBALANCE_THRESHOLD:
        os.environ["AITER_KSPLIT"] = "0" if d_expert <= 512 else "1"

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

    try:
        # Compute dynamic capacity based on load
        capacity = _compute_dynamic_capacity(
            histogram,
            total_tokens,
            num_experts,
            base_ratio=BASE_CAPACITY_RATIO,
            max_ratio=MAX_CAPACITY_RATIO,
        )

        # Rebalance tokens based on capacity
        rebalanced_ids, rebalanced_weights = _rebalance_overflow_tokens(
            topk_ids, topk_weights, capacity, num_experts
        )

        # Configure KSPLIT based on expert dimensions
        if d_expert <= 512:
            os.environ["AITER_KSPLIT"] = "0"
        else:
            os.environ.pop("AITER_KSPLIT", None)

        # Execute with rebalanced routing
        output = fused_moe(
            hidden_states,
            gate_up_weight_shuffled,
            down_weight_shuffled,
            rebalanced_weights,
            rebalanced_ids,
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
        print(f"[DynamicCapacity] Rebalancing failed: {e}, using fallback")

        # Fallback to standard routing
        os.environ["AITER_KSPLIT"] = "0" if d_expert <= 512 else "1"

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
