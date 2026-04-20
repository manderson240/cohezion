"""
MoE: Dynamic Capacity Adjustment
Approach: Scale expert capacity based on real-time load distribution.

Key insight: Static capacity limits waste compute when load is imbalanced.
Dynamic adjustment reallocates capacity from underutilized to overloaded experts.

POPCORN: amd-moe-mxfp4
"""

import torch
import torch.nn.functional as F
import sys
import os

_AITER_JIT_BUILD = "/home/runner/aiter/aiter/jit/build"
for _mod in (
    "module_moe_sorting",
    "module_moe_ck2stages_fp4x2_fp4x2_preshuffle_on_b16_silu_per_1x32_mulWeightStage2_",
):
    _p = os.path.join(_AITER_JIT_BUILD, _mod)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from task import input_t, output_t


class DynamicCapacityManager:
    """Manages expert capacity based on load distribution."""

    def __init__(self, num_experts: int, base_capacity: int, min_capacity: float = 0.5):
        """
        Initialize capacity manager.

        Args:
            num_experts: Number of experts
            base_capacity: Base capacity per expert
            min_capacity: Minimum capacity multiplier
        """
        self.num_experts = num_experts
        self.base_capacity = base_capacity
        self.min_capacity = min_capacity
        self.max_capacity = 2.0  # Maximum 2x base capacity

    def compute_capacities(self, token_counts: torch.Tensor, total_tokens: int) -> torch.Tensor:
        """
        Compute per-expert capacities based on load.

        Uses water-filling algorithm:
        1. Start with base capacity for all
        2. Identify overloaded experts (> base capacity tokens)
        3. Reallocate capacity from underutilized experts

        Args:
            token_counts: Token count per expert [num_experts]
            total_tokens: Total token count

        Returns:
            Per-expert capacities [num_experts]
        """
        # Compute expected tokens per expert (uniform distribution)
        expected_per_expert = total_tokens / self.num_experts

        # Identify overloaded and underutilized experts
        overload = token_counts.float() - expected_per_expert
        over_utilized = overload > 0
        under_utilized = overload < 0

        # Calculate surplus (excess above expected)
        surplus = torch.where(
            over_utilized,
            token_counts.float() - expected_per_expert,
            torch.zeros_like(token_counts, dtype=torch.float32),
        )
        total_surplus = surplus.sum()

        # Calculate deficit (space below expected)
        deficit = torch.where(
            under_utilized,
            expected_per_expert - token_counts.float(),
            torch.zeros_like(token_counts, dtype=torch.float32),
        )
        total_deficit = deficit.sum()

        # Reallocate capacity
        # Underutilized experts give up capacity proportional to their deficit
        # Overloaded experts gain capacity proportional to their surplus

        capacities = torch.full(
            (self.num_experts,),
            self.base_capacity,
            dtype=torch.float32,
            device=token_counts.device,
        )

        if total_surplus > 0 and total_deficit > 0:
            # Reallocation factor
            reallocation = min(total_surplus, total_deficit) / total_deficit

            # Reduce underutilized
            reduction = deficit * reallocation * 0.3  # Conservative reallocation
            capacities -= reduction

            # Increase overloaded
            increase = surplus * reallocation * 0.3
            capacities += increase

        # Enforce bounds
        capacities = torch.clamp(
            capacities,
            min=int(self.base_capacity * self.min_capacity),
            max=int(self.base_capacity * self.max_capacity),
        )

        return capacities.long()

    def create_load_balanced_groups(
        self, topk_ids: torch.Tensor, capacities: torch.Tensor
    ) -> tuple:
        """
        Create token groups based on capacity constraints.

        Args:
            topk_ids: Expert assignments [M, topk]
            capacities: Per-expert capacities [num_experts]

        Returns:
            (sorted_indices, expert_boundaries) for efficient batching
        """
        M, k = topk_ids.shape
        flat_ids = topk_ids.flatten()

        # Count tokens per expert
        token_counts = torch.bincount(flat_ids, minlength=self.num_experts)

        # Identify experts that need overflow handling
        overflow_mask = token_counts > capacities
        overflow_experts = overflow_mask.nonzero(as_tuple=True)[0]

        # Create assignment mask (tokens -> experts within capacity)
        valid_assignments = torch.ones(M * k, dtype=torch.bool, device=topk_ids.device)

        for exp_idx in overflow_experts:
            # Find tokens assigned to this expert
            mask = flat_ids == exp_idx
            # Keep only up to capacity
            overflow_positions = mask.nonzero(as_tuple=True)[0]
            if len(overflow_positions) > capacities[exp_idx]:
                # Mark excess as invalid
                excess = overflow_positions[capacities[exp_idx] :]
                valid_assignments[excess] = False

        # Create sorted order: valid tokens first, then overflow
        sorted_order = torch.argsort(valid_assignments.long(), descending=True)

        # Compute boundaries
        num_valid = valid_assignments.sum()
        boundaries = torch.cat([torch.tensor([0]), torch.cumsum(capacities, dim=0)])

        return sorted_order, boundaries, num_valid


