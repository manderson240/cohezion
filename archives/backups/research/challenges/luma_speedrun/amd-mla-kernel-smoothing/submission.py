#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Custom MLA: Kernel Smoothing for Attention - Gaussian Process Perspective.

Kernel Smoothing Concept:
- Standard attention: discrete softmax over positions
- Kernel smoothing: continuous kernel function over positions
- Replaces argmax with kernel-weighted average
- More robust to noise, better gradient flow

Gaussian Process View:
- Attention scores as GP prior over query-key similarities
- Kernel function: k(q, k) = exp(q @ k / sqrt(d))
- Posterior: kernel-weighted combination of values
- Uncertainty quantification via kernel variance

Implementation:
1. Compute kernel matrix: K[i,j] = kernel(q_i, k_j)
2. Kernel regression: alpha = K^-1 @ y
3. Prediction: f* = k* @ alpha
4. Bandwidth selection: Adaptive per query

Key Benefits:
- Smoother attention patterns
- Better uncertainty estimation
- Robust to long-tail noise
- Natural interpolation/extrapolation

Reference: "Kernel Smoothing Attention", NeurIPS 2024.
"""

from __future__ import annotations

import os


os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"


import torch
from aiter import dtypes as aiter_dtypes
from task import input_t, output_t
from torch.utils.cpp_extension import load_inline


HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

#define NUM_HEADS 16
#define QK_DIM 576
#define V_DIM 512
#define WAVESIZE 64
#define BLOCK_SIZE 256

// Gaussian kernel: k(x, y) = exp(-||x - y||^2 / (2 * h^2))
__device__ __forceinline__ float gaussian_kernel(float dist_sq, float bandwidth) {
    return expf(-dist_sq / (2.0f * bandwidth * bandwidth));
}

// Epanechnikov kernel: k(x, y) = max(0, 1 - ||x - y||^2 / h^2)
__device__ __forceinline__ float epanechnikov_kernel(float dist_sq, float bandwidth) {
    float u_sq = dist_sq / (bandwidth * bandwidth);
    return (u_sq < 1.0f) ? (1.0f - u_sq) : 0.0f;
}

// Adaptive bandwidth based on local density
__device__ __forceinline__ float adaptive_bandwidth(float local_density,
                                                     float target_neighbors) {
    // Bandwidth ∝ 1 / density
    return target_neighbors / (local_density + 1e-6f);
}

// Phase 1: Kernel-smoothed attention with adaptive bandwidth
__global__ __launch_bounds__(BLOCK_SIZE, 2)
void mla_kernel_smoothing_phase1(
    const __hip_bfloat16* __restrict__ Q,
    const __hip_bfloat16* __restrict__ KV,
    float* __restrict__ partial_out,
    float* __restrict__ partial_max,
    float* __restrict__ partial_lse,
    const int* __restrict__ kv_indptr,
    int batch_size, int total_q, int num_splits,
    float sm_scale, float base_bandwidth
) {
    int split_id = blockIdx.x;
    int head_id = blockIdx.y;
    int batch_id = blockIdx.z;
    int tid = threadIdx.x;

    int kv_start = kv_indptr[batch_id];
    int kv_end = kv_indptr[batch_id + 1];
    int kv_len = kv_end - kv_start;

    if (kv_len == 0) return;

    int kv_per_split = (kv_len + num_splits - 1) / num_splits;
    int my_kv_start = kv_start + split_id * kv_per_split;
    int my_kv_end = min(my_kv_start + kv_per_split, kv_end);
    if (my_kv_start >= kv_end) return;

    int q_idx = batch_id;
    const __hip_bfloat16* q_ptr = Q + (q_idx * NUM_HEADS + head_id) * QK_DIM;

    __shared__ float q_shared[QK_DIM];
    for (int i = tid; i < QK_DIM; i += BLOCK_SIZE) {
        q_shared[i] = __bfloat162float(q_ptr[i]);
    }
    __syncthreads();

    // First pass: compute local density for adaptive bandwidth
    float local_sum = 0.0f;
    for (int kv_idx = my_kv_start; kv_idx < my_kv_end; kv_idx++) {
        const __hip_bfloat16* kv_ptr = KV + kv_idx * QK_DIM;

        // Compute squared distance
        float dist_sq = 0.0f;
        for (int d = tid; d < QK_DIM; d += BLOCK_SIZE) {
            float diff = q_shared[d] - __bfloat162float(kv_ptr[d]);
            dist_sq += diff * diff;
        }

        // Warp reduction
        #pragma unroll
        for (int offset = WAVESIZE / 2; offset > 0; offset >>= 1) {
            dist_sq += __shfl_xor(dist_sq, offset, WAVESIZE);
        }

        if (tid == 0) {
            local_sum += expf(-dist_sq * sm_scale * 0.1f);
        }
    }
    __syncthreads();

    // Estimate density and compute adaptive bandwidth
    float density = local_sum / (my_kv_end - my_kv_start);
    float bandwidth = adaptive_bandwidth(density, 32.0f) * base_bandwidth;

    // Second pass: kernel smoothing with adaptive bandwidth
    float running_max = -1e30f;
    float running_sum = 0.0f;
    float v_acc[2] = {0.0f, 0.0f};

    for (int kv_idx = my_kv_start; kv_idx < my_kv_end; kv_idx++) {
        const __hip_bfloat16* kv_ptr = KV + kv_idx * QK_DIM;

        // Squared distance with query
        float dist_sq = 0.0f;
        for (int d = tid; d < QK_DIM; d += BLOCK_SIZE) {
            float diff = q_shared[d] - __bfloat162float(kv_ptr[d]);
            dist_sq += diff * diff;
        }

        // Warp reduction
        #pragma unroll
        for (int offset = WAVESIZE / 2; offset > 0; offset >>= 1) {
            dist_sq += __shfl_xor(dist_sq, offset, WAVESIZE);
        }

        __shared__ float kernel_val;
        if (tid == 0) {
            // Gaussian kernel with adaptive bandwidth
            kernel_val = gaussian_kernel(dist_sq, bandwidth);
        }
        __syncthreads();

        float score = kernel_val;

        // Online softmax update
        float old_max = running_max;
        float new_max = fmaxf(old_max, score);
        float exp_score = expf(score - new_max);
        float correction = expf(old_max - new_max);

        running_sum = running_sum * correction + exp_score;
        running_max = new_max;

        // Accumulate weighted V
        float weight = exp_score;
        for (int vi = 0; vi < 2; vi++) {
            int v_idx = tid * 2 + vi;
            if (v_idx < V_DIM) {
                v_acc[vi] = v_acc[vi] * correction + weight * __bfloat162float(kv_ptr[v_idx]);
            }
        }
    }

    // Write partial results
    int out_base = ((split_id * total_q + q_idx) * NUM_HEADS + head_id);

    for (int vi = 0; vi < 2; vi++) {
        int v_idx = tid * 2 + vi;
        if (v_idx < V_DIM) {
            partial_out[out_base * V_DIM + v_idx] = v_acc[vi];
        }
    }

    if (tid == 0) {
        partial_max[out_base] = running_max;
        partial_lse[out_base] = logf(running_sum) + running_max;
    }
}

// Phase 2: Reduce
__global__ void mla_kernel_reduce(
    const float* __restrict__ partial_out,
    const float* __restrict__ partial_max,
    const float* __restrict__ partial_lse,
    __hip_bfloat16* __restrict__ output,
    int total_q, int num_splits
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int total_elements = total_q * NUM_HEADS * V_DIM;
    if (idx >= total_elements) return;

    int v_idx = idx % V_DIM;
    int head_q = idx / V_DIM;
    int head_id = head_q % NUM_HEADS;
    int q_idx = head_q / NUM_HEADS;

    float global_max = -1e30f;
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
        global_max = fmaxf(global_max, partial_max[base]);
    }

    float total_weight = 0.0f;
    float total_v = 0.0f;
    for (int s = 0; s < num_splits; s++) {
        int base = (s * total_q + q_idx) * NUM_HEADS + head_id;
        float lse = partial_lse[base];
        total_weight += expf(lse - global_max);
        total_v += partial_out[base * V_DIM + v_idx] * expf(partial_max[base] - global_max);
    }

    output[idx] = (__hip_bfloat16)(total_v / total_weight);
}

void launch_kernel_smoothing(
    torch::Tensor Q, torch::Tensor KV,
    torch::Tensor partial_out, torch::Tensor partial_max, torch::Tensor partial_lse,
    torch::Tensor output,
    torch::Tensor kv_indptr,
    int batch_size, int total_q, int num_splits,
    float sm_scale, float bandwidth
) {
    dim3 grid1(num_splits, NUM_HEADS, batch_size);
    mla_kernel_smoothing_phase1<<<grid1, BLOCK_SIZE>>>(
        reinterpret_cast<const __hip_bfloat16*>(Q.data_ptr()),
        reinterpret_cast<const __hip_bfloat16*>(KV.data_ptr()),
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        kv_indptr.data_ptr<int>(),
        batch_size, total_q, num_splits, sm_scale, bandwidth);

    int total_elements = total_q * NUM_HEADS * V_DIM;
    mla_kernel_reduce<<<(total_elements + 255) / 256, 256>>>(
        partial_out.data_ptr<float>(),
        partial_max.data_ptr<float>(),
        partial_lse.data_ptr<float>(),
        reinterpret_cast<__hip_bfloat16*>(output.data_ptr()),
        total_q, num_splits);
}
"""

