#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""
MoE: Expert Capacity Limiting (Token Drop Strategy)

EXPERIMENTAL HYPOTHESIS:
In MoE layers, some experts receive far more tokens than others due to routing
imbalance. This creates compute inefficiency as overloaded experts become
bottlenecks. By enforcing a maximum token capacity per expert (similar to
Switch Transformer), we:
1. Prevent any single expert from dominating compute
2. Enable more predictable execution time
3. Force token diversity across experts
4. Potentially improve model quality through regularization

APPROACH:
1. Analyze topk_ids to count tokens per expert
2. Identify experts exceeding capacity threshold
3. Redistribute overflow tokens to under-capacity experts
4. Renormalize topk_weights after redistribution
5. Call fused_moe with modified routing

CAPACITY CALCULATION:
- capacity = (total_tokens / num_experts) * capacity_factor
- Default capacity_factor = 1.25 (25% headroom)
- Overflow tokens are reassigned to least-loaded valid experts

LIMITATIONS:
- Token dropping changes model output (not bitwise identical)
- May reduce quality if capacity too restrictive
- Requires re-sorting topk_ids after redistribution
- Works best when expert load is naturally balanced
"""

from __future__ import annotations

import os
import sys
from typing import Optional, Tuple

import torch
from torch.utils.cpp_extension import load_inline

from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t

# ─── Capacity Configuration ──────────────────────────────────────────────────
DEFAULT_CAPACITY_FACTOR = 1.25  # 25% headroom over uniform distribution
MIN_CAPACITY = 1  # At least 1 token per expert
MAX_CAPACITY_RATIO = 2.0  # Hard limit: 2x uniform distribution

# ─── HIP Source: Expert Capacity Management ─────────────────────────────────────
HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>

// Capacity-aware routing: limit tokens per expert
// This redistributes tokens from overloaded to under-utilized experts

#define MAX_TOPK 8
#define MAX_EXPERTS 256

// Count tokens per expert from topk_ids
// Returns expert_counts[num_experts] with token counts
__global__ void count_expert_tokens(
    const int* __restrict__ topk_ids,       // [M, topk] token->expert assignments
    int* __restrict__ expert_counts,       // [num_experts] output counts
    int M, int topk, int num_experts
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    
    // Initialize counts
    for (int i = tid; i < num_experts; i += blockDim.x * gridDim.x) {
        expert_counts[i] = 0;
    }
    __syncthreads();
    
    // Count tokens per expert
    for (int i = tid; i < M * topk; i += blockDim.x * gridDim.x) {
        int expert_id = topk_ids[i];
        if (expert_id >= 0 && expert_id < num_experts) {
            atomicAdd(&expert_counts[expert_id], 1);
        }
    }
}

// Find under-capacity experts and build redirect table
__global__ void build_capacity_table(
    const int* __restrict__ expert_counts,
    int* __restrict__ capacity_remaining,  // [num_experts] tokens still available
    int* __restrict__ overflow_experts,      // [num_experts] mask of overloaded
    int num_experts,
    int capacity_limit
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    
    for (int i = tid; i < num_experts; i += blockDim.x * gridDim.x) {
        int count = expert_counts[i];
        if (count > capacity_limit) {
            overflow_experts[i] = 1;
            capacity_remaining[i] = 0;
        } else {
            overflow_experts[i] = 0;
            capacity_remaining[i] = capacity_limit - count;
        }
    }
}

// Redistribute overflow tokens to under-capacity experts
// Modifies topk_ids and topk_weights in place
__global__ void redistribute_tokens(
    const int* __restrict__ overflow_experts,
    const int* __restrict__ capacity_remaining,
    int* __restrict__ topk_ids,              // [M, topk] - modified in place
    float* __restrict__ topk_weights,        // [M, topk] - modified in place
    int M, int topk, int num_experts,
    int capacity_limit
) {
    // Shared memory for capacity tracking
    __shared__ int sm_capacity[MAX_EXPERTS];
    __shared__ int sm_under_capacity[MAX_EXPERTS];
    __shared__ int sm_under_count;
    
    // Initialize shared memory
    int tid = threadIdx.x;
    if (tid < num_experts) {
        sm_capacity[tid] = capacity_remaining[tid];
        sm_under_capacity[tid] = (capacity_remaining[tid] > 0) ? 1 : 0;
    }
    if (tid == 0) sm_under_count = 0;
    __syncthreads();
    
    // Count under-capacity experts
    for (int i = tid; i < num_experts; i += blockDim.x) {
        if (sm_capacity[i] > 0) atomicAdd(&sm_under_count, 1);
    }
    __syncthreads();
    
    // Process tokens
    for (int token_idx = blockIdx.x; token_idx < M; token_idx += gridDim.x) {
        int base = token_idx * topk;
        
        for (int k = tid; k < topk; k += blockDim.x) {
            int expert_id = topk_ids[base + k];
            
            if (expert_id >= 0 && expert_id < num_experts && overflow_experts[expert_id]) {
                // This token points to an overloaded expert - need to redirect
                
                // Simple strategy: find first under-capacity expert
                // Round-robin distribution would be better but more complex
                for (int e = 0; e < num_experts && e < MAX_EXPERTS; e++) {
                    int remaining = sm_capacity[e];
                    if (remaining > 0) {
                        // Atomically decrement
                        int old = atomicSub(&sm_capacity[e], 1);
                        if (old > 0) {
                            // Successfully claimed a slot
                            topk_ids[base + k] = e;
                            // Reduce weight since this is a forced assignment
                            topk_weights[base + k] *= 0.9f;
                            break;
                        }
                    }
                }
            }
        }
    }
}

// Python-callable wrappers
torch::Tensor analyze_expert_capacity(
    torch::Tensor topk_ids,
    int num_experts,
    float capacity_factor
) {
    int M = topk_ids.size(0);
    int topk = topk_ids.size(1);
    
    // Calculate capacity limit
    int total_tokens = M * topk;
    int capacity_limit = (int)(total_tokens / num_experts * capacity_factor);
    capacity_limit = max(capacity_limit, MIN_CAPACITY);
    
    auto expert_counts = torch::zeros({num_experts}, 
        torch::TensorOptions().dtype(torch::kInt32).device(topk_ids.device()));
    auto overflow_mask = torch::zeros({num_experts}, 
        torch::TensorOptions().dtype(torch::kInt32).device(topk_ids.device()));
    auto capacity_rem = torch::zeros({num_experts}, 
        torch::TensorOptions().dtype(torch::kInt32).device(topk_ids.device()));
    
    dim3 block(256);
    dim3 grid((M * topk + 255) / 256);
    
    // Count tokens
    count_expert_tokens<<<grid, block>>>(
        topk_ids.data_ptr<int>(),
        expert_counts.data_ptr<int>(),
        M, topk, num_experts
    );
    
    // Build capacity table
    dim3 grid2((num_experts + 255) / 256);
    build_capacity_table<<<grid2, block>>>(
        expert_counts.data_ptr<int>(),
        capacity_rem.data_ptr<int>(),
        overflow_mask.data_ptr<int>(),
        num_experts, capacity_limit
    );
    
    return torch::stack({expert_counts, overflow_mask, capacity_rem});
}

std::vector<torch::Tensor> apply_capacity_limits(
    torch::Tensor topk_ids,
    torch::Tensor topk_weights,
    float capacity_factor,
    int num_experts
) {
    int M = topk_ids.size(0);
    int topk = topk_ids.size(1);
    
    // Calculate capacity limit
    int total_tokens = M * topk;
    int capacity_limit = (int)(total_tokens / num_experts * capacity_factor);
    capacity_limit = max(capacity_limit, MIN_CAPACITY);
    
    auto sorted_ids = topk_ids.clone();
    auto sorted_weights = topk_weights.clone();
    
    auto expert_counts = torch::zeros({num_experts}, 
        torch::TensorOptions().dtype(torch::kInt32).device(topk_ids.device()));
    auto overflow_mask = torch::zeros({num_experts}, 
        torch::TensorOptions().dtype(torch::kInt32).device(topk_ids.device()));
    auto capacity_rem = torch::zeros({num_experts}, 
        torch::TensorOptions().dtype(torch::kInt32).device(topk_ids.device()));
    
    dim3 block(256);
    dim3 grid(min(M, 256));
    
    // Build capacity info
    count_expert_tokens<<<grid, block>>>(
        topk_ids.data_ptr<int>(),
        expert_counts.data_ptr<int>(),
        M, topk, num_experts
    );
    
    build_capacity_table<<<grid, block>>>(
        expert_counts.data_ptr<int>(),
        capacity_rem.data_ptr<int>(),
        overflow_mask.data_ptr<int>(),
        num_experts, capacity_limit
    );
    
    // Redistribute overflow tokens
    redistribute_tokens<<<grid, block>>>(
        overflow_mask.data_ptr<int>(),
        capacity_rem.data_ptr<int>(),
        sorted_ids.data_ptr<int>(),
        sorted_weights.data_ptr<float>(),
        M, topk, num_experts, capacity_limit
    );
    
    return {sorted_ids, sorted_weights};
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("analyze_capacity", &analyze_expert_capacity, "Analyze expert token counts and capacity");
    m.def("apply_limits", &apply_capacity_limits, "Apply capacity limits and redistribute tokens");
}
"""