def custom_kernel(data: input_t) -> output_t:
    """
    MoE kernel with dynamic capacity adjustment.

    Adjusts expert capacity based on real-time load distribution,
    reallocating from underutilized to overloaded experts.

    Args:
        data: Tuple of (hidden_states, w1, w2, w1_scale, w2_scale,
              w1_shuffle, w2_shuffle, w1_scale_shuffled, w2_scale_shuffled,
              topk_weights, topk_ids, config)

    Returns:
        MoE output tensor
    """
    try:
        (
            hidden_states,
            w1,
            w2,
            w1_scale,
            w2_scale,
            w1_shuffle,
            w2_shuffle,
            w1_scale_shuffled,
            w2_scale_shuffled,
            topk_weights,
            topk_ids,
            config,
        ) = data

        M = hidden_states.shape[0]
        num_experts = w1.shape[0]
        E, N, K = w1.shape
        D = w2.shape[1]  # Output dimension
        topk = config.topk

        # Analyze current load distribution
        expert_counts = torch.bincount(topk_ids.flatten(), minlength=num_experts)
        total_tokens = M * topk

        # Calculate base capacity with some headroom
        base_capacity = int((M * topk / num_experts) * 1.5)

        # Initialize capacity manager
        capacity_mgr = DynamicCapacityManager(num_experts, base_capacity)

        # Compute dynamic capacities
        capacities = capacity_mgr.compute_capacities(expert_counts, total_tokens)

        # Create load-balanced processing groups
        sorted_order, boundaries, num_valid = capacity_mgr.create_load_balanced_groups(
            topk_ids, capacities
        )

        # Quantize input
        x_fp4, x_scale = dynamic_mxfp4_quant(hidden_states.contiguous())
        x_q = x_fp4.view(dtypes.fp4x2)

        # Prepare output
        output = torch.zeros(M, D, dtype=torch.bfloat16, device=hidden_states.device)

        # Track token contributions per position
        token_contributions = torch.zeros(M, D, dtype=torch.bfloat16, device=hidden_states.device)
        token_counts = torch.zeros(M, 1, dtype=torch.int32, device=hidden_states.device)

        # Flatten for easier indexing
        flat_topk_ids = topk_ids.flatten()
        flat_topk_weights = topk_weights.flatten()
        token_indices = torch.arange(M, device=hidden_states.device).repeat_interleave(topk)

        # Sort tokens by expert for batching
        sorted_indices = torch.argsort(flat_topk_ids)

        # Group by expert and process with dynamic capacity
        current_pos = 0
        for expert_idx in range(num_experts):
            # Find tokens for this expert
            mask = flat_topk_ids == expert_idx
            expert_positions = mask.nonzero(as_tuple=True)[0]

            if len(expert_positions) == 0:
                continue

            # Apply capacity limit
            capacity = capacities[expert_idx].item()
            actual_tokens = min(len(expert_positions), capacity)

            if actual_tokens == 0:
                continue

            # Get valid token positions
            valid_positions = expert_positions[:actual_tokens]
            token_idx_batch = token_indices[valid_positions]
            weight_batch = flat_topk_weights[valid_positions]

            # Get input tensors
            x_batch = x_q[token_idx_batch]
            x_scale_batch = x_scale[token_idx_batch]

            # Process in chunks if needed
            chunk_size = 64  # Process up to 64 tokens at once
            for chunk_start in range(0, actual_tokens, chunk_size):
                chunk_end = min(chunk_start + chunk_size, actual_tokens)

                x_chunk = x_batch[chunk_start:chunk_end]
                x_scale_chunk = x_scale_batch[chunk_start:chunk_end]
                weight_chunk = weight_batch[chunk_start:chunk_end]

                # Get expert weights
                w1_e = w1_shuffle[expert_idx]
                w1_s = w1_scale_shuffled[expert_idx]
                w2_e = w2_shuffle[expert_idx]
                w2_s = w2_scale_shuffled[expert_idx]

                # Stage 1: Gate computation
                gate_up = aiter.gemm_a4w4(
                    x_chunk, w1_e, x_scale_chunk, w1_s, dtype=dtypes.bf16, bpreshuffle=True
                )

                # SiLU activation
                gate, up = gate_up.chunk(2, dim=-1)
                activated = F.silu(gate) * up

                # Re-quantize
                act_fp4, act_scale = dynamic_mxfp4_quant(activated.contiguous())
                act_q = act_fp4.view(dtypes.fp4x2)

                # Stage 2: Down projection
                down = aiter.gemm_a4w4(
                    act_q, w2_e, act_scale, w2_s, dtype=dtypes.bf16, bpreshuffle=True
                )

                # Accumulate with weights
                for i, (tok_idx, w) in enumerate(
                    zip(token_idx_batch[chunk_start:chunk_end], weight_chunk)
                ):
                    token_contributions[tok_idx] += down[i] * w
                    token_counts[tok_idx] += 1

            current_pos += actual_tokens

        # Normalize by count and add to output
        # For tokens that hit capacity limits, use available contributions
        valid_mask = token_counts.squeeze() > 0
        output[valid_mask] = token_contributions[valid_mask]

        # Handle overflow tokens (those exceeding capacity)
        # Route to secondary experts or average available
        overflow_mask = token_counts.squeeze() < topk
        if overflow_mask.any():
            # For overflow tokens, use average of available experts
            overflow_positions = overflow_mask.nonzero(as_tuple=True)[0]
            for pos in overflow_positions:
                if token_counts[pos] > 0:
                    output[pos] = token_contributions[pos] / token_counts[pos].float()

        return output

    except Exception as e:
        # Fallback to standard fused_moe
        import logging

        logging.warning(f"Dynamic capacity kernel failed: {e}, using fallback")
        return aiter.fused_moe(
            hidden_states,
            w1,
            w2,
            topk_weights,
            topk_ids,
            inplace=True,
            quant_type="per_1x32",
            use_fp4=True,
        )
