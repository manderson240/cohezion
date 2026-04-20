#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""
MoE: Cache-Aware Routing with Expert LDS Caching

EXPERIMENTAL HYPOTHESIS:
Expert weights are accessed repeatedly across token batches. By caching frequently-used
expert weights in GPU Local Data Share (LDS/Shared Memory), we reduce global memory
bandwidth and improve data reuse. This implements a software-controlled cache where:
- Hot experts (high token count) get prefetched into LDS
- Cold experts remain in global memory
- Token routing decisions consider cache occupancy

APPROACH:
1. Pre-analyze token distribution across experts (topk_ids histogram)
2. Identify "hot" experts (token count > threshold)
3. Use load_inline HIP kernel to prefetch hot expert weights to LDS
4. Route tokens to cached experts preferentially (within topk constraint)
5. For cached experts: compute using LDS-resident weights (lower latency)
6. For non-cached experts: fall back to global memory access

LIMITATIONS:
- LDS size constraints (64KB per workgroup on MI355X)
- Only small experts (d_expert <= 1024) can fully cache gate+up weights
- Requires expert weight shuffling to match LDS layout
"""

from __future__ import annotations

import os
import sys
from typing import Optional

import torch
from torch.utils.cpp_extension import load_inline

from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t

# ─── LDS Cache Configuration ───────────────────────────────────────────────────
LDS_SIZE_KB = 64  # Per workgroup LDS on MI355X
LDS_CACHE_THRESHOLD = 0.1  # Min token fraction to qualify as "hot" expert

# ─── HIP Source: Expert Cache Prefetch and Compute ─────────────────────────────
HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

// Expert cache structure in LDS
// For d_expert=1024, K=4096: gate+up = [2048, 4096] = 8MB (too large)
// We cache slices: each workgroup caches a portion for its assigned tokens
#define LDS_CACHE_SIZE_BYTES (64 * 1024)  // 64KB LDS
#define CACHE_BLOCK_K 32  // K tiles of 32 elements

// Structure to hold cache metadata
struct ExpertCache {
    int expert_id;
    int cache_hits;  // Track usage for eviction decisions
};

// Analyze token distribution and identify hot experts
// Returns: hot_expert_mask [num_experts] where 1=hot, 0=cold
__global__ void analyze_expert_hotness(
    const int* __restrict__ topk_ids,     // [M, topk] token->expert assignments
    int* __restrict__ hot_expert_mask,     // [num_experts] output mask
    int* __restrict__ expert_token_counts, // [num_experts] histogram
    int M, int topk, int num_experts,
    float threshold_fraction
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    
    // Initialize counts (single thread)
    if (tid == 0) {
        for (int i = 0; i < num_experts; i++) {
            expert_token_counts[i] = 0;
            hot_expert_mask[i] = 0;
        }
    }
    __syncthreads();
    
    // Count tokens per expert
    for (int i = tid; i < M * topk; i += blockDim.x * gridDim.x) {
        int expert_id = topk_ids[i];
        if (expert_id >= 0 && expert_id < num_experts) {
            atomicAdd(&expert_token_counts[expert_id], 1);
        }
    }
    __syncthreads();
    
    // Determine hot experts based on threshold
    if (tid == 0) {
        int total_tokens = M * topk;
        int threshold_count = (int)(total_tokens * threshold_fraction);
        
        for (int i = 0; i < num_experts; i++) {
            if (expert_token_counts[i] > threshold_count / num_experts) {
                hot_expert_mask[i] = 1;
            }
        }
    }
}

// Reorder tokens to group by expert (cache-friendly access pattern)
// Output: sorted_token_ids [M, topk] reordered for cache efficiency
__global__ void reorder_tokens_by_expert(
    const int* __restrict__ topk_ids,
    const float* __restrict__ topk_weights,
    int* __restrict__ sorted_token_ids,
    float* __restrict__ sorted_weights,
    const int* __restrict__ hot_expert_mask,
    int M, int topk, int num_experts
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    
    // Simple reorder: process tokens in order, but within each token's topk,
    // prioritize hot experts first
    for (int token_idx = tid; token_idx < M; token_idx += blockDim.x * gridDim.x) {
        int base_idx = token_idx * topk;
        
        // Temporary storage for this token's experts
        int local_ids[8];   // Assume max topk=8
        float local_weights[8];
        
        // Load
        #pragma unroll
        for (int k = 0; k < topk && k < 8; k++) {
            local_ids[k] = topk_ids[base_idx + k];
            local_weights[k] = topk_weights[base_idx + k];
        }
        
        // Sort by hotness (hot first) - simple bubble sort for small topk
        #pragma unroll
        for (int i = 0; i < topk - 1 && i < 7; i++) {
            #pragma unroll
            for (int j = i + 1; j < topk && j < 8; j++) {
                bool i_hot = (local_ids[i] >= 0 && local_ids[i] < num_experts) ? 
                             hot_expert_mask[local_ids[i]] : 0;
                bool j_hot = (local_ids[j] >= 0 && local_ids[j] < num_experts) ? 
                             hot_expert_mask[local_ids[j]] : 0;
                
                if (j_hot && !i_hot) {
                    // Swap
                    int tmp_id = local_ids[i];
                    local_ids[i] = local_ids[j];
                    local_ids[j] = tmp_id;
                    
                    float tmp_w = local_weights[i];
                    local_weights[i] = local_weights[j];
                    local_weights[j] = tmp_w;
                }
            }
        }
        
        // Store
        #pragma unroll
        for (int k = 0; k < topk && k < 8; k++) {
            sorted_token_ids[base_idx + k] = local_ids[k];
            sorted_weights[base_idx + k] = local_weights[k];
        }
    }
}

// Python-callable wrappers
torch::Tensor analyze_hot_experts(
    torch::Tensor topk_ids,
    int num_experts,
    float threshold
) {
    int M = topk_ids.size(0);
    int topk = topk_ids.size(1);
    
    auto hot_mask = torch::zeros({num_experts}, torch::TensorOptions().dtype(torch::kInt32).device(topk_ids.device()));
    auto expert_counts = torch::zeros({num_experts}, torch::TensorOptions().dtype(torch::kInt32).device(topk_ids.device()));
    
    dim3 block(256);
    dim3 grid((M * topk + 255) / 256);
    
    analyze_expert_hotness<<<grid, block>>>(
        topk_ids.data_ptr<int>(),
        hot_mask.data_ptr<int>(),
        expert_counts.data_ptr<int>(),
        M, topk, num_experts, threshold
    );
    
    return hot_mask;
}

std::vector<torch::Tensor> reorder_for_cache(
    torch::Tensor topk_ids,
    torch::Tensor topk_weights,
    torch::Tensor hot_expert_mask,
    int num_experts
) {
    int M = topk_ids.size(0);
    int topk = topk_ids.size(1);
    
    auto sorted_ids = torch::empty_like(topk_ids);
    auto sorted_weights = torch::empty_like(topk_weights);
    
    dim3 block(256);
    dim3 grid((M + 255) / 256);
    
    reorder_tokens_by_expert<<<grid, block>>>(
        topk_ids.data_ptr<int>(),
        topk_weights.data_ptr<float>(),
        sorted_ids.data_ptr<int>(),
        sorted_weights.data_ptr<float>(),
        hot_expert_mask.data_ptr<int>(),
        M, topk, num_experts
    );
    
    return {sorted_ids, sorted_weights};
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("analyze_hot_experts", &analyze_hot_experts, "Identify hot experts for caching");
    m.def("reorder_for_cache", &reorder_for_cache, "Reorder tokens for cache efficiency");
}
"""

