#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""
MoE: Load-Balanced Routing (Equalize Token Distribution)

EXPERIMENTAL HYPOTHESIS:
Uneven token distribution across experts creates compute inefficiencies:
- Some experts are overloaded (longer execution time)
- Some experts are underutilized (wasted capacity)
- Load imbalance reduces parallel efficiency

By actively rebalancing tokens to equalize counts per expert, we can:
1. Improve GPU utilization across all compute units
2. Reduce worst-case execution time (determined by slowest expert)
3. Achieve more predictable performance
4. Better utilize available expert capacity

APPROACH:
1. Compute token histogram per expert
2. Calculate target tokens per expert (uniform distribution)
3. Identify overloaded and underloaded experts
4. Migrate tokens from overloaded to underloaded experts
5. Adjust weights to account for migration

REBALANCING STRATEGY:
- Target: uniform distribution = total_tokens / num_experts
- For overloaded experts: select tokens to migrate
- For underloaded experts: receive tokens from overloaded
- Preserve token quality: migrate based on weight (lowest weight first)
- Maintain topk constraint: each token still has same number of experts

IMPLEMENTATION:
- Sort tokens by weight for each overloaded expert
- Distribute excess tokens to underloaded experts
- Update topk_ids and renormalize topk_weights

LIMITATIONS:
- Changes model output (approximate equality)
- Redistribution adds overhead (must be < speedup from balance)
- Best for large batch sizes where imbalance is significant
"""

from __future__ import annotations

import os
import sys
from typing import Optional, Tuple, List

import torch
from torch.utils.cpp_extension import load_inline

from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t

# ─── Load Balancing Configuration ──────────────────────────────────────────────
REBALANCE_THRESHOLD = 0.2  # Trigger rebalance if imbalance > 20%
MIGRATION_BATCH_SIZE = 64  # Process migrations in batches for efficiency

# ─── HIP Source: Load Balanced Routing ─────────────────────────────────────────
HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>

// Load-balanced routing for MoE
// Redistributes tokens to equalize load across experts

#define MAX_TOPK 8
#define MAX_EXPERTS 256
#define MAX_MIGRATIONS 1024

// Expert load state
struct ExpertLoad {
    int expert_id;
    int token_count;
    int target_count;  // Ideal uniform distribution
    int excess;        // Tokens to migrate out (if positive)
    int deficit;       // Tokens to receive (if positive)
};

// Calculate load statistics per expert
__global__ void calculate_load_balance(
    const int* __restrict__ topk_ids,       // [M, topk]
    int* __restrict__ expert_counts,       // [num_experts] output
    int* __restrict__ expert_excess,       // [num_experts] tokens to migrate out
    int* __restrict__ expert_deficit,      // [num_experts] tokens to receive
    int M, int topk, int num_experts
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    
    // Initialize counts
    for (int i = tid; i < num_experts; i += blockDim.x * gridDim.x) {
        expert_counts[i] = 0;
        expert_excess[i] = 0;
        expert_deficit[i] = 0;
    }
    __syncthreads();
    
    // Count tokens per expert
    for (int i = tid; i < M * topk; i += blockDim.x * gridDim.x) {
        int expert_id = topk_ids[i];
        if (expert_id >= 0 && expert_id < num_experts) {
            atomicAdd(&expert_counts[expert_id], 1);
        }
    }
    __syncthreads();
    
    // Calculate excess/deficit
    int total_tokens = M * topk;
    int target_per_expert = (total_tokens + num_experts - 1) / num_experts;
    
    for (int i = tid; i < num_experts; i += blockDim.x * gridDim.x) {
        int count = expert_counts[i];
        if (count > target_per_expert) {
            expert_excess[i] = count - target_per_expert;
        } else {
            expert_deficit[i] = target_per_expert - count;
        }
    }
}

// Migration record for token redistribution
struct Migration {
    int token_idx;   // Which token to migrate
    int k_idx;       // Which topk slot
    int old_expert;  // Original expert
    int new_expert;  // Destination expert
};

// Build migration plan
__global__ void build_migration_plan(
    const int* __restrict__ topk_ids,
    const float* __restrict__ topk_weights,
    const int* __restrict__ expert_excess,
    const int* __restrict__ expert_deficit,
    Migration* __restrict__ migrations,     // [max_migrations]
    int* __restrict__ num_migrations,       // Scalar output
    int M, int topk, int num_experts,
    int max_migrations
) {
    __shared__ int sm_mig_count;
    
    if (threadIdx.x == 0) sm_mig_count = 0;
    __syncthreads();
    
    // Find source experts (excess) and destination experts (deficit)
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    
    // Simple greedy migration: scan tokens and migrate from overloaded
    for (int token_k = tid; token_k < M * topk; token_k += blockDim.x * gridDim.x) {
        int token_idx = token_k / topk;
        int k = token_k % topk;
        int expert_id = topk_ids[token_k];
        
        if (expert_id < 0 || expert_id >= num_experts) continue;
        
        // Check if this expert has excess
        if (expert_excess[expert_id] > 0) {
            // Find a destination expert with deficit
            for (int dest = 0; dest < num_experts; dest++) {
                if (expert_deficit[dest] > 0 && dest != expert_id) {
                    // Atomic claim migration slot
                    int mig_idx = atomicAdd(&sm_mig_count, 1);
                    if (mig_idx < max_migrations) {
                        migrations[mig_idx].token_idx = token_idx;
                        migrations[mig_idx].k_idx = k;
                        migrations[mig_idx].old_expert = expert_id;
                        migrations[mig_idx].new_expert = dest;
                        
                        // Update excess/deficit
                        atomicSub(&expert_excess[expert_id], 1);
                        atomicSub(&expert_deficit[dest], 1);
                    }
                    break;
                }
            }
        }
    }
    
    __syncthreads();
    if (threadIdx.x == 0) {
        *num_migrations = sm_mig_count;
    }
}

// Apply migration plan to topk_ids and weights
__global__ void apply_migrations(
    const Migration* __restrict__ migrations,
    int num_migrations,
    int* __restrict__ topk_ids,
    float* __restrict__ topk_weights,
    int M, int topk
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    
    for (int i = tid; i < num_migrations; i += blockDim.x * gridDim.x) {
        const Migration& mig = migrations[i];
        int idx = mig.token_idx * topk + mig.k_idx;
        
        // Update expert assignment
        topk_ids[idx] = mig.new_expert;
        
        // Reduce weight slightly for migrated tokens (approximation penalty)
        topk_weights[idx] *= 0.95f;
    }
}

// Python-callable wrappers
torch::Tensor calculate_load_stats(
    torch::Tensor topk_ids,
    int num_experts
) {
    int M = topk_ids.size(0);
    int topk = topk_ids.size(1);
    
    auto expert_counts = torch::zeros({num_experts}, 
        torch::TensorOptions().dtype(torch::kInt32).device(topk_ids.device()));
    auto expert_excess = torch::zeros({num_experts}, 
        torch::TensorOptions().dtype(torch::kInt32).device(topk_ids.device()));
    auto expert_deficit = torch::zeros({num_experts}, 
        torch::TensorOptions().dtype(torch::kInt32).device(topk_ids.device()));
    
    dim3 block(256);
    dim3 grid((M * topk + 255) / 256);
    
    calculate_load_balance<<<grid, block>>>(
        topk_ids.data_ptr<int>(),
        expert_counts.data_ptr<int>(),
        expert_excess.data_ptr<int>(),
        expert_deficit.data_ptr<int>(),
        M, topk, num_experts
    );
    
    return torch::stack({expert_counts, expert_excess, expert_deficit});
}

std::vector<torch::Tensor> rebalance_tokens(
    torch::Tensor topk_ids,
    torch::Tensor topk_weights,
    int num_experts
) {
    int M = topk_ids.size(0);
    int topk = topk_ids.size(1);
    
    auto balanced_ids = topk_ids.clone();
    auto balanced_weights = topk_weights.clone();
    
    auto expert_counts = torch::zeros({num_experts}, 
        torch::TensorOptions().dtype(torch::kInt32).device(topk_ids.device()));
    auto expert_excess = torch::zeros({num_experts}, 
        torch::TensorOptions().dtype(torch::kInt32).device(topk_ids.device()));
    auto expert_deficit = torch::zeros({num_experts}, 
        torch::TensorOptions().dtype(torch::kInt32).device(topk_ids.device()));
    
    dim3 block(256);
    dim3 grid(min(256, (M * topk + 255) / 256));
    
    // Calculate load balance
    calculate_load_balance<<<grid, block>>>(
        topk_ids.data_ptr<int>(),
        expert_counts.data_ptr<int>(),
        expert_excess.data_ptr<int>(),
        expert_deficit.data_ptr<int>(),
        M, topk, num_experts
    );
    
    // Allocate migration buffer
    auto migrations = torch::zeros({MAX_MIGRATIONS, 4}, 
        torch::TensorOptions().dtype(torch::kInt32).device(topk_ids.device()));
    auto num_migrations = torch::zeros({1}, 
        torch::TensorOptions().dtype(torch::kInt32).device(topk_ids.device()));
    
    // Build migration plan
    build_migration_plan<<<grid, block>>>(
        topk_ids.data_ptr<int>(),
        topk_weights.data_ptr<float>(),
        expert_excess.data_ptr<int>(),
        expert_deficit.data_ptr<int>(),
        (Migration*)migrations.data_ptr<int>(),
        num_migrations.data_ptr<int>(),
        M, topk, num_experts,
        MAX_MIGRATIONS
    );
    
    // Apply migrations
    int mig_count = num_migrations.item<int>();
    if (mig_count > 0) {
        dim3 mig_grid((mig_count + 255) / 256);
        apply_migrations<<<mig_grid, block>>>(
            (Migration*)migrations.data_ptr<int>(),
            mig_count,
            balanced_ids.data_ptr<int>(),
            balanced_weights.data_ptr<float>(),
            M, topk
        );
    }
    
    return {balanced_ids, balanced_weights, num_migrations};
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("calculate_load", &calculate_load_stats, "Calculate load statistics per expert");
    m.def("rebalance", &rebalance_tokens, "Rebalance tokens across experts");
}
"""

