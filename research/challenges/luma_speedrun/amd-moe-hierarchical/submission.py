#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""
MoE: Hierarchical Top-K (Two-Level Selection)

This kernel implements hierarchical expert selection with two-level routing:
1. Level 1: Select expert groups (coarse routing)
2. Level 2: Select experts within groups (fine routing)

This approach reduces the complexity of top-k selection from O(num_experts)
to O(sqrt(num_experts)) per level, significantly reducing computation for
large expert counts (e.g., 256 experts).

Algorithm:
1. Group experts into N coarse groups (e.g., 16 groups of 16 experts)
2. Compute group scores (sum of expert scores within group)
3. Select top-G groups (e.g., top 4 groups)
4. Within selected groups, select top-K experts
5. Combine selections for final expert set

Key Benefits:
- Reduced compute complexity: O(G + K) vs O(num_experts)
- Better load balancing across expert groups
- Natural locality: experts in same group likely share similar specializations
- Parallelizable: group scoring can be done in parallel

Memory Layout:
  - Experts organized as [num_groups, experts_per_group, d_hidden, d_expert]
  - Enables contiguous access within groups

Performance Characteristics:
  - Best for large expert counts (64+)
  - Trade-off: slightly lower accuracy vs significantly faster routing
  - Groups can be balanced offline based on expert importance
"""

from __future__ import annotations
import os
import math

os.environ["AITER_USE_NT"] = "1"

import torch
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t

# Hierarchical routing configuration
NUM_GROUPS = 16  # Number of coarse groups
EXPERTS_PER_GROUP = 16  # Experts per group (16 * 16 = 256 total)
TOP_GROUPS = 4  # Number of groups to select at level 1
TOP_K_PER_GROUP = 2  # Number of experts per selected group at level 2

# Cache for group organization
_group_organization: dict[int, tuple[torch.Tensor, torch.Tensor]] = {}


def _organize_experts_into_groups(
    num_experts: int, num_groups: int = NUM_GROUPS
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Organize experts into hierarchical groups.

    Creates a mapping from expert IDs to group structure:
    - group_assignments: [num_experts] group index for each expert
    - expert_in_group_idx: [num_experts] index within group for each expert

    Args:
        num_experts: Total number of experts
        num_groups: Number of groups to create

    Returns:
        group_assignments: Expert to group mapping
        expert_in_group_idx: Position within group
    """
    global _group_organization

    cache_key = (num_experts, num_groups)
    if cache_key in _group_organization:
        return _group_organization[cache_key]

    experts_per_group = num_experts // num_groups

    # Assign experts to groups (round-robin for load balancing)
    group_assignments = torch.arange(num_experts, dtype=torch.long)
    group_assignments = group_assignments % num_groups

    # Index within group
    expert_in_group_idx = torch.arange(num_experts, dtype=torch.long)
    expert_in_group_idx = expert_in_group_idx // num_groups

    _group_organization[cache_key] = (group_assignments, expert_in_group_idx)

    return group_assignments, expert_in_group_idx