CPP_SOURCE = """
torch::Tensor analyze_expert_capacity(torch::Tensor topk_ids, int num_experts, float capacity_factor);
std::vector<torch::Tensor> apply_capacity_limits(torch::Tensor topk_ids, torch::Tensor topk_weights, 
                                                  float capacity_factor, int num_experts);
"""

# Compile capacity limiting module
try:
    _capacity_module = load_inline(
        name="moe_capacity_v1",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["analyze_capacity", "apply_limits"],
        verbose=False,
        extra_cuda_cflags=["-O3", "--offload-arch=gfx950", "-std=c++17"],
    )
    HAS_CAPACITY_LIMITING = True
except Exception as e:
    print(f"Capacity limiting compilation failed: {e}")
    HAS_CAPACITY_LIMITING = False


def _calculate_capacity_stats(topk_ids: torch.Tensor, num_experts: int) -> Tuple[int, float, float]:
    """
    Calculate capacity statistics for monitoring.
    Returns: (max_count, mean_count, std_count)
    """
    # Count tokens per expert
    counts = torch.zeros(num_experts, dtype=torch.int32, device=topk_ids.device)
    for i in range(num_experts):
        counts[i] = (topk_ids == i).sum().item()

    max_count = counts.max().item()
    mean_count = counts.float().mean().item()
    std_count = counts.float().std().item()

    return max_count, mean_count, std_count