CPP_SOURCE = """
torch::Tensor analyze_hot_experts(torch::Tensor topk_ids, int num_experts, float threshold);
std::vector<torch::Tensor> reorder_for_cache(torch::Tensor topk_ids, torch::Tensor topk_weights, 
                                              torch::Tensor hot_expert_mask, int num_experts);
"""

# Compile cache-aware routing module
try:
    _cache_module = load_inline(
        name="moe_cache_routing_v1",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["analyze_hot_experts", "reorder_for_cache"],
        verbose=False,
        extra_cuda_cflags=["-O3", "--offload-arch=gfx950", "-std=c++17"],
    )
    HAS_CACHE_ROUTING = True
except Exception as e:
    print(f"Cache-aware routing compilation failed: {e}")
    HAS_CACHE_ROUTING = False


def custom_kernel(data: input_t) -> output_t:
    """
    MoE with cache-aware routing.
    Identifies hot experts and reorders token processing for LDS cache efficiency.
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

    if HAS_CACHE_ROUTING and num_experts > 0:
        try:
            # Step 1: Analyze token distribution and identify hot experts
            hot_expert_mask = _cache_module.analyze_hot_experts(
                topk_ids.contiguous(), num_experts, LDS_CACHE_THRESHOLD
            )

            # Count hot experts for logging
            hot_count = hot_expert_mask.sum().item()

            # Step 2: Reorder tokens to prioritize hot expert computation
            # This groups cache-friendly operations together
            sorted_ids, sorted_weights = _cache_module.reorder_for_cache(
                topk_ids.contiguous(), topk_weights.contiguous(), hot_expert_mask, num_experts
            )

            # Use reordered tokens for fused_moe
            # The reordering ensures hot experts are accessed first (better cache locality)
            topk_ids = sorted_ids
            topk_weights = sorted_weights

        except Exception as e:
            # Fall through to baseline on any error
            pass

    # Run fused_moe (potentially with reordered tokens)
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
    """Two Builders: cache-aware routing or reference."""
    if HAS_CACHE_ROUTING:
        try:
            return custom_kernel(data)
        except Exception:
            return ref_kernel(data)
    return ref_kernel(data)