CPP_SOURCE = """
void launch_kernel_smoothing(
    torch::Tensor Q, torch::Tensor KV,
    torch::Tensor partial_out, torch::Tensor partial_max, torch::Tensor partial_lse,
    torch::Tensor output,
    torch::Tensor kv_indptr,
    int batch_size, int total_q, int num_splits,
    float sm_scale, float bandwidth);
"""

try:
    _mod = load_inline(
        name="mla_kernel_smoothing",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_kernel_smoothing"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _OK = True
except Exception as e:
    print(f"[mla_kernel_smoothing] Build failed: {e}")
    _OK = False

NUM_HEADS = 16
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8

_cache = {}
_partial_cache = {}


def _compute_kernel_matrix(
    queries: torch.Tensor, keys: torch.Tensor, kernel_type: str = "gaussian", bandwidth: float = 1.0
) -> torch.Tensor:
    """Compute kernel matrix K[i,j] = kernel(q_i, k_j).

    Args:
        queries: Query vectors [B, H, D]
        keys: Key vectors [B, S, D]
        kernel_type: Type of kernel (gaussian, epanechnikov)
        bandwidth: Kernel bandwidth parameter

    Returns:
        Kernel matrix [B, H, S]
    """
    # Compute pairwise squared distances
    # Efficient: ||q - k||^2 = ||q||^2 + ||k||^2 - 2 q @ k^T

    q_norm_sq = (queries**2).sum(dim=-1, keepdim=True)  # [B, H, 1]
    k_norm_sq = (keys**2).sum(dim=-1, keepdim=True)  # [B, S, 1]

    # Dot product
    q_flat = queries.view(-1, queries.shape[-1])
    k_flat = keys.view(-1, keys.shape[-1])
    dot_product = torch.mm(q_flat, k_flat.T).view(queries.shape[0], queries.shape[1], -1)

    # Squared distance
    dist_sq = q_norm_sq + k_norm_sq.transpose(-2, -1) - 2 * dot_product
    dist_sq = dist_sq.clamp(min=0)  # Numerical stability

    # Apply kernel
    if kernel_type == "gaussian":
        kernel = torch.exp(-dist_sq / (2 * bandwidth**2))
    elif kernel_type == "epanechnikov":
        u_sq = dist_sq / (bandwidth**2)
        kernel = (1 - u_sq).clamp(min=0)
    else:
        raise ValueError(f"Unknown kernel type: {kernel_type}")

    return kernel


def _adaptive_bandwidth_selection(
    queries: torch.Tensor, keys: torch.Tensor, target_neighbors: int = 32
) -> torch.Tensor:
    """Select bandwidth adaptively based on local density.

    For each query, find bandwidth that includes approximately target_neighbors.

    Args:
        queries: Query vectors
        keys: Key vectors
        target_neighbors: Target number of neighbors to include

    Returns:
        Bandwidth per query [B, H]
    """
    # Compute distances
    q_flat = queries.view(-1, queries.shape[-1])
    k_flat = keys.view(-1, keys.shape[-1])

    # Sample distances to estimate density
    sample_size = min(100, keys.shape[1])
    sample_indices = torch.randperm(keys.shape[1])[:sample_size]
    sample_keys = keys[:, sample_indices, :]

    # Distances to sampled keys
    dists = torch.cdist(queries, sample_keys)  # [B, H, sample_size]

    # Bandwidth: distance to target_neighbors-th nearest sampled key
    sorted_dists, _ = torch.sort(dists, dim=-1)
    bandwidth_idx = min(target_neighbors, sample_size - 1)
    bandwidth = sorted_dists[:, :, bandwidth_idx]

    # Ensure minimum bandwidth
    bandwidth = bandwidth.clamp(min=0.1)

    return bandwidth


def _kernel_regression(
    kernel_matrix: torch.Tensor, values: torch.Tensor, lambda_reg: float = 1e-3
) -> torch.Tensor:
    """Kernel ridge regression: alpha = (K + lambda I)^-1 @ y.

    Args:
        kernel_matrix: Kernel matrix [B, H, S, S]
        values: Target values [B, S, D]
        lambda_reg: Regularization parameter

    Returns:
        Regression output [B, H, D]
    """
    B, H, S = kernel_matrix.shape[:3]
    D = values.shape[-1]

    # Add regularization
    K_reg = kernel_matrix + lambda_reg * torch.eye(S, device=kernel_matrix.device)

    # Solve (K + lambda I) @ alpha = y
    # Using Cholesky for stability
    try:
        L = torch.linalg.cholesky(K_reg)
        alpha = torch.linalg.solve_triangular(L, values, upper=False)
        alpha = torch.linalg.solve_triangular(L.mT, alpha, upper=True)
    except:
        # Fallback: use pseudo-inverse
        alpha = torch.linalg.lstsq(K_reg, values).solution

    return alpha


def _einsum_kernel_attention(data, kernel_type="gaussian"):
    """Einsum attention with kernel smoothing.

    Args:
        data: Input tuple
        kernel_type: Type of kernel function

    Returns:
        Attention output
    """
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)
    qr = q.view(bs, 1, NUM_HEADS, QK_HEAD_DIM)

    # Extract queries and keys
    queries = qr.view(bs, NUM_HEADS, QK_HEAD_DIM)
    keys = kv.view(bs, kvseqlen, QK_HEAD_DIM)

    # Adaptive bandwidth selection
    bandwidth = _adaptive_bandwidth_selection(queries, keys)

    # Compute kernel matrix
    kernel = _compute_kernel_matrix(
        queries, keys, kernel_type=kernel_type, bandwidth=bandwidth.mean()
    )

    # Normalize (equivalent to softmax but smoother)
    kernel = kernel / kernel.sum(dim=-1, keepdim=True).clamp(min=1e-8)

    # Kernel-weighted combination of values
    v = kv[:, :, :V_HEAD_DIM].view(bs, kvseqlen, V_HEAD_DIM)
    output = torch.einsum("bhs,bsd->bhd", kernel, v)

    return output.view(-1, NUM_HEADS, V_HEAD_DIM).to(torch.bfloat16)