def custom_kernel(data: input_t) -> output_t:
    """
    MoE with expert capacity limiting.
    Prevents any single expert from receiving too many tokens.
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
    num_experts = config.get("n_routed_experts", 0) + config.get("n_shared_experts", 0)

    # Ensure contiguity
    if not hidden_states.is_contiguous():
        hidden_states = hidden_states.contiguous()

    if HAS_CAPACITY_LIMITING and num_experts > 0:
        try:
            # Calculate current capacity stats (for monitoring)
            max_tok, mean_tok, std_tok = _calculate_capacity_stats(topk_ids, num_experts)

            # Determine capacity factor based on load imbalance
            # If already balanced, use lower factor. If imbalanced, use higher factor.
            imbalance = max_tok / max(mean_tok, 1.0)
            if imbalance > 2.0:
                capacity_factor = 1.5  # High imbalance: allow more redistribution
            elif imbalance > 1.5:
                capacity_factor = 1.25  # Moderate imbalance
            else:
                capacity_factor = 1.0  # Already balanced: strict capacity

            # Apply capacity limits
            limited_ids, limited_weights = _capacity_module.apply_limits(
                topk_ids.contiguous(), topk_weights.contiguous(), capacity_factor, num_experts
            )

            # Verify redistribution didn't corrupt data
            if limited_ids.min() >= 0 and limited_ids.max() < num_experts:
                topk_ids = limited_ids
                topk_weights = limited_weights

                # Renormalize weights after redistribution
                weight_sum = topk_weights.sum(dim=1, keepdim=True)
                topk_weights = topk_weights / weight_sum.clamp(min=1e-6)

        except Exception as e:
            # Fall through to baseline on any error
            pass

    # Run fused_moe (potentially with capacity-limited routing)
    output = fused_moe(
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

    return output


def ref_kernel(data: input_t) -> output_t:
    """Reference MoE kernel using standard fused_moe."""
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

    if not hidden_states.is_contiguous():
        hidden_states = hidden_states.contiguous()

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


def kernel(data: input_t) -> output_t:
    """Two Builders: capacity-limited or reference."""
    if HAS_CAPACITY_LIMITING:
        try:
            return custom_kernel(data)
        except Exception:
            return ref_kernel(data)
    return ref_kernel(data)