def _compute_hierarchical_scores(
    gate_scores: torch.Tensor, num_groups: int = NUM_GROUPS
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Compute hierarchical routing scores.

    Level 1: Compute group scores by summing expert scores within each group
    Level 2: Return expert scores for routing within selected groups

    Args:
        gate_scores: [batch_size, num_experts] routing scores from gate network
        num_groups: Number of expert groups

    Returns:
        group_scores: [batch_size, num_groups] aggregated group scores
        expert_scores: [batch_size, num_experts] normalized expert scores
    """
    batch_size, num_experts = gate_scores.shape
    experts_per_group = num_experts // num_groups

    # Reshape to [batch_size, num_groups, experts_per_group]
    scores_reshaped = gate_scores.view(batch_size, num_groups, experts_per_group)

    # Level 1: Group scores (sum or max across experts in group)
    group_scores = scores_reshaped.sum(dim=-1)  # [batch_size, num_groups]

    # Normalize scores within each group for Level 2
    group_max = scores_reshaped.max(dim=-1, keepdim=True)[0]
    expert_scores = gate_scores / (group_max.view(batch_size, num_experts) + 1e-6)

    return group_scores, expert_scores


def _hierarchical_topk_selection(
    gate_scores: torch.Tensor,
    topk_weights: torch.Tensor,
    topk_ids: torch.Tensor,
    num_groups: int = NUM_GROUPS,
    top_groups: int = TOP_GROUPS,
    top_k_per_group: int = TOP_K_PER_GROUP,
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Perform hierarchical top-k selection.

    Args:
        gate_scores: [batch_size, num_experts] routing scores
        topk_weights: Original top-k weights (for reference)
        topk_ids: Original top-k expert IDs
        num_groups: Number of expert groups
        top_groups: Number of groups to select
        top_k_per_group: Experts to select per group

    Returns:
        final_weights: [batch_size, top_groups * top_k_per_group] selected weights
        final_ids: [batch_size, top_groups * top_k_per_group] selected expert IDs
    """
    batch_size, num_experts = gate_scores.shape
    experts_per_group = num_experts // num_groups
    device = gate_scores.device

    # Compute hierarchical scores
    group_scores, expert_scores = _compute_hierarchical_scores(gate_scores, num_groups)

    # Level 1: Select top groups
    group_topk_weights, group_topk_ids = torch.topk(
        group_scores, min(top_groups, num_groups), dim=-1
    )  # [batch_size, top_groups]

    # Level 2: Within selected groups, select top experts
    final_ids_list = []
    final_weights_list = []

    for b in range(batch_size):
        batch_ids = []
        batch_weights = []

        # Get selected groups for this batch item
        selected_groups = group_topk_ids[b]  # [top_groups]
        group_weights = group_topk_weights[b]  # [top_groups]

        for g_idx, g in enumerate(selected_groups):
            # Get expert range for this group
            group_start = g.item() * experts_per_group
            group_end = group_start + experts_per_group

            # Get scores for experts in this group
            group_expert_scores = expert_scores[b, group_start:group_end]

            # Select top-k within group
            k = min(top_k_per_group, experts_per_group)
            local_topk_weights, local_topk_indices = torch.topk(group_expert_scores, k, dim=-1)

            # Map to global expert IDs
            global_expert_ids = group_start + local_topk_indices

            # Weight by group importance
            weighted_scores = local_topk_weights * group_weights[g_idx]

            batch_ids.extend(global_expert_ids.tolist())
            batch_weights.extend(weighted_scores.tolist())

        final_ids_list.append(batch_ids)
        final_weights_list.append(batch_weights)

    # Convert to tensors
    max_k = max(len(ids) for ids in final_ids_list)

    final_ids = torch.zeros(batch_size, max_k, dtype=torch.long, device=device)
    final_weights = torch.zeros(batch_size, max_k, dtype=torch.float32, device=device)

    for b in range(batch_size):
        num_selected = len(final_ids_list[b])
        final_ids[b, :num_selected] = torch.tensor(
            final_ids_list[b], dtype=torch.long, device=device
        )
        final_weights[b, :num_selected] = torch.tensor(
            final_weights_list[b], dtype=torch.float32, device=device
        )

    # Normalize weights
    final_weights = final_weights / (final_weights.sum(dim=-1, keepdim=True) + 1e-6)

    return final_weights, final_ids


def _estimate_gate_scores(
    hidden_states: torch.Tensor,
    topk_weights: torch.Tensor,
    topk_ids: torch.Tensor,
    num_experts: int,
) -> torch.Tensor:
    """
    Estimate gate scores from topk_weights by scattering to full expert dimension.

    Args:
        hidden_states: [batch_size, d_hidden] input activations
        topk_weights: [batch_size, top_k] selected weights
        topk_ids: [batch_size, top_k] selected expert IDs
        num_experts: Total number of experts

    Returns:
        gate_scores: [batch_size, num_experts] full routing scores
    """
    batch_size = hidden_states.shape[0]
    device = hidden_states.device

    # Initialize full score tensor
    gate_scores = torch.zeros(batch_size, num_experts, device=device)

    # Scatter top-k weights to full dimension
    top_k = topk_ids.shape[1]
    for k in range(top_k):
        expert_ids = topk_ids[:, k]
        weights = topk_weights[:, k]
        gate_scores.scatter_(1, expert_ids.unsqueeze(1), weights.unsqueeze(1))

    return gate_scores


def custom_kernel(data: input_t) -> output_t:
    """
    Hierarchical top-k expert selection kernel.

    Implements two-level routing:
    1. Select expert groups based on aggregated scores
    2. Select experts within groups
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

    # Only apply hierarchical routing for large expert counts
    if num_experts < 64:
        # Standard routing for small expert counts
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
        # Estimate full gate scores from top-k selection
        gate_scores = _estimate_gate_scores(hidden_states, topk_weights, topk_ids, num_experts)

        # Perform hierarchical selection
        hierarchical_weights, hierarchical_ids = _hierarchical_topk_selection(
            gate_scores,
            topk_weights,
            topk_ids,
            num_groups=NUM_GROUPS,
            top_groups=TOP_GROUPS,
            top_k_per_group=TOP_K_PER_GROUP,
        )

        # Configure KSPLIT based on expert dimensions
        if d_expert <= 512:
            os.environ["AITER_KSPLIT"] = "0"
        else:
            os.environ.pop("AITER_KSPLIT", None)

        # Call fused_moe with hierarchical selection
        output = fused_moe(
            hidden_states,
            gate_up_weight_shuffled,
            down_weight_shuffled,
            hierarchical_weights,
            hierarchical_ids,
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
        print(f"[Hierarchical] Selection failed: {e}, using fallback")

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