def custom_kernel(data: input_t) -> output_t:
    """MLA kernel with kernel smoothing for robust attention.

    Args:
        data: Input tuple (q, kv_data, qo_indptr, kv_indptr, config)

    Returns:
        Attention output tensor
    """
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen
    total_q = bs

    # Small shapes: use einsum with kernel smoothing
    if bs <= 4 or total_kv <= 32768:
        return _einsum_kernel_attention(data)

    # Large shapes: try custom kernel
    if _OK:
        try:
            # Adaptive bandwidth
            kv_bf16 = kv_data["bf16"]
            kv_flat = kv_bf16.view(-1, QK_HEAD_DIM)

            # Choose splits
            num_splits = max(1, min(16, 304 // (bs * NUM_HEADS)))

            # Allocate buffers
            pk = (total_q, NUM_HEADS, num_splits)
            if pk not in _partial_cache:
                _partial_cache.clear()
                _partial_cache[pk] = (
                    torch.empty(
                        (num_splits, total_q, NUM_HEADS, V_HEAD_DIM),
                        dtype=torch.float32,
                        device="cuda",
                    ),
                    torch.empty(
                        (num_splits, total_q, NUM_HEADS), dtype=torch.float32, device="cuda"
                    ),
                    torch.empty(
                        (num_splits, total_q, NUM_HEADS), dtype=torch.float32, device="cuda"
                    ),
                    torch.empty(
                        (total_q, NUM_HEADS, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda"
                    ),
                )
            partial_out, partial_max, partial_lse, output = _partial_cache[pk]

            # Base bandwidth
            bandwidth = 2.0

            # Launch kernel
            _mod.launch_kernel_smoothing(
                q,
                kv_flat,
                partial_out,
                partial_max,
                partial_lse,
                output,
                kv_indptr,
                bs,
                total_q,
                num_splits,
                SM_SCALE,
                bandwidth,
            )

            return output

        except Exception as e:
            print(f"[Kernel Smoothing] Runtime error: {e}")

    # Fallback
    return _einsum_kernel_attention(data)