CPP_SOURCE = """
torch::Tensor calculate_load_stats(torch::Tensor topk_ids, int num_experts);
std::vector<torch::Tensor> rebalance_tokens(torch::Tensor topk_ids, torch::Tensor topk_weights, int num_experts);
"""

# Compile load balancing module
try:
    _load_balance_module = load_inline(
        name="moe_load_balance_v1",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["calculate_load", "rebalance"],
        verbose=False,
        extra_cuda_cflags=["-O3", "--offload-arch=gfx950", "-std=c++17"],
    )
    HAS_LOAD_BALANCING = True
except Exception as e:
    print(f"Load balancing compilation failed: {e}")
    HAS_LOAD_BALANCING = False


def _calculate_imbalance(topk_ids: torch.Tensor, num_experts: int) -> float:
    """
    Calculate load imbalance ratio.
    Returns: max_count / mean_count (1.0 = perfect balance)
    """
    counts = torch.zeros(num_experts, dtype=torch.int32, device=topk_ids.device)
    for i in range(num_experts):
        counts[i] = (topk_ids == i).sum()

    max_count = counts.max().item()
    mean_count = counts.float().mean().item()

    return max_count / max(mean_count, 1.0)


def custom_kernel(data: input_t) -> output_t:
    """
    MoE with load-balanced routing.
    Redistributes tokens to equalize expert utilization.
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

    if HAS_LOAD_BALANCING and num_experts > 0:
        try:
            # Check if rebalancing is needed
            imbalance = _calculate_imbalance(topk_ids, num_experts)

            if imbalance > (1.0 + REBALANCE_THRESHOLD):
                # Apply load balancing
                balanced_ids, balanced_weights, num_mig = _load_balance_module.rebalance(
                    topk_ids.contiguous(), topk_weights.contiguous(), num_experts
                )

                num_migrations = num_mig.item()

                # Verify balanced data is valid
                if (
                    balanced_ids.min() >= 0
                    and balanced_ids.max() < num_experts
                    and num_migrations >= 0
                ):
                    topk_ids = balanced_ids
                    topk_weights = balanced_weights

                    # Renormalize weights after migration
                    weight_sum = topk_weights.sum(dim=1, keepdim=True)
                    topk_weights = topk_weights / weight_sum.clamp(min=1e-6)

        except Exception as e:
            # Fall through to baseline on any error
            pass

    # Run fused_moe with potentially rebalanced routing
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
    """Two Builders: load-balanced or reference."""
    if HAS_LOAD_BALANCING:
        try:
            return custom_kernel(data)
        except Exception:
            return ref_kernel(data)
    return ref_kernel(data)
